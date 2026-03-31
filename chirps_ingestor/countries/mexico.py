from .base_country import BaseCountry
from ..domain.models import CountryConfig, Temporality


class Mexico(BaseCountry):

    @property
    def config(self) -> CountryConfig:
        return CountryConfig(
            name="mexico",
            code="MX",
            shapefile_path="shapefiles/mexico/mexico.shp",
            bbox=(-118.4, 14.5, -86.7, 32.7),
            temporalities=[
                Temporality.DAILY,
                Temporality.PENTAD,
                Temporality.DEKAD,
                Temporality.MONTHLY,
            ],
            start_year=2015,
        )
