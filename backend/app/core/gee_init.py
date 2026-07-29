import ee
from app.config import settings


def initialize_gee():

    credentials = ee.ServiceAccountCredentials(
        email=None,
        key_file=settings.GOOGLE_APPLICATION_CREDENTIALS
    )

    ee.Initialize(
        credentials=credentials,
        project=settings.GEE_PROJECT
    )

    print("✅ Google Earth Engine Initialized")