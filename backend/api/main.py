import os
import sys
import joblib
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

# Inicialización de FastAPI
app = FastAPI(
    title="FinTech Fraud Guard — API de Clasificación IA",
    description="Servicio API REST para la detección en tiempo real de transacciones anómalas.",
    version="1.0.0"
)

# Rutas adaptadas a la estructura real de tu workspace
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODELS_DIR = os.path.join(BASE_DIR, "models", "saved")

SCALER_PATH = os.path.join(MODELS_DIR, "scaler.joblib")
SVM_PATH = os.path.join(MODELS_DIR, "svm_model.joblib")
KNN_PATH = os.path.join(MODELS_DIR, "knn_model.joblib")
MLP_PATH = os.path.join(MODELS_DIR, "mlp_model.joblib")

loaded_artifacts = {}

@app.on_event("startup")
def load_models():
    """Carga el escalador y los modelos serializados en memoria al iniciar la API."""
    try:
        if not os.path.exists(SCALER_PATH):
            print(f"[ADVERTENCIA] No se encontró el escalador en {SCALER_PATH}")
        else:
            loaded_artifacts["scaler"] = joblib.load(SCALER_PATH)

        loaded_artifacts["svm"] = joblib.load(SVM_PATH) if os.path.exists(SVM_PATH) else None
        loaded_artifacts["knn"] = joblib.load(KNN_PATH) if os.path.exists(KNN_PATH) else None
        loaded_artifacts["mlp"] = joblib.load(MLP_PATH) if os.path.exists(MLP_PATH) else None

        print("[ÉXITO] Artefactos de IA cargados correctamente.")
    except Exception as e:
        print(f"[ERROR] Fallo al cargar artefactos: {str(e)}")

# Esquema Pydantic para validar peticiones JSON
class TransactionInput(BaseModel):
    transaction_id: str = Field(..., example="TXN_99812", description="Identificador de la transacción")
    amount: float = Field(..., example=650.00, description="Monto de la transacción")
    time_step: int = Field(..., example=42, description="Secuencia temporal")
    v1_feature: float = Field(..., example=3.15, description="Característica de comportamiento v1")
    v2_feature: float = Field(..., example=-2.80, description="Característica de comportamiento v2")

# Esquema de respuesta JSON
class TransactionPredictionResponse(BaseModel):
    transaction_id: str
    model_used: str
    fraud_probability: float
    is_fraud_predicted: int
    risk_level: str
    threshold_applied: float

@app.get("/", tags=["Estado"])
def root():
    return {
        "status": "online",
        "service": "FinTech Fraud Guard - API REST",
        "available_models": [k for k in ["svm", "knn", "mlp"] if loaded_artifacts.get(k) is not None]
    }

@app.post("/predict/transaction", response_model=TransactionPredictionResponse, tags=["Inferencia IA"])
def predict_transaction(
    payload: TransactionInput,
    model_type: str = Query("svm", description="Modelo a evaluar: 'svm', 'knn' o 'mlp'")
):
    """
    Evalúa el riesgo de una transacción recibida en formato JSON utilizando el modelo especificado.
    """
    model_key = model_type.lower()
    if model_key not in loaded_artifacts or loaded_artifacts[model_key] is None:
        raise HTTPException(
            status_code=400,
            detail=f"El modelo '{model_type}' no se encuentra cargado en el servidor."
        )

    scaler = loaded_artifacts.get("scaler")
    model = loaded_artifacts.get(model_key)

    if not scaler:
        raise HTTPException(status_code=500, detail="El escalador de datos no está disponible.")

    # Inferencia con las características de entrada
    raw_features = np.array([[
        payload.amount,
        payload.time_step,
        payload.v1_feature,
        payload.v2_feature
    ]])

    scaled_features = scaler.transform(raw_features)
    threshold = 0.30

    if hasattr(model, "predict_proba"):
        proba = float(model.predict_proba(scaled_features)[0][1])
    else:
        proba = float(model.predict(scaled_features)[0])

    is_fraud = 1 if proba >= threshold else 0

    if proba < 0.30:
        risk = "BAJO"
    elif proba < 0.70:
        risk = "MEDIO"
    else:
        risk = "ALTO"

    return TransactionPredictionResponse(
        transaction_id=payload.transaction_id,
        model_used=model_type.upper(),
        fraud_probability=round(proba, 4),
        is_fraud_predicted=is_fraud,
        risk_level=risk,
        threshold_applied=threshold
    )