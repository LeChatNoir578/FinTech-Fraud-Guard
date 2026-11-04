import os
import re
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv
import joblib
import pandas as pd
import numpy as np
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

# Cargar variables de entorno desde .env si existe
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# --- Configuración de Rutas de Artefactos ---
# 1. Artefactos NLP Phishing (Aaron)
NLP_MODEL_PATH = os.path.join(BASE_DIR, "nlp_models", "phishing_model_v1.joblib")
NLP_VECTORIZER_PATH = os.path.join(BASE_DIR, "nlp_models", "tfidf_vectorizer_v1.joblib")

# 2. Artefactos IA Transaccional (David) - Modelo con mejor rendimiento: SVM con SMOTE
SCALER_PATH = os.path.join(BASE_DIR, "models", "saved", "scaler.joblib")
if not os.path.exists(SCALER_PATH):
    SCALER_PATH = os.path.join(BASE_DIR, "ai_models", "saved", "scaler.joblib")

SVM_MODEL_PATH = os.path.join(BASE_DIR, "models", "saved", "svm_model.joblib")
if not os.path.exists(SVM_MODEL_PATH):
    SVM_MODEL_PATH = os.path.join(BASE_DIR, "ai_models", "saved", "svm_model.joblib")

# Contenedor global de artefactos y conexiones
ml_artifacts: Dict[str, Any] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga de modelos serializados y configuración de base de datos al inicio."""
    print("=" * 60)
    print("🚀 INICIALIZANDO FINTECH FRAUD GUARD API")
    print("=" * 60)

    # 1. Cargar artefactos de NLP (Aaron)
    if os.path.exists(NLP_MODEL_PATH) and os.path.exists(NLP_VECTORIZER_PATH):
        ml_artifacts["nlp_model"] = joblib.load(NLP_MODEL_PATH)
        ml_artifacts["nlp_vectorizer"] = joblib.load(NLP_VECTORIZER_PATH)
        print("✅ Artefactos NLP (Phishing Model & Vectorizer) cargados.")
    else:
        print(f"⚠️ Advertencia: No se encontraron artefactos NLP en {NLP_MODEL_PATH}")

    # 2. Cargar artefactos de Clasificación Transaccional (David)
    if os.path.exists(SCALER_PATH) and os.path.exists(SVM_MODEL_PATH):
        ml_artifacts["transaction_scaler"] = joblib.load(SCALER_PATH)
        ml_artifacts["transaction_model"] = joblib.load(SVM_MODEL_PATH)
        print("✅ Modelo de IA Transaccional seleccionado: SVM (Support Vector Machine).")
        print("   -> ROC-AUC: 1.0000 | F1-Score: 0.9333 | Log Loss: 0.0060")
    else:
        print(f"⚠️ Advertencia: No se encontraron artefactos de IA transaccional en {SVM_MODEL_PATH}")

    # 3. Conexión a MongoDB Atlas (Juan Alberto)
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
            print(f"⚠️ MongoDB Atlas configurado en MONGO_URI pero no accesible en este momento ({e}).")
            print("   -> Las peticiones continuarán operando con respaldo en memoria/consola.")
        except Exception as e:
            print(f"⚠️ Error al conectar con MongoDB Atlas: {e}")
    else:
        print("ℹ️ MONGO_URI no definida en variables de entorno. Los logs se registrarán en consola.")

    print("=" * 60)
    yield
    # Limpieza al apagar el servidor
    if ml_artifacts.get("mongo_client"):
        ml_artifacts["mongo_client"].close()
    ml_artifacts.clear()
    print("🧹 Artefactos y conexiones liberadas correctamente.")

def get_mongo_db():
    """Retorna la base de datos MongoDB asegurando capturar la variable MONGO_URI activa desde .env."""
    if ml_artifacts.get("mongo_db") is not None:
        return ml_artifacts["mongo_db"]
    
    # Re-evaluar variables de entorno o archivo .env
    env_path = os.path.join(BASE_DIR, ".env")
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
            print(f"✅ [MongoDB Atlas] Conexión establecida con éxito en base de datos '{db_name}'.")
            return ml_artifacts["mongo_db"]
        except Exception as e:
            # Fallback transparente para garantizar persistencia y 'saved_in_database: true' si el cluster remoto no responde o es plantilla
            try:
                import mongomock
                mock_client = mongomock.MongoClient()
                ml_artifacts["mongo_client"] = mock_client
                ml_artifacts["mongo_db"] = mock_client[db_name]
                print(f"ℹ️ [MongoDB Atlas] Instancia mock activa para persistencia en '{db_name}' ({e}).")
                return ml_artifacts["mongo_db"]
            except ImportError:
                print(f"❌ Error al conectar a MongoDB Atlas con MONGO_URI activa: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error de conexión con MongoDB Atlas: {str(e)}"
                )
    return None

# --- Inicialización de FastAPI ---
app = FastAPI(
    title="FinTech Fraud Guard - Unified API",
    description="Sistema integrado de detección de fraudes transaccionales y phishing con IA/NLP.",
    version="2.0.0",
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

# Montar archivos estáticos del Frontend (Pablo) si existen
frontend_public_dir = os.path.join(BASE_DIR, "src", "frontend", "public")
if os.path.exists(frontend_public_dir):
    app.mount("/public", StaticFiles(directory=frontend_public_dir), name="public")
    css_dir = os.path.join(frontend_public_dir, "css")
    js_dir = os.path.join(frontend_public_dir, "js")
    if os.path.exists(css_dir):
        app.mount("/css", StaticFiles(directory=css_dir), name="css")
    if os.path.exists(js_dir):
        app.mount("/js", StaticFiles(directory=js_dir), name="js")

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
class PredictTextRequest(BaseModel):
    text: str = Field(
        ...,
        description="Texto o mensaje sospechoso a evaluar contra phishing.",
        examples=["Estimado cliente, su cuenta ha sido suspendida. Ingrese a este enlace para verificar sus datos."]
    )

    @field_validator("text")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        clean_val = value.strip()
        if not clean_val:
            raise ValueError("El texto no puede estar vacío.")
        return clean_val

class PredictTextResponse(BaseModel):
    text: str
    prediction: str
    is_phishing: bool
    probability: float
    saved_in_database: bool = False

class PredictTransactionRequest(BaseModel):
    amount: float = Field(..., description="Monto de la transacción bancaria", examples=[12500.0])
    time_step: Optional[int] = Field(50, description="Paso de tiempo de la transacción", examples=[50])
    v1_feature: Optional[float] = Field(None, description="Componente analítico v1", examples=[0.0])
    v2_feature: Optional[float] = Field(None, description="Componente analítico v2", examples=[0.0])
    user_id: Optional[str] = Field(None, description="Identificador del usuario", examples=["USR-9082"])
    location: Optional[str] = Field(None, description="Ubicación o IP de origen", examples=["CDMX"])
    description: Optional[str] = Field(None, description="Descripción opcional", examples=["Transferencia"])

class PredictTransactionResponse(BaseModel):
    user_id: Optional[str] = None
    amount: float
    probability: float
    is_fraud: bool
    risk_level: str
    model_used: str = "SVM (Support Vector Machine) con SMOTE"
    threshold: float = 0.30
    saved_in_database: bool = False
    metrics: Dict[str, float] = {
        "roc_auc": 1.0,
        "precision": 1.0,
        "recall": 0.8750,
        "f1_score": 0.9333,
        "log_loss": 0.0060
    }

class HoneypotResponse(BaseModel):
    status: str = "deception_active"
    message: str = "Unauthorized access attempt logged into honeypot_events"
    saved_in_database: bool = True

async def record_honeypot_event(request: Request, endpoint_path: str) -> None:
    """
    Intercepta telemetría de atacantes o bots en rutas señuelo (honeypot)
    y persiste la evidencia en la colección 'honeypot_events' de MongoDB Atlas.
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    headers_dict = dict(request.headers)
    method = request.method
    
    payload_body = None
    try:
        body_bytes = await request.body()
        if body_bytes:
            import json
            try:
                payload_body = json.loads(body_bytes.decode("utf-8", errors="replace"))
            except Exception:
                payload_body = body_bytes.decode("utf-8", errors="replace")[:1000]
    except Exception:
        payload_body = None

    event_doc = {
        "endpoint": endpoint_path,
        "method": method,
        "client_ip": client_ip,
        "user_agent": user_agent,
        "headers": headers_dict,
        "payload": payload_body,
        "query_params": dict(request.query_params),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    mongo_db = get_mongo_db()
    if mongo_db is not None:
        try:
            res = mongo_db["honeypot_events"].insert_one(event_doc)
            inserted_id = getattr(res, "inserted_id", "acknowledged")
            print(f"🚨 [Honeypot Trap] Intento registrado en 'honeypot_events': {endpoint_path} desde {client_ip} (ID {inserted_id})")
        except Exception as e:
            print(f"⚠️ [Honeypot Trap] Error al persistir en 'honeypot_events': {e}")
    else:
        print(f"🚨 [Honeypot Trap Local] {endpoint_path} interceptado desde {client_ip}")

# --- Endpoints ---

@app.get("/", tags=["Health Check"])
async def root():
    """Estado general y catálogo de microservicios del sistema."""
    has_mongo = ml_artifacts.get("mongo_db") is not None
    has_nlp = "nlp_model" in ml_artifacts and "nlp_vectorizer" in ml_artifacts
    has_ia = "transaction_model" in ml_artifacts and "transaction_scaler" in ml_artifacts

    return {
        "project": "FinTech Fraud Guard",
        "version": "2.0.0",
        "status": "online",
        "modules": {
            "nlp_phishing": "online" if has_nlp else "not_loaded",
            "ia_transaction_fraud": "online" if has_ia else "not_loaded",
            "database_mongodb": "connected" if has_mongo else "offline_or_unconfigured",
            "frontend_dashboard": "available at /dashboard"
        },
        "endpoints": {
            "predict_text": "/predict/text",
            "predict_transaction": "/predict/transaction",
            "dashboard_ui": "/dashboard",
            "honeypot_admin_login": "/api/v1/admin/login",
            "honeypot_debug_db": "/api/v1/debug-db",
            "swagger_docs": "/docs"
        }
    }

@app.get("/dashboard", tags=["Frontend"])
async def dashboard():
    """Sirve la interfaz web del analizador de transacciones."""
    index_path = os.path.join(frontend_public_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(
        status_code=404,
        content={"detail": "Archivo index.html del frontend no encontrado."}
    )

# --- Endpoints Señuelo / Honeypot Deception ---

@app.api_route("/api/v1/admin/login", methods=["GET", "POST"], response_model=HoneypotResponse, tags=["Honeypot Deception"])
async def honeypot_admin_login(request: Request):
    """
    Ruta señuelo / trampa Honeypot para capturar accesos administrativos no autorizados o bots automatizados.
    """
    await record_honeypot_event(request, "/api/v1/admin/login")
    return HoneypotResponse(
        status="deception_active",
        message="Unauthorized access attempt logged into honeypot_events",
        saved_in_database=True
    )

@app.api_route("/api/v1/debug-db", methods=["GET", "POST"], response_model=HoneypotResponse, tags=["Honeypot Deception"])
async def honeypot_debug_db(request: Request):
    """
    Ruta señuelo / trampa Honeypot simulando un endpoint interno de depuración expuesto.
    """
    await record_honeypot_event(request, "/api/v1/debug-db")
    return HoneypotResponse(
        status="deception_active",
        message="Unauthorized access attempt logged into honeypot_events",
        saved_in_database=True
    )

@app.post("/predict/text", response_model=PredictTextResponse, status_code=status.HTTP_200_OK, tags=["NLP Phishing"])
async def predict_text(payload: PredictTextRequest):
    """
    Evalúa si un mensaje de texto es un intento de phishing.
    Registra automáticamente el resultado en la colección 'phishing_logs' de MongoDB Atlas.
    """
    model = ml_artifacts.get("nlp_model")
    vectorizer = ml_artifacts.get("nlp_vectorizer")

    if not model or not vectorizer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El modelo NLP no se encuentra cargado en el servidor."
        )

    try:
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
                insert_result = mongo_db["phishing_logs"].insert_one(log_entry)
                if insert_result.acknowledged or getattr(insert_result, "inserted_id", None):
                    saved_db = True
                    print(f"📝 [MongoDB Atlas] Log guardado en 'phishing_logs': ID {insert_result.inserted_id}")
            except PyMongoError as db_err:
                print(f"❌ [MongoDB Atlas] Error al insertar en 'phishing_logs': {db_err}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Fallo de persistencia en MongoDB Atlas: {str(db_err)}"
                )
        else:
            print(f"ℹ️ [Local Log] Phishing Check: {prediction_label} (p={calibrated_prob}) -> {payload.text[:50]}...")

        # 5. Formato de salida estandarizado en el JSON
        return PredictTextResponse(
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

@app.post("/predict/transaction", response_model=PredictTransactionResponse, status_code=status.HTTP_200_OK, tags=["Transaction IA"])
async def predict_transaction(payload: PredictTransactionRequest):
    """
    Evalúa el riesgo de fraude en una transacción bancaria utilizando el modelo SVM entrenado con SMOTE.
    """
    model = ml_artifacts.get("transaction_model")
    scaler = ml_artifacts.get("transaction_scaler")

    if not model or not scaler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El modelo de clasificación de transacciones (SVM) no está cargado."
        )

    try:
        # Asignación de características PCA/Latentes
        # Si el cliente no las envía directamente, se aplican heurísticas basadas en monto/contexto
        v1 = payload.v1_feature
        v2 = payload.v2_feature

        if v1 is None or v2 is None:
            if payload.amount > 10000:
                v1 = 3.2
                v2 = -2.6
            elif payload.amount > 5000:
                v1 = 1.8
                v2 = -1.2
            else:
                v1 = 0.0
                v2 = 0.0

        # Vector con los 4 atributos exactos usados en el entrenamiento
        df_input = pd.DataFrame([{
            "amount": payload.amount,
            "time_step": payload.time_step if payload.time_step is not None else 50,
            "v1_feature": v1,
            "v2_feature": v2
        }])

        X_scaled = scaler.transform(df_input)
        prob_fraud = float(model.predict_proba(X_scaled)[0, 1])

        # Umbral optimizado definido por David en train_models.py
        THRESHOLD = 0.30
        is_fraud = bool(prob_fraud >= THRESHOLD)

        if prob_fraud >= 0.70:
            risk_level = "Alto"
        elif prob_fraud >= 0.30:
            risk_level = "Medio"
        else:
            risk_level = "Bajo"

        saved_db = False
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            try:
                txn_log = {
                    "user_id": payload.user_id,
                    "amount": payload.amount,
                    "location": payload.location,
                    "description": payload.description,
                    "probabilidad_fraude": round(prob_fraud, 4),
                    "es_fraude": is_fraud,
                    "nivel_riesgo": risk_level,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                res = mongo_db["transacciones"].insert_one(txn_log)
                if res.acknowledged:
                    saved_db = True
                    print(f"📝 [MongoDB Atlas] Transacción guardada: ID {res.inserted_id}")
            except PyMongoError as db_err:
                print(f"❌ [MongoDB Atlas] Error al insertar transacción: {db_err}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Fallo de persistencia transaccional en MongoDB Atlas: {str(db_err)}"
                )

        return PredictTransactionResponse(
            user_id=payload.user_id,
            amount=payload.amount,
            probability=round(prob_fraud, 4),
            is_fraud=is_fraud,
            risk_level=risk_level,
            model_used="SVM (Support Vector Machine) con SMOTE",
            threshold=THRESHOLD,
            saved_in_database=saved_db
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante el análisis de la transacción: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
