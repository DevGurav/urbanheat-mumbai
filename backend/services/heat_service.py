from app.services.gee_service import (
    get_lst_image,
    get_mumbai_geometry
)

from app.services.statistics_service import calculate_statistics


def analyze_heat():
    """
    Compute Land Surface Temperature statistics.
    """

    lst = get_lst_image()

    stats = calculate_statistics(
        image=lst,
        geometry=get_mumbai_geometry()
    )

    average_temperature = round(stats["LST_mean"], 2)
    minimum_temperature = round(stats["LST_min"], 2)
    maximum_temperature = round(stats["LST_max"], 2)

    if average_temperature < 28:
        risk_level = "Low"
    elif average_temperature < 34:
        risk_level = "Moderate"
    elif average_temperature < 40:
        risk_level = "High"
    else:
        risk_level = "Extreme"

    return {
        "average_temperature": average_temperature,
        "minimum_temperature": minimum_temperature,
        "maximum_temperature": maximum_temperature,
        "risk_level": risk_level
    }