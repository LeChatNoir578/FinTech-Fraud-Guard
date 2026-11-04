import os
import re
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv
import joblib
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

# Cargar variables de entorno
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

MODEL_PATH = os.path.join(BASE_DIR, "phishing_model_v1.joblib")
VECTORIZER_PATH = os.path.join(BASE_DIR, "tfidf_vectorizer_v1.joblib")

ml_artifacts: Dict[str, Any] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga persistente de artefactos ML y conexión a MongoDB Atlas."""
    if not os.path.exists(MODEL_PATH) or not os.path.exists(VECTORIZER_PATH):
        raise FileNotFoundError(
            f"No se encontraron los artefactos en {MODEL_PATH} o {VECTORIZER_PATH}."
        )

    ml_artifacts["model"] = joblib.load(MODEL_PATH)
    ml_artifacts["vectorizer"] = joblib.load(VECTORIZER_PATH)
    print("✅ Artefactos ML cargados exitosamente.")

    # Conexión a MongoDB Atlas
    mongo_uri = os.getenv("MONGO_URI")
    ml_artifacts["mongo_client"] = None
    ml_artifacts["mongo_db"] = None

    if mongo_uri:
        try:
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2500)
            client.admin.command('ping')
            db_name = "sistema_financiero"
            try:
                default_db = client.get_default_database()
                if default_db is not None:
                    db_name = default_db.name
            except Exception:
                pass
            ml_artifacts["mongo_client"] = client
            ml_artifacts["mongo_db"] = client[db_name]
            print(f"✅ Conectado a MongoDB Atlas (Base de datos: '{db_name}').")
        except (ServerSelectionTimeoutError, PyMongoError) as e:
            print(f"⚠️ MongoDB Atlas no accesible en este momento ({e}).")
        except Exception as e:
            print(f"⚠️ Error conectando a MongoDB Atlas: {e}")

    yield
    if ml_artifacts.get("mongo_client"):
        ml_artifacts["mongo_client"].close()
    ml_artifacts.clear()
    print("🧹 Artefactos ML liberados.")

# --- Inicialización de FastAPI ---
app = FastAPI(
    title="FinTech Fraud Guard - NLP Phishing Detection API",
    description="API para la detección de mensajes de phishing en tiempo real mediante NLP y registro en MongoDB Atlas.",
    version="1.1.0",
    lifespan=lifespan
)

# --- Configuración CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Esquemas Pydantic ---
class PredictRequest(BaseModel):
    text: str = Field(
        ...,
        description="Texto o mensaje a analizar para determinar riesgo de phishing.",
        examples=["Estimado cliente, su cuenta ha sido suspendida. Haga clic aquí para verificar sus datos."]
    )

    @field_validator("text")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        clean_text = value.strip()
        if not clean_text:
            raise ValueError("El texto proporcionado no puede estar vacío.")
        return clean_text

class PredictResponse(BaseModel):
    text: str
    prediction: str
    probability: float
    is_phishing: bool
    saved_in_database: bool = False

# --- Endpoints ---
@app.get("/", tags=["Health Check"])
async def root():
    return {
        "project": "FinTech Fraud Guard",
        "module": "NLP Phishing Detection",
        "status": "online",
        "database": "connected" if ml_artifacts.get("mongo_db") is not None else "offline_or_unconfigured",
        "author": "Aaron + Juan Alberto"
    }

@app.post("/predict/text", response_model=PredictResponse, status_code=status.HTTP_200_OK, tags=["Prediction"])
async def predict_phishing(payload: PredictRequest):
    try:
        model = ml_artifacts["model"]
        vectorizer = ml_artifacts["vectorizer"]

        # 1. Preprocesamiento del texto de entrada
        raw_text = payload.text.lower().strip()
        processed_text = re.sub(r"[^\w\s]", "", raw_text)

        # 2. Vectorización TF-IDF
        text_vectorized = vectorizer.transform([processed_text])

        # 3. Predicción directa del modelo
        raw_pred = model.predict(text_vectorized)[0]

        # 4. Inferencia precisa de probabilidad para phishing
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(text_vectorized)[0]
            classes = list(model.classes_)

            if 1 in classes:
                phishing_idx = classes.index(1)
            elif "phishing" in classes:
                phishing_idx = classes.index("phishing")
            elif "Phishing" in classes:
                phishing_idx = classes.index("Phishing")
            else:
                phishing_idx = 1 if len(classes) > 1 else 0

            prob_phishing = float(probs[phishing_idx])
        else:
            prob_phishing = 1.0 if raw_pred in [1, "phishing", "Phishing"] else 0.0

        is_phishing = raw_pred in [1, "phishing", "Phishing"] or prob_phishing >= 0.5
        label = "phishing" if is_phishing else "normal"
        final_prob = prob_phishing if is_phishing else (1.0 - prob_phishing)
        saved_db = False

        # 5. Registro automático en MongoDB Atlas ('phishing_logs')
        mongo_db = ml_artifacts.get("mongo_db")
        if mongo_db is not None:
            try:
                log_entry = {
                    "text": payload.text,
                    "prediction": label,
                    "is_phishing": is_phishing,
                    "probability": round(final_prob, 4),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                mongo_db["phishing_logs"].insert_one(log_entry)
                saved_db = True
                print(f"📝 [MongoDB] Log de phishing registrado en colección 'phishing_logs'")
            except Exception as e:
                print(f"⚠️ [MongoDB] Error registrando log: {e}")

        return PredictResponse(
            text=payload.text,
            prediction=label,
            probability=round(final_prob, 4),
            is_phishing=is_phishing,
            saved_in_database=saved_db
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante el procesamiento del texto: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
