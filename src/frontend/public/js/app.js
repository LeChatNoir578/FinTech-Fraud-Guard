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
            // Alerta por Sanitización OWASP / Caracteres Prohibidos (Imperativo + First Conditional)
            alert("[SECURITY ALERT] Invalid characters detected! Stop the input. If you include special symbols, the system will block your request immediately.");
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
            const isFraud = Boolean(transactionRes.is_fraud);
            const isPhishing = Boolean(nlpRes.is_phishing);
            const nlpProbability = parseFloat(nlpRes.probability || 0);
            const fraudProbability = (parseFloat(transactionRes.probability || 0) * 100).toFixed(1);
            const nlpProbabilityPercent = (nlpProbability * 100).toFixed(1);

            // Nivel de riesgo combinado consolidado
            let combinedRiskLevel = transactionRes.risk_level || 'Bajo';
            if (nlpProbability > 0.70 || (isPhishing && isFraud)) {
                combinedRiskLevel = 'Alto';
            } else if (isPhishing || combinedRiskLevel === 'Medio') {
                combinedRiskLevel = 'Medio';
            } else {
                combinedRiskLevel = 'Bajo';
            }

            // Formateo del mensaje analítico de NLP
            let nlpMessage = "";
            if (nlpProbability > 0.70 || isPhishing) {
                nlpMessage = `[ALERTA PHISHING] Probabilidad: ${nlpProbabilityPercent}% — Patrón de ingeniería social detectado en la descripción.`;
            } else {
                nlpMessage = `Texto verificado sin indicios de phishing (Riesgo estimado: ${nlpProbabilityPercent}%).`;
            }

            const combinedResult = {
                riskLevel: combinedRiskLevel,
                fraudProbability: fraudProbability,
                nlpProbability: nlpProbabilityPercent,
                nlpAnalysis: nlpMessage,
                triggerAlert: combinedRiskLevel === 'Alto' || nlpProbability > 0.70
            };

            // 5. Renderizado seguro en el DOM (#resultsSection)
            renderResults(combinedResult);

            // Mejora 1: Calibración del Trigger para la Alerta Emergente (Second Conditional)
            if (combinedRiskLevel === 'Alto' || nlpProbability > 0.70) {
                alert("[CRITICAL RISK] If a threat actor attempted a phishing attack, Fraud Guard would isolate the transaction. Please review the input parameters!");
            }

        } catch (error) {
            console.error("Error conectando con la API o Base de Datos:", error);
            // Alerta por fallo de red o estado de base de datos (Imperativo)
            alert("[SYSTEM NOTICE] Check your internet connection or verify the database status before submitting again.");
            updateUIState('reset');
        }
    });
});

function updateUIState(state) {
    const riskLevelElem = document.getElementById('riskLevel');
    const fraudElem = document.getElementById('fraudProbability');
    const nlpProbElem = document.getElementById('nlpProbability');
    const nlpResult = document.getElementById('nlpResult');
    const englishAlert = document.getElementById('englishAlert');
    const lblBajo = document.getElementById('lblBajo');
    const lblMedio = document.getElementById('lblMedio');
    const lblAlto = document.getElementById('lblAlto');

    if (state === 'loading') {
        if (riskLevelElem) {
            riskLevelElem.textContent = "...";
            riskLevelElem.classList.remove('text-success', 'text-warning', 'text-danger');
        }
        if (fraudElem) fraudElem.textContent = "...";
        if (nlpProbElem) nlpProbElem.textContent = "...";
        if (nlpResult) nlpResult.innerHTML = '<span class="placeholder-text">Analizando parámetros y contactando modelos de IA...</span>';
        if (englishAlert) englishAlert.style.display = 'none';

        if (lblBajo) lblBajo.classList.remove('active');
        if (lblMedio) lblMedio.classList.remove('active');
        if (lblAlto) lblAlto.classList.remove('active');
    } else if (state === 'reset') {
        if (riskLevelElem) {
            riskLevelElem.textContent = "--";
            riskLevelElem.classList.remove('text-success', 'text-warning', 'text-danger');
        }
        if (fraudElem) fraudElem.textContent = "--";
        if (nlpProbElem) nlpProbElem.textContent = "--";
        if (nlpResult) nlpResult.innerHTML = '<span class="placeholder-text">Esperando ejecución del modelo...</span>';
        if (englishAlert) englishAlert.style.display = 'none';

        if (lblBajo) lblBajo.classList.remove('active');
        if (lblMedio) lblMedio.classList.remove('active');
        if (lblAlto) lblAlto.classList.remove('active');
    }
}

function renderResults(data) {
    // 1. Elemento del nivel de riesgo (#riskLevel) con clases de color
    const riskLevelElem = document.getElementById('riskLevel');
    if (riskLevelElem) {
        const levelUpper = data.riskLevel.toUpperCase();
        riskLevelElem.textContent = levelUpper;
        riskLevelElem.classList.remove('text-success', 'text-warning', 'text-danger');

        if (levelUpper === 'BAJO') {
            riskLevelElem.classList.add('text-success'); // Verde
        } else if (levelUpper === 'MEDIO') {
            riskLevelElem.classList.add('text-warning'); // Amarillo / Naranja
        } else if (levelUpper === 'ALTO') {
            riskLevelElem.classList.add('text-danger');  // Rojo
        }
    }

    // 2. Renderizado de porcentajes dinámicos en #resultsSection
    const fraudElem = document.getElementById('fraudProbability');
    if (fraudElem) {
        fraudElem.textContent = data.fraudProbability;
    }

    const nlpProbElem = document.getElementById('nlpProbability');
    if (nlpProbElem) {
        nlpProbElem.textContent = data.nlpProbability;
    }

    // 3. Activación de los chips en el indicador visual
    const lblBajo = document.getElementById('lblBajo');
    const lblMedio = document.getElementById('lblMedio');
    const lblAlto = document.getElementById('lblAlto');
    
    if (lblBajo) lblBajo.classList.remove('active');
    if (lblMedio) lblMedio.classList.remove('active');
    if (lblAlto) lblAlto.classList.remove('active');

    const levelStr = data.riskLevel.toUpperCase();
    if (levelStr === 'BAJO' && lblBajo) lblBajo.classList.add('active');
    else if (levelStr === 'MEDIO' && lblMedio) lblMedio.classList.add('active');
    else if (levelStr === 'ALTO' && lblAlto) lblAlto.classList.add('active');

    // 4. Inserción de resultado descriptivo de NLP
    const nlpBox = document.getElementById('nlpResult');
    if (nlpBox) {
        nlpBox.textContent = data.nlpAnalysis;
        nlpBox.style.color = data.triggerAlert ? 'var(--high-risk)' : 'var(--text-main)';
    }

    // 5. Despliegue de la Alerta Ejecutiva
    const alertBox = document.getElementById('englishAlert');
    if (alertBox) {
        if (data.triggerAlert) {
            alertBox.style.display = 'block';
            alertBox.innerHTML = `<strong>Security Alert:</strong> If a threat actor attempted a phishing attack, Fraud Guard would isolate the transaction. Please review the input parameters!`;
        } else {
            alertBox.style.display = 'none';
        }
    }
}
