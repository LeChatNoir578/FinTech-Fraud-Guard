import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../theme/app_theme.dart';
import '../services/api_service.dart';

class UserWebView extends StatefulWidget {
  const UserWebView({super.key});

  @override
  State<UserWebView> createState() => _UserWebViewState();
}

class _UserWebViewState extends State<UserWebView> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  WebViewController? _webViewController;
  bool _isWebLoading = true;
  bool _hasWebError = false;
  String _targetUrl = "http://192.168.120.156:8000/dashboard";
  Timer? _loadTimeoutTimer;

  // Controladores y estado del Formulario Nativo (Requisito 3)
  final _messageController = TextEditingController(text: "");
  final _amountController = TextEditingController(text: "");
  final _userIdController = TextEditingController(text: "");
  final _honeypotController = TextEditingController(text: "");

  bool _isEvaluating = false;
  TextPredictionResult? _evaluationResult;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _determineUrl();
    _initWebView();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _messageController.dispose();
    _amountController.dispose();
    _userIdController.dispose();
    _honeypotController.dispose();
    _loadTimeoutTimer?.cancel();
    super.dispose();
  }

  void _determineUrl() {
    _targetUrl = "${ApiService.baseUrl}/dashboard";
  }

  void _initWebView() {
    _determineUrl();
    _loadTimeoutTimer?.cancel();

    if (kIsWeb) {
      _isWebLoading = false;
      _hasWebError = false;
      return;
    }

    // Timer de seguridad: Si en 8 segundos no responde la URL web, activar fallback
    _loadTimeoutTimer = Timer(const Duration(seconds: 8), () {
      if (mounted && _isWebLoading) {
        setState(() {
          _isWebLoading = false;
          _hasWebError = true;
        });
      }
    });

    try {
      final controller = WebViewController()
        ..setJavaScriptMode(JavaScriptMode.unrestricted)
        ..setBackgroundColor(AppTheme.surface)
        ..setNavigationDelegate(
          NavigationDelegate(
            onPageStarted: (String url) {
              if (mounted) {
                setState(() {
                  _isWebLoading = true;
                  _hasWebError = false;
                });
              }
            },
            onPageFinished: (String url) {
              _loadTimeoutTimer?.cancel();
              if (mounted) {
                setState(() {
                  _isWebLoading = false;
                  _hasWebError = false;
                });
              }
            },
            onWebResourceError: (WebResourceError error) {
              debugPrint("WebView error: ${error.description} (isMainFrame: ${error.isForMainFrame})");
              if (error.isForMainFrame ?? true) {
                _loadTimeoutTimer?.cancel();
                if (mounted) {
                  setState(() {
                    _isWebLoading = false;
                    _hasWebError = true;
                  });
                }
              }
            },
          ),
        )
        ..loadRequest(Uri.parse(_targetUrl));

      _webViewController = controller;
    } catch (e) {
      debugPrint("Error inicializando WebViewController: $e");
      if (mounted) {
        setState(() {
          _isWebLoading = false;
          _hasWebError = true;
        });
      }
    }
  }

  void _refreshDashboard() {
    _determineUrl();
    if (kIsWeb) {
      setState(() {
        _isWebLoading = false;
        _hasWebError = false;
      });
      return;
    }
    if (_webViewController != null) {
      setState(() {
        _isWebLoading = true;
        _hasWebError = false;
      });
      _webViewController!.loadRequest(Uri.parse(_targetUrl));
    } else {
      _initWebView();
    }
  }

  Future<void> _evaluateMessage() async {
    // Verificación de trampa Honeypot en móvil
    if (_honeypotController.text.trim().isNotEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          backgroundColor: AppTheme.riskHigh,
          content: Text(
            "[HONEYPOT DETECTED] Automated bot pattern identified! Stop the automated script.",
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
        ),
      );
      return;
    }

    final text = _messageController.text.trim();
    if (text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Ingresa un mensaje o texto para evaluar")),
      );
      return;
    }

    final amount = double.tryParse(_amountController.text.trim()) ?? 150.0;
    final userId = _userIdController.text.trim().isNotEmpty ? _userIdController.text.trim() : "USR-MOBILE";

    setState(() => _isEvaluating = true);
    final result = await ApiService.evaluateSuspiciousMessage(
      text: text,
      amount: amount,
      userId: userId,
    );

    if (mounted) {
      setState(() {
        _isEvaluating = false;
        _evaluationResult = result;
      });
    }
  }

  void _showServerConfigDialog() {
    final ipController = TextEditingController(text: ApiService.host);
    final portController = TextEditingController(text: ApiService.port.toString());

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surface,
        title: const Text(
          "Configuración de Servidor FastAPI",
          style: TextStyle(color: AppTheme.goldImperial, fontSize: 16),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "Configura la dirección IP local de tu servidor en la red local:",
              style: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: ipController,
              decoration: const InputDecoration(
                labelText: "Host IP",
                hintText: "ej. 192.168.100.23",
              ),
              style: const TextStyle(color: AppTheme.textPrimary),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: portController,
              decoration: const InputDecoration(
                labelText: "Puerto",
                hintText: "8000",
              ),
              keyboardType: TextInputType.number,
              style: const TextStyle(color: AppTheme.textPrimary),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text("Cancelar", style: TextStyle(color: AppTheme.textSecondary)),
          ),
          ElevatedButton(
            onPressed: () {
              final newHost = ipController.text.trim();
              final newPort = int.tryParse(portController.text.trim()) ?? 8000;
              if (newHost.isNotEmpty) {
                ApiService.setNetworkConfig(newHost, newPort);
                _refreshDashboard();
                _evaluateMessage();
              }
              Navigator.pop(ctx);
            },
            child: const Text("Guardar y Conectar"),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.shield_outlined, color: AppTheme.goldImperial, size: 18),
                SizedBox(width: 8),
                Text("Panel de Usuario Normal", style: TextStyle(fontSize: 16)),
              ],
            ),
            Text(
              "Host: ${ApiService.host}:${ApiService.port}",
              style: const TextStyle(color: AppTheme.textSecondary, fontSize: 10),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_ethernet),
            tooltip: "Configurar IP del Host",
            onPressed: _showServerConfigDialog,
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: "Recargar",
            onPressed: () {
              if (_tabController.index == 0) {
                _evaluateMessage();
              } else {
                _refreshDashboard();
              }
            },
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppTheme.goldImperial,
          labelColor: AppTheme.goldImperial,
          unselectedLabelColor: AppTheme.textSecondary,
          tabs: const [
            Tab(icon: Icon(Icons.analytics_outlined), text: "Evaluador Nativo"),
            Tab(icon: Icon(Icons.web_asset), text: "Dashboard Web"),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          // PESTAÑA 1: Formulario Nativo en Dart (Requisito 3)
          _buildNativeEvaluationForm(),

          // PESTAÑA 2: WebView Embebido (Requisito 2)
          _buildWebViewSection(),
        ],
      ),
    );
  }

  /// Pestaña 1: Formulario nativo interactivo para evaluar mensajes y textos sospechosos
  Widget _buildNativeEvaluationForm() {
    final res = _evaluationResult;
    Color badgeColor = AppTheme.riskLow;
    if (res != null) {
      if (res.riskLevel == "ALTO") {
        badgeColor = AppTheme.riskHigh;
      } else if (res.riskLevel == "MEDIO") {
        badgeColor = AppTheme.riskMedium;
      }
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 650),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Barra de telemetría y Honeypot
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(
                  color: AppTheme.surface,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppTheme.borderColor),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: const BoxDecoration(
                            shape: BoxShape.circle,
                            color: AppTheme.riskLow,
                          ),
                        ),
                        const SizedBox(width: 8),
                        const Text(
                          "STATUS: SECURE (HONEYPOT ACTIVE)",
                          style: TextStyle(
                            color: AppTheme.riskLow,
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    Text(
                      res?.isLocalFallback == true ? "MODO LOCAL" : "FASTAPI CONECTADO",
                      style: TextStyle(
                        color: res?.isLocalFallback == true ? AppTheme.riskMedium : AppTheme.goldLight,
                        fontSize: 9,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),

              // Tarjeta del Formulario
              Card(
                color: AppTheme.surface,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                  side: const BorderSide(color: AppTheme.borderGold),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(18.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.edit_note, color: AppTheme.goldImperial, size: 22),
                          SizedBox(width: 8),
                          Text(
                            "Evaluación de Texto y Mensajes",
                            style: TextStyle(
                              color: AppTheme.goldImperial,
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),

                      // Campo: Mensaje / Texto sospechoso
                      const Text(
                        "Mensaje / Texto sospechoso:",
                        style: TextStyle(color: AppTheme.textPrimary, fontSize: 12, fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 6),
                      TextFormField(
                        controller: _messageController,
                        maxLines: 3,
                        style: const TextStyle(color: AppTheme.textPrimary, fontSize: 13),
                        decoration: InputDecoration(
                          hintText: "Ingresa el texto o mensaje a evaluar...",
                          hintStyle: const TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                          filled: true,
                          fillColor: AppTheme.surfaceLight,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                            borderSide: const BorderSide(color: AppTheme.borderColor),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                            borderSide: const BorderSide(color: AppTheme.goldImperial),
                          ),
                        ),
                      ),
                      const SizedBox(height: 14),

                      // Parámetros secundarios (Monto e ID)
                      Row(
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text("Monto (\$ MXN):", style: TextStyle(color: AppTheme.textPrimary, fontSize: 11)),
                                const SizedBox(height: 4),
                                TextFormField(
                                  controller: _amountController,
                                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                  style: const TextStyle(color: AppTheme.textPrimary, fontSize: 12),
                                  decoration: InputDecoration(
                                    prefixIcon: const Icon(Icons.attach_money, size: 16),
                                    hintText: "0.00",
                                    hintStyle: const TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                                    filled: true,
                                    fillColor: AppTheme.surfaceLight,
                                    contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text("ID Usuario:", style: TextStyle(color: AppTheme.textPrimary, fontSize: 11)),
                                const SizedBox(height: 4),
                                TextFormField(
                                  controller: _userIdController,
                                  style: const TextStyle(color: AppTheme.textPrimary, fontSize: 12),
                                  decoration: InputDecoration(
                                    prefixIcon: const Icon(Icons.person_outline, size: 16),
                                    hintText: "Ej. USR-9082",
                                    hintStyle: const TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                                    filled: true,
                                    fillColor: AppTheme.surfaceLight,
                                    contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 18),

                      // Botón principal: Evaluar Fraude
                      ElevatedButton.icon(
                        onPressed: _isEvaluating ? null : _evaluateMessage,
                        icon: _isEvaluating
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                              )
                            : const Icon(Icons.security, size: 20),
                        label: Text(
                          _isEvaluating ? "Analizando con IA y NLP..." : "Evaluar Fraude",
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                        ),
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          backgroundColor: AppTheme.goldImperial,
                          foregroundColor: Colors.black,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // Tarjeta de Resultados del Badge de Riesgo (Requisito 3)
              if (res != null) ...[
                Card(
                  color: AppTheme.surface,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                    side: BorderSide(color: badgeColor.withValues(alpha: 0.6), width: 1.5),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(18.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text(
                              "Nivel de Riesgo Consolidado:",
                              style: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                              decoration: BoxDecoration(
                                color: badgeColor.withValues(alpha: 0.15),
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: badgeColor),
                              ),
                              child: Text(
                                res.riskLevel,
                                style: TextStyle(
                                  color: badgeColor,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 14,
                                  letterSpacing: 1.0,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const Divider(height: 24),

                        // Métricas en vivo
                        Row(
                          children: [
                            Expanded(
                              child: _buildMetricTile(
                                label: "Phishing (NLP)",
                                value: "${res.phishingProbability.toStringAsFixed(1)}%",
                                isDanger: res.phishingProbability >= 50.0,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: _buildMetricTile(
                                label: "Fraude (SVM)",
                                value: "${res.fraudProbability.toStringAsFixed(1)}%",
                                isDanger: res.fraudProbability >= 30.0,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),

                        // Alerta Ejecutiva en Inglés
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: AppTheme.surfaceLight,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: AppTheme.borderColor),
                          ),
                          child: Text(
                            res.englishAlert,
                            style: const TextStyle(
                              color: AppTheme.goldLight,
                              fontSize: 11,
                              fontStyle: FontStyle.italic,
                              height: 1.3,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ] else ...[
                Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    color: AppTheme.surface,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: AppTheme.borderGold),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.info_outline, color: AppTheme.goldImperial, size: 24),
                      SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          "Ingresa el texto o mensaje a evaluar y pulsa 'Evaluar Fraude' para analizar el nivel de riesgo en tiempo real.",
                          style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMetricTile({required String label, required String value, required bool isDanger}) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.surfaceLight,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              color: isDanger ? AppTheme.riskHigh : AppTheme.riskLow,
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  /// Pestaña 2: WebView Embebido con manejo de errores y fallback
  Widget _buildWebViewSection() {
    if (kIsWeb) {
      return _buildWebPlatformView();
    }
    return Column(
      children: [
        if (_isWebLoading)
          const LinearProgressIndicator(
            backgroundColor: AppTheme.surfaceLight,
            valueColor: AlwaysStoppedAnimation<Color>(AppTheme.goldImperial),
          ),

        Expanded(
          child: _hasWebError || _webViewController == null
              ? _buildWebFallbackOverlay()
              : WebViewWidget(controller: _webViewController!),
        ),
      ],
    );
  }

  Widget _buildWebPlatformView() {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 550),
          child: Card(
            color: AppTheme.surface,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
              side: const BorderSide(color: AppTheme.borderGold),
            ),
            child: Padding(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Icon(Icons.language, color: AppTheme.goldImperial, size: 48),
                  const SizedBox(height: 12),
                  const Text(
                    "Dashboard Web de FinTech Fraud Guard",
                    textAlign: TextAlign.center,
                    style: TextStyle(color: AppTheme.goldImperial, fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    "Estás utilizando la aplicación en entorno Web.\nPuedes evaluar mensajes directamente con el 'Evaluador Nativo' o consultar el dashboard HTML en:\n$_targetUrl",
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13, height: 1.4),
                  ),
                  const Divider(height: 28),
                  ElevatedButton.icon(
                    onPressed: () {
                      _tabController.animateTo(0);
                    },
                    icon: const Icon(Icons.analytics_outlined),
                    label: const Text("Ir al Evaluador de Mensajes"),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.goldImperial,
                      foregroundColor: Colors.black,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  /// Overlay que se muestra si la URL web HTTP no responde o falla
  Widget _buildWebFallbackOverlay() {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 550),
          child: Card(
            color: AppTheme.surface,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
              side: const BorderSide(color: AppTheme.borderGold),
            ),
            child: Padding(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Icon(Icons.wifi_off_outlined, color: AppTheme.riskMedium, size: 48),
                  const SizedBox(height: 12),
                  const Text(
                    "Servidor Web No Disponible",
                    textAlign: TextAlign.center,
                    style: TextStyle(color: AppTheme.goldImperial, fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    "No se pudo cargar la interfaz web en:\n$_targetUrl",
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    "Verifica que tu teléfono físico esté conectado a la misma red Wi-Fi que la PC. Puedes usar inmediatamente el Evaluador Nativo mientras reconectas:",
                    textAlign: TextAlign.center,
                    style: TextStyle(color: AppTheme.textPrimary, fontSize: 13),
                  ),
                  const Divider(height: 28),

                  ElevatedButton.icon(
                    onPressed: () {
                      _tabController.animateTo(0);
                    },
                    icon: const Icon(Icons.analytics_outlined),
                    label: const Text("Usar Evaluador Nativo"),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.goldImperial,
                      foregroundColor: Colors.black,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: _showServerConfigDialog,
                          icon: const Icon(Icons.settings_ethernet, size: 16),
                          label: const Text("Cambiar Host IP"),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: _refreshDashboard,
                          icon: const Icon(Icons.refresh, size: 16),
                          label: const Text("Reintentar"),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
