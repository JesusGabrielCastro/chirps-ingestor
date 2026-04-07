import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from ...domain.models import DataStatus

logger = logging.getLogger(__name__)

# URLs raíz — datos finales validados
REAL_URLS = {
    "pentad":  "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_pentad/tifs/",
    "daily":   "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/tifs/p05/",
    "dekad":   "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_dekad/tifs/",
    "monthly": "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/tifs/",
}

# URLs prelim — estimación por satélite, publicadas antes que la versión final
PRELIM_URLS = {
    "pentad":  "https://data.chc.ucsb.edu/products/CHIRPS-2.0/prelim/global_pentad/tifs/",
    "daily":   "https://data.chc.ucsb.edu/products/CHIRPS-2.0/prelim/global_daily/tifs/p05/",
    "dekad":   "https://data.chc.ucsb.edu/products/CHIRPS-2.0/prelim/global_dekad/tifs/",
    "monthly": "https://data.chc.ucsb.edu/products/CHIRPS-2.0/prelim/global_monthly/tifs/",
}

# El status lo determina únicamente el árbol de URLs — sin heurísticas de fechas
URL_STATUS_MAP = {
    **{v: DataStatus.REAL   for v in REAL_URLS.values()},
    **{v: DataStatus.PRELIM for v in PRELIM_URLS.values()},
}


def build_driver() -> webdriver.Chrome:
    """
    Construye un driver Chrome headless.
    Compatible con Docker/Linux (--no-sandbox, --disable-dev-shm-usage)
    y con Windows local (--headless=new).
    Selenium Manager descarga el chromedriver compatible automáticamente.
    """
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=options)
