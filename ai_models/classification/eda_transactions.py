import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def run_eda(file_path: str):
    """
    Carga el conjunto de datos de transacciones, realiza limpieza inicial,
    analiza el desbalance de clases y guarda la gráfica para la documentación.
    """
    print("=" * 65)
    print("FINTECH FRAUD GUARD — ANÁLISIS EXPLORATORIO DE DATOS (EDA)")
    print("=" * 65)

    if not os.path.exists(file_path):
        print(f"[ERROR] No se encontró el archivo de datos en: {file_path}")
        sys.exit(1)

    print(f"[INFO] Cargando dataset desde: {file_path} ...")
    df = pd.read_csv(file_path)
    
    # 1. Resumen General
    print("\n[1] INFORMACIÓN GENERAL DEL DATASET:")
    print(f" - Total de registros (filas): {df.shape[0]:,}")
    print(f" - Total de características (columnas): {df.shape[1]}")
    print(f" - Columnas detectadas: {list(df.columns)}")

    # 2. Limpieza Inicial
    print("\n[2] LIMPIEZA INICIAL Y CALIDAD DE DATOS:")
    null_counts = df.isnull().sum()
    total_nulls = null_counts.sum()
    print(f" - Total de valores nulos/faltantes: {total_nulls}")
    
    if total_nulls > 0:
        df = df.dropna()
        print(f"   -> Registros tras eliminar nulos: {df.shape[0]:,}")
    else:
        print("   -> Sin valores faltantes detectados.")

    duplicates = df.duplicated().sum()
    print(f" - Registros duplicados detectados: {duplicates:,}")
    if duplicates > 0:
        df = df.drop_duplicates()
        print(f"   -> Registros tras eliminar duplicados: {df.shape[0]:,}")

    # 3. Variable Objetivo
    target_col = None
    possible_targets = ['is_fraud', 'Class', 'label', 'fraude', 'target', 'isFraud']
    
    for col in possible_targets:
        if col in df.columns:
            target_col = col
            break

    if not target_col:
        print("\n[ERROR] No se encontró la columna objetivo.")
        return df

    # 4. Desbalance de Clases
    print(f"\n[3] ANÁLISIS DE DESBALANCE DE CLASES (Variable: '{target_col}'):")
    class_counts = df[target_col].value_counts()
    class_percentages = df[target_col].value_counts(normalize=True) * 100

    normal_count = class_counts.get(0, 0)
    fraud_count = class_counts.get(1, 0)

    print(f" - Transacciones Normales (Clase 0): {normal_count:,} ({class_percentages.get(0, 0):.2f}%)")
    print(f" - Transacciones Anómalas/Fraude (Clase 1): {fraud_count:,} ({class_percentages.get(1, 0):.2f}%)")

    # 5. Generar y Guardar Gráfica de Apoyo
    assets_dir = os.path.join("docs", "assets")
    os.makedirs(assets_dir, exist_ok=True)
    chart_path = os.path.join(assets_dir, "class_distribution.png")

    plt.figure(figsize=(7, 4.5))
    bars = plt.bar(['Legítimas (0)', 'Fraude (1)'], [normal_count, fraud_count], color=['#2ec4b6', '#e71d36'])
    plt.title("Distribución de Clases: Transacciones Normales vs. Anómalas", fontsize=11, fontweight='bold')
    plt.ylabel("Cantidad de Transacciones")
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval + 10, f'{int(yval):,}', ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()
    plt.savefig(chart_path, dpi=300)
    plt.close()

    print(f"\n[ÉXITO] Gráfica de distribución guardada en: {chart_path}")
    print("\n" + "=" * 65)
    print("ANÁLISIS EXPLORATORIO COMPLETADO")
    print("=" * 65)
    
    return df

if __name__ == "__main__":
    DATA_PATH = os.path.join("data", "raw", "transactions.csv")
    if len(sys.argv) > 1:
        DATA_PATH = sys.argv[1]
    run_eda(DATA_PATH)