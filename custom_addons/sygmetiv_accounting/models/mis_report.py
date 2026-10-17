# -*- coding: utf-8 -*-

import base64
import io
import json
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import Command, api, fields, models
from odoo.exceptions import UserError


def _json_id(value):
    if isinstance(value, int):
        return value
    origin = getattr(value, 'origin', None)
    return origin or False


REPORT_TYPES = [
    ('executive', 'Executive MIS'),
    ('pnl', 'Profit and Loss'),
    ('balance_sheet', 'Balance Sheet'),
    ('trial_balance', 'Trial Balance'),
    ('cash_flow', 'Cash Flow'),
    ('partner_ledger', 'Partner Ledger'),
    ('aged_receivable', 'Aged Receivable'),
    ('aged_payable', 'Aged Payable'),
    ('tax', 'Tax Summary'),
]


class SygMisReport(models.TransientModel):
    _name = 'syg.mis.report'
    _inherit = 'syg.dashboard.mixin'
    _description = 'MIS Report'

    name = fields.Char(compute='_compute_name')
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related='company_id.currency_id')
    report_type = fields.Selection(REPORT_TYPES, required=True, default='executive')
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True)
    compare_previous = fields.Boolean(default=True)
    hide_zero = fields.Boolean(default=True)
    line_ids = fields.One2many('syg.mis.report.line', 'report_id')
    show_aged = fields.Boolean(compute='_compute_flags')
    show_trial = fields.Boolean(compute='_compute_flags')
    period_label = fields.Char(compute='_compute_labels')
    previous_label = fields.Char(compute='_compute_labels')
    report_payload = fields.Text(compute='_compute_report_payload')

    @api.depends('report_type')
    def _compute_name(self):
        labels = dict(REPORT_TYPES)
        for rec in self:
            rec.name = labels.get(rec.report_type) or self.env._("MIS Report")

    @api.depends('report_type')
    def _compute_flags(self):
        for rec in self:
            rec.show_aged = rec.report_type in ('aged_receivable', 'aged_payable')
            rec.show_trial = rec.report_type in ('trial_balance', 'partner_ledger', 'tax', 'cash_flow')

    @api.depends('period_start', 'period_end', 'compare_previous')
    def _compute_labels(self):
        for rec in self:
            rec.period_label = ''
            rec.previous_label = ''
            if rec.period_start and rec.period_end:
                rec.period_label = '%s – %s' % (
                    rec.period_start.strftime('%d %b %Y'),
                    rec.period_end.strftime('%d %b %Y'),
                )
                if rec.compare_previous:
                    prev_start, prev_end = rec._previous_window()
                    rec.previous_label = '%s – %s' % (
                        prev_start.strftime('%d %b %Y'),
                        prev_end.strftime('%d %b %Y'),
                    )

    @api.depends(
        'line_ids', 'line_ids.name', 'line_ids.balance', 'line_ids.previous',
        'line_ids.debit', 'line_ids.credit', 'line_ids.variance', 'line_ids.line_type',
        'line_ids.code', 'line_ids.account_id', 'line_ids.partner_id',
        'line_ids.not_due', 'line_ids.days_30', 'line_ids.days_60',
        'line_ids.days_90', 'line_ids.days_older', 'line_ids.level', 'line_ids.percent',
        'name', 'period_label', 'previous_label', 'show_aged', 'show_trial',
        'compare_previous', 'hide_zero', 'currency_id',
    )
    def _compute_report_payload(self):
        for rec in self:
            lines = []
            for line in rec.line_ids:
                if rec.hide_zero and line.line_type == 'account' and not any((
                    line.balance, line.previous, line.debit, line.credit,
                    line.not_due, line.days_30, line.days_60, line.days_90, line.days_older,
                )):
                    continue
                lines.append({
                    'id': _json_id(line.id),
                    'type': line.line_type,
                    'level': line.level or 0,
                    'code': line.code or '',
                    'name': line.name or '',
                    'account_id': _json_id(line.account_id.id),
                    'partner_id': _json_id(line.partner_id.id),
                    'debit': line.debit,
                    'credit': line.credit,
                    'balance': line.balance,
                    'previous': line.previous,
                    'variance': line.variance,
                    'percent': line.percent,
                    'not_due': line.not_due,
                    'days_30': line.days_30,
                    'days_60': line.days_60,
                    'days_90': line.days_90,
                    'days_older': line.days_older,
                })
            rec.report_payload = json.dumps({
                'title': rec.name or '',
                'period': rec.period_label or '',
                'previous_label': rec.previous_label or '',
                'symbol': rec.currency_id.symbol if rec.currency_id else '',
                'compare': bool(rec.compare_previous),
                'aged': bool(rec.show_aged),
                'trial': bool(rec.show_trial),
                'lines': lines,
            })

    @api.model
    def action_open(self, report_type='executive', period_start=None, period_end=None):
        today = fields.Date.context_today(self)
        rec = self.create({
            'report_type': report_type,
            'period_start': period_start or today.replace(day=1),
            'period_end': period_end or (today + relativedelta(day=31)),
            'company_id': self.env.company.id,
        })
        rec._generate_lines()
        return {
            'type': 'ir.actions.act_window',
            'name': rec.name,
            'res_model': 'syg.mis.report',
            'res_id': rec.id,
            'view_mode': 'form',
            'views': [(self.env.ref('sygmetiv_accounting.view_syg_mis_report_form').id, 'form')],
            'target': 'current',
            'context': rec._dashboard_form_context({'default_report_type': report_type}),
        }

    def action_compute(self):
        self.ensure_one()
        self._generate_lines()
        return True

    def action_print(self):
        self.ensure_one()
        self._generate_lines()
        return self.env.ref('sygmetiv_accounting.action_report_syg_mis').report_action(self)

    def action_export_xlsx(self):
        self.ensure_one()
        self._generate_lines()
        attachment = self.env['ir.attachment'].create({
            'name': '%s.xlsx' % (self.name or self.env._('MIS Report')),
            'type': 'binary',
            'datas': base64.b64encode(self._xlsx_content()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name,
            'res_id': self.id,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'download',
        }

    def _xlsx_content(self):
        self.ensure_one()
        import xlsxwriter  # noqa: PLC0415

        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        sheet = workbook.add_worksheet((self.name or 'MIS')[:31])
        title = workbook.add_format({'bold': True, 'font_size': 14})
        header = workbook.add_format({'bold': True, 'bottom': 1})
        money = workbook.add_format({'num_format': '#,##0.00'})
        money_bold = workbook.add_format({'num_format': '#,##0.00', 'bold': True})
        section = workbook.add_format({'bold': True, 'bg_color': '#F8F9FA'})
        indent = workbook.add_format()
        indent_bold = workbook.add_format({'bold': True})
        percent = workbook.add_format({'num_format': '0.0%'})
        percent_bold = workbook.add_format({'num_format': '0.0%', 'bold': True})

        headers = [self.env._('Account')]
        if self.compare_previous:
            headers.append(self.env._('Previous Period'))
        if self.show_trial:
            headers.extend([self.env._('Debit'), self.env._('Credit')])
        if self.show_aged:
            headers.extend([
                self.env._('Not Due'),
                self.env._('1-30'),
                self.env._('31-60'),
                self.env._('61-90'),
                self.env._('Older'),
            ])
        headers.append(self.env._('Current Period'))
        if self.compare_previous:
            headers.extend([self.env._('% of Period'), self.env._('Variance')])

        sheet.write(0, 0, self.name or '', title)
        sheet.write(1, 0, '%s  %s' % (self.company_id.display_name or '', self.period_label or ''))
        sheet.write_row(3, 0, headers, header)

        row = 4
        for line in self.line_ids:
            if self.hide_zero and line.line_type == 'account' and not any((
                line.balance, line.previous, line.debit, line.credit,
                line.not_due, line.days_30, line.days_60, line.days_90, line.days_older,
            )):
                continue
            is_total = line.line_type == 'total'
            is_section = line.line_type == 'section'
            name_fmt = section if is_section else (indent_bold if is_total else indent)
            num_fmt = money_bold if is_total or is_section else money
            name = '%s%s%s' % (
                '    ' * (line.level or 0),
                ('%s ' % line.code) if line.code else '',
                line.name or '',
            )
            col = 0
            sheet.write(row, col, name, name_fmt)
            col += 1
            if self.compare_previous:
                sheet.write_number(row, col, line.previous or 0.0, num_fmt)
                col += 1
            if self.show_trial:
                sheet.write_number(row, col, line.debit or 0.0, num_fmt)
                col += 1
                sheet.write_number(row, col, line.credit or 0.0, num_fmt)
                col += 1
            if self.show_aged:
                for value in (line.not_due, line.days_30, line.days_60, line.days_90, line.days_older):
                    sheet.write_number(row, col, value or 0.0, num_fmt)
                    col += 1
            sheet.write_number(row, col, line.balance or 0.0, num_fmt)
            col += 1
            if self.compare_previous:
                sheet.write_number(
                    row, col, (line.percent or 0.0) / 100.0,
                    percent_bold if is_total or is_section else percent,
                )
                col += 1
                sheet.write_number(row, col, line.variance or 0.0, num_fmt)
            row += 1

        sheet.set_column(0, 0, 48)
        if headers:
            sheet.set_column(1, len(headers) - 1, 16)
        workbook.close()
        content = buffer.getvalue()
        buffer.close()
        return content

    def action_period_month(self):
        today = fields.Date.context_today(self)
        self.period_start = today.replace(day=1)
        self.period_end = today + relativedelta(day=31)
        self._generate_lines()
        return True

    def action_period_quarter(self):
        today = fields.Date.context_today(self)
        quarter = ((today.month - 1) // 3) * 3 + 1
        self.period_start = today.replace(month=quarter, day=1)
        self.period_end = self.period_start + relativedelta(months=3, days=-1)
        self._generate_lines()
        return True

    def action_period_year(self):
        today = fields.Date.context_today(self)
        fy = self.company_id.compute_fiscalyear_dates(today)
        self.period_start = fy['date_from']
        self.period_end = fy['date_to']
        self._generate_lines()
        return True

    def action_open_move_lines(self, account_id=False, partner_id=False):
        self.ensure_one()
        domain = self._base_domain()
        if self.report_type in ('balance_sheet', 'aged_receivable', 'aged_payable'):
            domain += [('date', '<=', self.period_end)]
        else:
            domain += [('date', '>=', self.period_start), ('date', '<=', self.period_end)]
        if account_id:
            domain.append(('account_id', '=', account_id))
        if partner_id:
            domain.append(('partner_id', '=', partner_id))
        if self.report_type in ('aged_receivable', 'aged_payable'):
            domain.append(('amount_residual', '!=', 0))
        action = self.env.ref('account.action_account_moves_all').sudo().read()[0]
        action['domain'] = domain
        action['name'] = self.env._("Journal Items")
        action['context'] = {'search_default_posted': 1}
        return action

    @api.onchange('report_type', 'period_start', 'period_end', 'company_id', 'compare_previous', 'hide_zero')
    def _onchange_generate(self):
        if self.period_start and self.period_end and self.company_id:
            if self.period_start > self.period_end:
                self.period_end = self.period_start
            self._generate_lines()

    def _previous_window(self):
        days = (self.period_end - self.period_start).days + 1
        prev_end = self.period_start - relativedelta(days=1)
        prev_start = prev_end - relativedelta(days=days - 1)
        return prev_start, prev_end

    def _base_domain(self):
        return [
            ('company_id', '=', self.company_id.id),
            ('parent_state', '=', 'posted'),
            ('display_type', 'not in', ('line_section', 'line_note')),
        ]

    def _group_accounts(self, extra_domain, start=None, end=None):
        domain = self._base_domain() + extra_domain
        if start:
            domain += [('date', '>=', start)]
        if end:
            domain += [('date', '<=', end)]
        grouped = self.env['account.move.line'].sudo()._read_group(
            domain,
            ['account_id'],
            ['debit:sum', 'credit:sum', 'balance:sum'],
        )
        rows = []
        for account, debit, credit, balance in grouped:
            if not account:
                continue
            rows.append({
                'account': account,
                'code': account.code or '',
                'name': account.display_name,
                'debit': debit or 0.0,
                'credit': credit or 0.0,
                'balance': balance or 0.0,
            })
        return sorted(rows, key=lambda row: (row['code'], row['name']))

    def _sum_balance(self, extra_domain, start=None, end=None):
        return sum(row['balance'] for row in self._group_accounts(extra_domain, start, end))

    def _section(self, name, sequence, level=0):
        return {
            'sequence': sequence,
            'line_type': 'section',
            'name': name,
            'level': level,
        }

    def _total(self, name, sequence, **amounts):
        vals = {
            'sequence': sequence,
            'line_type': 'total',
            'name': name,
            'level': amounts.pop('level', 0),
        }
        vals.update(amounts)
        return vals

    def _account_line(self, sequence, row, amount=None, previous=0.0, invert=False, level=1):
        raw = row['balance']
        value = amount if amount is not None else (-raw if invert else raw)
        previous_value = -previous if invert else previous
        return {
            'sequence': sequence,
            'line_type': 'account',
            'name': row['name'],
            'code': row['code'],
            'level': level,
            'account_id': row['account'].id,
            'debit': row['debit'],
            'credit': row['credit'],
            'balance': value,
            'previous': previous_value,
            'variance': value - previous_value,
        }

    def _generate_lines(self):
        self.ensure_one()
        if not (self.period_start and self.period_end and self.company_id):
            raise UserError(self.env._("Set company and dates first."))
        method = getattr(self, '_lines_%s' % self.report_type)
        vals_list = method()
        if self.hide_zero:
            vals_list = [
                vals for vals in vals_list
                if vals.get('line_type') != 'account' or any(
                    abs(vals.get(key) or 0.0) > 0.004
                    for key in ('balance', 'previous', 'debit', 'credit', 'not_due', 'days_30', 'days_60', 'days_90', 'days_older')
                )
            ]
        self._apply_percents(vals_list)
        self.line_ids = [Command.clear()] + [Command.create(vals) for vals in vals_list]

    def _apply_percents(self, vals_list):
        base = next(
            (abs(vals.get('balance') or 0.0) for vals in vals_list if vals.get('name') in (
                self.env._("Total Income"), self.env._("Revenue"),
            )),
            0.0,
        )
        if not base:
            base = max((abs(vals.get('balance') or 0.0) for vals in vals_list), default=0.0)
        if not base:
            return
        for vals in vals_list:
            if vals.get('line_type') == 'section':
                continue
            vals['percent'] = 100.0 * (vals.get('balance') or 0.0) / base

    def _prev_map(self, extra_domain):
        if not self.compare_previous:
            return {}
        prev_start, prev_end = self._previous_window()
        return {
            row['account'].id: row['balance']
            for row in self._group_accounts(extra_domain, prev_start, prev_end)
        }

    def _lines_pnl(self):
        seq = 10
        lines = [self._section(self.env._("Income"), seq)]
        seq += 1
        income_domain = [('account_id.internal_group', '=', 'income')]
        prev = self._prev_map(income_domain)
        income_total = 0.0
        income_prev = 0.0
        for row in self._group_accounts(income_domain, self.period_start, self.period_end):
            previous = prev.get(row['account'].id, 0.0)
            lines.append(self._account_line(seq, row, invert=True, previous=previous))
            income_total += -row['balance']
            income_prev += -previous
            seq += 1
        lines.append(self._total(
            self.env._("Total Income"), seq,
            balance=income_total, previous=income_prev, variance=income_total - income_prev,
        ))
        seq += 1
        lines.append(self._section(self.env._("Cost of Revenue"), seq))
        seq += 1
        cogs_domain = [('account_id.account_type', '=', 'expense_direct_cost')]
        prev_cogs = self._prev_map(cogs_domain)
        cogs_total = 0.0
        cogs_prev = 0.0
        for row in self._group_accounts(cogs_domain, self.period_start, self.period_end):
            previous = prev_cogs.get(row['account'].id, 0.0)
            lines.append(self._account_line(seq, row, previous=previous))
            cogs_total += row['balance']
            cogs_prev += previous
            seq += 1
        lines.append(self._total(
            self.env._("Gross Profit"), seq,
            balance=income_total - cogs_total,
            previous=income_prev - cogs_prev,
            variance=(income_total - cogs_total) - (income_prev - cogs_prev),
        ))
        seq += 1
        lines.append(self._section(self.env._("Operating Expenses"), seq))
        seq += 1
        opex_domain = [
            ('account_id.internal_group', '=', 'expense'),
            ('account_id.account_type', '!=', 'expense_direct_cost'),
        ]
        prev_opex = self._prev_map(opex_domain)
        opex_total = 0.0
        opex_prev = 0.0
        for row in self._group_accounts(opex_domain, self.period_start, self.period_end):
            previous = prev_opex.get(row['account'].id, 0.0)
            lines.append(self._account_line(seq, row, previous=previous))
            opex_total += row['balance']
            opex_prev += previous
            seq += 1
        net = income_total - cogs_total - opex_total
        net_prev = income_prev - cogs_prev - opex_prev
        lines.append(self._total(
            self.env._("Net Profit"), seq,
            balance=net, previous=net_prev, variance=net - net_prev,
        ))
        return lines

    def _balance_at(self, extra_domain, at_date):
        return self._sum_balance(extra_domain, end=at_date)

    def _lines_balance_sheet(self):
        sections = [
            (self.env._("Assets"), [('account_id.internal_group', '=', 'asset')]),
            (self.env._("Liabilities"), [('account_id.internal_group', '=', 'liability')]),
            (self.env._("Equity"), [('account_id.internal_group', '=', 'equity')]),
        ]
        seq = 10
        lines = []
        totals = {}
        for title, domain in sections:
            lines.append(self._section(title, seq))
            seq += 1
            section_total = 0.0
            for row in self._group_accounts(domain, end=self.period_end):
                lines.append(self._account_line(seq, row))
                section_total += row['balance']
                seq += 1
            lines.append(self._total(self.env._("Total %s", title), seq, balance=section_total))
            totals[title] = section_total
            seq += 1
        fy = self.company_id.compute_fiscalyear_dates(self.period_end)
        retained = -self._sum_balance(
            [('account_id.internal_group', 'in', ('income', 'expense'))],
            start=fy['date_from'],
            end=self.period_end,
        )
        lines.append(self._total(self.env._("Current Year Earnings"), seq, balance=retained))
        seq += 1
        equity = totals.get(self.env._("Equity"), 0.0) + retained
        lines.append(self._total(
            self.env._("Liabilities + Equity"),
            seq,
            balance=totals.get(self.env._("Liabilities"), 0.0) + equity,
        ))
        return lines

    def _lines_trial_balance(self):
        fy = self.company_id.compute_fiscalyear_dates(self.period_start)
        seq = 10
        lines = [self._section(self.env._("Trial Balance"), seq)]
        seq += 1
        opening_by_account = {}
        for row in self._group_accounts([('account_id.include_initial_balance', '=', True)], end=self.period_start - relativedelta(days=1)):
            opening_by_account[row['account'].id] = row
        for row in self._group_accounts(
            [('account_id.include_initial_balance', '=', False)],
            start=fy['date_from'],
            end=self.period_start - relativedelta(days=1),
        ):
            opening_by_account[row['account'].id] = row
        movement = {
            row['account'].id: row
            for row in self._group_accounts([], self.period_start, self.period_end)
        }
        account_ids = set(opening_by_account) | set(movement)
        accounts = self.env['account.account'].browse(list(account_ids)).sorted(lambda acc: acc.code or acc.name)
        tot_open = tot_debit = tot_credit = tot_end = 0.0
        for account in accounts:
            open_row = opening_by_account.get(account.id, {})
            move_row = movement.get(account.id, {})
            opening = open_row.get('balance', 0.0)
            debit = move_row.get('debit', 0.0)
            credit = move_row.get('credit', 0.0)
            ending = opening + (move_row.get('balance', 0.0) if move_row else 0.0)
            if not any((opening, debit, credit, ending)):
                continue
            lines.append({
                'sequence': seq,
                'line_type': 'account',
                'name': account.display_name,
                'code': account.code or '',
                'account_id': account.id,
                'previous': opening,
                'debit': debit,
                'credit': credit,
                'balance': ending,
                'variance': ending - opening,
            })
            tot_open += opening
            tot_debit += debit
            tot_credit += credit
            tot_end += ending
            seq += 1
        lines.append(self._total(
            self.env._("Total"),
            seq,
            previous=tot_open,
            debit=tot_debit,
            credit=tot_credit,
            balance=tot_end,
            variance=tot_end - tot_open,
        ))
        return lines

    def _lines_cash_flow(self):
        start, end = self.period_start, self.period_end
        seq = 10
        lines = [self._section(self.env._("Operating activities"), seq)]
        seq += 1
        income = -self._sum_balance([('account_id.internal_group', '=', 'income')], start, end)
        expense = self._sum_balance([('account_id.internal_group', '=', 'expense')], start, end)
        ar_move = self._balance_at([('account_id.account_type', '=', 'asset_receivable')], end) - self._balance_at(
            [('account_id.account_type', '=', 'asset_receivable')], start - relativedelta(days=1)
        )
        ap_move = self._balance_at([('account_id.account_type', '=', 'liability_payable')], end) - self._balance_at(
            [('account_id.account_type', '=', 'liability_payable')], start - relativedelta(days=1)
        )
        operating = income - expense - ar_move + ap_move
        lines.append(self._total(self.env._("Net profit"), seq, balance=income - expense))
        seq += 1
        lines.append(self._total(self.env._("Change in receivables"), seq, balance=-ar_move))
        seq += 1
        lines.append(self._total(self.env._("Change in payables"), seq, balance=ap_move))
        seq += 1
        lines.append(self._total(self.env._("Cash from operations"), seq, balance=operating))
        seq += 1
        lines.append(self._section(self.env._("Investing activities"), seq))
        seq += 1
        investing = -(
            self._balance_at([('account_id.account_type', 'in', ('asset_fixed', 'asset_non_current'))], end)
            - self._balance_at([('account_id.account_type', 'in', ('asset_fixed', 'asset_non_current'))], start - relativedelta(days=1))
        )
        lines.append(self._total(self.env._("Net investing"), seq, balance=investing))
        seq += 1
        lines.append(self._section(self.env._("Financing activities"), seq))
        seq += 1
        financing = (
            self._balance_at([('account_id.account_type', 'in', ('liability_non_current', 'equity'))], end)
            - self._balance_at([('account_id.account_type', 'in', ('liability_non_current', 'equity'))], start - relativedelta(days=1))
        )
        lines.append(self._total(self.env._("Net financing"), seq, balance=financing))
        seq += 1
        cash_change = operating + investing + financing
        lines.append(self._total(self.env._("Net change in cash"), seq, balance=cash_change))
        seq += 1
        cash_end = self._balance_at([('account_id.account_type', '=', 'asset_cash')], end)
        cash_start = self._balance_at([('account_id.account_type', '=', 'asset_cash')], start - relativedelta(days=1))
        lines.append(self._total(self.env._("Opening cash"), seq, balance=cash_start))
        seq += 1
        lines.append(self._total(self.env._("Closing cash"), seq, balance=cash_end))
        return lines

    def _lines_executive(self):
        start, end = self.period_start, self.period_end
        prev_start, prev_end = self._previous_window()
        income = -self._sum_balance([('account_id.internal_group', '=', 'income')], start, end)
        expense = self._sum_balance([('account_id.internal_group', '=', 'expense')], start, end)
        cogs = self._sum_balance([('account_id.account_type', '=', 'expense_direct_cost')], start, end)
        income_prev = -self._sum_balance([('account_id.internal_group', '=', 'income')], prev_start, prev_end) if self.compare_previous else 0.0
        expense_prev = self._sum_balance([('account_id.internal_group', '=', 'expense')], prev_start, prev_end) if self.compare_previous else 0.0
        cogs_prev = self._sum_balance([('account_id.account_type', '=', 'expense_direct_cost')], prev_start, prev_end) if self.compare_previous else 0.0
        ar = self._balance_at([('account_id.account_type', '=', 'asset_receivable')], end)
        ap = -self._balance_at([('account_id.account_type', '=', 'liability_payable')], end)
        cash = self._balance_at([('account_id.account_type', '=', 'asset_cash')], end)
        seq = 10
        kpis = [
            (self.env._("Revenue"), income, income_prev),
            (self.env._("Cost of revenue"), cogs, cogs_prev),
            (self.env._("Gross profit"), income - cogs, income_prev - cogs_prev),
            (self.env._("Expenses"), expense, expense_prev),
            (self.env._("Net profit"), income - expense, income_prev - expense_prev),
            (self.env._("Cash"), cash, 0.0),
            (self.env._("Receivables"), ar, 0.0),
            (self.env._("Payables"), ap, 0.0),
        ]
        lines = [self._section(self.env._("Executive MIS"), seq)]
        seq += 1
        for label, amount, previous in kpis:
            lines.append(self._total(label, seq, balance=amount, previous=previous, variance=amount - previous))
            seq += 1
        return lines

    def _lines_partner_ledger(self):
        domain = self._base_domain() + [
            ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
            ('date', '>=', self.period_start),
            ('date', '<=', self.period_end),
        ]
        grouped = self.env['account.move.line'].sudo()._read_group(
            domain,
            ['partner_id', 'account_id'],
            ['debit:sum', 'credit:sum', 'balance:sum'],
        )
        seq = 10
        lines = [self._section(self.env._("Partner Ledger"), seq)]
        seq += 1
        tot_debit = tot_credit = tot_balance = 0.0
        for partner, account, debit, credit, balance in grouped:
            lines.append({
                'sequence': seq,
                'line_type': 'account',
                'name': '%s — %s' % (partner.display_name if partner else self.env._("Unknown"), account.display_name if account else ''),
                'partner_id': partner.id if partner else False,
                'account_id': account.id if account else False,
                'debit': debit or 0.0,
                'credit': credit or 0.0,
                'balance': balance or 0.0,
            })
            tot_debit += debit or 0.0
            tot_credit += credit or 0.0
            tot_balance += balance or 0.0
            seq += 1
        lines.append(self._total(self.env._("Total"), seq, debit=tot_debit, credit=tot_credit, balance=tot_balance))
        return lines

    def _aged_lines(self, account_type):
        today = self.period_end
        domain = self._base_domain() + [
            ('account_id.account_type', '=', account_type),
            ('amount_residual', '!=', 0),
            ('date', '<=', today),
        ]
        buckets = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        partner_name = {}
        for line in self.env['account.move.line'].sudo().search(domain):
            residual = line.amount_residual or 0.0
            if account_type == 'liability_payable':
                residual = -residual
            due = line.date_maturity or line.date
            days = (today - due).days if due else 0
            key = line.partner_id.id or 0
            partner_name[key] = line.partner_id.display_name if line.partner_id else self.env._("Unknown")
            data = buckets[key]
            data[5] += residual
            if days <= 0:
                data[0] += residual
            elif days <= 30:
                data[1] += residual
            elif days <= 60:
                data[2] += residual
            elif days <= 90:
                data[3] += residual
            else:
                data[4] += residual
        seq = 10
        title = self.env._("Aged Receivable") if account_type == 'asset_receivable' else self.env._("Aged Payable")
        lines = [self._section(title, seq)]
        seq += 1
        totals = [0.0] * 6
        for partner_id, amounts in sorted(buckets.items(), key=lambda item: partner_name.get(item[0], '')):
            lines.append({
                'sequence': seq,
                'line_type': 'account',
                'name': partner_name.get(partner_id, self.env._("Unknown")),
                'partner_id': partner_id or False,
                'not_due': amounts[0],
                'days_30': amounts[1],
                'days_60': amounts[2],
                'days_90': amounts[3],
                'days_older': amounts[4],
                'balance': amounts[5],
            })
            for idx in range(6):
                totals[idx] += amounts[idx]
            seq += 1
        lines.append({
            'sequence': seq,
            'line_type': 'total',
            'name': self.env._("Total"),
            'not_due': totals[0],
            'days_30': totals[1],
            'days_60': totals[2],
            'days_90': totals[3],
            'days_older': totals[4],
            'balance': totals[5],
        })
        return lines

    def _lines_aged_receivable(self):
        return self._aged_lines('asset_receivable')

    def _lines_aged_payable(self):
        return self._aged_lines('liability_payable')

    def _lines_tax(self):
        domain = self._base_domain() + [
            ('tax_line_id', '!=', False),
            ('date', '>=', self.period_start),
            ('date', '<=', self.period_end),
        ]
        grouped = self.env['account.move.line'].sudo()._read_group(
            domain,
            ['tax_line_id'],
            ['debit:sum', 'credit:sum', 'balance:sum'],
        )
        seq = 10
        lines = [self._section(self.env._("Tax Summary"), seq)]
        seq += 1
        tot_debit = tot_credit = tot_balance = 0.0
        for tax, debit, credit, balance in grouped:
            lines.append({
                'sequence': seq,
                'line_type': 'account',
                'name': tax.display_name if tax else self.env._("Tax"),
                'debit': debit or 0.0,
                'credit': credit or 0.0,
                'balance': balance or 0.0,
            })
            tot_debit += debit or 0.0
            tot_credit += credit or 0.0
            tot_balance += balance or 0.0
            seq += 1
        lines.append(self._total(self.env._("Total"), seq, debit=tot_debit, credit=tot_credit, balance=tot_balance))
        return lines


class SygMisReportLine(models.TransientModel):
    _name = 'syg.mis.report.line'
    _description = 'MIS Report Line'
    _order = 'sequence, id'

    report_id = fields.Many2one('syg.mis.report', required=True, ondelete='cascade')
    sequence = fields.Integer()
    line_type = fields.Selection(
        [('section', 'Section'), ('account', 'Line'), ('total', 'Total')],
        default='account',
        required=True,
    )
    name = fields.Char(required=True)
    code = fields.Char()
    account_id = fields.Many2one('account.account')
    partner_id = fields.Many2one('res.partner')
    debit = fields.Monetary(currency_field='currency_id')
    credit = fields.Monetary(currency_field='currency_id')
    balance = fields.Monetary(currency_field='currency_id')
    previous = fields.Monetary(currency_field='currency_id')
    variance = fields.Monetary(currency_field='currency_id')
    not_due = fields.Monetary(currency_field='currency_id')
    days_30 = fields.Monetary(currency_field='currency_id')
    days_60 = fields.Monetary(currency_field='currency_id')
    days_90 = fields.Monetary(currency_field='currency_id')
    days_older = fields.Monetary(currency_field='currency_id')
    percent = fields.Float()
    level = fields.Integer()
    currency_id = fields.Many2one(related='report_id.currency_id')
