from app.services.heat_service import analyze_heat
from app.services.vegetation_service import analyze_vegetation

from app.services.gee_service import (
    get_lst_tiles,
    get_ndvi_tiles,
)


def heat_tool():
    """
    Returns heat statistics + LST tile URL.
    """

    statistics = analyze_heat()

    tile = get_lst_tiles()

    return {
        "statistics": statistics,
        "tile_url": tile["tile_fetcher"].url_format,
        "active_layer": "LST",
    }


def vegetation_tool():
    """
    Returns vegetation statistics + NDVI tile URL.
    """

    statistics = analyze_vegetation()

    tile = get_ndvi_tiles()

    return {
        "statistics": statistics,
        "tile_url": tile["tile_fetcher"].url_format,
        "active_layer": "NDVI",
    }