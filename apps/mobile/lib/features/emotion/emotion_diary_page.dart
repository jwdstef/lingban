import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/theme/app_theme.dart';

class EmotionDiaryPage extends ConsumerStatefulWidget {
  const EmotionDiaryPage({super.key});

  @override
  ConsumerState<EmotionDiaryPage> createState() => _EmotionDiaryPageState();
}

class _EmotionDiaryPageState extends ConsumerState<EmotionDiaryPage> {
  static const _emotionLabels = {
    'anxious': '焦虑',
    'sad': '低落',
    'tired': '疲惫',
    'angry': '生气',
    'lonely': '孤独',
    'happy': '开心',
    'calm': '平静',
  };

  static const _emotionIcons = {
    'anxious': Icons.bolt_outlined,
    'sad': Icons.water_drop_outlined,
    'tired': Icons.nightlight_outlined,
    'angry': Icons.local_fire_department_outlined,
    'lonely': Icons.cloud_outlined,
    'happy': Icons.wb_sunny_outlined,
    'calm': Icons.spa_outlined,
  };

  List<Map<String, dynamic>> _records = [];
  List<Map<String, dynamic>> _points = [];
  Map<String, int> _emotionCounts = {};
  bool _isLoading = true;
  bool _hasError = false;
  double _averageIntensity = 0;

  @override
  void initState() {
    super.initState();
    _loadDiary();
  }

  Future<void> _loadDiary() async {
    setState(() {
      _isLoading = true;
      _hasError = false;
    });

    try {
      final responses = await Future.wait([
        apiClient.getEmotionDiary(limit: 30),
        apiClient.getEmotionTrend(days: 14),
      ]);
      final diaryData = responses[0].data as Map<String, dynamic>;
      final trendData = responses[1].data as Map<String, dynamic>;
      if (!mounted) return;

      setState(() {
        _records = List<Map<String, dynamic>>.from(diaryData['records'] ?? []);
        _points = List<Map<String, dynamic>>.from(trendData['points'] ?? []);
        _emotionCounts = _parseCounts(trendData['emotion_counts']);
        _averageIntensity =
            ((trendData['average_intensity'] ?? 0) as num).toDouble();
        _isLoading = false;
      });
    } catch (_) {
      if (mounted) {
        setState(() {
          _hasError = true;
          _isLoading = false;
        });
      }
    }
  }

  Map<String, int> _parseCounts(Object? value) {
    if (value is! Map) return {};
    return value.map(
      (key, count) => MapEntry(key.toString(), (count as num).toInt()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        child: Column(
          children: [
            _buildHeader(),
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _hasError
                      ? _buildErrorState()
                      : RefreshIndicator(
                          onRefresh: _loadDiary,
                          color: AppTheme.spiritGlow,
                          backgroundColor: AppTheme.cardColor,
                          child: ListView(
                            padding: const EdgeInsets.fromLTRB(16, 8, 16, 60),
                            children: [
                              _buildTrendPanel(),
                              const SizedBox(height: 20),
                              _buildRecordsSection(),
                            ],
                          ),
                        ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: AppTheme.spiritGlow.withValues(alpha: 0.12),
              shape: BoxShape.circle,
              border: Border.all(
                color: AppTheme.spiritGlow.withValues(alpha: 0.25),
              ),
            ),
            child: const Icon(
              Icons.mood_outlined,
              color: AppTheme.spiritGlow,
              size: 20,
            ),
          ),
          const SizedBox(width: 10),
          const Text(
            '情绪日记',
            style: TextStyle(
              color: AppTheme.primaryColor,
              fontSize: 20,
              fontWeight: FontWeight.w700,
            ),
          ),
          const Spacer(),
          IconButton(
            tooltip: '刷新',
            onPressed: _loadDiary,
            icon: Icon(
              Icons.refresh,
              color: AppTheme.primaryColor.withValues(alpha: 0.55),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTrendPanel() {
    final topEmotion = _topEmotion();
    final topLabel = topEmotion == null ? '暂无' : _emotionLabel(topEmotion);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AppTheme.primaryColor.withValues(alpha: 0.1),
          width: 0.5,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                '最近 14 天',
                style: TextStyle(
                  color: AppTheme.primaryColor.withValues(alpha: 0.82),
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const Spacer(),
              _buildTinyStat('主情绪', topLabel),
              const SizedBox(width: 12),
              _buildTinyStat('平均', '${(_averageIntensity * 100).round()}%'),
            ],
          ),
          const SizedBox(height: 18),
          SizedBox(
            height: 132,
            width: double.infinity,
            child: CustomPaint(
              painter: _EmotionTrendPainter(
                points: _points,
                lineColor: AppTheme.spiritGlow,
                accentColor: AppTheme.accentColor,
                gridColor: AppTheme.primaryColor.withValues(alpha: 0.08),
              ),
            ),
          ),
          const SizedBox(height: 12),
          if (_points.isEmpty)
            Center(
              child: Text(
                '还没有记录，和 AI 聊天后会自动记录',
                style: TextStyle(
                  color: AppTheme.primaryColor.withValues(alpha: 0.38),
                  fontSize: 13,
                ),
              ),
            )
          else
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _emotionCounts.entries
                  .map((entry) => _buildEmotionChip(entry.key, entry.value))
                  .toList(),
            ),
        ],
      ),
    );
  }

  Widget _buildTinyStat(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Text(
          value,
          style: const TextStyle(
            color: AppTheme.spiritGlow,
            fontSize: 14,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: TextStyle(
            color: AppTheme.primaryColor.withValues(alpha: 0.36),
            fontSize: 10,
          ),
        ),
      ],
    );
  }

  Widget _buildEmotionChip(String emotion, int count) {
    final color = _emotionColor(emotion);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withValues(alpha: 0.2), width: 0.5),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(_emotionIcon(emotion), color: color, size: 14),
          const SizedBox(width: 5),
          Text(
            '${_emotionLabel(emotion)} $count',
            style: TextStyle(
              color: AppTheme.primaryColor.withValues(alpha: 0.72),
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRecordsSection() {
    if (_records.isEmpty) {
      return _buildEmptyState();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '每日记录',
          style: TextStyle(
            color: AppTheme.primaryColor.withValues(alpha: 0.82),
            fontSize: 14,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 12),
        ..._records.map(_buildRecordItem),
      ],
    );
  }

  Widget _buildRecordItem(Map<String, dynamic> record) {
    final emotion = record['dominant_emotion']?.toString() ?? '';
    final intensity = ((record['intensity'] ?? 0) as num).toDouble();
    final triggers = List<String>.from(record['triggers'] ?? []);
    final color = _emotionColor(emotion);

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.cardColor.withValues(alpha: 0.82),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: color.withValues(alpha: 0.18),
          width: 0.5,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              shape: BoxShape.circle,
            ),
            child: Icon(_emotionIcon(emotion), color: color, size: 19),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        _formatDate(record['date']?.toString()),
                        style: TextStyle(
                          color: AppTheme.primaryColor.withValues(alpha: 0.48),
                          fontSize: 12,
                        ),
                      ),
                    ),
                    Text(
                      _emotionLabel(emotion),
                      style: TextStyle(
                        color: color,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(999),
                  child: LinearProgressIndicator(
                    value: intensity.clamp(0, 1),
                    minHeight: 5,
                    backgroundColor:
                        AppTheme.primaryColor.withValues(alpha: 0.08),
                    valueColor: AlwaysStoppedAnimation<Color>(color),
                  ),
                ),
                if (triggers.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Text(
                    triggers.first,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: AppTheme.primaryColor.withValues(alpha: 0.72),
                      fontSize: 13,
                      height: 1.35,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 42),
      alignment: Alignment.center,
      child: Column(
        children: [
          Icon(
            Icons.mood_bad_outlined,
            size: 42,
            color: AppTheme.primaryColor.withValues(alpha: 0.22),
          ),
          const SizedBox(height: 12),
          Text(
            '还没有记录，和 AI 聊天后会自动记录',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: AppTheme.primaryColor.withValues(alpha: 0.38),
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.error_outline,
            color: AppTheme.primaryColor.withValues(alpha: 0.35),
            size: 40,
          ),
          const SizedBox(height: 12),
          Text(
            '加载失败',
            style: TextStyle(
              color: AppTheme.primaryColor.withValues(alpha: 0.5),
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 14),
          FilledButton.icon(
            onPressed: _loadDiary,
            icon: const Icon(Icons.refresh),
            label: const Text('重试'),
          ),
        ],
      ),
    );
  }

  String? _topEmotion() {
    if (_emotionCounts.isEmpty) return null;
    return _emotionCounts.entries
        .reduce((left, right) => left.value >= right.value ? left : right)
        .key;
  }

  String _emotionLabel(String emotion) {
    return _emotionLabels[emotion] ?? '未知';
  }

  IconData _emotionIcon(String emotion) {
    return _emotionIcons[emotion] ?? Icons.mood_outlined;
  }

  Color _emotionColor(String emotion) {
    switch (emotion) {
      case 'happy':
        return AppTheme.emotionHappy;
      case 'calm':
        return AppTheme.emotionThinking;
      case 'angry':
        return AppTheme.accentColor;
      case 'sad':
      case 'lonely':
        return const Color(0xFF60A5FA);
      case 'tired':
        return const Color(0xFF34D399);
      case 'anxious':
      default:
        return AppTheme.spiritGlow;
    }
  }

  String _formatDate(String? value) {
    if (value == null || value.isEmpty) return '';
    final date = DateTime.tryParse(value);
    if (date == null) return value;
    return '${date.month}月${date.day}日';
  }
}

class _EmotionTrendPainter extends CustomPainter {
  final List<Map<String, dynamic>> points;
  final Color lineColor;
  final Color accentColor;
  final Color gridColor;

  _EmotionTrendPainter({
    required this.points,
    required this.lineColor,
    required this.accentColor,
    required this.gridColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final gridPaint = Paint()
      ..color = gridColor
      ..strokeWidth = 1;
    for (var index = 0; index < 4; index += 1) {
      final y = size.height * index / 3;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    if (points.isEmpty) {
      final emptyPaint = Paint()
        ..color = lineColor.withValues(alpha: 0.12)
        ..strokeWidth = 10
        ..strokeCap = StrokeCap.round;
      canvas.drawLine(
        Offset(size.width * 0.12, size.height * 0.62),
        Offset(size.width * 0.88, size.height * 0.62),
        emptyPaint,
      );
      return;
    }

    final values = points
        .map((point) => ((point['intensity'] ?? 0) as num).toDouble())
        .map((value) => value.clamp(0.05, 1.0).toDouble())
        .toList();
    final step = values.length == 1 ? 0.0 : size.width / (values.length - 1);
    final offsets = values.asMap().entries.map((entry) {
      final x = values.length == 1 ? size.width / 2 : entry.key * step;
      final y = size.height - entry.value * (size.height - 10) - 5;
      return Offset(x, y);
    }).toList();

    final path = Path()..moveTo(offsets.first.dx, offsets.first.dy);
    for (var index = 1; index < offsets.length; index += 1) {
      final previous = offsets[index - 1];
      final current = offsets[index];
      final controlX = (previous.dx + current.dx) / 2;
      path.cubicTo(
          controlX, previous.dy, controlX, current.dy, current.dx, current.dy);
    }

    final linePaint = Paint()
      ..shader = LinearGradient(colors: [lineColor, accentColor]).createShader(
        Rect.fromLTWH(0, 0, size.width, size.height),
      )
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(path, linePaint);

    for (var index = 0; index < offsets.length; index += 1) {
      final color =
          Color.lerp(lineColor, accentColor, values[index]) ?? lineColor;
      canvas.drawCircle(
        offsets[index],
        5,
        Paint()..color = color.withValues(alpha: 0.22),
      );
      canvas.drawCircle(offsets[index], 3, Paint()..color = color);
    }

    final fillPath = Path.from(path)
      ..lineTo(offsets.last.dx, size.height)
      ..lineTo(offsets.first.dx, size.height)
      ..close();
    canvas.drawPath(
      fillPath,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            lineColor.withValues(alpha: 0.14),
            lineColor.withValues(alpha: 0.0),
          ],
        ).createShader(Rect.fromLTWH(0, 0, size.width, size.height)),
    );
  }

  @override
  bool shouldRepaint(covariant _EmotionTrendPainter oldDelegate) {
    return oldDelegate.points != points ||
        oldDelegate.lineColor != lineColor ||
        oldDelegate.accentColor != accentColor ||
        oldDelegate.gridColor != gridColor;
  }
}
