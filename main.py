import os
import re
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, status
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
            # Intento de ping rápido para validar conectividad
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
        clean_text = value.strip()
        if not clean_text:
            raise ValueError("El texto no puede estar vacío.")
        return clean_text

class PredictTextResponse(BaseModel):
    text: str
    prediction: str
    probability: float
    is_phishing: bool
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
        # 1. Preprocesamiento de texto
        raw_text = payload.text.lower().strip()
        processed_text = re.sub(r"[^\w\s]", "", raw_text)

        # 2. Vectorización TF-IDF
        text_vectorized = vectorizer.transform([processed_text])

        # 3. Inferencia directa
        raw_pred = model.predict(text_vectorized)[0]

        # 4. Cálculo de probabilidad
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

        is_phishing = bool(raw_pred in [1, "phishing", "Phishing"] or prob_phishing >= 0.5)
        label = "phishing" if is_phishing else "normal"
        final_prob = prob_phishing if is_phishing else (1.0 - prob_phishing)
        saved_db = False

        # 5. Registro automático en MongoDB Atlas ('phishing_logs')
        log_entry = {
            "text": payload.text,
            "prediction": label,
            "is_phishing": is_phishing,
            "probability": round(final_prob, 4),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        mongo_db = ml_artifacts.get("mongo_db")
        if mongo_db is not None:
            try:
                mongo_db["phishing_logs"].insert_one(log_entry)
                saved_db = True
                print(f"📝 [MongoDB] Log de phishing guardado: {label} ({final_prob:.2f})")
            except Exception as db_err:
                print(f"⚠️ [MongoDB] Error guardando log en 'phishing_logs': {db_err}")
        else:
            print(f"ℹ️ [Local Log] Phishing: {label} ({final_prob:.2f}) -> {payload.text[:50]}...")

        return PredictTextResponse(
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
        mongo_db = ml_artifacts.get("mongo_db")
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
                mongo_db["transacciones"].insert_one(txn_log)
                saved_db = True
            except Exception as db_err:
                print(f"⚠️ [MongoDB] Error guardando log en 'transacciones': {db_err}")

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
