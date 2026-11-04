import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../services/api_service.dart';
import 'user_web_view.dart';
import 'bank_batch_view.dart';

class LoginView extends StatefulWidget {
  const LoginView({super.key});

  @override
  State<LoginView> createState() => _LoginViewState();
}

class _LoginViewState extends State<LoginView> {
  final _formKey = GlobalKey<FormState>();
  final TextEditingController _userController = TextEditingController(text: 'admin@fraudguard.fintech');
  final TextEditingController _passwordController = TextEditingController(text: '••••••••');
  
  String _selectedRole = 'Usuario Normal';
  final List<String> _roles = ['Usuario Normal', 'Entidad Bancaria'];
  bool _obscurePassword = true;

  @override
  void dispose() {
    _userController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _handleLogin() {
    if (_formKey.currentState!.validate()) {
      if (_selectedRole == 'Usuario Normal') {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => const UserWebView()),
        );
      } else {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => const BankBatchView()),
        );
      }
    }
  }

  void _showServerConfigDialog() {
    final ipController = TextEditingController(text: ApiService.host);
    final portController = TextEditingController(text: ApiService.port.toString());

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surface,
        title: const Text("Configuración de Servidor FastAPI", style: TextStyle(color: AppTheme.goldImperial, fontSize: 16)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "Configura la IP de tu PC en la red local para conectar tu dispositivo móvil físico:",
              style: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: ipController,
              decoration: const InputDecoration(labelText: "IP Local del Servidor", hintText: "ej. 192.168.120.159"),
              style: const TextStyle(color: AppTheme.textPrimary),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: portController,
              decoration: const InputDecoration(labelText: "Puerto", hintText: "8000"),
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
                setState(() {});
              }
              Navigator.pop(ctx);
            },
            child: const Text("Guardar"),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 32.0),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 480),
              child: Card(
                color: AppTheme.surface,
                elevation: 8,
                shadowColor: Colors.black.withValues(alpha: 0.6),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                  side: const BorderSide(color: AppTheme.borderGold, width: 1.2),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(32.0),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // Icono y Logo Institucional
                        Center(
                          child: Container(
                            width: 80,
                            height: 80,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              gradient: const RadialGradient(
                                colors: [Color(0x33D4AF37), Colors.transparent],
                              ),
                              border: Border.all(color: AppTheme.goldImperial, width: 1.5),
                            ),
                            child: const Icon(
                              Icons.shield_outlined,
                              color: AppTheme.goldImperial,
                              size: 44,
                            ),
                          ),
                        ),
                        const SizedBox(height: 20),
                        const Text(
                          "FinTech Fraud Guard",
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: AppTheme.goldImperial,
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 0.5,
                          ),
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          "Sistema Inteligente de Detección de Fraude & Phishing",
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 12.5,
                            letterSpacing: 0.2,
                          ),
                        ),
                        const SizedBox(height: 14),

                        // Indicador de IP del Servidor FastAPI para Dispositivos Físicos
                        Center(
                          child: InkWell(
                            onTap: _showServerConfigDialog,
                            borderRadius: BorderRadius.circular(20),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                              decoration: BoxDecoration(
                                color: AppTheme.surfaceLight,
                                borderRadius: BorderRadius.circular(20),
                                border: Border.all(color: AppTheme.borderGold),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  const Icon(Icons.wifi, color: AppTheme.goldImperial, size: 14),
                                  const SizedBox(width: 6),
                                  Text(
                                    "Host API: ${ApiService.host}:${ApiService.port}",
                                    style: const TextStyle(color: AppTheme.goldLight, fontSize: 11, fontWeight: FontWeight.w600),
                                  ),
                                  const SizedBox(width: 6),
                                  const Icon(Icons.edit, color: AppTheme.textSecondary, size: 12),
                                ],
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 24),

                        // Selector de Rol (Dropdown)
                        const Text(
                          "Selecciona tu Perfil / Rol:",
                          style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                          decoration: BoxDecoration(
                            color: AppTheme.surfaceLight,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: AppTheme.borderGold, width: 1),
                          ),
                          child: DropdownButtonHideUnderline(
                            child: DropdownButton<String>(
                              value: _selectedRole,
                              isExpanded: true,
                              dropdownColor: AppTheme.surface,
                              icon: const Icon(Icons.arrow_drop_down, color: AppTheme.goldImperial),
                              style: const TextStyle(
                                color: AppTheme.textPrimary,
                                fontSize: 14,
                                fontWeight: FontWeight.w500,
                              ),
                              items: _roles.map((role) {
                                return DropdownMenuItem<String>(
                                  value: role,
                                  child: Row(
                                    children: [
                                      Icon(
                                        role == 'Usuario Normal'
                                            ? Icons.person_outline
                                            : Icons.account_balance_outlined,
                                        color: AppTheme.goldImperial,
                                        size: 20,
                                      ),
                                      const SizedBox(width: 12),
                                      Text(role),
                                    ],
                                  ),
                                );
                              }).toList(),
                              onChanged: (newVal) {
                                if (newVal != null) {
                                  setState(() => _selectedRole = newVal);
                                }
                              },
                            ),
                          ),
                        ),
                        const SizedBox(height: 20),

                        // Campo Usuario / Email
                        const Text(
                          "Usuario o Correo Institucional:",
                          style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 8),
                        TextFormField(
                          controller: _userController,
                          style: const TextStyle(color: AppTheme.textPrimary),
                          decoration: const InputDecoration(
                            hintText: "ej. usuario@banco.com",
                            prefixIcon: Icon(Icons.email_outlined, color: AppTheme.textSecondary),
                          ),
                          validator: (value) {
                            if (value == null || value.trim().isEmpty) {
                              return "Por favor ingresa tu usuario.";
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: 20),

                        // Campo Contraseña
                        const Text(
                          "Contraseña:",
                          style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 8),
                        TextFormField(
                          controller: _passwordController,
                          obscureText: _obscurePassword,
                          style: const TextStyle(color: AppTheme.textPrimary),
                          decoration: InputDecoration(
                            hintText: "Ingresa tu contraseña",
                            prefixIcon: const Icon(Icons.lock_outline, color: AppTheme.textSecondary),
                            suffixIcon: IconButton(
                              icon: Icon(
                                _obscurePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                                color: AppTheme.textSecondary,
                              ),
                              onPressed: () {
                                setState(() => _obscurePassword = !_obscurePassword);
                              },
                            ),
                          ),
                          validator: (value) {
                            if (value == null || value.trim().isEmpty) {
                              return "Por favor ingresa tu contraseña.";
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: 32),

                        // Botón de Inicio de Sesión
                        ElevatedButton.icon(
                          onPressed: _handleLogin,
                          icon: const Icon(Icons.arrow_forward, size: 18),
                          label: Text(
                            "Ingresar como $_selectedRole",
                            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(height: 20),

                        // Pie Informativo de Seguridad
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: const Color(0x1AD4AF37),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: const Color(0x33D4AF37)),
                          ),
                          child: const Row(
                            children: [
                              Icon(Icons.verified_user_outlined, color: AppTheme.goldImperial, size: 18),
                              SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  "Módulos Honeypot y Redes IA activos para salvaguarda en tiempo real.",
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
          ),
        ),
      ),
    );
  }
}
