from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut



geolocator = Nominatim(
    user_agent="urban_heat_planner"
)



def get_coordinates(location_name):

    try:

        query = (
            f"{location_name}, Mumbai, India"
        )


        location = geolocator.geocode(
            query
        )


        if location is None:

            return None



        return {

            "latitude":
                location.latitude,

            "longitude":
                location.longitude,

            "address":
                location.address

        }



    except GeocoderTimedOut:

        return None