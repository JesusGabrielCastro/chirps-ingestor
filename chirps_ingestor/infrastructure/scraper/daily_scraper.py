import re
import logging
from datetime import date

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base_scraper import build_driver, REAL_URLS, PRELIM_URLS
from ...domain.models import CHIRPSFileInfo, Temporality, DataStatus
from ...domain.ports import FileListingPort

logger = logging.getLogger(__name__)

# chirps-v2.0.2025.01.01.tif.gz
DAILY_PATTERN = re.compile(r"chirps-v2\.0\.(\d{4})\.(\d{2})\.(\d{2})\.tif(?:\.gz)?$")


class DailyScraper(FileListingPort):
    """
    Daily tiene subcarpetas por año en ambos árboles (real y prelim).
    year es obligatorio. El orchestrator llama a este scraper una vez
    por año que haga falta revisar (típicamente año actual y anterior).
    """

    def get_available_files(
        self, temporality: str, year: int | None = None
    ) -> list[CHIRPSFileInfo]:
        if year is None:
            raise ValueError("DailyScraper requiere el parámetro 'year'")

        files: list[CHIRPSFileInfo] = []
        for base_url, status in [
            (REAL_URLS["daily"],   DataStatus.REAL),
            (PRELIM_URLS["daily"], DataStatus.PRELIM),
        ]:
            url = f"{base_url}{year}/"
            files.extend(self._scrape_url(url, status, year))

        real_count   = sum(1 for f in files if f.status == DataStatus.REAL)
        prelim_count = sum(1 for f in files if f.status == DataStatus.PRELIM)
        logger.info(
            f"Daily {year}: {len(files)} archivos "
            f"({real_count} real, {prelim_count} prelim)"
        )
        return files

    def _scrape_url(self, url: str, status: DataStatus, year: int) -> list[CHIRPSFileInfo]:
        driver = build_driver()
        files: list[CHIRPSFileInfo] = []
        try:
            logger.info(f"  Navegando a: {url}")
            driver.get(url)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "a"))
            )
            for link in driver.find_elements(By.TAG_NAME, "a"):
                href = link.get_attribute("href") or ""
                filename = href.split("/")[-1]
                match = DAILY_PATTERN.match(filename)
                if not match:
                    continue
                y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if y != year:
                    continue
                try:
                    file_date = date(y, m, d)
                except ValueError:
                    continue
                files.append(CHIRPSFileInfo(
                    filename=filename,
                    url=href,
                    temporality=Temporality.DAILY,
                    year=y,
                    month=m,
                    day=d,
                    period_num=None,
                    status=status,
                    file_date=file_date,
                ))
        except Exception as e:
            logger.error(f"  Error scraping daily {url}: {e}")
        finally:
            driver.quit()
        return files
