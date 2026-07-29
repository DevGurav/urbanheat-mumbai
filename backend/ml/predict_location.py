import pickle
import pandas as pd
import os


MODEL_PATH = (
    "app/models/xgboost_lst_model.pkl"
)


# Load model once
with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)



FEATURES = [
    "latitude",
    "longitude",
    "year",
    "month",
    "NDVI",
    "NDBI",
    "NDWI"
]



def predict_lst(
        latitude,
        longitude,
        year,
        month,
        ndvi,
        ndbi,
        ndwi
):


    input_data = pd.DataFrame(
        [
            {
                "latitude": latitude,
                "longitude": longitude,
                "year": year,
                "month": month,
                "NDVI": ndvi,
                "NDBI": ndbi,
                "NDWI": ndwi
            }
        ]
    )


    # important: same order as training
    input_data = input_data[FEATURES]


    prediction = model.predict(
        input_data
    )


    return round(
        float(prediction[0]),
        2
    )



def calculate_risk(lst):

    if lst >= 40:
        return "HIGH"

    elif lst >= 35:
        return "MODERATE"

    else:
        return "LOW"