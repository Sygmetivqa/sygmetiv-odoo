# -*- coding: utf-8 -*-

import json

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools.misc import format_date


class SygDashboardMixin(models.AbstractModel):
    _name = 'syg.dashboard.mixin'
    _description = 'Sygmetiv dashboard helpers'

    def _hours_label(self, hours):
        total_minutes = int(round((hours or 0.0) * 60))
        sign = '-' if total_minutes < 0 else ''
        hours_part, minutes = divmod(abs(total_minutes), 60)
        return '%s%d:%02d' % (sign, hours_part, minutes)

    def _money_label(self, amount, currency=None):
        currency = currency or self.currency_id
        if currency:
            return currency.format(amount or 0.0)
        return '%.2f' % (amount or 0.0)

    def _date_label(self, value):
        return format_date(self.env, value) if value else '—'

    def _selection_map(self, model, field_name):
        field = self.env[model]._fields.get(field_name)
        if not field:
            return {}
        desc = field.get_description(self.env, attributes={'selection'})
        return dict(desc.get('selection') or [])

    def _graph_json(self, values, key):
        if not values:
            values = [{'label': self.env._("No data"), 'value': 0, 'type': 'past'}]
        return json.dumps([{
            'values': values,
            'key': key,
            'is_sample_data': False,
        }])

    def _graph_series_json(self, series):
        """Stacked chart payload. ``series`` is ``[(name, [{label, value}, ...])]``."""
        payload = []
        for key, values in series:
            if not values:
                continue
            payload.append({
                'values': values,
                'key': key,
                'is_sample_data': False,
            })
        if not payload:
            return self._graph_json([], self.env._("No data"))
        return json.dumps(payload)

    def _month_window(self):
        today = fields.Date.context_today(self)
        return today.replace(day=1), today + relativedelta(day=31), today

    def _dashboard_form_context(self, extra=None):
        context = {'form_view_initial_mode': 'edit'}
        if extra:
            context.update(extra)
        return context

    @api.onchange('period_start', 'period_end')
    def _onchange_dashboard_period(self):
        if self.period_start and self.period_end and self.period_start > self.period_end:
            self.period_end = self.period_start
        for method_name in (
            '_compute_kpis',
            '_compute_display_labels',
            '_compute_manager_stats',
            '_compute_employee_graphs',
            '_compute_employee_profile',
            '_compute_welcome',
            '_compute_announcement_board',
            '_compute_dashboard_flags',
            '_compute_task_request_kpis',
        ):
            method = getattr(type(self), method_name, None)
            if method:
                method(self)
