import ee

from app.core.gee_init import initialize_gee


initialize_gee()


MUMBAI_REGION = ee.Geometry.Rectangle(
    [
        72.75,
        18.85,
        73.05,
        19.35
    ]
)



def create_grid(region, size):

    """
    Creates square grid cells

    size:
    grid size in meters
    """


    projection = ee.Projection(
        "EPSG:3857"
    )


    grid = region.coveringGrid(
        projection,
        size
    )


    return grid



def add_cell_id(feature):

    centroid = feature.geometry().centroid(1)


    coords = centroid.coordinates()


    lon = ee.Number(
        coords.get(0)
    )

    lat = ee.Number(
        coords.get(1)
    )


    cell_id = (
        ee.String("MUM_")
        .cat(
            lon.format("%.4f")
        )
        .cat("_")
        .cat(
            lat.format("%.4f")
        )
    )


    return feature.set(
        {
            "cell_id": cell_id,
            "longitude": lon,
            "latitude": lat
        }
    )

def get_mumbai_grid():

    grid = create_grid(
        MUMBAI_REGION,
        500
    )


    grid = grid.map(
        add_cell_id
    )


    return grid