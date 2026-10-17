# -*- coding: utf-8 -*-

import html
from datetime import timedelta

from odoo import api, fields, models

CHART_COLORS = ['#8B6914', '#FFB347', '#3b82f6', '#22c55e']
SCORE_BUCKETS = ['0-25', '25-50', '50-75', '75-100', '100+']


class SygEvaluationDashboard(models.TransientModel):
    _name = 'syg.evaluation.dashboard'
    _description = 'Evaluation Dashboard'

    name = fields.Char(readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    employee_id = fields.Many2one('hr.employee', string="Employee")
    is_manager = fields.Boolean(compute='_compute_is_manager')
    kpi_dashboard_html = fields.Html(compute='_compute_kpi_dashboard_html', sanitize=False)

    @api.depends_context('uid')
    def _compute_is_manager(self):
        allowed = self.env.user.has_group('sygmetiv_company_management.group_company_manager')
        for dash in self:
            dash.is_manager = allowed

    def _scoped_employee(self, employee=None):
        if self.env.user.has_group('sygmetiv_company_management.group_company_manager'):
            return employee
        return self.env.user.employee_id

    @api.model
    def action_open(self, employee=None):
        employee = self._scoped_employee(employee)
        dash = self.create({
            'name': self.env._("Evaluation Dashboard"),
            'company_id': self.env.company.id,
            'employee_id': employee.id if employee else False,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': dash.name,
            'res_model': 'syg.evaluation.dashboard',
            'res_id': dash.id,
            'view_mode': 'form',
            'views': [(self.env.ref('sygmetiv_kpi.view_syg_evaluation_dashboard_form').id, 'form')],
            'target': 'current',
            'context': {'form_view_initial_mode': 'edit'},
        }

    def action_refresh(self):
        self.ensure_one()
        return self.action_open(self._scoped_employee(self.employee_id))

    def _kpi_domain(self, date_from, date_to, scored_only=False):
        domain = [
            ('date_start', '<=', date_to),
            ('date_end', '>=', date_from),
            ('state', '=', 'submitted'),
        ]
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        employee = self._scoped_employee(self.employee_id)
        if employee:
            domain.append(('employee_id', '=', employee.id))
        elif not self.is_manager:
            domain.append(('employee_id', '=', False))
        if scored_only:
            domain.append(('net_score', '>', 0))
        return domain

    def _kpi_evaluations(self, date_from, date_to, scored_only=False):
        return self.env['syg.kpi.evaluation'].search(self._kpi_domain(date_from, date_to, scored_only))

    def _high_scorers(self, date_from, date_to, limit=10):
        best = {}
        for evaluation in self._kpi_evaluations(date_from, date_to, scored_only=True):
            employee = evaluation.employee_id
            key = employee.id or ('none', evaluation.id)
            score = evaluation.net_score or 0.0
            if key not in best or score > best[key]['score']:
                best[key] = {
                    'employee': employee.name or 'Unknown',
                    'score': score,
                    'status': evaluation.status_id.name or '-',
                }
        return sorted(best.values(), key=lambda item: item['score'], reverse=True)[:limit]

    def _status_distribution(self, date_from, date_to):
        counts = {}
        for evaluation in self._kpi_evaluations(date_from, date_to):
            name = evaluation.status_id.name or 'Unassigned'
            counts[name] = counts.get(name, 0) + 1
        return sorted(counts.items(), key=lambda item: item[1], reverse=True)

    def _score_buckets(self, date_from, date_to):
        buckets = {key: 0 for key in SCORE_BUCKETS}
        for evaluation in self._kpi_evaluations(date_from, date_to, scored_only=True):
            score = float(evaluation.net_score or 0)
            if score <= 25:
                buckets['0-25'] += 1
            elif score <= 50:
                buckets['25-50'] += 1
            elif score <= 75:
                buckets['50-75'] += 1
            elif score <= 100:
                buckets['75-100'] += 1
            else:
                buckets['100+'] += 1
        result = [(key, buckets[key]) for key in SCORE_BUCKETS if buckets[key]]
        return result or [('0-25', 0)]

    def _period_stats(self, date_from, date_to):
        evaluations = self._kpi_evaluations(date_from, date_to)
        total = len(evaluations)
        average = sum(evaluations.mapped('net_score')) / total if total else 0.0
        return {'total': total, 'avg': average}

    def _last_seven_days(self):
        today = fields.Date.context_today(self)
        rows = []
        for offset in range(7):
            day = today - timedelta(days=offset)
            evaluations = self._kpi_evaluations(day, day)
            count = len(evaluations)
            average = sum(evaluations.mapped('net_score')) / count if count else 0.0
            top = '-'
            if evaluations:
                best = max(evaluations, key=lambda evaluation: float(evaluation.net_score or 0))
                top = best.employee_id.name or 'Unknown'
            rows.append({
                'date_str': day.strftime('%a %d %b'),
                'count': count,
                'avg': average,
                'top_scorer': top,
            })
        return rows

    def _status_color(self, name):
        label = (name or '').lower()
        if 'exceed' in label or 'excellent' in label:
            return '#16a34a'
        if 'meet' in label or 'good' in label:
            return '#eab308'
        if 'develop' in label or 'need' in label or 'average' in label:
            return '#dc2626'
        return '#64748b'

    def _status_badge(self, name):
        if not name or name == '-':
            return '<span class="kpi-badge kpi-badge-muted">-</span>'
        label = name.lower()
        css = 'kpi-badge-default'
        if 'exceed' in label or 'excellent' in label:
            css = 'kpi-badge-success'
        elif 'develop' in label or 'need' in label or 'improv' in label:
            css = 'kpi-badge-warning'
        elif 'meet' in label or 'good' in label:
            css = 'kpi-badge-info'
        return '<span class="kpi-badge %s">%s</span>' % (css, html.escape(name))

    def _donut_html(self, center_value, segments, center_label):
        total = sum(count for _name, count in segments)
        if total <= 0:
            return '<p class="kpi-empty">No data</p>'
        degree = 0.0
        parts = []
        legends = []
        for index, (name, count) in enumerate(segments):
            percent = count / total * 100
            color = CHART_COLORS[index % len(CHART_COLORS)]
            if percent > 0.01:
                parts.append('%s %.1f%% %.1f%%' % (color, degree, degree + percent))
            degree += percent
            legends.append(
                '<div class="kpi-donut-legend-item"><span class="kpi-dot" style="background:%s"></span>'
                '<span>%s</span><span class="kpi-donut-pct">%s</span></div>'
                % (color, html.escape(name or ''), count)
            )
        gradient = 'conic-gradient(%s)' % ', '.join(parts) if parts else '#e5e7eb'
        return (
            '<div class="kpi-donut-area"><div class="kpi-donut">'
            '<div class="kpi-donut-ring" style="background:%s"></div>'
            '<div class="kpi-donut-center"><span class="kpi-donut-total">%s</span>'
            '<span class="kpi-donut-lbl">%s</span></div></div>'
            '<div class="kpi-donut-legend">%s</div></div>'
        ) % (gradient, html.escape(str(center_value)), html.escape(center_label), ''.join(legends))

    def _status_bar_html(self, distribution):
        if not distribution:
            return '<p class="kpi-empty">No evaluations yet</p>'
        maximum = max(count for _name, count in distribution) or 1
        bars = []
        for name, count in distribution[:5]:
            height = count / maximum * 100
            bars.append(
                '<div class="kpi-vbar-item"><div class="kpi-vbar-val">%s</div>'
                '<div class="kpi-vbar" style="height:%.1f%%;background:%s"></div>'
                '<div class="kpi-vbar-label">%s</div></div>'
                % (count, height, self._status_color(name), html.escape((name or '-')[:20]))
            )
        return '<div class="kpi-vbar-chart">%s</div>' % ''.join(bars)

    def _top_bar_html(self, scorers, max_score):
        if not scorers:
            return '<p class="kpi-empty">No evaluations this year</p>'
        bars = []
        for index, item in enumerate(scorers[:10]):
            score = float(item['score'] or 0)
            width = (score / max_score * 100) if max_score else 0
            color = CHART_COLORS[index % len(CHART_COLORS)]
            bars.append(
                '<div class="kpi-top10-row"><span class="kpi-top10-name">%s</span>'
                '<div class="kpi-top10-track"><div class="kpi-top10-fill" style="width:%.1f%%;background:%s">'
                '<span class="kpi-top10-val">%.1f</span></div></div></div>'
                % (html.escape((item['employee'] or 'Unknown')[:30]), width, color, score)
            )
        return '<div class="kpi-top10-chart">%s</div>' % ''.join(bars)

    def _card_html(self, css, icon, label, value, subtitle, button):
        return (
            '<div class="kpi-card %s">'
            '<div class="kpi-card-label"><i class="fa %s me-1"/> %s</div>'
            '<div class="kpi-card-val">%s</div>'
            '<div class="kpi-card-sub">%s</div>'
            '<a href="/odoo/syg.kpi.evaluation" class="kpi-card-btn"><i class="fa fa-list me-1"/> %s</a>'
            '</div>'
        ) % (css, icon, html.escape(label), html.escape(str(value)), subtitle, html.escape(button))

    @api.depends('company_id', 'employee_id')
    def _compute_kpi_dashboard_html(self):
        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        for dash in self:
            year_list = dash._high_scorers(year_start, today, 10)
            status_dist = dash._status_distribution(year_start, today)
            buckets = dash._score_buckets(year_start, today)
            stats_today = dash._period_stats(today, today)
            stats_month = dash._period_stats(month_start, today)
            stats_year = dash._period_stats(year_start, today)
            scores = [float(item['score'] or 0) for item in year_list]
            max_score = max(scores or [100]) or 100
            top_score = scores[0] if scores else 0.0
            best = (year_list[0]['employee'] if year_list else '-')[:40]
            ranks = [
                '<span class="kpi-rank kpi-rank-1">1</span>',
                '<span class="kpi-rank kpi-rank-2">2</span>',
                '<span class="kpi-rank kpi-rank-3">3</span>',
            ]
            top_rows = []
            for index, item in enumerate(year_list[:5]):
                rank = ranks[index] if index < 3 else ''
                top_rows.append(
                    '<tr><td>%s%s</td><td class="kpi-score">%.1f</td><td>%s</td></tr>'
                    % (
                        rank,
                        html.escape((item['employee'] or 'Unknown')[:25]),
                        float(item['score']),
                        dash._status_badge(item.get('status')),
                    )
                )
            if not top_rows:
                top_rows.append(
                    '<tr><td colspan="3" style="padding:24px;text-align:center;color:#94a3b8">No evaluations this year</td></tr>'
                )
            day_rows = []
            for row in dash._last_seven_days():
                day_rows.append(
                    '<tr><td>%s</td><td>%s</td><td>%.1f</td><td>%s</td></tr>'
                    % (row['date_str'], row['count'], float(row['avg']), html.escape((row['top_scorer'] or '-')[:30]))
                )
            cards = ''.join([
                dash._card_html(
                    'kd-teal', 'fa-sun-o', 'Evaluations today', stats_today['total'],
                    '%s evaluations • Avg %.1f' % (stats_today['total'], float(stats_today['avg'])),
                    'View evaluations',
                ),
                dash._card_html(
                    'kd-blue', 'fa-calendar', 'This month', stats_month['total'],
                    '%s evaluations • Avg %.1f' % (stats_month['total'], float(stats_month['avg'])),
                    'View evaluations',
                ),
                dash._card_html(
                    'kd-orange', 'fa-calendar-o', 'This year', stats_year['total'],
                    '%s evaluations • Avg %.1f' % (stats_year['total'], float(stats_year['avg'])),
                    'View evaluations',
                ),
                dash._card_html(
                    'kd-green', 'fa-trophy', 'Top score (year)', '%.1f' % top_score,
                    'Best performer: ' + html.escape(best),
                    'View top scorers',
                ),
            ])
            dash.kpi_dashboard_html = '''
            <div class="kpi-wrap">
                <div class="kpi-header">
                    <h1><i class="fa fa-pie-chart"/> Employee performance rating</h1>
                    <p>KPI evaluations, score bands, and top performers</p>
                </div>
                <div class="kpi-cards">%s</div>
                <div class="kpi-charts-row">
                    <div class="kpi-chart-card"><div class="kpi-chart-title">Evaluations by score band</div>%s</div>
                    <div class="kpi-chart-card"><div class="kpi-chart-title">Score distribution</div>%s</div>
                    <div class="kpi-chart-card"><div class="kpi-chart-title">Employees by score band</div>%s</div>
                </div>
                <div class="kpi-charts-row">
                    <div class="kpi-chart-card kpi-chart-wide">
                        <div class="kpi-chart-title">Top 10 employees by performance score</div>%s
                    </div>
                </div>
                <div class="kpi-tables">
                    <div class="kpi-table-wrap">
                        <div class="kpi-table-hdr"><i class="fa fa-calendar-check-o"/> Last 7 days</div>
                        <div class="kpi-table-sub">Evaluations covering each day, and the top scorer</div>
                        <table class="kpi-t"><thead><tr><th>Date</th><th>Count</th><th>Avg</th><th>Top scorer</th></tr></thead><tbody>%s</tbody></table>
                    </div>
                    <div class="kpi-table-wrap">
                        <div class="kpi-table-hdr"><i class="fa fa-trophy"/> Top scorers this year</div>
                        <div class="kpi-table-sub">Best score in the year so far</div>
                        <table class="kpi-t"><thead><tr><th>Employee</th><th>Score</th><th>Band</th></tr></thead><tbody>%s</tbody></table>
                    </div>
                </div>
            </div>
            ''' % (
                cards,
                dash._donut_html(stats_year['total'], status_dist, 'Total'),
                dash._donut_html('%.1f' % stats_year['avg'], buckets, 'Avg score'),
                dash._status_bar_html(status_dist),
                dash._top_bar_html(year_list, max_score),
                ''.join(day_rows),
                ''.join(top_rows),
            )
