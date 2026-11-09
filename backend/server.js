// Carga las variables del archivo .env ubicado en la raíz del proyecto
require('dotenv').config({ path: '../.env' });

const express = require('express');
const cors = require('cors');
const conectarDB = require('./config/db');

const app = express();

// Conectar a la base de datos de MongoDB Atlas
conectarDB();

// Middlewares
app.use(cors());
app.use(express.json());

// Ruta de prueba
app.get('/', (req, res) => {
  res.send('API FinTech-Fraud-Guard funcionando correctamente');
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`🚀 Servidor corriendo en el puerto ${PORT}`);
});