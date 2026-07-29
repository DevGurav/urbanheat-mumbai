import ee

from app.services.gee_service import (
    get_lst_image,
    get_ndvi_image
)

from app.services.risk_service import (
    calculate_heat_risk,
    vegetation_status
)



def sample_location(lat: float, lon: float):


    point = ee.Geometry.Point(
        [lon, lat]
    )


    lst_image = get_lst_image()

    ndvi_image = get_ndvi_image()



    # Extract LST value

    lst_value = lst_image.reduceRegion(
        reducer=ee.Reducer.first(),
        geometry=point,
        scale=30
    ).get("LST")



    # Extract NDVI value

    ndvi_value = ndvi_image.reduceRegion(
        reducer=ee.Reducer.first(),
        geometry=point,
        scale=30
    ).get("NDVI")



    # Convert EE values

    lst_value = ee.Number(
        lst_value
    ).getInfo()



    ndvi_value = ee.Number(
        ndvi_value
    ).getInfo()



    risk = calculate_heat_risk(
        lst_value,
        ndvi_value
    )


    vegetation = vegetation_status(
        ndvi_value
    )



    return {

        "location":{
            "latitude":lat,
            "longitude":lon
        },


        "environment":{

            "lst":lst_value,

            "ndvi":ndvi_value,

            "risk":risk,

            "vegetation":vegetation

        }

    }