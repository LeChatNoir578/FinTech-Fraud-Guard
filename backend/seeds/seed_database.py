import os
import sys
import json
from dotenv import load_dotenv
from pymongo import MongoClient
import bson.json_util

# Cargar variables de entorno
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

MONGO_URI = os.getenv("MONGO_URI")

def seed():
    if not MONGO_URI or "usuario_ejemplo" in MONGO_URI or "<usuario>" in MONGO_URI:
        print("❌ Error: MONGO_URI en .env contiene valores de plantilla.")
        print("   Por favor reemplaza <usuario> y <password> con tus credenciales reales de MongoDB Atlas.")
        print(f"   URI actual: {MONGO_URI}")
        return

    print("=" * 60)
    print("🌱 INICIANDO CARGA DE SEMILLAS A MONGODB ATLAS")
    print("=" * 60)
    print(f"📡 Conectando a MongoDB Atlas...")

    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        
        # Determinar base de datos
        db_name = "sistema_financiero"
        try:
            default_db = client.get_default_database()
            if default_db is not None:
                db_name = default_db.name
        except Exception:
            pass

        db = client[db_name]
        print(f"✅ Conexión exitosa a la base de datos: '{db_name}'")

        seeds_dir = os.path.dirname(os.path.abspath(__file__))
        seed_files = {
            "usuarios": "usuarios.json",
            "cuentas": "cuentas.json",
            "transacciones": "transacciones.json",
            "alertas": "alertas.json"
        }

        for collection_name, filename in seed_files.items():
            filepath = os.path.join(seeds_dir, filename)
            if not os.path.exists(filepath):
                print(f"⚠️ Archivo no encontrado: {filepath}")
                continue

            with open(filepath, "r", encoding="utf-8") as f:
                raw_data = f.read()

            documents = bson.json_util.loads(raw_data)
            if not isinstance(documents, list):
                documents = [documents]

            collection = db[collection_name]
            
            # Insertar o actualizar documentos
            inserted_count = 0
            for doc in documents:
                doc_id = doc.get("_id")
                if doc_id:
                    res = collection.replace_one({"_id": doc_id}, doc, upsert=True)
                    inserted_count += 1
                else:
                    collection.insert_one(doc)
                    inserted_count += 1

            total_in_collection = collection.count_documents({})
            print(f"📦 Colección '{collection_name}': {inserted_count} documentos cargados (Total en BD: {total_in_collection})")

        print("=" * 60)
        print("🎉 Semillas cargadas exitosamente en MongoDB Atlas.")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Error al conectar o insertar en MongoDB Atlas: {e}")

if __name__ == "__main__":
    seed()
