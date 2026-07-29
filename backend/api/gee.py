from fastapi import APIRouter
from app.services.gee_service import (
    get_rgb_tiles,
    get_ndvi_tiles,
    get_lst_tiles
)
router = APIRouter(prefix="/gee", tags=["Google Earth Engine"])


@router.get("/rgb")
def rgb():

    map_id = get_rgb_tiles()

    return {
        "tile_url": map_id["tile_fetcher"].url_format
    }


@router.get("/ndvi")
def ndvi():

    map_id = get_ndvi_tiles()

    return {
        "tile_url": map_id["tile_fetcher"].url_format
    }


@router.get("/lst")
def lst():

    map_id = get_lst_tiles()

    return {
        "tile_url": map_id["tile_fetcher"].url_format
    }