# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError


class SygPayslipGenerateWizard(models.TransientModel):
    _name = 'syg.payslip.generate.wizard'
    _description = 'Generate Payslips'

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    employee_ids = fields.Many2many('hr.employee', string="Employees")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        today = fields.Date.context_today(self)
        defaults.setdefault('date_from', today.replace(day=1))
        defaults.setdefault('date_to', today + relativedelta(day=31))
        return defaults

    def action_generate(self):
        self.ensure_one()
        if not self.env.user.has_group('sygmetiv_company_management.group_company_manager'):
            raise AccessError(self.env._("You do not have access to generate payslips."))
        employees = self.employee_ids or self.env['hr.employee'].search([
            ('company_id', '=', self.company_id.id),
            ('active', '=', True),
        ])
        slips = self.env['syg.payslip']
        for employee in employees:
            existing = slips.search([
                ('employee_id', '=', employee.id),
                ('date_from', '=', self.date_from),
                ('date_to', '=', self.date_to),
                ('state', '!=', 'cancel'),
            ], limit=1)
            if existing:
                existing.action_compute_sheet()
                slips |= existing
                continue
            slip = slips.create({
                'employee_id': employee.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
            })
            slip.action_compute_sheet()
            slips |= slip
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Payslips"),
            'res_model': 'syg.payslip',
            'view_mode': 'list,form',
            'domain': [('id', 'in', slips.ids)],
        }
