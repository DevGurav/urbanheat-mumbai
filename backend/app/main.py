from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.heat_prediction import router


# -----------------------------
# FastAPI Application
# -----------------------------

app = FastAPI(

    title="Urban Heat Intelligence API",

    description=(
        "AI based Urban Heat Island Prediction System "
        "using Satellite Data, ML and Geospatial Analysis"
    ),

    version="1.0.0"

)



# -----------------------------
# CORS Configuration
# -----------------------------

app.add_middleware(

    CORSMiddleware,

    allow_origins=[

        "http://localhost:3000",   # Next.js frontend

    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)



# -----------------------------
# Register Routers
# -----------------------------

app.include_router(router)



# -----------------------------
# Root Endpoint
# -----------------------------

@app.get("/")
def home():

    return {

        "status": "running",

        "message":
        "Urban Heat AI API is running",

        "service":
        "Urban Heat Intelligence Platform"

    }



# -----------------------------
# Health Check
# -----------------------------

@app.get("/health")
def health():

    return {

        "api": "healthy",

        "model": "XGBoost LST Predictor",

        "version": "1.0"

    }