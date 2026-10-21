document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('transactionForm');
    
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

        // 4. Ejecución del análisis
        updateUIState('loading');
        
        try {
            // Simulador de latencia para el backend de FastAPI
            await new Promise(resolve => setTimeout(resolve, 1200));
            
            // Mock de los modelos de IA de Arón y NLP de David
            const result = mockPredict(safeData);
            
            // 5. Renderizado seguro en el DOM
            renderResults(result);

        } catch (error) {
            console.error("Error conectando con la API:", error);
            alert("Error de red al intentar contactar el servidor de análisis.");
            updateUIState('reset');
        }
    });
});

function mockPredict(data) {
    // Lógica básica de simulación para pruebas de frontend
    const isHighRisk = data.amount > 10000 || data.description.toLowerCase().includes('urgente') || data.location.includes('desconocida');
    const isMediumRisk = data.amount > 5000 && !isHighRisk;

    let riskLevel = 'Bajo';
    if (isHighRisk) riskLevel = 'Alto';
    else if (isMediumRisk) riskLevel = 'Medio';

    return {
        riskLevel: riskLevel,
        probability: isHighRisk ? (Math.random() * (99 - 75) + 75).toFixed(1) : (Math.random() * (20 - 2) + 2).toFixed(1),
        nlpAnalysis: isHighRisk ? "Indicadores de manipulación psicológica detectados en el texto." : "Texto estándar sin indicadores de phishing.",
        triggerAlert: isHighRisk
    };
}

function updateUIState(state) {
    if (state === 'loading') {
        document.getElementById('fraudProbability').textContent = "...";
        document.getElementById('nlpResult').innerHTML = '<span class="placeholder-text">Analizando parámetros...</span>';
        document.getElementById('englishAlert').style.display = 'none';
        
        document.getElementById('lblBajo').classList.remove('active');
        document.getElementById('lblMedio').classList.remove('active');
        document.getElementById('lblAlto').classList.remove('active');
    } else if (state === 'reset') {
        document.getElementById('fraudProbability').textContent = "--";
        document.getElementById('nlpResult').innerHTML = '<span class="placeholder-text">Esperando ejecución del modelo...</span>';
    }
}

function renderResults(data) {
    document.getElementById('fraudProbability').textContent = data.probability;
    
    // Activar el color correspondiente al riesgo
    if (data.riskLevel === 'Bajo') document.getElementById('lblBajo').classList.add('active');
    else if (data.riskLevel === 'Medio') document.getElementById('lblMedio').classList.add('active');
    else if (data.riskLevel === 'Alto') document.getElementById('lblAlto').classList.add('active');

    // Insertar resultado NLP (como safeData ya fue sanitizado al inicio, el flujo interno es seguro)
    const nlpBox = document.getElementById('nlpResult');
    nlpBox.textContent = data.nlpAnalysis;
    nlpBox.style.color = data.triggerAlert ? 'var(--high-risk)' : 'var(--text-main)';

    // Desplegar la alerta de Emily si el riesgo es alto
    const alertBox = document.getElementById('englishAlert');
    if (data.triggerAlert) {
        alertBox.style.display = 'block';
        alertBox.innerHTML = `<strong>Security Alert:</strong> If suspicious activity is detected, the system will flag the transaction for review and temporarily block the funds.`;
    }
}