// Carga las variables del archivo .env ubicado en la raíz del proyecto
require('dotenv').config({ path: '../.env' });

const express = require('express');
const cors = require('cors');
const mongoose = require('mongoose');
const conectarDB = require('./config/db');

const app = express();

// Conectar a la base de datos de MongoDB Atlas
conectarDB();

// Middlewares
app.use(cors());
app.use(express.json());

// Ruta de prueba inicial
app.get('/', (req, res) => {
  res.send('API FinTech-Fraud-Guard funcionando correctamente');
});

// --- RUTAS DE CONSULTA (GET) ---

// 1. Obtener usuarios
app.get('/api/usuarios', async (req, res) => {
  try {
    const db = mongoose.connection.db;
    const usuarios = await db.collection('usuarios').find({}).toArray();
    res.json(usuarios);
  } catch (error) {
    res.status(500).json({ mensaje: 'Error al obtener usuarios', error: error.message });
  }
});

// 2. Obtener cuentas
app.get('/api/cuentas', async (req, res) => {
  try {
    const db = mongoose.connection.db;
    const cuentas = await db.collection('cuentas').find({}).toArray();
    res.json(cuentas);
  } catch (error) {
    res.status(500).json({ mensaje: 'Error al obtener cuentas', error: error.message });
  }
});

// 3. Obtener transacciones
app.get('/api/transacciones', async (req, res) => {
  try {
    const db = mongoose.connection.db;
    const transacciones = await db.collection('transacciones').find({}).toArray();
    res.json(transacciones);
  } catch (error) {
    res.status(500).json({ mensaje: 'Error al obtener transacciones', error: error.message });
  }
});

// 4. Obtener alertas
app.get('/api/alertas', async (req, res) => {
  try {
    const db = mongoose.connection.db;
    const alertas = await db.collection('alertas').find({}).toArray();
    res.json(alertas);
  } catch (error) {
    res.status(500).json({ mensaje: 'Error al obtener alertas', error: error.message });
  }
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`🚀 Servidor corriendo en el puerto ${PORT}`);
});