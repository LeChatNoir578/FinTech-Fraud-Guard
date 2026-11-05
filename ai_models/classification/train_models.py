import os
import sys
import warnings
import joblib
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from imblearn.over_sampling import SMOTE
from sklearn.metrics import (
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
    log_loss,
    confusion_matrix
)

# Ocultar advertencias futuras de Scikit-Learn
warnings.filterwarnings('ignore')

def train_classification_models(data_path: str, models_output_dir: str):
    print("=" * 70)
    print("FINTECH FRAUD GUARD — ENTRENAMIENTO DE MODELOS DE CLASIFICACIÓN")
    print("=" * 70)

    if not os.path.exists(data_path):
        print(f"[ERROR] No se encontró el dataset en: {data_path}")
        sys.exit(1)

    df = pd.read_csv(data_path)

    target_col = None
    for col in ['is_fraud', 'Class', 'label', 'fraude', 'target', 'isFraud']:
        if col in df.columns:
            target_col = col
            break

    drop_cols = [target_col]
    if 'transaction_id' in df.columns:
        drop_cols.append('transaction_id')

    X = df.drop(columns=drop_cols)
    y = df[target_col]

    # División de datos (80% entrenamiento, 20% prueba)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    # Escalado de características
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    os.makedirs(models_output_dir, exist_ok=True)
    joblib.dump(scaler, os.path.join(models_output_dir, "scaler.joblib"))

    # Aplicar SMOTE en entrenamiento
    print("\n[INFO] Aplicando rebalanceo de clases con SMOTE...")
    smote = SMOTE(random_state=42)
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train_scaled, y_train)

    models = {
        "SVM (Support Vector Machine)": SVC(kernel='rbf', C=1.0, probability=True, random_state=42),
        "KNN (K-Nearest Neighbors)": KNeighborsClassifier(n_neighbors=5, weights='distance'),
        "Red Neuronal (MLP)": MLPClassifier(hidden_layer_sizes=(32, 16), activation='relu', solver='adam', max_iter=600, random_state=42)
    }

    results = []
    THRESHOLD = 0.30  # Umbral ajustado para la detección de fraude desbalanceado

    print("\n" + "-" * 70)
    print(f"EVALUACIÓN DE MODELOS (Umbral de decisión para fraude: {THRESHOLD})")
    print("-" * 70)

    for name, model in models.items():
        print(f"\n[ENTRENANDO] {name}...")
        model.fit(X_train_resampled, y_train_resampled)

        # Probabilidades predichas
        if hasattr(model, "predict_proba"):
            y_prob = model.predict_proba(X_test_scaled)[:, 1]
        else:
            y_prob = model.predict(X_test_scaled)

        # Clasificación binaria según umbral ajustado
        y_pred = (y_prob >= THRESHOLD).astype(int)

        # Métricas obligatorias
        roc_auc = roc_auc_score(y_test, y_prob)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        try:
            loss = log_loss(y_test, y_prob)
        except Exception:
            loss = np.nan

        cm = confusion_matrix(y_test, y_pred)

        print(f"  -> ROC-AUC:             {roc_auc:.4f}")
        print(f"  -> Precisión (Precision): {precision:.4f}")
        print(f"  -> Sensibilidad (Recall): {recall:.4f}")
        print(f"  -> F1-Score:            {f1:.4f}")
        print(f"  -> Log Loss (Entropía): {loss:.4f}" if not np.isnan(loss) else "  -> Log Loss: N/A")
        print(f"  -> Matriz de Confusión:\n{cm}")

        # Serialización (.joblib)
        short_name = name.split()[0].lower() + "_model.joblib"
        joblib.dump(model, os.path.join(models_output_dir, short_name))

        results.append({
            "Modelo": name,
            "ROC-AUC": round(roc_auc, 4),
            "Precision": round(precision, 4),
            "Recall": round(recall, 4),
            "F1-Score": round(f1, 4),
            "Log Loss": round(loss, 4) if not np.isnan(loss) else "N/A"
        })

    print("\n" + "=" * 70)
    print("TABLA COMPARATIVA FINAL")
    print("=" * 70)
    summary_df = pd.DataFrame(results)
    print(summary_df.to_string(index=False))
    print("=" * 70)

if __name__ == "__main__":
    DATA_PATH = os.path.join("data", "raw", "transactions.csv")
    MODELS_DIR = os.path.join("models", "saved")
    train_classification_models(DATA_PATH, MODELS_DIR)