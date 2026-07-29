from sqlalchemy import (
    Column,
    Integer,
    Float,
    String
)

from geoalchemy2 import Geometry

from app.database.connection import Base



class HeatFeature(Base):

    __tablename__ = "heat_features"


    id = Column(
        Integer,
        primary_key=True
    )


    cell_id = Column(
        String,
        index=True
    )


    latitude = Column(
        Float
    )


    longitude = Column(
        Float
    )


    year = Column(
        Integer,
        index=True
    )


    month = Column(
        Integer,
        index=True
    )


    lst = Column(
        Float
    )


    ndvi = Column(
        Float
    )


    ndbi = Column(
        Float
    )


    ndwi = Column(
        Float
    )


    geometry = Column(
        Geometry(
            "POINT",
            srid=4326
        )
    )