# -*- coding: utf-8 -*-

from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class SygSalesDashboard(models.TransientModel):
    _name = 'syg.sales.dashboard'
    _inherit = 'syg.dashboard.mixin'
    _description = 'Sales Dashboard'

    name = fields.Char(default="Sales Dashboard", readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    period_start = fields.Date()
    period_end = fields.Date()
    d_period = fields.Char(compute='_compute_kpis')

    lead_count = fields.Integer(compute='_compute_kpis')
    opportunity_count = fields.Integer(compute='_compute_kpis')
    won_count = fields.Integer(compute='_compute_kpis')
    lost_count = fields.Integer(compute='_compute_kpis')
    pipeline_amount = fields.Monetary(currency_field='currency_id', compute='_compute_kpis')
    quotation_count = fields.Integer(compute='_compute_kpis')
    order_count = fields.Integer(compute='_compute_kpis')
    sales_amount = fields.Monetary(currency_field='currency_id', compute='_compute_kpis')
    quotation_amount = fields.Monetary(currency_field='currency_id', compute='_compute_kpis')

    d_leads = fields.Char(compute='_compute_kpis')
    d_opportunities = fields.Char(compute='_compute_kpis')
    d_won = fields.Char(compute='_compute_kpis')
    d_lost = fields.Char(compute='_compute_kpis')
    d_pipeline = fields.Char(compute='_compute_kpis')
    d_quotations = fields.Char(compute='_compute_kpis')
    d_orders = fields.Char(compute='_compute_kpis')
    d_sales = fields.Char(compute='_compute_kpis')
    d_quotation_amt = fields.Char(compute='_compute_kpis')

    graph_leads = fields.Text(compute='_compute_kpis')
    graph_pipeline = fields.Text(compute='_compute_kpis')
    graph_sales = fields.Text(compute='_compute_kpis')
    graph_mix = fields.Text(compute='_compute_kpis')

    @api.model
    def action_open(self, period_start=None, period_end=None):
        today = fields.Date.context_today(self)
        dash = self.create({
            'name': self.env._("Sales Dashboard"),
            'company_id': self.env.company.id,
            'period_start': period_start or today.replace(day=1),
            'period_end': period_end or (today + relativedelta(day=31)),
        })
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Sales Dashboard"),
            'res_model': 'syg.sales.dashboard',
            'res_id': dash.id,
            'view_mode': 'form',
            'views': [(self.env.ref('sygmetiv_sales.view_syg_sales_dashboard_form').id, 'form')],
            'target': 'current',
            'context': self._dashboard_form_context(),
        }

    def action_refresh(self):
        self.ensure_one()
        return self.action_open(self.period_start, self.period_end)

    def action_open_leads(self):
        action = self.env.ref('crm.crm_lead_all_leads', raise_if_not_found=False)
        if not action:
            action = self.env.ref('crm.crm_lead_action_pipeline', raise_if_not_found=False)
        return action.sudo().read()[0] if action else False

    def action_open_opportunities(self):
        action = self.env.ref('crm.action_your_pipeline', raise_if_not_found=False)
        return action.sudo().read()[0] if action else False

    def action_open_quotations(self):
        return self.env.ref('sale.action_quotations_with_onboarding').sudo().read()[0]

    def action_open_orders(self):
        return self.env.ref('sale.action_orders').sudo().read()[0]

    @api.depends('company_id', 'period_start', 'period_end', 'currency_id')
    def _compute_kpis(self):
        Lead = self.env['crm.lead']
        Order = self.env['sale.order']
        for dash in self:
            start, end, company = dash.period_start, dash.period_end, dash.company_id
            dash.d_period = '%s – %s' % (start.strftime('%d %b'), end.strftime('%d %b %Y')) if start and end else ''
            company_domain = [('company_id', '=', company.id)] if company else []
            lead_domain = company_domain + [('type', '=', 'lead')]
            opp_domain = company_domain + [('type', '=', 'opportunity')]
            if start and end:
                lead_period = lead_domain + [('create_date', '>=', start), ('create_date', '<', end + relativedelta(days=1))]
                opp_period = opp_domain + [('create_date', '>=', start), ('create_date', '<', end + relativedelta(days=1))]
            else:
                lead_period = lead_domain
                opp_period = opp_domain
            dash.lead_count = Lead.search_count(lead_period)
            dash.opportunity_count = Lead.search_count(opp_period)
            won_domain = opp_domain + [('probability', '=', 100), ('active', '=', True)]
            if start and end:
                won_domain += [('date_closed', '>=', start), ('date_closed', '<=', end)]
            dash.won_count = Lead.search_count(won_domain)
            lost_domain = company_domain + [('active', '=', False), ('probability', '=', 0)]
            if start and end:
                lost_domain += [('date_closed', '>=', start), ('date_closed', '<=', end)]
            dash.lost_count = Lead.search_count(lost_domain)
            pipeline_leads = Lead.search(opp_domain + [('active', '=', True), ('probability', '<', 100)])
            dash.pipeline_amount = sum(pipeline_leads.mapped('expected_revenue'))
            quote_domain = company_domain + [('state', 'in', ('draft', 'sent'))]
            sale_domain = company_domain + [('state', '=', 'sale')]
            if start and end:
                quote_domain += [('date_order', '>=', start), ('date_order', '<=', end)]
                sale_domain += [('date_order', '>=', start), ('date_order', '<=', end)]
            quotations = Order.search(quote_domain)
            orders = Order.search(sale_domain)
            dash.quotation_count = len(quotations)
            dash.order_count = len(orders)
            dash.quotation_amount = sum(quotations.mapped('amount_total'))
            dash.sales_amount = sum(orders.mapped('amount_total'))
            dash.d_leads = str(dash.lead_count)
            dash.d_opportunities = str(dash.opportunity_count)
            dash.d_won = str(dash.won_count)
            dash.d_lost = str(dash.lost_count)
            dash.d_pipeline = dash._money_label(dash.pipeline_amount)
            dash.d_quotations = str(dash.quotation_count)
            dash.d_orders = str(dash.order_count)
            dash.d_sales = dash._money_label(dash.sales_amount)
            dash.d_quotation_amt = dash._money_label(dash.quotation_amount)
            dash.graph_leads = dash._graph_leads(company, start, end)
            dash.graph_pipeline = dash._graph_pipeline(company)
            dash.graph_sales = dash._graph_sales(company, end or fields.Date.context_today(self))
            dash.graph_mix = dash._graph_mix(dash)

    def _graph_leads(self, company, start, end):
        domain = [('company_id', '=', company.id)] if company else []
        if start and end:
            domain += [('create_date', '>=', start), ('create_date', '<', end + relativedelta(days=1))]
        grouped = self.env['crm.lead']._read_group(domain, ['type'], ['__count'])
        labels = {'lead': self.env._("Leads"), 'opportunity': self.env._("Opportunities")}
        values = []
        for lead_type, count in grouped:
            values.append({
                'label': labels.get(lead_type, lead_type),
                'value': count,
                'type': 'past',
            })
        return self._graph_json(values, self.env._("New pipeline"))

    def _graph_pipeline(self, company):
        domain = [('company_id', '=', company.id), ('type', '=', 'opportunity'), ('active', '=', True)]
        grouped = self.env['crm.lead']._read_group(domain, ['stage_id'], ['expected_revenue:sum'])
        values = []
        for stage, revenue in grouped:
            values.append({
                'label': stage.display_name if stage else self.env._("No stage"),
                'value': round(revenue or 0.0, 2),
                'type': 'past',
            })
        return self._graph_json(values[:8], self.env._("Pipeline by stage"))

    def _graph_sales(self, company, end):
        start = (end.replace(day=1) - relativedelta(months=5))
        orders = self.env['sale.order'].search([
            ('company_id', '=', company.id),
            ('state', '=', 'sale'),
            ('date_order', '>=', start),
            ('date_order', '<=', end),
        ])
        by_month = defaultdict(float)
        for order in orders:
            key = order.date_order.strftime('%b %Y')
            by_month[key] += order.amount_total or 0.0
        values = []
        cursor = start
        while cursor <= end:
            label = cursor.strftime('%b %Y')
            values.append({'label': label, 'value': round(by_month.get(label, 0.0), 2), 'type': 'past'})
            cursor += relativedelta(months=1)
        return self._graph_json(values, self.env._("Confirmed sales"))

    def _graph_mix(self, dash):
        return self._graph_json([
            {'label': self.env._("Quotations"), 'value': dash.quotation_count, 'type': 'future'},
            {'label': self.env._("Orders"), 'value': dash.order_count, 'type': 'past'},
            {'label': self.env._("Won deals"), 'value': dash.won_count, 'type': 'past'},
            {'label': self.env._("Lost"), 'value': dash.lost_count, 'type': 'future'},
        ], self.env._("Company mix"))
