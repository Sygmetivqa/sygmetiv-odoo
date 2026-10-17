# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    syg_overtime_multiplier = fields.Float(
        string="Overtime Multiplier",
        default=1.5,
        help="Hourly overtime pay = (monthly wage / monthly hours) × this multiplier.",
    )
    syg_monthly_hours = fields.Float(
        string="Standard Monthly Hours",
        default=176.0,
        help="Used to convert monthly wage into an hourly rate for overtime and payroll.",
    )
    syg_payroll_journal_id = fields.Many2one(
        'account.journal',
        string="Payroll Journal",
        domain="[('type', '=', 'general'), ('company_id', '=', id)]",
    )
    syg_payroll_expense_account_id = fields.Many2one(
        'account.account',
        string="Salary Expense Account",
        domain="[('account_type', 'in', ('expense', 'expense_other')), ('company_ids', 'in', id)]",
    )
    syg_payroll_payable_account_id = fields.Many2one(
        'account.account',
        string="Salary Payable Account",
        domain="[('account_type', '=', 'liability_payable'), ('company_ids', 'in', id)]",
    )
