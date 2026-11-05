import os
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
import joblib

# --- Configuración de Rutas de Artefactos ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "phishing_model_v1.joblib")
VECTORIZER_PATH = os.path.join(BASE_DIR, "tfidf_vectorizer_v1.joblib")

# Contenedor global de artefactos ML
ml_artifacts = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga persistente de artefactos ML al iniciar la API."""
    if not os.path.exists(MODEL_PATH) or not os.path.exists(VECTORIZER_PATH):
        raise FileNotFoundError(
            f"No se encontraron los artefactos en {MODEL_PATH} o {VECTORIZER_PATH}."
        )

    ml_artifacts["model"] = joblib.load(MODEL_PATH)
    ml_artifacts["vectorizer"] = joblib.load(VECTORIZER_PATH)
    print("✅ Artefactos ML cargados exitosamente.")
    yield
    ml_artifacts.clear()
    print("🧹 Artefactos ML liberados.")

# --- Inicialización de FastAPI ---
app = FastAPI(
    title="FinTech Fraud Guard - NLP Phishing Detection API",
    description="API para la detección de mensajes de phishing en tiempo real mediante NLP.",
    version="1.0.0",
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

# --- Endpoints ---
@app.get("/", tags=["Health Check"])
async def root():
    return {
        "project": "FinTech Fraud Guard",
        "module": "NLP Phishing Detection",
        "status": "online",
        "author": "Aaron"
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

        return PredictResponse(
            text=payload.text,
            prediction=label,
            probability=round(final_prob, 4),
            is_phishing=is_phishing
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante el procesamiento del texto: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
