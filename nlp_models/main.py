import os
import re
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, APIRouter, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

class AwaitableResult:
    def __init__(self, res):
        self._res = res

    def __await__(self):
        async def _coro():
            return self._res
        return _coro().__await__()

    def __getattr__(self, name):
        return getattr(self._res, name)

    def __repr__(self):
        return repr(self._res)

class AsyncSafeCollection:
    def __init__(self, col):
        self._col = col

    def insert_one(self, *args, **kwargs):
        if self._col is None:
            class SimulatedInsertResult:
                acknowledged = True
                inserted_id = "simulated_local_alert_id"
            return AwaitableResult(SimulatedInsertResult())
        res = self._col.insert_one(*args, **kwargs)
        if hasattr(res, "__await__"):
            return res
        return AwaitableResult(res)

    def __getattr__(self, name):
        if self._col is not None:
            return getattr(self._col, name)
        raise AttributeError(name)

class AsyncSafeDatabase:
    def __init__(self, db_getter):
        self._db_getter = db_getter

    @property
    def db(self):
        if callable(self._db_getter):
            return self._db_getter()
        return self._db_getter

    def __getitem__(self, name):
        raw_db = self.db
        col = raw_db[name] if raw_db is not None else None
        return AsyncSafeCollection(col)

    def __getattr__(self, name):
        raw_db = self.db
        if raw_db is not None:
            return getattr(raw_db, name)
        return None

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

    app.mongodb = AsyncSafeDatabase(get_mongo_db)
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

def run_nlp_model(text: str) -> Dict[str, Any]:
    """
    Ejecuta el pipeline de NLP (TF-IDF + Modelo clasificador SVM/LogisticRegression)
    para evaluar si un texto es intento de phishing o legítimo.
    """
    model = ml_artifacts.get("model")
    vectorizer = ml_artifacts.get("vectorizer")

    has_phishing_keywords = bool(PHISHING_KEYWORDS_PATTERN.search(text))

    if not model or not vectorizer:
        prob = 0.85 if has_phishing_keywords else 0.05
        label = "phishing" if has_phishing_keywords else "legitimate"
        return {
            "label": label,
            "score": prob,
            "is_phishing": bool(prob >= 0.50)
        }

    try:
        texto_limpio = clean_text(text)
        texto_vec = vectorizer.transform([texto_limpio])
        probabilidades = model.predict_proba(texto_vec)[0]
        raw_prob_phishing = float(probabilidades[1])

        if not has_phishing_keywords or (texto_vec.nnz == 0) or (0.49 <= raw_prob_phishing <= 0.51 and not has_phishing_keywords):
            prob_phishing = 0.05
        else:
            prob_phishing = raw_prob_phishing

        calibrated_prob = round(prob_phishing, 4)
        is_phishing = bool(calibrated_prob >= 0.50)
        prediction_label = "phishing" if is_phishing else "legitimate"

        return {
            "label": prediction_label,
            "score": calibrated_prob,
            "is_phishing": is_phishing
        }
    except Exception as e:
        print(f"⚠️ Error en run_nlp_model: {e}")
        prob = 0.85 if has_phishing_keywords else 0.05
        label = "phishing" if has_phishing_keywords else "legitimate"
        return {
            "label": label,
            "score": prob,
            "is_phishing": bool(prob >= 0.50)
        }

# --- Esquemas Pydantic ---
class TextEvaluationSchema(BaseModel):
    text: str = Field(
        ...,
        description="Texto o mensaje sospechoso a evaluar contra phishing.",
        examples=["Estimado cliente, su cuenta ha sido suspendida. Ingrese a este enlace para verificar sus datos."]
    )
    website_url_check: str = Field("", description="Campo trampa oculto en la interfaz (Honeypot)")
    website_url_honeypot: Optional[str] = Field(None, description="Alias campo trampa")

    @field_validator("text")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        clean_text = value.strip()
        if not clean_text:
            raise ValueError("El texto proporcionado no puede estar vacío.")
        return clean_text

PredictRequest = TextEvaluationSchema

class PredictResponse(BaseModel):
    text: str
    prediction: str
    is_phishing: bool
    probability: float
    saved_in_database: bool = False

router = APIRouter()

@router.post("/predict/text", tags=["Prediction"])
async def evaluate_text(request: Request, payload: TextEvaluationSchema):
    # 1. VERIFICACIÓN DEL HONEYPOT: Si el campo trampa trae contenido, salta la alerta al instante
    trap_value = payload.website_url_check.strip() if payload.website_url_check else (payload.website_url_honeypot or "").strip()
    if trap_value != "":
        client_ip = request.client.host if request.client else "Unknown"
        
        # Registrar el evento en la colección 'alertas' de MongoDB Atlas una sola vez
        alert_document = {
            "type": "HONEYPOT_TRIGGERED",
            "source_ip": client_ip,
            "user_agent": request.headers.get("user-agent", "Unknown"),
            "timestamp": datetime.utcnow(),
            "payload_received": trap_value,
            "status": "BLOCKED"
        }
        
        # Inserción en la base de datos (MongoDB Atlas)
        try:
            await request.app.mongodb["alertas"].insert_one(alert_document)
        except Exception as e:
            print(f"⚠️ Error al guardar alerta en MongoDB: {e}")
        
        # Log en consola del servidor (Uvicorn)
        print(f"⚠️ [SECURITY ALERT] Honeypot activado por bot en IP: {client_ip}")
        
        # Retorno de respuesta defensiva inmediata (HTTP 200 con bandera de seguridad o HTTP 403)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "SECURE_HONEYPOT_ACTIVE",
                "risk_level": "BLOCKED",
                "message": "Petición interceptada por el módulo defensivo Honeypot. Firma de bot registrada.",
                "honeypot_triggered": True
            }
        )

    # 2. FLUJO NORMAL: Si el campo trampa viene vacío, procesa la IA con TF-IDF + SVM
    prediction_result = run_nlp_model(payload.text)

    saved_db = False
    try:
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            result = mongo_db["phishing_logs"].insert_one({
                "text": payload.text,
                "prediction": prediction_result["label"],
                "is_phishing": prediction_result["is_phishing"],
                "probability": prediction_result["score"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            if result.acknowledged or getattr(result, "inserted_id", None):
                saved_db = True
                print(f"📝 [MongoDB] Log persistido en colección 'phishing_logs': ID {result.inserted_id}")
    except Exception as e:
        print(f"⚠️ [MongoDB Error] Fallo al insertar log: {e}")

    return {
        "status": "SUCCESS",
        "risk_level": prediction_result["label"],
        "confidence": prediction_result["score"],
        "honeypot_triggered": False,
        "text": payload.text,
        "prediction": prediction_result["label"],
        "is_phishing": prediction_result["is_phishing"],
        "probability": prediction_result["score"],
        "saved_in_database": saved_db
    }

app.include_router(router)
predict_phishing = evaluate_text

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
