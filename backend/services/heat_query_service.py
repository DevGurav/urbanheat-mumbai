from sqlalchemy import text


def get_nearest_cell(
        db,
        latitude,
        longitude
):


    query = text(
        """
        SELECT
            cell_id,
            latitude,
            longitude,
            lst,
            ndvi,
            ndbi,
            ndwi,
            year,
            month

        FROM heat_features

        ORDER BY geometry <->

        ST_SetSRID(
            ST_Point(
                :longitude,
                :latitude
            ),
            4326
        )

        LIMIT 1;
        """
    )


    result = db.execute(
        query,
        {
            "latitude": latitude,
            "longitude": longitude
        }
    )


    row = result.fetchone()


    if row is None:
        return None


    return {
        "cell_id": row.cell_id,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "lst": row.lst,
        "ndvi": row.ndvi,
        "ndbi": row.ndbi,
        "ndwi": row.ndwi,
        "year": row.year,
        "month": row.month
    }