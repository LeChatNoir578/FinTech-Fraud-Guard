import 'package:flutter/material.dart';
import 'theme/app_theme.dart';
import 'views/login_view.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const FinTechFraudGuardApp());
}

class FinTechFraudGuardApp extends StatelessWidget {
  const FinTechFraudGuardApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FinTech Fraud Guard',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      home: const LoginView(),
    );
  }
}
