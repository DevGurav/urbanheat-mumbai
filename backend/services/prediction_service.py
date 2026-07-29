from app.services.heat_query_service import (
    get_nearest_cell
)

from app.ml.predict_location import (
    predict_lst,
    calculate_risk
)



def predict_heat_location(
        db,
        location,
        latitude,
        longitude,
        year,
        month
):


    # Get nearest historical features

    cell = get_nearest_cell(
        db,
        latitude,
        longitude
    )


    if cell is None:
        return None



    predicted_lst = predict_lst(

        latitude,
        longitude,

        year,
        month,

        cell["ndvi"],
        cell["ndbi"],
        cell["ndwi"]
    )



    return {

        "location": location,

        "coordinates": {
            "latitude": latitude,
            "longitude": longitude
        },

        "year": year,

        "month": month,


        "predicted_LST":
            predicted_lst,


        "NDVI":
            cell["ndvi"],


        "NDBI":
            cell["ndbi"],


        "NDWI":
            cell["ndwi"],


        "risk":
            calculate_risk(
                predicted_lst
            )

    }