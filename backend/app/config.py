import os
from dotenv import load_dotenv


load_dotenv()


class Settings:

    """
    Application Configuration
    """


    # -----------------------------
    # Project
    # -----------------------------

    PROJECT_NAME = "Urban Heat Intelligence Platform"

    VERSION = "1.0.0"



    # -----------------------------
    # Groq LLM
    # -----------------------------

    GROQ_API_KEY = os.getenv(
        "GROQ_API_KEY"
    )


    GROQ_MODEL = os.getenv(
        "GROQ_MODEL",
        "llama-3.3-70b-versatile"
    )



    # -----------------------------
    # Google Earth Engine
    # -----------------------------

    GOOGLE_APPLICATION_CREDENTIALS = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS"
    )


    GEE_PROJECT = os.getenv(
        "GEE_PROJECT"
    )



    # -----------------------------
    # Database
    # -----------------------------

    DATABASE_URL = os.getenv(
        "DATABASE_URL"
    )



    # -----------------------------
    # Vector Database
    # -----------------------------

    CHROMA_DB_PATH = os.getenv(
        "CHROMA_DB_PATH",
        "./chroma_db"
    )



    # -----------------------------
    # Debug
    # -----------------------------

    DEBUG = os.getenv(
        "DEBUG",
        "False"
    ).lower() == "true"



settings = Settings()