import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../theme/app_theme.dart';
import '../services/api_service.dart';

class BankBatchView extends StatefulWidget {
  const BankBatchView({super.key});

  @override
  State<BankBatchView> createState() => _BankBatchViewState();
}

class _BankBatchViewState extends State<BankBatchView> {
  bool _isProcessing = false;
  double _progressValue = 0.0;
  String? _selectedFileName;
  BatchUploadResponse? _batchResult;
  String? _errorMessage;

  Future<void> _pickAndUploadFile() async {
    try {
      setState(() {
        _errorMessage = null;
      });

      final List<PlatformFile> files = await FilePicker.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['csv', 'json', 'xlsx', 'xls'],
      );

      if (files.isNotEmpty) {
        final file = files.first;
        setState(() {
          _selectedFileName = file.name;
          _isProcessing = true;
          _progressValue = 0.2;
        });

        // Simular avance de barra de progreso visual
        await Future.delayed(const Duration(milliseconds: 300));
        setState(() => _progressValue = 0.6);

        final bytes = await file.readAsBytes();

        // Llamada a la API
        final response = await ApiService.uploadBankBatch(
          fileName: file.name,
          fileBytes: bytes,
          filePath: kIsWeb ? null : file.path,
        );

        setState(() {
          _progressValue = 1.0;
          _isProcessing = false;
          _batchResult = response;
        });
      }
    } catch (e) {
      setState(() {
        _isProcessing = false;
        _errorMessage = "Error al procesar el archivo: $e";
      });
    }
  }

  void _loadDemoDataset() async {
    setState(() {
      _selectedFileName = "lote_transacciones_bancarias.csv";
      _isProcessing = true;
      _progressValue = 0.3;
      _errorMessage = null;
    });

    await Future.delayed(const Duration(milliseconds: 400));
    setState(() => _progressValue = 0.75);

    final demoCsv = '''id,user_id,amount,description,location
TXN-1001,USR-5012,240.0,Pago de colegiatura mensual,CDMX
TXN-1002,USR-3391,14800.0,Su cuenta bancaria ha sido bloqueada. Ingrese aqui a verificar datos de inmediato,GDL
TXN-1003,USR-8820,5400.0,Transferencia comercial para proveedores,MTY
TXN-1004,USR-1290,120.0,Compra en farmacia San Pablo,QRO
TXN-1005,USR-6631,19200.0,Urgente actualice sus contrasenas y token bancario,PUE
TXN-1006,USR-9402,480.0,Despensa quincenal en tienda de autoservicio,TIJ
TXN-1007,USR-7110,8500.0,Retiro en cajero automatico foraneo,CUN
''';

    final bytes = Uint8List.fromList(demoCsv.codeUnits);
    final response = await ApiService.uploadBankBatch(
      fileName: "lote_transacciones_bancarias.csv",
      fileBytes: bytes,
    );

    setState(() {
      _progressValue = 1.0;
      _isProcessing = false;
      _batchResult = response;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.account_balance, color: AppTheme.goldImperial, size: 20),
            SizedBox(width: 8),
            Text("Entidad Bancaria • Procesamiento en Lote"),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: "Reiniciar lote",
            onPressed: () {
              setState(() {
                _selectedFileName = null;
                _batchResult = null;
                _errorMessage = null;
                _progressValue = 0.0;
              });
            },
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Panel Superior: Carga de Archivos
              _buildUploadCard(),
              const SizedBox(height: 24),

              // Barra de Progreso si está procesando
              if (_isProcessing) ...[
                _buildProgressIndicator(),
                const SizedBox(height: 24),
              ],

              // Mensaje de Error si existió
              if (_errorMessage != null) ...[
                _buildErrorBox(),
                const SizedBox(height: 24),
              ],

              // Resumen y Tabla de Resultados
              if (_batchResult != null) ...[
                _buildSummaryCards(),
                const SizedBox(height: 24),
                _buildResultsTable(),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildUploadCard() {
    return Card(
      color: AppTheme.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: AppTheme.borderGold, width: 1.2),
      ),
      child: Padding(
        padding: const EdgeInsets.all(28.0),
        child: Column(
          children: [
            Container(
              width: 68,
              height: 68,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppTheme.surfaceLight,
                border: Border.all(color: AppTheme.goldImperial, width: 1.2),
              ),
              child: const Icon(
                Icons.upload_file_outlined,
                color: AppTheme.goldImperial,
                size: 36,
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              "Carga Masiva de Transacciones Bancarias",
              textAlign: TextAlign.center,
              style: TextStyle(
                color: AppTheme.goldImperial,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              "Sube o arrastra archivos en formato CSV, Excel (.xlsx) o JSON para ejecutar inferencia dual con IA Transaccional y NLP Phishing.",
              textAlign: TextAlign.center,
              style: TextStyle(
                color: AppTheme.textSecondary,
                fontSize: 13,
              ),
            ),
            const SizedBox(height: 24),

            if (_selectedFileName != null)
              Container(
                margin: const EdgeInsets.only(bottom: 20),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceLight,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppTheme.borderGold),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.insert_drive_file, color: AppTheme.goldImperial, size: 18),
                    const SizedBox(width: 8),
                    Flexible(
                      child: Text(
                        _selectedFileName!,
                        style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.w600, fontSize: 13),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),

            Wrap(
              spacing: 16,
              runSpacing: 12,
              alignment: WrapAlignment.center,
              children: [
                ElevatedButton.icon(
                  onPressed: _isProcessing ? null : _pickAndUploadFile,
                  icon: const Icon(Icons.folder_open),
                  label: const Text("Seleccionar Archivo (CSV / Excel / JSON)"),
                ),
                OutlinedButton.icon(
                  onPressed: _isProcessing ? null : _loadDemoDataset,
                  icon: const Icon(Icons.playlist_play, color: AppTheme.goldImperial),
                  label: const Text(
                    "Cargar Lote de Demostración",
                    style: TextStyle(color: AppTheme.goldImperial, fontWeight: FontWeight.bold),
                  ),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppTheme.goldImperial),
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProgressIndicator() {
    final percent = (_progressValue * 100).toInt();
    return Card(
      color: AppTheme.surface,
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  "Procesando lote en FastAPI / Modelos IA...",
                  style: TextStyle(color: AppTheme.goldImperial, fontWeight: FontWeight.w600, fontSize: 13),
                ),
                Text(
                  "$percent%",
                  style: const TextStyle(color: AppTheme.goldImperial, fontWeight: FontWeight.bold, fontSize: 13),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: _progressValue,
                minHeight: 8,
                backgroundColor: AppTheme.surfaceLight,
                valueColor: const AlwaysStoppedAnimation<Color>(AppTheme.goldImperial),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorBox() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0x20FF1744),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.riskHigh),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: AppTheme.riskHigh),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              _errorMessage!,
              style: const TextStyle(color: AppTheme.riskHigh, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryCards() {
    final summary = _batchResult!.summary;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          "Resumen Ejecutivo del Lote",
          style: TextStyle(color: AppTheme.goldImperial, fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        LayoutBuilder(
          builder: (context, constraints) {
            final isMobile = constraints.maxWidth < 600;
            return GridView.count(
              crossAxisCount: isMobile ? 2 : 4,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              childAspectRatio: isMobile ? 1.6 : 1.9,
              children: [
                _buildMetricCard("Total Procesadas", _batchResult!.totalTransactions.toString(), AppTheme.textPrimary, Icons.analytics_outlined),
                _buildMetricCard("Riesgo BAJO", summary.lowRiskCount.toString(), AppTheme.riskLow, Icons.check_circle_outline),
                _buildMetricCard("Riesgo MEDIO", summary.mediumRiskCount.toString(), AppTheme.riskMedium, Icons.warning_amber_outlined),
                _buildMetricCard("Riesgo ALTO", summary.highRiskCount.toString(), AppTheme.riskHigh, Icons.gpp_bad_outlined),
              ],
            );
          },
        ),
      ],
    );
  }

  Widget _buildMetricCard(String title, String value, Color color, IconData icon) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.4), width: 1),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 28),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11),
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  value,
                  style: TextStyle(color: color, fontSize: 20, fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildResultsTable() {
    return Card(
      color: AppTheme.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: AppTheme.borderGold),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  "Detalle de Inferencia y Detección de Amenazas",
                  style: TextStyle(color: AppTheme.goldImperial, fontSize: 15, fontWeight: FontWeight.bold),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppTheme.surfaceLight,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: AppTheme.borderGold),
                  ),
                  child: Text(
                    "${_batchResult!.transactions.length} registros",
                    style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                headingRowColor: WidgetStateProperty.all(AppTheme.surfaceLight),
                headingTextStyle: const TextStyle(
                  color: AppTheme.goldImperial,
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
                dataTextStyle: const TextStyle(color: AppTheme.textPrimary, fontSize: 12),
                columnSpacing: 20,
                columns: const [
                  DataColumn(label: Text("ID Transacción")),
                  DataColumn(label: Text("Usuario")),
                  DataColumn(label: Text("Monto (MXN)")),
                  DataColumn(label: Text("Descripción")),
                  DataColumn(label: Text("IA Fraude")),
                  DataColumn(label: Text("NLP Phishing")),
                  DataColumn(label: Text("Nivel de Riesgo")),
                ],
                rows: _batchResult!.transactions.map((tx) {
                  return DataRow(
                    cells: [
                      DataCell(Text(tx.id, style: const TextStyle(fontWeight: FontWeight.w600))),
                      DataCell(Text(tx.userId)),
                      DataCell(Text("\$${tx.amount.toStringAsFixed(2)}")),
                      DataCell(
                        ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 240),
                          child: Text(
                            tx.description,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ),
                      DataCell(Text("${tx.fraudProbability.toStringAsFixed(1)}%")),
                      DataCell(Text("${tx.phishingProbability.toStringAsFixed(1)}%")),
                      DataCell(_buildRiskBadge(tx.riskLevel)),
                    ],
                  );
                }).toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRiskBadge(String riskLevel) {
    Color bg;
    Color text;
    String label = riskLevel.toUpperCase();

    if (label == 'BAJO') {
      bg = AppTheme.riskLow.withValues(alpha: 0.15);
      text = AppTheme.riskLow;
    } else if (label == 'MEDIO') {
      bg = AppTheme.riskMedium.withValues(alpha: 0.15);
      text = AppTheme.riskMedium;
    } else {
      bg = AppTheme.riskHigh.withValues(alpha: 0.15);
      text = AppTheme.riskHigh;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: text, width: 1),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: text,
          fontSize: 11,
          fontWeight: FontWeight.bold,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}
