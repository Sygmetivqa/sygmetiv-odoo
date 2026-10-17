# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    syg_overtime_multiplier = fields.Float(
        related='company_id.syg_overtime_multiplier',
        readonly=False,
    )
    syg_monthly_hours = fields.Float(
        related='company_id.syg_monthly_hours',
        readonly=False,
    )
    syg_payroll_journal_id = fields.Many2one(
        related='company_id.syg_payroll_journal_id',
        readonly=False,
    )
    syg_payroll_expense_account_id = fields.Many2one(
        related='company_id.syg_payroll_expense_account_id',
        readonly=False,
    )
    syg_payroll_payable_account_id = fields.Many2one(
        related='company_id.syg_payroll_payable_account_id',
        readonly=False,
    )
