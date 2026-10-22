import os
import sys
import pandas as pd
import numpy as np

def run_eda(file_path: str):
    """
    Carga el conjunto de datos de transacciones, realiza una limpieza inicial
    y analiza el desbalance de clases entre transacciones normales y anómalas.
    """
    print("=" * 65)
    print("FINTECH FRAUD GUARD — ANÁLISIS EXPLORATORIO DE DATOS (EDA)")
    print("=" * 65)

    # 1. Carga y verificación del archivo
    if not os.path.exists(file_path):
        print(f"[ERROR] No se encontró el archivo de datos en: {file_path}")
        print("Asegúrate de colocar tu conjunto de datos (ej. transactions.csv) en la ruta indicada.")
        sys.exit(1)

    print(f"[INFO] Cargando dataset desde: {file_path} ...")
    df = pd.read_csv(file_path)
    
    print("\n[1] INFORMACIÓN GENERAL DEL DATASET:")
    print(f" - Total de registros (filas): {df.shape[0]:,}")
    print(f" - Total de columnas: {df.shape[1]}")
    print(f" - Nombres de columnas: {list(df.columns)}")

    # 2. Verificación de nulos y duplicados
    print("\n[2] LIMPIEZA INICIAL Y CALIDAD DE DATOS:")
    
    null_counts = df.isnull().sum()
    total_nulls = null_counts.sum()
    print(f" - Total de valores nulos/faltantes: {total_nulls}")
    
    if total_nulls > 0:
        print("   Detalle de nulos por columna:")
        print(null_counts[null_counts > 0])
        df = df.dropna()
        print(f"   -> Registros tras eliminar nulos: {df.shape[0]:,}")
    else:
        print("   -> Sin valores faltantes detectados.")

    duplicates = df.duplicated().sum()
    print(f" - Registros duplicados detectados: {duplicates:,}")
    if duplicates > 0:
        df = df.drop_duplicates()
        print(f"   -> Registros tras eliminar duplicados: {df.shape[0]:,}")

    # 3. Detección de la variable objetivo
    target_col = None
    possible_targets = ['is_fraud', 'Class', 'label', 'fraude', 'target', 'isFraud']
    
    for col in possible_targets:
        if col in df.columns:
            target_col = col
            break

    if not target_col:
        print("\n[ADVERTENCIA] No se identificó automáticamente la columna objetivo.")
        print(f"Asegúrate de que la columna de fraude se llame una de estas: {possible_targets}")
        return df

    # 4. Identificación del desbalance de clases
    print(f"\n[3] ANÁLISIS DE DESBALANCE DE CLASES (Variable: '{target_col}'):")
    class_counts = df[target_col].value_counts()
    class_percentages = df[target_col].value_counts(normalize=True) * 100

    normal_count = class_counts.get(0, 0)
    fraud_count = class_counts.get(1, 0)

    print(f" - Transacciones Normales (Clase 0): {normal_count:,} ({class_percentages.get(0, 0):.2f}%)")
    print(f" - Transacciones Anómalas/Fraude (Clase 1): {fraud_count:,} ({class_percentages.get(1, 0):.2f}%)")

    # Diagnóstico técnico del desbalance
    imbalance_ratio = (fraud_count / normal_count) * 100 if normal_count > 0 else 0
    print(f" - Proporción de Fraude: {imbalance_ratio:.2f}% respecto a normales.")
    
    print("\n[4] DIAGNÓSTICO Y RECOMENDACIONES TÉCNICAS:")
    if imbalance_ratio < 5:
        print(" [!] ALERTA: Desbalance SEVERO de clases detectado.")
        print("     Recomendación para la etapa de modelado:")
        print("     1. Usar métricas orientadas a desbalance: ROC-AUC, Precision, Recall y F1-Score.")
        print("     2. Evitar usar 'Accuracy' (Exactitud) como métrica principal.")
        print("     3. Considerar técnicas de rebalanceo (SMOTE, Undersampling o pesos de clase).")
    else:
        print(" [i] El conjunto de datos presenta una distribución con balance moderado.")

    print("\n" + "=" * 65)
    print("ANÁLISIS EXPLORATORIO COMPLETADO CON ÉXITO")
    print("=" * 65)
    
    return df

if __name__ == "__main__":
    # Ruta predeterminada para el dataset
    DATA_PATH = os.path.join("data", "raw", "transactions.csv")
    
    # Permitir pasar una ruta desde consola si el dataset está en otro lugar
    if len(sys.argv) > 1:
        DATA_PATH = sys.argv[1]
        
    run_eda(DATA_PATH)