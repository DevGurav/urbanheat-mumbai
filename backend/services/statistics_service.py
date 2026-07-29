import ee


def calculate_statistics(
    image: ee.Image,
    geometry: ee.Geometry,
    scale: int = 30
):
    """
    Calculate mean, min and max statistics for a single-band Earth Engine image.

    Parameters
    ----------
    image : ee.Image
        Earth Engine image (single band)

    geometry : ee.Geometry
        Area over which statistics will be calculated

    scale : int
        Resolution in meters

    Returns
    -------
    dict
        Statistics dictionary
    """

    stats = image.reduceRegion(
        reducer=(
            ee.Reducer.mean()
            .combine(
                reducer2=ee.Reducer.min(),
                sharedInputs=True
            )
            .combine(
                reducer2=ee.Reducer.max(),
                sharedInputs=True
            )
        ),
        geometry=geometry,
        scale=scale,
        maxPixels=1e9
    )

    return stats.getInfo()