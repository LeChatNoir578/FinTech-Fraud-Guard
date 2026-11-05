import os
import pandas as pd
import numpy as np

os.makedirs(os.path.join("data", "raw"), exist_ok=True)

np.random.seed(42)
n_samples = 2000

# 1. 98% Transacciones normales
n_normal = int(n_samples * 0.98)
normal_data = {
    "transaction_id": [f"TXN_{i:05d}" for i in range(1, n_normal + 1)],
    "amount": np.round(np.random.exponential(scale=50, size=n_normal), 2),
    "time_step": np.random.randint(1, 100, size=n_normal),
    "v1_feature": np.random.normal(0, 1, size=n_normal),
    "v2_feature": np.random.normal(0, 1, size=n_normal),
    "is_fraud": 0
}

# 2. 2% Transacciones anómalas (fraude con características distintas)
n_fraud = n_samples - n_normal
fraud_data = {
    "transaction_id": [f"TXN_{i:05d}" for i in range(n_normal + 1, n_samples + 1)],
    "amount": np.round(np.random.exponential(scale=400, size=n_fraud) + 250, 2),
    "time_step": np.random.randint(1, 100, size=n_fraud),
    "v1_feature": np.random.normal(3.0, 1.0, size=n_fraud),
    "v2_feature": np.random.normal(-2.5, 1.0, size=n_fraud),
    "is_fraud": 1
}

df_normal = pd.DataFrame(normal_data)
df_fraud = pd.DataFrame(fraud_data)

df = pd.concat([df_normal, df_fraud]).sample(frac=1, random_state=42).reset_index(drop=True)

output_path = os.path.join("data", "raw", "transactions.csv")
df.to_csv(output_path, index=False)

print(f"[ÉXITO] Nuevo dataset generado correctamente en: {output_path}")
print(f"Total registros: {len(df)} | Normales: {n_normal} | Fraudes: {n_fraud}")