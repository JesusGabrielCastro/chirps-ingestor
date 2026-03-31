from .colombia import Colombia
from .mexico import Mexico
from .peru import Peru
from .base_country import BaseCountry

COUNTRY_REGISTRY: dict[str, BaseCountry] = {
    "colombia": Colombia(),
    "mexico":   Mexico(),
    "peru":     Peru(),
}


def get_country(name: str) -> BaseCountry:
    if name not in COUNTRY_REGISTRY:
        raise ValueError(
            f"País no soportado: {name}. Disponibles: {list(COUNTRY_REGISTRY.keys())}"
        )
    return COUNTRY_REGISTRY[name]


def get_all_countries() -> list[BaseCountry]:
    return list(COUNTRY_REGISTRY.values())
