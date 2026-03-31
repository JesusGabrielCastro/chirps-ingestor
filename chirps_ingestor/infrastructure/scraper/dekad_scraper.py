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

# chirps-v2.0.1981.01.3.tif.gz
DEKAD_PATTERN = re.compile(r"chirps-v2\.0\.(\d{4})\.(\d{2})\.([1-3])\.tif(?:\.gz)?$")


class DekadScraper(FileListingPort):

    def get_available_files(
        self, temporality: str, year: int | None = None
    ) -> list[CHIRPSFileInfo]:
        files: list[CHIRPSFileInfo] = []
        for url, status in [
            (REAL_URLS["dekad"],   DataStatus.REAL),
            (PRELIM_URLS["dekad"], DataStatus.PRELIM),
        ]:
            files.extend(self._scrape_url(url, status))
        real_count   = sum(1 for f in files if f.status == DataStatus.REAL)
        prelim_count = sum(1 for f in files if f.status == DataStatus.PRELIM)
        logger.info(f"Dekad total: {len(files)} archivos ({real_count} real, {prelim_count} prelim)")
        return files

    def _scrape_url(self, url: str, status: DataStatus) -> list[CHIRPSFileInfo]:
        driver = build_driver()
        files: list[CHIRPSFileInfo] = []
        try:
            driver.get(url)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "a"))
            )
            for link in driver.find_elements(By.TAG_NAME, "a"):
                href = link.get_attribute("href") or ""
                filename = href.split("/")[-1]
                match = DEKAD_PATTERN.match(filename)
                if not match:
                    continue
                y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
                approx_day = (d - 1) * 10 + 1
                try:
                    file_date = date(y, m, min(approx_day, 28))
                except ValueError:
                    continue
                files.append(CHIRPSFileInfo(
                    filename=filename,
                    url=href,
                    temporality=Temporality.DEKAD,
                    year=y,
                    month=m,
                    day=None,
                    period_num=d,
                    status=status,
                    file_date=file_date,
                ))
        except Exception as e:
            logger.error(f"Error scraping dekad {url}: {e}")
        finally:
            driver.quit()
        return files
