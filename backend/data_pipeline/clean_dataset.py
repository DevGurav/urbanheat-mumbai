import pandas as pd
import os


INPUT_FILE = (
    "mumbai_heat_features_2019_2024.csv"
)

OUTPUT_FILE = (
    "cleaned_dataset.csv"
)


def clean_dataset():

    print("Loading dataset...")

    df = pd.read_csv(INPUT_FILE)


    print("\nOriginal dataset:")
    print(df.shape)


    print("\nMissing values:")
    print(df.isnull().sum())


    # --------------------------------
    # 1. Remove completely empty rows
    # --------------------------------

    df = df.dropna(
        how="all"
    )


    # --------------------------------
    # 2. Remove rows with missing
    # important features
    # --------------------------------

    required_columns = [
        "year",
        "month",
        "latitude",
        "longitude",
        "LST",
        "NDVI",
        "NDBI",
        "NDWI"
    ]


    df = df.dropna(
        subset=required_columns
    )


    print(
        "\nAfter removing missing values:",
        df.shape
    )


    # --------------------------------
    # 3. Remove invalid LST values
    # --------------------------------

    df = df[
        (df["LST"] > 0) &
        (df["LST"] < 60)
    ]


    # --------------------------------
    # 4. Validate vegetation indexes
    # --------------------------------

    df = df[
        (df["NDVI"] >= -1) &
        (df["NDVI"] <= 1)
    ]


    df = df[
        (df["NDBI"] >= -1) &
        (df["NDBI"] <= 1)
    ]


    df = df[
        (df["NDWI"] >= -1) &
        (df["NDWI"] <= 1)
    ]


    print(
        "\nAfter range filtering:",
        df.shape
    )


    # --------------------------------
    # 5. Remove duplicate observations
    # --------------------------------

    df = df.drop_duplicates()


    print(
        "\nAfter removing duplicates:",
        df.shape
    )


    # --------------------------------
    # 6. Sort data
    # --------------------------------

    df = df.sort_values(
        [
            "year",
            "month",
            "latitude",
            "longitude"
        ]
    )


    # --------------------------------
    # 7. Save cleaned dataset
    # --------------------------------

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )


    print("\nCleaning completed")
    print(
        "Saved:",
        OUTPUT_FILE
    )


    print("\nFinal dataset:")
    print(df.head())


    print("\nFinal missing values:")
    print(df.isnull().sum())



if __name__ == "__main__":

    clean_dataset()