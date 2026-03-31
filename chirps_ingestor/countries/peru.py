from .base_country import BaseCountry
from ..domain.models import CountryConfig, Temporality


class Peru(BaseCountry):

    @property
    def config(self) -> CountryConfig:
        return CountryConfig(
            name="peru",
            code="PE",
            shapefile_path="shapefiles/peru/peru.shp",
            bbox=(-81.4, -18.4, -68.6, -0.1),
            temporalities=[
                Temporality.DAILY,
                Temporality.PENTAD,
                Temporality.DEKAD,
                Temporality.MONTHLY,
            ],
            start_year=2015,
        )
