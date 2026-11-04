document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('transactionForm');
    
    // Detección dinámica de la URL base de FastAPI (compatible con localhost y archivo local)
    const API_BASE_URL = (window.location.origin && window.location.origin !== "null" && !window.location.protocol.startsWith("file"))
        ? window.location.origin
        : "http://localhost:8000";

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // 1. Recolección de datos crudos
        const rawData = {
            userId: document.getElementById('userId').value,
            amount: parseFloat(document.getElementById('amount').value),
            location: document.getElementById('location').value,
            description: document.getElementById('description').value
        };

        // 2. Hardening OWASP: Sanitización contra XSS usando DOMPurify
        const safeData = {
            userId: DOMPurify.sanitize(rawData.userId.trim()),
            amount: rawData.amount,
            location: DOMPurify.sanitize(rawData.location.trim()),
            description: DOMPurify.sanitize(rawData.description.trim())
        };

        // 3. Hardening OWASP: Validación estática contra inyección SQL/Comandos
        const dangerousPattern = /(\b(SELECT|UPDATE|DELETE|INSERT|DROP|EXEC|UNION)\b)|(;|\||&&|`|\$|<|>)/i;
        if (dangerousPattern.test(safeData.description) || dangerousPattern.test(safeData.location)) {
            alert("[ALERTA DE SEGURIDAD] Caracteres no permitidos detectados. Operación bloqueada.");
            return;
        }

        // 4. Ejecución del análisis conectando con los endpoints de FastAPI
        updateUIState('loading');
        
        try {
            // Petición 1: Evaluación de Fraude Transaccional (IA - David: Modelo SVM con SMOTE)
            const transactionPromise = fetch(`${API_BASE_URL}/predict/transaction`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    amount: safeData.amount,
                    user_id: safeData.userId,
                    location: safeData.location,
                    description: safeData.description
                })
            }).then(async (response) => {
                if (!response.ok) {
                    const errorBody = await response.json().catch(() => ({}));
                    throw new Error(errorBody.detail || `Error HTTP ${response.status} en /predict/transaction`);
                }
                return response.json();
            });

            // Petición 2: Evaluación de Minería de Texto y Phishing (NLP - Aaron + Juan Alberto: MongoDB)
            const textToAnalyze = safeData.description || "Transacción bancaria ordinaria";
            const nlpPromise = fetch(`${API_BASE_URL}/predict/text`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    text: textToAnalyze
                })
            }).then(async (response) => {
                if (!response.ok) {
                    const errorBody = await response.json().catch(() => ({}));
                    throw new Error(errorBody.detail || `Error HTTP ${response.status} en /predict/text`);
                }
                return response.json();
            });

            // Ejecución en paralelo
            const [transactionRes, nlpRes] = await Promise.all([transactionPromise, nlpPromise]);

            // Consolidación de métricas
            const isFraud = transactionRes.is_fraud;
            const isPhishing = nlpRes.is_phishing;
            const fraudProbability = (transactionRes.probability * 100).toFixed(1);

            // Nivel de riesgo combinado ponderado
            let combinedRiskLevel = transactionRes.risk_level;
            if (isPhishing && combinedRiskLevel === 'Bajo') {
                combinedRiskLevel = 'Medio';
            }
            if (isPhishing && isFraud) {
                combinedRiskLevel = 'Alto';
            }

            // Formateo del mensaje analítico de NLP
            let nlpMessage = "";
            if (isPhishing) {
                nlpMessage = `[ALERTA PHISHING] Probabilidad: ${(nlpRes.probability * 100).toFixed(1)}% — Patrón de ingeniería social detectado en la descripción.`;
            } else {
                nlpMessage = `Texto verificado sin indicios de phishing (Riesgo estimado: ${(nlpRes.probability * 100).toFixed(1)}%).`;
            }

            const combinedResult = {
                riskLevel: combinedRiskLevel,
                probability: fraudProbability,
                nlpAnalysis: nlpMessage,
                triggerAlert: isFraud || isPhishing
            };

            // 5. Renderizado seguro en el DOM
            renderResults(combinedResult);

        } catch (error) {
            console.error("Error conectando con la API:", error);
            alert("Error al comunicar con la API de FinTech Fraud Guard: " + error.message);
            updateUIState('reset');
        }
    });
});

function updateUIState(state) {
    if (state === 'loading') {
        document.getElementById('fraudProbability').textContent = "...";
        document.getElementById('nlpResult').innerHTML = '<span class="placeholder-text">Analizando parámetros y contactando modelos de IA...</span>';
        document.getElementById('englishAlert').style.display = 'none';
        
        document.getElementById('lblBajo').classList.remove('active');
        document.getElementById('lblMedio').classList.remove('active');
        document.getElementById('lblAlto').classList.remove('active');
    } else if (state === 'reset') {
        document.getElementById('fraudProbability').textContent = "--";
        document.getElementById('nlpResult').innerHTML = '<span class="placeholder-text">Esperando ejecución del modelo...</span>';
        document.getElementById('lblBajo').classList.remove('active');
        document.getElementById('lblMedio').classList.remove('active');
        document.getElementById('lblAlto').classList.remove('active');
    }
}

function renderResults(data) {
    document.getElementById('fraudProbability').textContent = data.probability;
    
    // Activar el color correspondiente al riesgo
    document.getElementById('lblBajo').classList.remove('active');
    document.getElementById('lblMedio').classList.remove('active');
    document.getElementById('lblAlto').classList.remove('active');

    if (data.riskLevel === 'Bajo') document.getElementById('lblBajo').classList.add('active');
    else if (data.riskLevel === 'Medio') document.getElementById('lblMedio').classList.add('active');
    else if (data.riskLevel === 'Alto') document.getElementById('lblAlto').classList.add('active');

    // Insertar resultado NLP de forma segura
    const nlpBox = document.getElementById('nlpResult');
    nlpBox.textContent = data.nlpAnalysis;
    nlpBox.style.color = data.triggerAlert ? 'var(--high-risk)' : 'var(--text-main)';

    // Desplegar la alerta de Emily si el riesgo es alto o fraude
    const alertBox = document.getElementById('englishAlert');
    if (data.triggerAlert) {
        alertBox.style.display = 'block';
        alertBox.innerHTML = `<strong>Security Alert:</strong> If suspicious activity is detected, the system will flag the transaction for review and temporarily block the funds.`;
    } else {
        alertBox.style.display = 'none';
    }
}
