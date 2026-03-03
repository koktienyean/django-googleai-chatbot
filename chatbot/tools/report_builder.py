"""
Report builder for generating structured reports from queried data.
Generates markdown tables, summaries, and chart-ready data.
"""
from datetime import timedelta
from django.utils import timezone
from .query_engine import execute_query, parse_date


class ReportBuilder:
    """Build formatted reports from Django model data."""

    def __init__(self, user):
        self.user = user

    def generate_report(self, report_type, data_type, time_range='last_30_days', output_format='markdown'):
        """Main entry point for report generation.

        Args:
            report_type: 'summary', 'detailed', 'trend', 'comparison'
            data_type: 'tasks', 'chats', 'sessions', etc.
            time_range: 'today', 'this_week', 'this_month', 'last_30_days', 'custom'
            output_format: 'markdown', 'table', 'chart_data'

        Returns:
            dict with report data
        """
        date_from = self._resolve_time_range(time_range)
        filters = {}
        if date_from:
            filters['date_from'] = str(date_from.date())

        if report_type == 'summary':
            return self._build_summary(data_type, filters, time_range, output_format)
        elif report_type == 'detailed':
            return self._build_detailed(data_type, filters, time_range, output_format)
        elif report_type == 'trend':
            return self._build_trend(data_type, filters, time_range, output_format)
        elif report_type == 'comparison':
            return self._build_comparison(data_type, filters, time_range, output_format)
        else:
            return {'error': f'Unknown report type: {report_type}'}

    def _resolve_time_range(self, time_range):
        """Convert time range string to a start date."""
        now = timezone.now()
        if time_range == 'today':
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == 'this_week':
            start = now - timedelta(days=now.weekday())
            return start.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == 'this_month':
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif time_range == 'last_30_days':
            return now - timedelta(days=30)
        elif time_range == 'last_7_days':
            return now - timedelta(days=7)
        return None

    def _build_summary(self, data_type, filters, time_range, output_format):
        """Build a summary report with key metrics."""
        count_data = execute_query(self.user, data_type, filters=filters, aggregation='count')
        total = count_data.get('count', 0)

        report = {
            'title': f'{data_type.replace("_", " ").title()} Summary — {time_range.replace("_", " ").title()}',
            'time_range': time_range,
            'data_type': data_type,
            'total': total,
        }

        # Add status breakdown for tasks
        if data_type == 'tasks':
            status_data = execute_query(self.user, data_type, filters=filters, aggregation='group_by_status')
            priority_data = execute_query(self.user, data_type, filters=filters, aggregation='group_by_priority')
            report['by_status'] = status_data.get('groups', [])
            report['by_priority'] = priority_data.get('groups', [])

            # Compute completion rate
            completed = sum(g['count'] for g in report['by_status'] if g.get('status') == 'completed')
            report['completion_rate'] = round((completed / total * 100), 1) if total > 0 else 0

        if output_format == 'markdown':
            report['markdown'] = self._format_summary_markdown(report)

        return report

    def _build_detailed(self, data_type, filters, time_range, output_format):
        """Build a detailed report showing individual records."""
        data = execute_query(self.user, data_type, filters=filters, limit=50)
        report = {
            'title': f'{data_type.replace("_", " ").title()} Detail — {time_range.replace("_", " ").title()}',
            'time_range': time_range,
            'data_type': data_type,
            'total': data.get('count', 0),
            'results': data.get('results', []),
        }

        if output_format == 'markdown':
            report['markdown'] = self._format_detailed_markdown(report, data_type)

        return report

    def _build_trend(self, data_type, filters, time_range, output_format):
        """Build a trend report showing changes over time."""
        trend_data = execute_query(self.user, data_type, filters=filters, aggregation='trend')
        report = {
            'title': f'{data_type.replace("_", " ").title()} Trend — {time_range.replace("_", " ").title()}',
            'time_range': time_range,
            'data_type': data_type,
            'trend': trend_data.get('trend', []),
        }

        if output_format == 'markdown':
            report['markdown'] = self._format_trend_markdown(report)
        elif output_format == 'chart_data':
            report['chart'] = {
                'labels': [t['date'] for t in report['trend']],
                'values': [t['count'] for t in report['trend']],
                'type': 'line',
            }

        return report

    def _build_comparison(self, data_type, filters, time_range, output_format):
        """Build a comparison between current and previous period."""
        now = timezone.now()
        date_from = self._resolve_time_range(time_range)
        if not date_from:
            return {'error': 'Comparison requires a time range'}

        period_length = (now - date_from).days

        # Current period
        current_data = execute_query(self.user, data_type, filters=filters, aggregation='count')

        # Previous period
        prev_filters = dict(filters)
        prev_end = date_from
        prev_start = date_from - timedelta(days=period_length)
        prev_filters['date_from'] = str(prev_start.date())
        prev_filters['date_to'] = str(prev_end.date())
        prev_data = execute_query(self.user, data_type, filters=prev_filters, aggregation='count')

        current_count = current_data.get('count', 0)
        prev_count = prev_data.get('count', 0)
        change = current_count - prev_count
        pct = round((change / prev_count * 100), 1) if prev_count > 0 else 0

        report = {
            'title': f'{data_type.replace("_", " ").title()} Comparison',
            'time_range': time_range,
            'current_period': current_count,
            'previous_period': prev_count,
            'change': change,
            'change_pct': pct,
        }

        if output_format == 'markdown':
            direction = "up" if change > 0 else ("down" if change < 0 else "unchanged")
            report['markdown'] = (
                f"## {report['title']}\n\n"
                f"| Period | Count |\n|--------|-------|\n"
                f"| Current ({time_range}) | {current_count} |\n"
                f"| Previous period | {prev_count} |\n\n"
                f"**Change:** {change:+d} ({pct:+.1f}%) — {direction}"
            )

        return report

    def _format_summary_markdown(self, report):
        """Format summary report as markdown."""
        lines = [f"## {report['title']}", f"\n**Total:** {report['total']}"]

        if 'completion_rate' in report:
            lines.append(f"**Completion Rate:** {report['completion_rate']}%")

        if report.get('by_status'):
            lines.append("\n### By Status\n| Status | Count |\n|--------|-------|")
            for g in report['by_status']:
                lines.append(f"| {g.get('status', 'N/A')} | {g['count']} |")

        if report.get('by_priority'):
            lines.append("\n### By Priority\n| Priority | Count |\n|----------|-------|")
            for g in report['by_priority']:
                lines.append(f"| {g.get('priority', 'N/A')} | {g['count']} |")

        return '\n'.join(lines)

    def _format_detailed_markdown(self, report, data_type):
        """Format detailed report as markdown table."""
        lines = [f"## {report['title']}", f"\n**Showing {len(report['results'])} of {report['total']} records**\n"]

        if data_type == 'tasks' and report['results']:
            lines.append("| # | Title | Status | Priority | Created |")
            lines.append("|---|-------|--------|----------|---------|")
            for i, r in enumerate(report['results'][:50], 1):
                title = r.get('title', '')[:40]
                lines.append(f"| {i} | {title} | {r.get('status', '')} | {r.get('priority', '')} | {str(r.get('created_at', ''))[:10]} |")
        elif data_type == 'chats' and report['results']:
            lines.append("| # | Message | Created |")
            lines.append("|---|---------|---------|")
            for i, r in enumerate(report['results'][:50], 1):
                msg = r.get('message', '')[:50]
                lines.append(f"| {i} | {msg} | {str(r.get('created_at', ''))[:10]} |")
        elif report['results']:
            # Generic table
            if report['results']:
                keys = list(report['results'][0].keys())[:5]
                lines.append("| " + " | ".join(keys) + " |")
                lines.append("| " + " | ".join(["---"] * len(keys)) + " |")
                for r in report['results'][:50]:
                    vals = [str(r.get(k, ''))[:30] for k in keys]
                    lines.append("| " + " | ".join(vals) + " |")

        return '\n'.join(lines)

    def _format_trend_markdown(self, report):
        """Format trend report as simple text chart."""
        lines = [f"## {report['title']}\n"]
        trend = report.get('trend', [])

        if not trend:
            lines.append("No data available for this period.")
            return '\n'.join(lines)

        max_count = max(t['count'] for t in trend) if trend else 1
        max_count = max(max_count, 1)

        # Show last 14 days in a bar-chart style
        recent = trend[-14:] if len(trend) > 14 else trend
        for t in recent:
            bar_len = int(t['count'] / max_count * 20)
            bar = '█' * bar_len
            lines.append(f"{t['date'][-5:]} | {bar} {t['count']}")

        total = sum(t['count'] for t in trend)
        avg = round(total / len(trend), 1) if trend else 0
        lines.append(f"\n**Total:** {total} | **Daily avg:** {avg}")

        return '\n'.join(lines)
