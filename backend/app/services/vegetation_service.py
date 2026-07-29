from app.services.gee_service import (
    get_ndvi_image,
    get_mumbai_geometry
)

from app.services.statistics_service import calculate_statistics


def analyze_vegetation():
    """
    Compute NDVI statistics.
    """

    ndvi = get_ndvi_image()

    stats = calculate_statistics(
        image=ndvi,
        geometry=get_mumbai_geometry()
    )

    average_ndvi = round(stats["NDVI_mean"], 3)
    minimum_ndvi = round(stats["NDVI_min"], 3)
    maximum_ndvi = round(stats["NDVI_max"], 3)

    if average_ndvi < 0.20:
        vegetation_health = "Poor"
    elif average_ndvi < 0.40:
        vegetation_health = "Moderate"
    elif average_ndvi < 0.60:
        vegetation_health = "Good"
    else:
        vegetation_health = "Excellent"

    return {
        "average_ndvi": average_ndvi,
        "minimum_ndvi": minimum_ndvi,
        "maximum_ndvi": maximum_ndvi,
        "vegetation_health": vegetation_health
    }