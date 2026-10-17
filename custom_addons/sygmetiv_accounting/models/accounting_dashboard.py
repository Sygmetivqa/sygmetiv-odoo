# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class SygAccountingDashboard(models.TransientModel):
    _name = 'syg.accounting.dashboard'
    _inherit = 'syg.dashboard.mixin'
    _description = 'Accounting Dashboard'

    name = fields.Char(default="Accounting Dashboard", readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    period_start = fields.Date()
    period_end = fields.Date()
    d_period = fields.Char(compute='_compute_kpis')
    income_amount = fields.Monetary(currency_field='currency_id', compute='_compute_kpis')
    expense_amount = fields.Monetary(currency_field='currency_id', compute='_compute_kpis')
    profit_amount = fields.Monetary(currency_field='currency_id', compute='_compute_kpis')
    receivable_amount = fields.Monetary(currency_field='currency_id', compute='_compute_kpis')
    payable_amount = fields.Monetary(currency_field='currency_id', compute='_compute_kpis')
    invoice_count = fields.Integer(compute='_compute_kpis')
    bill_count = fields.Integer(compute='_compute_kpis')
    d_income = fields.Char(compute='_compute_kpis')
    d_expense = fields.Char(compute='_compute_kpis')
    d_profit = fields.Char(compute='_compute_kpis')
    d_receivable = fields.Char(compute='_compute_kpis')
    d_payable = fields.Char(compute='_compute_kpis')
    d_invoices = fields.Char(compute='_compute_kpis')
    d_bills = fields.Char(compute='_compute_kpis')
    graph_pnl = fields.Text(compute='_compute_kpis')

    @api.model
    def action_open(self, period_start=None, period_end=None):
        today = fields.Date.context_today(self)
        dash = self.create({
            'period_start': period_start or today.replace(day=1),
            'period_end': period_end or (today + relativedelta(day=31)),
        })
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Accounting Dashboard"),
            'res_model': 'syg.accounting.dashboard',
            'res_id': dash.id,
            'view_mode': 'form',
            'views': [(self.env.ref('sygmetiv_accounting.view_syg_accounting_dashboard_form').id, 'form')],
            'target': 'current',
            'context': self._dashboard_form_context(),
        }

    def action_refresh(self):
        self.ensure_one()
        return self.action_open(self.period_start, self.period_end)

    def action_open_invoices(self):
        return self.env.ref('account.action_move_out_invoice').sudo().read()[0]

    def action_open_bills(self):
        return self.env.ref('account.action_move_in_invoice').sudo().read()[0]

    def action_open_receivable(self):
        action = self.env.ref('account.action_account_moves_all').sudo().read()[0]
        action['domain'] = [
            ('parent_state', '=', 'posted'),
            ('account_id.account_type', '=', 'asset_receivable'),
            ('amount_residual', '!=', 0),
        ]
        action['name'] = self.env._("Aged Receivables")
        return action

    def action_open_mis(self):
        self.ensure_one()
        return self.env['syg.mis.report'].action_open('executive', self.period_start, self.period_end)

    def action_open_mis_pnl(self):
        self.ensure_one()
        return self.env['syg.mis.report'].action_open('pnl', self.period_start, self.period_end)

    def action_open_mis_balance_sheet(self):
        self.ensure_one()
        return self.env['syg.mis.report'].action_open('balance_sheet', self.period_start, self.period_end)

    def action_open_payable(self):
        action = self.env.ref('account.action_account_moves_all').sudo().read()[0]
        action['domain'] = [
            ('parent_state', '=', 'posted'),
            ('account_id.account_type', '=', 'liability_payable'),
            ('amount_residual', '!=', 0),
        ]
        action['name'] = self.env._("Aged Payables")
        return action

    @api.depends('company_id', 'period_start', 'period_end', 'currency_id')
    def _compute_kpis(self):
        Move = self.env['account.move']
        Line = self.env['account.move.line'].sudo()
        for dash in self:
            start, end, company = dash.period_start, dash.period_end, dash.company_id
            dash.d_period = '%s – %s' % (start.strftime('%d %b'), end.strftime('%d %b %Y')) if start and end else ''
            company_domain = [('company_id', '=', company.id)] if company else []
            period_domain = company_domain[:]
            if start and end:
                period_domain += [('date', '>=', start), ('date', '<=', end)]
            posted = period_domain + [('parent_state', '=', 'posted')]
            income = sum(Line.search(posted + [
                ('account_id.account_type', 'in', ('income', 'income_other')),
            ]).mapped('balance')) * -1
            expense = sum(Line.search(posted + [
                ('account_id.account_type', 'in', (
                    'expense', 'expense_other', 'expense_direct_cost', 'expense_depreciation',
                )),
            ]).mapped('balance'))
            receivable = sum(Line.search(company_domain + [
                ('parent_state', '=', 'posted'),
                ('account_id.account_type', '=', 'asset_receivable'),
            ]).mapped('amount_residual'))
            payable = sum(Line.search(company_domain + [
                ('parent_state', '=', 'posted'),
                ('account_id.account_type', '=', 'liability_payable'),
            ]).mapped('amount_residual'))
            invoice_domain = company_domain + [('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]
            bill_domain = company_domain + [('move_type', '=', 'in_invoice'), ('state', '=', 'posted')]
            if start and end:
                invoice_domain += [('invoice_date', '>=', start), ('invoice_date', '<=', end)]
                bill_domain += [('invoice_date', '>=', start), ('invoice_date', '<=', end)]
            dash.income_amount = income
            dash.expense_amount = expense
            dash.profit_amount = income - expense
            dash.receivable_amount = receivable
            dash.payable_amount = abs(payable)
            dash.invoice_count = Move.search_count(invoice_domain)
            dash.bill_count = Move.search_count(bill_domain)
            dash.d_income = dash._money_label(income)
            dash.d_expense = dash._money_label(expense)
            dash.d_profit = dash._money_label(income - expense)
            dash.d_receivable = dash._money_label(receivable)
            dash.d_payable = dash._money_label(abs(payable))
            dash.d_invoices = str(dash.invoice_count)
            dash.d_bills = str(dash.bill_count)
            dash.graph_pnl = dash._graph_json([
                {'label': self.env._("Income"), 'value': round(income, 2), 'type': 'past'},
                {'label': self.env._("Expense"), 'value': round(expense, 2), 'type': 'future'},
                {'label': self.env._("Profit"), 'value': round(income - expense, 2), 'type': 'past'},
            ], self.env._("P&L"))
