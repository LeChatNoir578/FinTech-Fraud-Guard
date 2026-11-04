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

# --- Mapeo de Términos / Normalización para el Vectorizador TF-IDF ---
SPANISH_TO_STEMS = {
    r"\bverifi\w*": "verify",
    r"\bcuentas?\b": "account",
    r"\bseguridad\b": "security",
    r"\bdispositiv\w*": "devic",
    r"\b(expir\w*|caduc\w*|venc\w*)": "expir",
    r"\bsuscripci\w*": "subscription",
    r"\b(ofert\w*|premio\w*)": "offer",
    r"\b(paquet\w*|env[ií]\w*)": "parcel shipp",
    r"\b(urgente|inmediat\w*|alerta)": "act limit verify",
    r"\b(gracias|agradezc\w*)": "thanks",
    r"\badjunt\w*": "attach",
    r"\b(revis\w*|favor)\b": "review ple",
    r"\b(saludos|cordiales|atentamente)": "regards",
    r"\bequipo\b": "team",
    r"\bfacturas?\b": "invoic",
    r"\bsemanal\w*": "weekly"
}

def clean_text(text: str) -> str:
    """Normaliza y preprocesa el texto para inferencia precisa."""
    raw = text.lower().strip()
    for pattern, repl in SPANISH_TO_STEMS.items():
        raw = re.sub(pattern, repl, raw)
    return re.sub(r"[^\w\s]", "", raw)

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
    is_phishing: bool
    probability: float
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

        # 1. Transformación TF-IDF sobre el texto de entrada limpio
        texto_limpio = clean_text(payload.text)
        texto_vec = vectorizer.transform([texto_limpio])

        # 2. Inferencia de probabilidad real con predict_proba
        probabilidades = model.predict_proba(texto_vec)[0]
        prob_phishing = float(probabilidades[1])

        # 3. Estado binario con umbral explícito (is_phishing = prob_phishing >= 0.50)
        is_phishing = bool(prob_phishing >= 0.50)
        prediction_label = "phishing" if is_phishing else "legitimate"
        calibrated_prob = round(prob_phishing, 4)

        # 4. Registro y persistencia en MongoDB Atlas ('phishing_logs')
        saved_db = False
        mongo_db = ml_artifacts.get("mongo_db")
        if mongo_db is not None:
            try:
                log_entry = {
                    "text": payload.text,
                    "prediction": prediction_label,
                    "is_phishing": is_phishing,
                    "probability": calibrated_prob,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                mongo_db["phishing_logs"].insert_one(log_entry)
                saved_db = True
                print(f"📝 [MongoDB] Log de phishing registrado en colección 'phishing_logs': {prediction_label} (p={calibrated_prob})")
            except Exception as e:
                print(f"⚠️ [MongoDB] Error registrando log: {e}")

        # 5. Formato de salida estandarizado en el JSON
        return PredictResponse(
            text=payload.text,
            prediction=prediction_label,
            is_phishing=is_phishing,
            probability=calibrated_prob,
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
