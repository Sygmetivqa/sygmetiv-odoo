# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class SygPayslip(models.Model):
    _name = 'syg.payslip'
    _description = 'Payslip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_to desc, id desc'

    name = fields.Char(required=True, copy=False, default='New', tracking=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True, index=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    company_id = fields.Many2one(
        'res.company',
        related='employee_id.company_id',
        store=True,
        index=True,
    )
    currency_id = fields.Many2one(related='company_id.currency_id')
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('computed', 'Computed'),
            ('done', 'Done'),
            ('cancel', 'Cancelled'),
        ],
        default='draft',
        tracking=True,
        copy=False,
        index=True,
    )
    wage = fields.Monetary(string="Basic Wage", currency_field='currency_id')
    timesheet_hours = fields.Float(readonly=True)
    overtime_hours = fields.Float(readonly=True)
    overtime_amount = fields.Monetary(currency_field='currency_id')
    allowance_amount = fields.Monetary(currency_field='currency_id')
    deduction_amount = fields.Monetary(currency_field='currency_id')
    net_amount = fields.Monetary(compute='_compute_net_amount', store=True, currency_field='currency_id')
    line_ids = fields.One2many('syg.payslip.line', 'payslip_id', string="Lines")
    move_id = fields.Many2one('account.move', string="Journal Entry", copy=False, readonly=True)
    note = fields.Text()

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        today = fields.Date.context_today(self)
        defaults.setdefault('date_from', today.replace(day=1))
        defaults.setdefault('date_to', today + relativedelta(day=31))
        return defaults

    @api.depends('wage', 'overtime_amount', 'allowance_amount', 'deduction_amount')
    def _compute_net_amount(self):
        for slip in self:
            slip.net_amount = (
                slip.wage + slip.overtime_amount + slip.allowance_amount - slip.deduction_amount
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('syg.payslip') or 'New'
        return super().create(vals_list)

    def action_compute_sheet(self):
        for slip in self:
            employee = slip.employee_id.sudo()
            company = slip.company_id
            monthly_hours = company.syg_monthly_hours or 176.0
            multiplier = company.syg_overtime_multiplier or 1.5
            wage = employee.wage or 0.0
            timesheet_hours = sum(self.env['account.analytic.line'].sudo().search([
                ('employee_id', '=', employee.id),
                ('date', '>=', slip.date_from),
                ('date', '<=', slip.date_to),
                ('project_id', '!=', False),
            ]).mapped('unit_amount'))
            overtime_hours = sum(self.env['syg.overtime.request'].search([
                ('employee_id', '=', employee.id),
                ('date', '>=', slip.date_from),
                ('date', '<=', slip.date_to),
                ('state', '=', 'approved'),
            ]).mapped('hours'))
            hourly = wage / monthly_hours if monthly_hours else 0.0
            overtime_amount = overtime_hours * hourly * multiplier
            allowance = employee.syg_allowance_monthly or 0.0
            deduction = employee.syg_deduction_monthly or 0.0
            slip.write({
                'wage': wage,
                'timesheet_hours': timesheet_hours,
                'overtime_hours': overtime_hours,
                'overtime_amount': overtime_amount,
                'allowance_amount': allowance,
                'deduction_amount': deduction,
                'state': 'computed',
                'line_ids': [Command.clear()] + [
                    Command.create({'name': self.env._("Basic wage"), 'code': 'BASIC', 'amount': wage}),
                    Command.create({'name': self.env._("Overtime"), 'code': 'OT', 'amount': overtime_amount}),
                    Command.create({'name': self.env._("Allowance"), 'code': 'ALW', 'amount': allowance}),
                    Command.create({'name': self.env._("Deduction"), 'code': 'DED', 'amount': -deduction}),
                    Command.create({
                        'name': self.env._("Net"),
                        'code': 'NET',
                        'amount': wage + overtime_amount + allowance - deduction,
                    }),
                ],
            })
        return True

    def action_done(self):
        for slip in self:
            if slip.state not in ('computed', 'draft'):
                raise UserError(self.env._("Only draft or computed payslips can be posted."))
            if slip.state == 'draft':
                slip.action_compute_sheet()
            slip._create_account_move()
            slip.state = 'done'
            slip.message_post(body=self.env._("Payslip confirmed."))
        return True

    def _create_account_move(self):
        self.ensure_one()
        if self.move_id:
            return self.move_id
        if not self.net_amount:
            return self.env['account.move']
        company = self.company_id
        journal = company.syg_payroll_journal_id
        expense = company.syg_payroll_expense_account_id
        payable = company.syg_payroll_payable_account_id
        if not (journal and expense and payable):
            return self.env['account.move']
        move = self.env['account.move'].sudo().create({
            'move_type': 'entry',
            'date': self.date_to,
            'journal_id': journal.id,
            'ref': self.name,
            'company_id': company.id,
            'line_ids': [
                Command.create({
                    'name': self.env._("Salary expense %s", self.employee_id.name),
                    'account_id': expense.id,
                    'debit': self.net_amount,
                    'credit': 0.0,
                    'partner_id': self.employee_id.work_contact_id.id,
                }),
                Command.create({
                    'name': self.env._("Salary payable %s", self.employee_id.name),
                    'account_id': payable.id,
                    'debit': 0.0,
                    'credit': self.net_amount,
                    'partner_id': self.employee_id.work_contact_id.id,
                }),
            ],
        })
        move.action_post()
        self.move_id = move
        return move

    def action_cancel(self):
        for slip in self:
            if slip.move_id and slip.move_id.state == 'posted':
                slip.move_id.button_draft()
                slip.move_id.button_cancel()
            slip.state = 'cancel'
        return True

    def action_draft(self):
        self.filtered(lambda s: s.state == 'cancel').write({'state': 'draft', 'move_id': False})
        return True

    def action_open_move(self):
        self.ensure_one()
        if not self.move_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
        }


class SygPayslipLine(models.Model):
    _name = 'syg.payslip.line'
    _description = 'Payslip Line'
    _order = 'id'

    payslip_id = fields.Many2one('syg.payslip', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    code = fields.Char()
    amount = fields.Monetary()
    currency_id = fields.Many2one(related='payslip_id.currency_id')
    company_id = fields.Many2one(related='payslip_id.company_id', store=True)
