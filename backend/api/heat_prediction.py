from fastapi import APIRouter, Depends
from pydantic import BaseModel


from app.services.location_service import get_coordinates

from app.services.prediction_service import (
    predict_heat_location
)

from app.database.connection import get_db


from app.llm.response_generator import (
    generate_heat_explanation
)



router = APIRouter(
    prefix="/heat",
    tags=["Heat Prediction"]
)



class HeatRequest(BaseModel):

    location: str

    year: int

    month: int





@router.post("/predict")
def predict(
        request: HeatRequest,
        db=Depends(get_db)
):


    # -----------------------------
    # Location -> Coordinates
    # -----------------------------

    coordinates = get_coordinates(
        request.location
    )


    if coordinates is None:

        return {

            "error":
            "Location not found"

        }



    # -----------------------------
    # ML Prediction
    # -----------------------------

    result = predict_heat_location(

        db,

        request.location,

        coordinates["latitude"],

        coordinates["longitude"],

        request.year,

        request.month

    )



    if result is None:

        return {

            "error":
            "No data available"

        }



    # -----------------------------
    # LLM Explanation
    # -----------------------------

    ai_response = generate_heat_explanation(
        result
    )



    # -----------------------------
    # Final Response
    # -----------------------------

    result["ai_response"] = ai_response


    result["coordinates"] = coordinates


    return result