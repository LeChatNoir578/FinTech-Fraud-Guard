import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../theme/app_theme.dart';
import '../services/api_service.dart';

class UserWebView extends StatefulWidget {
  const UserWebView({super.key});

  @override
  State<UserWebView> createState() => _UserWebViewState();
}

class _UserWebViewState extends State<UserWebView> {
  WebViewController? _controller;
  bool _isLoading = true;
  bool _hasError = false;
  String _targetUrl = "http://192.168.120.159:8000/dashboard";

  @override
  void initState() {
    super.initState();
    _determineUrl();
    _initWebView();
  }

  void _determineUrl() {
    _targetUrl = "${ApiService.baseUrl}/dashboard";
  }

  void _initWebView() {
    _determineUrl();
    try {
      final controller = WebViewController()
        ..setJavaScriptMode(JavaScriptMode.unrestricted)
        ..setBackgroundColor(AppTheme.background)
        ..setNavigationDelegate(
          NavigationDelegate(
            onPageStarted: (String url) {
              if (mounted) {
                setState(() {
                  _isLoading = true;
                  _hasError = false;
                });
              }
            },
            onPageFinished: (String url) {
              if (mounted) {
                setState(() {
                  _isLoading = false;
                  _hasError = false;
                });
              }
            },
            onWebResourceError: (WebResourceError error) {
              debugPrint("WebView Error: ${error.description} (code: ${error.errorCode}, isMainFrame: ${error.isForMainFrame})");
              // Solo cambiar a estado de error si falla la carga del frame principal
              if (error.isForMainFrame ?? true) {
                if (mounted) {
                  setState(() {
                    _isLoading = false;
                    _hasError = true;
                  });
                }
              }
            },
          ),
        )
        ..loadRequest(Uri.parse(_targetUrl));

      _controller = controller;
    } catch (e) {
      debugPrint("Error inicializando WebViewController: $e");
      if (mounted) {
        setState(() {
          _isLoading = false;
          _hasError = true;
        });
      }
    }
  }

  /// Refresca la carga hacia `http://<HOST_IP>:8000/dashboard`
  void _refreshDashboard() {
    _determineUrl();
    if (_controller != null) {
      setState(() {
        _isLoading = true;
        _hasError = false;
      });
      _controller!.loadRequest(Uri.parse(_targetUrl));
    } else {
      _initWebView();
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
              "Dirección IP del host FastAPI:",
              style: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: ipController,
              decoration: const InputDecoration(
                labelText: "Host IP",
                hintText: "ej. 192.168.120.159",
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
              }
              Navigator.pop(ctx);
            },
            child: const Text("Conectar"),
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
                Text("Panel Personal de Usuario", style: TextStyle(fontSize: 16)),
              ],
            ),
            Text(
              _targetUrl,
              style: const TextStyle(color: AppTheme.textSecondary, fontSize: 10),
              overflow: TextOverflow.ellipsis,
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
            tooltip: "Recargar Dashboard",
            onPressed: _refreshDashboard,
          ),
        ],
      ),
      body: Column(
        children: [
          // Barra de Telemetría y Honeypot del Frontend
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            color: AppTheme.surface,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      width: 10,
                      height: 10,
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
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: AppTheme.surfaceLight,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: AppTheme.borderGold),
                  ),
                  child: const Text(
                    "OWASP TOP 10",
                    style: TextStyle(color: AppTheme.goldLight, fontSize: 10),
                  ),
                ),
              ],
            ),
          ),
          if (_isLoading)
            const LinearProgressIndicator(
              backgroundColor: AppTheme.surfaceLight,
              valueColor: AlwaysStoppedAnimation<Color>(AppTheme.goldImperial),
            ),

          // Contenedor del WebView o Fallback Interactivo
          Expanded(
            child: _hasError || _controller == null
                ? _buildFallbackNativeView()
                : WebViewWidget(controller: _controller!),
          ),
        ],
      ),
    );
  }

  /// Vista nativa integrada para plataformas o entornos donde el webview local no esté disponible
  Widget _buildFallbackNativeView() {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 600),
          child: Card(
            color: AppTheme.surface,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
              side: const BorderSide(color: AppTheme.borderGold),
            ),
            child: Padding(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.dashboard_outlined, color: AppTheme.goldImperial, size: 28),
                      SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          "Formulario de Evaluación de Riesgo",
                          style: TextStyle(
                            color: AppTheme.goldImperial,
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    "Conectando a: $_targetUrl",
                    style: const TextStyle(color: AppTheme.goldLight, fontSize: 12),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    "Si el WebView no carga en el dispositivo físico, verifica que tu teléfono esté en la misma red Wi-Fi y pulsa 'Recargar' o cambia la IP del host.",
                    style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                  ),
                  const Divider(height: 28),

                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: _showServerConfigDialog,
                          icon: const Icon(Icons.settings_ethernet, size: 16),
                          label: const Text("Cambiar Host IP"),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: _refreshDashboard,
                          icon: const Icon(Icons.refresh, size: 16),
                          label: const Text("Reintentar"),
                        ),
                      ),
                    ],
                  ),
                  const Divider(height: 28),

                  // Campos nativos sincronizados con el dashboard
                  const Text("ID de Usuario:", style: TextStyle(color: AppTheme.textPrimary, fontSize: 12)),
                  const SizedBox(height: 6),
                  TextFormField(
                    initialValue: "USR-9921",
                    readOnly: true,
                    style: const TextStyle(color: AppTheme.textPrimary),
                    decoration: const InputDecoration(prefixIcon: Icon(Icons.person_outline, size: 18)),
                  ),
                  const SizedBox(height: 14),

                  const Text("Monto de la Transferencia (MXN):", style: TextStyle(color: AppTheme.textPrimary, fontSize: 12)),
                  const SizedBox(height: 6),
                  TextFormField(
                    initialValue: "250.00",
                    readOnly: true,
                    style: const TextStyle(color: AppTheme.textPrimary),
                    decoration: const InputDecoration(prefixIcon: Icon(Icons.attach_money, size: 18)),
                  ),
                  const SizedBox(height: 14),

                  const Text("Descripción / Concepto:", style: TextStyle(color: AppTheme.textPrimary, fontSize: 12)),
                  const SizedBox(height: 6),
                  TextFormField(
                    initialValue: "Pago ordinario de colegiatura mensual",
                    readOnly: true,
                    maxLines: 2,
                    style: const TextStyle(color: AppTheme.textPrimary),
                  ),
                  const SizedBox(height: 20),

                  // Honeypot Field Status
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceLight,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppTheme.borderColor),
                    ),
                    child: const Row(
                      children: [
                        Icon(Icons.lock_outline, color: AppTheme.goldImperial, size: 18),
                        SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            "Trampa Honeypot: Campo invisible 'website_url_honeypot' activo para mitigación de bots.",
                            style: TextStyle(color: AppTheme.goldLight, fontSize: 11),
                          ),
                        ),
                      ],
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
}
