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

# chirps-v2.0.2025.06.4.tif.gz
PENTAD_PATTERN = re.compile(r"chirps-v2\.0\.(\d{4})\.(\d{2})\.([1-6])\.tif(?:\.gz)?$")


class PentadScraper(FileListingPort):

    def get_available_files(
        self, temporality: str, year: int | None = None
    ) -> list[CHIRPSFileInfo]:
        files: list[CHIRPSFileInfo] = []
        for url, status in [
            (REAL_URLS["pentad"],   DataStatus.REAL),
            (PRELIM_URLS["pentad"], DataStatus.PRELIM),
        ]:
            files.extend(self._scrape_url(url, status))
        real_count   = sum(1 for f in files if f.status == DataStatus.REAL)
        prelim_count = sum(1 for f in files if f.status == DataStatus.PRELIM)
        logger.info(f"Pentad total: {len(files)} archivos ({real_count} real, {prelim_count} prelim)")
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
                match = PENTAD_PATTERN.match(filename)
                if not match:
                    continue
                y, m, p = int(match.group(1)), int(match.group(2)), int(match.group(3))
                approx_day = (p - 1) * 5 + 1
                try:
                    file_date = date(y, m, min(approx_day, 28))
                except ValueError:
                    continue
                files.append(CHIRPSFileInfo(
                    filename=filename,
                    url=href,
                    temporality=Temporality.PENTAD,
                    year=y,
                    month=m,
                    day=None,
                    period_num=p,
                    status=status,
                    file_date=file_date,
                ))
        except Exception as e:
            logger.error(f"Error scraping pentad {url}: {e}")
        finally:
            driver.quit()
        return files
