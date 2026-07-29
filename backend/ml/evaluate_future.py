import pandas as pd
import numpy as np
import joblib


# -----------------------------
# Paths
# -----------------------------

MODEL_PATH = (
    "app/models/xgboost_lst_model.pkl"
)


DATA_PATH = (
    "app/data_pipeline/cleaned_dataset.csv"
)


# -----------------------------
# Load Model
# -----------------------------

print("Loading model...")

model = joblib.load(
    MODEL_PATH
)

print("Model loaded")



# -----------------------------
# Load Historical Dataset
# -----------------------------

df = pd.read_csv(
    DATA_PATH
)


print(
    "Dataset loaded:",
    df.shape
)



# -----------------------------
# Future Location Prediction
# -----------------------------

def predict_lst(
        latitude,
        longitude,
        year,
        month
):


    # Find nearest historical location

    distance = (
        (df["latitude"] - latitude)**2 +
        (df["longitude"] - longitude)**2
    )


    nearest = df.loc[
        distance.idxmin()
    ]


    print("\nNearest Grid Cell")
    print(nearest)



    # Create future feature vector

    input_data = pd.DataFrame(
        {

        "latitude":[latitude],

        "longitude":[longitude],
"year":[year],

        "month":[month],

        

        "NDVI":[
            nearest["NDVI"]
        ],

        "NDBI":[
            nearest["NDBI"]
        ],

        "NDWI":[
            nearest["NDWI"]
        ]

        }
    )


    prediction = model.predict(
        input_data
    )


    lst = prediction[0]


    return lst



# -----------------------------
# Heat Classification
# -----------------------------

def classify_heat(lst):

    if lst < 30:
        return "LOW"

    elif lst < 38:
        return "MODERATE"

    elif lst < 42:
        return "HIGH"

    else:
        return "EXTREME"



# -----------------------------
# Test Prediction
# -----------------------------


if __name__ == "__main__":


    predicted_temperature = predict_lst(

        latitude=19.23,     # Borivali

        longitude=72.85,

        year=2025,

        month=5

    )


    print(
        "\n======================"
    )


    print(
        "Predicted LST:",
        round(
            predicted_temperature,
            2
        ),
        "°C"
    )


    print(
        "Risk:",
        classify_heat(
            predicted_temperature
        )
    )