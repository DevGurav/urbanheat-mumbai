import ee
import pandas as pd
import os
import time

from app.core.gee_init import initialize_gee

from app.data_pipeline.grid_generator import get_mumbai_grid
from app.data_pipeline.historical_data import (
    get_monthly_images,
    calculate_lst
)


# Initialize Earth Engine
initialize_gee()


OUTPUT_FILE = (
    "mumbai_heat_features_2019_2024.csv"
)


START_YEAR = 2019
END_YEAR = 2024



# -----------------------------
# Spectral Indices
# -----------------------------

def calculate_ndvi(image):

    return (
        image
        .normalizedDifference(
            [
                "SR_B5",
                "SR_B4"
            ]
        )
        .rename("NDVI")
    )



def calculate_ndbi(image):

    return (
        image
        .normalizedDifference(
            [
                "SR_B6",
                "SR_B5"
            ]
        )
        .rename("NDBI")
    )



def calculate_ndwi(image):

    return (
        image
        .normalizedDifference(
            [
                "SR_B3",
                "SR_B5"
            ]
        )
        .rename("NDWI")
    )



# -----------------------------
# Monthly Feature Extraction
# -----------------------------

def extract_month_features(
        year,
        month,
        grid
):

    print(
        f"Processing {year}-{month}"
    )


    image = get_monthly_images(
        year,
        month
    )


    combined = (
        calculate_lst(image)
        .addBands(
            calculate_ndvi(image)
        )
        .addBands(
            calculate_ndbi(image)
        )
        .addBands(
            calculate_ndwi(image)
        )
    )


    features = (
        combined
        .reduceRegions(
            collection=grid,
            reducer=ee.Reducer.mean(),
            scale=30,
            tileScale=8
        )
    )


    # remove geometry
    features = features.map(
        lambda f:
        f.setGeometry(None)
        .set(
            {
                "year": year,
                "month": month
            }
        )
    )


    return features




# -----------------------------
# Earth Engine Pagination
# -----------------------------

def download_features(
        collection,
        batch_size=500
):


    total = collection.size().getInfo()


    print(
        "Total cells:",
        total
    )


    records = []


    for start in range(
        0,
        total,
        batch_size
    ):


        print(
            f"Downloading {start} - {min(start+batch_size,total)}"
        )


        batch = (
            collection
            .toList(
                batch_size,
                start
            )
            .getInfo()
        )


        for item in batch:

            records.append(
                item["properties"]
            )


    return records




# -----------------------------
# Main Pipeline
# -----------------------------

def generate_dataset():


    grid = get_mumbai_grid()


    all_records = []



    for year in range(
        START_YEAR,
        END_YEAR + 1
    ):


        for month in range(
            1,
            13
        ):


            try:

                fc = extract_month_features(
                    year,
                    month,
                    grid
                )


                rows = download_features(
                    fc
                )


                all_records.extend(
                    rows
                )


                # Save checkpoint
                df = pd.DataFrame(
                    all_records
                )


                df.to_csv(
                    OUTPUT_FILE,
                    index=False
                )


                print(
                    f"Saved {len(all_records)} rows"
                )


            except Exception as e:


                print(
                    "FAILED:",
                    year,
                    month,
                    e
                )

                continue



    print(
        "COMPLETE"
    )


    print(
        "Final rows:",
        len(all_records)
    )




if __name__ == "__main__":

    generate_dataset()