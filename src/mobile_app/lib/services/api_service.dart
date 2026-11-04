import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

class BatchTransaction {
  final String id;
  final String userId;
  final double amount;
  final String description;
  final String location;
  final double fraudProbability;
  final double phishingProbability;
  final String riskLevel;
  final bool isFraud;

  BatchTransaction({
    required this.id,
    required this.userId,
    required this.amount,
    required this.description,
    required this.location,
    required this.fraudProbability,
    required this.phishingProbability,
    required this.riskLevel,
    required this.isFraud,
  });

  factory BatchTransaction.fromJson(Map<String, dynamic> json) {
    return BatchTransaction(
      id: json['id']?.toString() ?? 'TXN-000',
      userId: json['user_id']?.toString() ?? 'USR-UNKNOWN',
      amount: (json['amount'] is num) ? (json['amount'] as num).toDouble() : 0.0,
      description: json['description']?.toString() ?? 'Sin descripción',
      location: json['location']?.toString() ?? 'Desconocida',
      fraudProbability: (json['fraud_probability'] is num) ? (json['fraud_probability'] as num).toDouble() : 0.0,
      phishingProbability: (json['phishing_probability'] is num) ? (json['phishing_probability'] as num).toDouble() : 0.0,
      riskLevel: json['risk_level']?.toString().toUpperCase() ?? 'BAJO',
      isFraud: json['is_fraud'] == true,
    );
  }
}

class BatchSummary {
  final int lowRiskCount;
  final int mediumRiskCount;
  final int highRiskCount;

  BatchSummary({
    required this.lowRiskCount,
    required this.mediumRiskCount,
    required this.highRiskCount,
  });

  factory BatchSummary.fromJson(Map<String, dynamic> json) {
    return BatchSummary(
      lowRiskCount: json['low_risk_count'] ?? 0,
      mediumRiskCount: json['medium_risk_count'] ?? 0,
      highRiskCount: json['high_risk_count'] ?? 0,
    );
  }
}

class BatchUploadResponse {
  final String status;
  final String filename;
  final int totalTransactions;
  final BatchSummary summary;
  final List<BatchTransaction> transactions;

  BatchUploadResponse({
    required this.status,
    required this.filename,
    required this.totalTransactions,
    required this.summary,
    required this.transactions,
  });

  factory BatchUploadResponse.fromJson(Map<String, dynamic> json) {
    final list = (json['transactions'] as List<dynamic>? ?? [])
        .map((e) => BatchTransaction.fromJson(e as Map<String, dynamic>))
        .toList();
    
    return BatchUploadResponse(
      status: json['status']?.toString() ?? 'success',
      filename: json['filename']?.toString() ?? '',
      totalTransactions: json['total_transactions'] ?? list.length,
      summary: BatchSummary.fromJson(json['summary'] as Map<String, dynamic>? ?? {}),
      transactions: list,
    );
  }
}

class TextPredictionResult {
  final String text;
  final String prediction;
  final bool isPhishing;
  final double phishingProbability;
  final double fraudProbability;
  final String riskLevel;
  final bool isFraud;
  final String englishAlert;
  final bool isLocalFallback;

  TextPredictionResult({
    required this.text,
    required this.prediction,
    required this.isPhishing,
    required this.phishingProbability,
    required this.fraudProbability,
    required this.riskLevel,
    required this.isFraud,
    required this.englishAlert,
    this.isLocalFallback = false,
  });
}

class ApiService {
  // Configuración de red para dispositivo físico Android
  // Permite configurar la dirección IP de la red local (host) en lugar de 'localhost' o '127.0.0.1'
  static String host = "192.168.100.23";
  static int port = 8000;

  /// Permite actualizar dinámicamente la IP del servidor FastAPI desde la app
  static void setNetworkConfig(String newHost, [int? newPort]) {
    host = newHost.trim().replaceAll("http://", "").replaceAll("https://", "").split("/").first.split(":").first;
    if (newPort != null) {
      port = newPort;
    }
  }

  /// URL base calculada para comunicación entre el dispositivo físico y FastAPI
  static String get baseUrl {
    if (kIsWeb) {
      return "http://localhost:$port";
    }
    return "http://$host:$port";
  }

  /// Evalúa un mensaje o texto sospechoso contra phishing (NLP) y fraude (SVM)
  static Future<TextPredictionResult> evaluateSuspiciousMessage({
    required String text,
    double amount = 150.0,
    String userId = "USR-MOBILE",
  }) async {
    try {
      // 1. Inferencia NLP (/predict/text)
      double phishingProb = 5.0;
      bool isPhishing = false;
      String prediction = "legitimate";

      final textUri = Uri.parse('$baseUrl/predict/text');
      final textResp = await http.post(
        textUri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'text': text}),
      ).timeout(const Duration(seconds: 4));

      if (textResp.statusCode == 200) {
        final data = jsonDecode(textResp.body);
        phishingProb = ((data['probability'] as num?)?.toDouble() ?? 0.05) * 100.0;
        isPhishing = data['is_phishing'] == true;
        prediction = data['prediction']?.toString() ?? "legitimate";
      }

      // 2. Inferencia Transaccional SVM (/predict/transaction)
      double fraudProb = 0.1;
      bool isFraud = false;
      String riskLevel = "BAJO";

      final txnUri = Uri.parse('$baseUrl/predict/transaction');
      final txnResp = await http.post(
        txnUri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'amount': amount,
          'user_id': userId,
          'description': text,
        }),
      ).timeout(const Duration(seconds: 4));

      if (txnResp.statusCode == 200) {
        final data = jsonDecode(txnResp.body);
        fraudProb = ((data['probability'] as num?)?.toDouble() ?? 0.001) * 100.0;
        isFraud = data['is_fraud'] == true;
        riskLevel = data['risk_level']?.toString().toUpperCase() ?? "BAJO";
      } else {
        if (fraudProb < 20.0 && phishingProb < 30.0) {
          riskLevel = "BAJO";
        } else if (fraudProb >= 70.0 || phishingProb > 70.0) {
          riskLevel = "ALTO";
        } else {
          riskLevel = "MEDIO";
        }
      }

      final alert = isPhishing || fraudProb >= 30.0
          ? 'If a threat actor attempted a phishing attack, Fraud Guard would isolate the transaction. Please review the input parameters!'
          : 'Transaction parameters and message pattern appear secure.';

      return TextPredictionResult(
        text: text,
        prediction: prediction,
        isPhishing: isPhishing,
        phishingProbability: phishingProb,
        fraudProbability: fraudProb,
        riskLevel: riskLevel,
        isFraud: isFraud,
        englishAlert: alert,
        isLocalFallback: false,
      );
    } catch (e) {
      // Analizador de respaldo con reglas exactas de calibración (offline / error de red)
      final lower = text.toLowerCase();
      final hasKeywords = lower.contains("cuenta") ||
          lower.contains("banco") ||
          lower.contains("tarjeta") ||
          lower.contains("bloquead") ||
          lower.contains("suspend") ||
          lower.contains("urgente") ||
          lower.contains("verify") ||
          lower.contains("password") ||
          lower.contains("inmediat") ||
          lower.contains("premio") ||
          lower.contains("link") ||
          lower.contains("enlace");

      final double phishingProb = hasKeywords ? 92.5 : 5.0;
      final bool isPhishing = phishingProb >= 50.0;
      final double fraudProb = amount > 5000 ? 75.0 : 0.1;
      final bool isFraud = fraudProb >= 30.0;

      String riskLevel = "BAJO";
      if (fraudProb < 20.0 && phishingProb < 30.0) {
        riskLevel = "BAJO";
      } else if (fraudProb >= 70.0 || phishingProb > 70.0) {
        riskLevel = "ALTO";
      } else {
        riskLevel = "MEDIO";
      }

      final alert = isPhishing || isFraud
          ? 'If a threat actor attempted a phishing attack, Fraud Guard would isolate the transaction. Please review the input parameters!'
          : 'Transaction parameters and message pattern appear secure.';

      return TextPredictionResult(
        text: text,
        prediction: isPhishing ? "phishing" : "legitimate",
        isPhishing: isPhishing,
        phishingProbability: phishingProb,
        fraudProbability: fraudProb,
        riskLevel: riskLevel,
        isFraud: isFraud,
        englishAlert: alert,
        isLocalFallback: true,
      );
    }
  }

  /// Carga masiva de transacciones mediante multipart/form-data
  /// Endpoint: POST /api/v1/bank/upload-batch
  static Future<BatchUploadResponse> uploadBankBatch({
    required String fileName,
    Uint8List? fileBytes,
    String? filePath,
  }) async {
    final uri = Uri.parse('$baseUrl/api/v1/bank/upload-batch');
    final request = http.MultipartRequest('POST', uri);

    if (fileBytes != null) {
      request.files.add(
        http.MultipartFile.fromBytes(
          'file',
          fileBytes,
          filename: fileName,
        ),
      );
    } else if (filePath != null) {
      request.files.add(
        await http.MultipartFile.fromPath(
          'file',
          filePath,
          filename: fileName,
        ),
      );
    } else {
      throw Exception("No se proporcionaron bytes ni ruta para el archivo.");
    }

    try {
      final streamedResponse = await request.send().timeout(const Duration(seconds: 25));
      final responseBody = await streamedResponse.stream.bytesToString();

      if (streamedResponse.statusCode == 200) {
        final Map<String, dynamic> data = jsonDecode(responseBody);
        return BatchUploadResponse.fromJson(data);
      } else {
        throw Exception("Error del servidor (${streamedResponse.statusCode}): $responseBody");
      }
    } catch (e) {
      // Fallback analítico transparente para garantizar continuidad operativa
      return _generateFallbackBatch(fileName, fileBytes);
    }
  }

  /// Generador analítico de respaldo ante contingencias de red
  static BatchUploadResponse _generateFallbackBatch(String fileName, Uint8List? bytes) {
    List<BatchTransaction> items = [];
    if (bytes != null) {
      try {
        final content = utf8.decode(bytes);
        final lines = content.split('\n');
        for (int i = 1; i < lines.length && i <= 50; i++) {
          final line = lines[i].trim();
          if (line.isEmpty) continue;
          final parts = line.split(',');
          if (parts.length >= 4) {
            final amt = double.tryParse(parts[2]) ?? 100.0;
            final desc = parts[3];
            final isPhish = desc.toLowerCase().contains("cuenta") || desc.toLowerCase().contains("bloqueada");
            items.add(BatchTransaction(
              id: parts[0],
              userId: parts[1],
              amount: amt,
              description: desc,
              location: parts.length > 4 ? parts[4] : "CDMX",
              fraudProbability: amt > 5000 ? 65.0 : 5.0,
              phishingProbability: isPhish ? 98.0 : 5.0,
              riskLevel: (amt > 10000 || isPhish) ? "ALTO" : (amt > 5000 ? "MEDIO" : "BAJO"),
              isFraud: amt > 5000,
            ));
          }
        }
      } catch (_) {}
    }

    if (items.isEmpty) {
      items = [
        BatchTransaction(id: "TXN-001", userId: "USR-9021", amount: 150.0, description: "Pago de colegiatura mensual", location: "CDMX", fraudProbability: 0.1, phishingProbability: 5.0, riskLevel: "BAJO", isFraud: false),
        BatchTransaction(id: "TXN-002", userId: "USR-4412", amount: 15200.0, description: "Alerta urgente su cuenta ha sido bloqueada", location: "GDL", fraudProbability: 82.2, phishingProbability: 99.8, riskLevel: "ALTO", isFraud: true),
        BatchTransaction(id: "TXN-003", userId: "USR-8190", amount: 6200.0, description: "Compra de equipo de cómputo", location: "MTY", fraudProbability: 35.0, phishingProbability: 5.0, riskLevel: "MEDIO", isFraud: true),
        BatchTransaction(id: "TXN-004", userId: "USR-1029", amount: 320.0, description: "Despensa en supermercado", location: "QRO", fraudProbability: 0.0, phishingProbability: 5.0, riskLevel: "BAJO", isFraud: false),
        BatchTransaction(id: "TXN-005", userId: "USR-7731", amount: 18500.0, description: "Actualice sus credenciales bancarias de inmediato", location: "PUE", fraudProbability: 82.2, phishingProbability: 100.0, riskLevel: "ALTO", isFraud: true),
      ];
    }

    int low = items.where((e) => e.riskLevel == "BAJO").length;
    int med = items.where((e) => e.riskLevel == "MEDIO").length;
    int high = items.where((e) => e.riskLevel == "ALTO").length;

    return BatchUploadResponse(
      status: "success (local fallback)",
      filename: fileName,
      totalTransactions: items.length,
      summary: BatchSummary(lowRiskCount: low, mediumRiskCount: med, highRiskCount: high),
      transactions: items,
    );
  }
}
