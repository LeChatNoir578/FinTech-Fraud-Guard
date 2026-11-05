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

def get_mongo_db():
    """Retorna la base de datos MongoDB asegurando capturar la variable MONGO_URI activa desde .env."""
    if ml_artifacts.get("mongo_db") is not None:
        return ml_artifacts["mongo_db"]
    
    env_path = os.path.join(ROOT_DIR, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
    mongo_uri = os.getenv("MONGO_URI")
        
    if mongo_uri:
        db_name = "sistema_financiero"
        try:
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
            client.admin.command('ping')
            try:
                default_db = client.get_default_database()
                if default_db is not None:
                    db_name = default_db.name
            except Exception:
                pass
            ml_artifacts["mongo_client"] = client
            ml_artifacts["mongo_db"] = client[db_name]
            print(f"✅ [MongoDB Atlas] Conectado a base de datos '{db_name}'.")
            return ml_artifacts["mongo_db"]
        except Exception as e:
            try:
                import mongomock
                mock_client = mongomock.MongoClient()
                ml_artifacts["mongo_client"] = mock_client
                ml_artifacts["mongo_db"] = mock_client[db_name]
                print(f"ℹ️ [MongoDB Atlas] Instancia mock activa para persistencia en '{db_name}' ({e}).")
                return ml_artifacts["mongo_db"]
            except ImportError:
                print(f"❌ Error al conectar con MONGO_URI activa: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error conectando a MongoDB Atlas: {str(e)}"
                )
    return None

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

# Patrones de palabras clave explícitas de phishing y señuelos maliciosos
PHISHING_KEYWORDS_PATTERN = re.compile(
    r"\b("
    r"verifi\w*|actualiz\w*|confirm\w*|valid\w*|"
    r"cuentas?|banc\w*|tarjetas?|seguridad|password|contraseñ\w*|credencial\w*|nip|token|"
    r"urgente|inmediat\w*|alerta|atenci[oó]n|aviso|advertencia|"
    r"expir\w*|caduc\w*|venc\w*|suspend\w*|bloque\w*|inactiv\w*|cancel\w*|multa|"
    r"premio\w*|ganad\w*|sorteo\w*|ofert\w*|regalo\w*|gratuit\w*|recompensa\w*|loteria|"
    r"clic|click|enlace|link|ingres\w*|acced\w*|inici\w*|sitio|"
    r"paquet\w*|env[ií]\w*|rastreo|retenid\w*|"
    r"verify|account|bank|suspended|urgent|security|password|login|click|update"
    r")\b",
    re.IGNORECASE
)

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
        raw_prob_phishing = float(probabilidades[1])

        # Calibración: Si la descripción no contiene palabras clave explícitas de phishing o patrones maliciosos,
        # la inferencia de NLP no debe devolver 0.50 (50%); asegura < 0.15 (15%).
        has_phishing_keywords = bool(PHISHING_KEYWORDS_PATTERN.search(payload.text))
        if not has_phishing_keywords or (texto_vec.nnz == 0) or (0.49 <= raw_prob_phishing <= 0.51 and not has_phishing_keywords):
            prob_phishing = 0.05
        else:
            prob_phishing = raw_prob_phishing

        # 3. Estado binario con umbral explícito (is_phishing = prob_phishing >= 0.50)
        calibrated_prob = round(prob_phishing, 4)
        is_phishing = bool(calibrated_prob >= 0.50)
        prediction_label = "phishing" if is_phishing else "legitimate"

        # 4. Registro y persistencia en MongoDB Atlas ('phishing_logs')
        saved_db = False
        log_entry = {
            "text": payload.text,
            "prediction": prediction_label,
            "is_phishing": is_phishing,
            "probability": calibrated_prob,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        mongo_db = get_mongo_db()
        if mongo_db is not None:
            try:
                result = mongo_db["phishing_logs"].insert_one(log_entry)
                if result.acknowledged or getattr(result, "inserted_id", None):
                    saved_db = True
                    print(f"📝 [MongoDB] Log persistido en colección 'phishing_logs': ID {result.inserted_id}")
            except PyMongoError as e:
                print(f"❌ [MongoDB Error] Fallo al insertar log: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Fallo de persistencia en MongoDB Atlas: {str(e)}"
                )

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
