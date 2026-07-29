from fastapi import APIRouter

from app.services.heat_service import analyze_heat
from app.services.vegetation_service import analyze_vegetation
from app.services.population_service import analyze_population
from app.services.pixel_service import sample_location


router = APIRouter(
    prefix="/analysis",
    tags=["Analysis"]
)


# ---------------------------------------------------
# Heat Analysis
# ---------------------------------------------------

@router.get("/heat")
def get_heat_analysis():
    """
    Returns Urban Heat Island statistics.
    """

    return analyze_heat()


# ---------------------------------------------------
# Vegetation Analysis
# ---------------------------------------------------

@router.get("/vegetation")
def get_vegetation_analysis():
    """
    Returns vegetation statistics.
    """

    return analyze_vegetation()


# ---------------------------------------------------
# Population Analysis
# ---------------------------------------------------

@router.get("/population")
def get_population_analysis():
    """
    Returns population statistics.
    """

    return analyze_population()




@router.get("/location")
def location_analysis(lat: float, lon: float):

    return sample_location(lat, lon)