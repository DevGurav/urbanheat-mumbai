import pandas as pd
import os
import joblib

from xgboost import XGBRegressor

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


# ==============================
# Paths
# ==============================

DATASET_PATH = (
    "app/data_pipeline/cleaned_dataset.csv"
)

MODEL_DIR = (
    "app/models"
)

MODEL_PATH = (
    "app/models/xgboost_lst_model.pkl"
)

FEATURE_PATH = (
    "app/models/features.pkl"
)


# ==============================
# Load Dataset
# ==============================

print("\nLoading dataset...")


df = pd.read_csv(
    DATASET_PATH
)


print(df.head())


print(
    "\nDataset size:",
    df.shape
)



# ==============================
# Data Cleaning Safety
# ==============================

print("\nChecking missing values")

print(
    df.isnull().sum()
)


df = df.dropna()


print(
    "\nAfter removing missing values:",
    df.shape
)



# ==============================
# Feature Selection
# ==============================

FEATURES = [

    "latitude",
    "longitude",

    "year",
    "month",

    "NDVI",
    "NDBI",
    "NDWI"

]


TARGET = "LST"



X = df[FEATURES]

y = df[TARGET]



# Save feature order for API prediction

os.makedirs(
    MODEL_DIR,
    exist_ok=True
)


joblib.dump(
    FEATURES,
    FEATURE_PATH
)



# ==============================
# Train Test Split
# ==============================


X_train, X_test, y_train, y_test = train_test_split(

    X,

    y,

    test_size=0.2,

    random_state=42

)



print(
    "\nTraining:",
    X_train.shape
)


print(
    "Testing:",
    X_test.shape
)



# ==============================
# XGBoost Model
# ==============================


model = XGBRegressor(

    n_estimators=800,

    learning_rate=0.03,

    max_depth=8,

    min_child_weight=5,

    subsample=0.85,

    colsample_bytree=0.85,

    objective="reg:squarederror",

    random_state=42,

    n_jobs=-1,

    tree_method="hist"

)



print(
    "\nTraining XGBoost..."
)



model.fit(

    X_train,

    y_train,

    eval_set=[
        (
            X_test,
            y_test
        )
    ],

    verbose=False

)



print(
    "Training completed"
)



# ==============================
# Prediction
# ==============================


prediction = model.predict(
    X_test
)



# ==============================
# Evaluation
# ==============================


mae = mean_absolute_error(

    y_test,

    prediction

)



mse = mean_squared_error(

    y_test,

    prediction

)


rmse = mse ** 0.5



r2 = r2_score(

    y_test,

    prediction

)



print("\n======================")

print("MODEL PERFORMANCE")

print("======================")


print(
    "MAE:",
    round(mae,4),
    "°C"
)


print(
    "RMSE:",
    round(rmse,4),
    "°C"
)


print(
    "R2 Score:",
    round(r2,4)
)



# ==============================
# Feature Importance
# ==============================


importance = pd.DataFrame(

    {

        "feature": FEATURES,

        "importance":
        model.feature_importances_

    }

)


importance = importance.sort_values(

    by="importance",

    ascending=False

)


print(
    "\nFeature Importance"
)


print(
    importance
)



importance.to_csv(

    "app/models/feature_importance.csv",

    index=False

)



# ==============================
# Save Model
# ==============================


joblib.dump(

    model,

    MODEL_PATH

)



print(
    "\nModel saved:"
)

print(
    MODEL_PATH
)