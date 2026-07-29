import ee


# ==========================================================
# Study Area
# ==========================================================

def get_mumbai_geometry():
    return ee.Geometry.Rectangle([
        72.77,
        18.88,
        72.99,
        19.30
    ])


# ==========================================================
# Landsat Composite
# ==========================================================

def get_landsat_composite():

    mumbai = get_mumbai_geometry()

    image = (
        ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        .filterBounds(mumbai)
        .filterDate("2023-01-01", "2023-12-31")
        .filter(ee.Filter.lt("CLOUD_COVER", 10))
        .median()
    )

    return image


# ==========================================================
# RGB Image
# ==========================================================

def get_rgb_image():

    image = get_landsat_composite()

    rgb = (
        image
        .select(["SR_B4", "SR_B3", "SR_B2"])
        .multiply(0.0000275)
        .add(-0.2)
    )

    return rgb


# ==========================================================
# NDVI Image
# ==========================================================

def get_ndvi_image():

    image = get_landsat_composite()

    ndvi = (
        image
        .normalizedDifference(["SR_B5", "SR_B4"])
        .rename("NDVI")
    )

    return ndvi


# ==========================================================
# Land Surface Temperature
# ==========================================================

def get_lst_image():

    image = get_landsat_composite()

    lst = (
        image
        .select("ST_B10")
        .multiply(0.00341802)
        .add(149.0)
        .subtract(273.15)
        .rename("LST")
    )

    return lst


# ==========================================================
# RGB Tiles
# ==========================================================

def get_rgb_tiles():

    rgb = get_rgb_image()

    vis = {
        "min": 0,
        "max": 0.30
    }

    return rgb.getMapId(vis)


# ==========================================================
# NDVI Tiles
# ==========================================================

def get_ndvi_tiles():

    ndvi = get_ndvi_image()

    vis = {
        "min": -0.2,
        "max": 0.8,
        "palette": [
            "blue",
            "white",
            "yellow",
            "green",
            "darkgreen"
        ]
    }

    return ndvi.getMapId(vis)


# ==========================================================
# LST Tiles
# ==========================================================

def get_lst_tiles():

    lst = get_lst_image()

    vis = {
        "min": 20,
        "max": 45,
        "palette": [
            "#0000FF",
            "#00FFFF",
            "#00FF00",
            "#FFFF00",
            "#FFA500",
            "#FF0000",
            "#800000"
        ]
    }

    return lst.getMapId(vis)