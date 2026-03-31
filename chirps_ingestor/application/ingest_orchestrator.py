import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from ..domain.models import CHIRPSFileInfo, Temporality, DataStatus
from ..domain.ports import FileListingPort, CatalogPort, GeoClipperPort, StoragePort
from ..countries.base_country import BaseCountry
from .batch_processor import BatchProcessor

logger = logging.getLogger(__name__)


class IngestOrchestrator:
    """
    Orquesta el pipeline completo de ingesta:
    1. Scraping paralelo — cada scraper consulta real + prelim de su temporalidad
    2. Deduplicación: si un filename existe en real Y prelim, REAL gana
    3. Detección de upgrades: archivos que estaban en prelim y ya tienen versión real
    4. Comparación con BD por país y temporalidad
    5. Procesamiento en lotes de 6
    6. Registro en catálogo
    """

    def __init__(
        self,
        scrapers: dict[str, FileListingPort],
        catalog: CatalogPort,
        clipper: GeoClipperPort,
        storage: StoragePort,
        batch_size: int = 6,
    ):
        # scrapers = {"daily": DailyScraper(), "pentad": PentadScraper(), ...}
        self._scrapers = scrapers
        self._catalog = catalog
        self._clipper = clipper
        self._storage = storage
        self._batch_processor = BatchProcessor(clipper, storage, catalog, batch_size)

    def run(
        self,
        countries: list[BaseCountry],
        temporalities: list[str] | None = None,
    ):
        logger.info(f"Iniciando ingesta para {len(countries)} países")

        # PASO 1: Scraping paralelo
        logger.info("Obteniendo lista de archivos disponibles en UCSB...")
        available_files = self._scrape_all_parallel(temporalities)
        logger.info(f"Total archivos detectados: {len(available_files)}")

        # PASO 2: Deduplicar — si un mismo filename tiene REAL y PRELIM, queda solo REAL
        available_files = self._deduplicate_prefer_real(available_files)
        logger.info(f"Tras deduplicación: {len(available_files)} archivos únicos")

        # PASO 3 y 4: Por cada país, detectar upgrades y archivos nuevos
        for country in countries:
            self._process_country(country, available_files)

        logger.info("Ingesta completada.")

    def _scrape_all_parallel(
        self, temporalities: list[str] | None
    ) -> list[CHIRPSFileInfo]:
        """
        Lanza los scrapers en paralelo con ThreadPoolExecutor.
        Cada scraper ya maneja internamente real + prelim.
        Para daily, lanza una tarea por cada año a revisar.
        """
        target_temps = (
            [Temporality(t) for t in temporalities]
            if temporalities
            else list(Temporality)
        )

        current_year = date.today().year
        all_files: list[CHIRPSFileInfo] = []

        tasks: list[tuple[Temporality, int | None]] = []
        for temp in target_temps:
            if temp == Temporality.DAILY:
                tasks.append((temp, current_year))
                tasks.append((temp, current_year - 1))
            else:
                tasks.append((temp, None))

        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            future_map = {
                executor.submit(
                    self._scrapers[temp.value].get_available_files, temp.value, year
                ): (temp, year)
                for temp, year in tasks
            }
            for future in as_completed(future_map):
                temp, year = future_map[future]
                label = f"{temp.value}/{year}" if year else temp.value
                try:
                    files = future.result()
                    all_files.extend(files)
                    real_count   = sum(1 for f in files if f.status == DataStatus.REAL)
                    prelim_count = sum(1 for f in files if f.status == DataStatus.PRELIM)
                    logger.info(f"  [{label}] {real_count} real + {prelim_count} prelim")
                except Exception as e:
                    logger.error(f"  Error scraping [{label}]: {e}")

        return all_files

    def _deduplicate_prefer_real(
        self, files: list[CHIRPSFileInfo]
    ) -> list[CHIRPSFileInfo]:
        """
        Si un mismo filename aparece en real y prelim, conserva solo el REAL.
        Clave de deduplicación: (filename, temporality).
        """
        seen: dict[tuple[str, Temporality], CHIRPSFileInfo] = {}
        for f in files:
            key = (f.filename, f.temporality)
            existing = seen.get(key)
            if existing is None:
                seen[key] = f
            elif f.status == DataStatus.REAL and existing.status == DataStatus.PRELIM:
                seen[key] = f
        return list(seen.values())

    def _process_country(
        self, country: BaseCountry, available_files: list[CHIRPSFileInfo]
    ):
        logger.info(f"\n{'='*50}")
        logger.info(f"Procesando país: {country.config.name.upper()}")

        for temporality in country.config.temporalities:
            temp_files = [f for f in available_files if f.temporality == temporality]

            catalog_entries = self._catalog.get_processed_entries(
                country.config.name, temporality.value
            )

            pending_new: list[CHIRPSFileInfo] = []
            pending_upgrade: list[CHIRPSFileInfo] = []

            for f in temp_files:
                current_status = catalog_entries.get(f.filename)

                if current_status is None:
                    pending_new.append(f)
                elif current_status == "prelim" and f.status == DataStatus.REAL:
                    pending_upgrade.append(f)

            total = len(pending_new) + len(pending_upgrade)
            if total == 0:
                logger.info(f"  [{temporality.value}] Sin cambios.")
                continue

            logger.info(
                f"  [{temporality.value}] {len(pending_new)} nuevos, "
                f"{len(pending_upgrade)} upgrades prelim→real"
            )

            if pending_new:
                self._batch_processor.process_all(pending_new, country)
            if pending_upgrade:
                self._batch_processor.process_upgrades(pending_upgrade, country)
