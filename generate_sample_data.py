import os
import pandas as pd
import numpy as np

# 1. Crear automáticamente la carpeta data/raw/ en la raíz si no existe
os.makedirs(os.path.join("data", "raw"), exist_ok=True)

# 2. Generar 1,000 transacciones sintéticas
np.random.seed(42)
n_samples = 1000

data = {
    "transaction_id": [f"TXN_{i:05d}" for i in range(1, n_samples + 1)],
    "amount": np.round(np.random.exponential(scale=100, size=n_samples), 2),
    "time_step": np.random.randint(1, 100, size=n_samples),
    "v1_feature": np.random.normal(0, 1, size=n_samples),
    "v2_feature": np.random.normal(0, 1, size=n_samples),
    "is_fraud": np.random.choice([0, 1], size=n_samples, p=[0.98, 0.02])
}

df = pd.DataFrame(data)
output_path = os.path.join("data", "raw", "transactions.csv")
df.to_csv(output_path, index=False)

print(f"[ÉXITO] Dataset de prueba generado correctamente en: {output_path}")
print(f"Total de registros: {len(df)} | Fraudes simulados: {df['is_fraud'].sum()}")