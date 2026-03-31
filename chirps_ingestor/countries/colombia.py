from .base_country import BaseCountry
from ..domain.models import CountryConfig, Temporality


class Colombia(BaseCountry):

    @property
    def config(self) -> CountryConfig:
        return CountryConfig(
            name="colombia",
            code="CO",
            shapefile_path="shapefiles/colombia/colombia.shp",
            # Bounding box: cubre el territorio continental + islas
            bbox=(-79.0, -4.5, -66.8, 13.4),
            temporalities=[
                Temporality.DAILY,
                Temporality.PENTAD,
                Temporality.DEKAD,
                Temporality.MONTHLY,
            ],
            start_year=2015,
        )
