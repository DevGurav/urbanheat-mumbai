import ee

from app.core.gee_init import initialize_gee


# Initialize Earth Engine
initialize_gee()


# Mumbai Region
MUMBAI_REGION = ee.Geometry.Rectangle(
    [
        72.75,
        18.85,
        73.05,
        19.35
    ]
)


# Landsat Collection
LANDSAT_COLLECTION = (
    ee.ImageCollection(
        "LANDSAT/LC08/C02/T1_L2"
    )
    .filterBounds(
        MUMBAI_REGION
    )
    .filterDate(
        "2019-01-01",
        "2024-12-31"
    )
)



def get_region():

    return MUMBAI_REGION



def mask_clouds(image):

    qa = image.select(
        "QA_PIXEL"
    )


    cloud_mask = (
        qa.bitwiseAnd(1 << 3)
        .eq(0)
        .And(
            qa.bitwiseAnd(1 << 4)
            .eq(0)
        )
    )


    return (
        image
        .updateMask(
            cloud_mask
        )
    )



def apply_scale_factors(image):
    """
    Landsat Collection 2 Level-2 scaling
    """

    optical = (
        image
        .select(
            "SR_B.*"
        )
        .multiply(
            0.0000275
        )
        .add(
            -0.2
        )
    )


    thermal = (
        image
        .select(
            "ST_B10"
        )
    )


    return (
        image
        .addBands(
            optical,
            None,
            True
        )
        .addBands(
            thermal,
            None,
            True
        )
    )



def get_monthly_images(year, month):


    start = ee.Date.fromYMD(
        year,
        month,
        1
    )


    end = start.advance(
        1,
        "month"
    )


    collection = (
        LANDSAT_COLLECTION
        .filterDate(
            start,
            end
        )
        .map(
            mask_clouds
        )
        .map(
            apply_scale_factors
        )
    )


    count = collection.size()



    empty = (
        ee.Image.constant(
            [
                0,0,0,0,0,0,0,0
            ]
        )
        .rename(
            [
                "SR_B1",
                "SR_B2",
                "SR_B3",
                "SR_B4",
                "SR_B5",
                "SR_B6",
                "SR_B7",
                "ST_B10"
            ]
        )
    )



    image = ee.Algorithms.If(
        count.gt(0),
        collection.mean(),
        empty
    )


    return ee.Image(
        image
    )



def calculate_lst(image):

    thermal = image.select(
        "ST_B10"
    )


    lst = (
        thermal
        .multiply(
            0.00341802
        )
        .add(
            149
        )
        .subtract(
            273.15
        )
        .rename(
            "LST"
        )
    )


    return lst