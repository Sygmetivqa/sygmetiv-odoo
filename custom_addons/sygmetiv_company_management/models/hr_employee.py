# -*- coding: utf-8 -*-

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Work fields such as department and job are stored on hr.version and
    # reached through version_id. That delegate is HR-officer only in standard
    # Odoo, so an Employee user cannot open their own profile until it is widened.
    version_id = fields.Many2one(
        groups="hr.group_hr_user,sygmetiv_company_management.group_company_user",
    )
    # The employee kanban and presence icon read the current time off.
    # Those fields are HR-officer only in standard Odoo, so an Employee
    # user cannot open Employees until they are widened.
    current_leave_id = fields.Many2one(
        groups="hr.group_hr_user,sygmetiv_company_management.group_company_user",
    )
    current_leave_state = fields.Selection(
        groups="hr.group_hr_user,sygmetiv_company_management.group_company_user",
    )
    leave_date_from = fields.Date(
        groups="hr.group_hr_user,sygmetiv_company_management.group_company_user",
    )

    syg_allowance_monthly = fields.Monetary(
        string="Monthly Allowance",
        currency_field='currency_id',
        groups="hr.group_hr_manager",
        help="Fixed monthly allowance added on payslips.",
    )
    syg_deduction_monthly = fields.Monetary(
        string="Monthly Deduction",
        currency_field='currency_id',
        groups="hr.group_hr_manager",
        help="Fixed monthly deduction subtracted on payslips.",
    )
    syg_overtime_ids = fields.One2many(
        'syg.overtime.request',
        'employee_id',
        string="Overtime Requests",
    )
    syg_payslip_ids = fields.One2many(
        'syg.payslip',
        'employee_id',
        string="Payslips",
    )
    syg_review_ids = fields.One2many(
        'syg.performance.review',
        'employee_id',
        string="Performance Reviews",
    )
    syg_goal_ids = fields.One2many(
        'syg.performance.goal',
        'employee_id',
        string="Performance Goals",
    )
    syg_overtime_count = fields.Integer(compute='_compute_syg_hr_counts')
    syg_payslip_count = fields.Integer(compute='_compute_syg_hr_counts')
    syg_review_count = fields.Integer(compute='_compute_syg_hr_counts')

    def _compute_syg_hr_counts(self):
        overtime = self.env['syg.overtime.request']._read_group(
            [('employee_id', 'in', self.ids)],
            ['employee_id'],
            ['__count'],
        )
        payslips = self.env['syg.payslip']._read_group(
            [('employee_id', 'in', self.ids)],
            ['employee_id'],
            ['__count'],
        )
        reviews = self.env['syg.performance.review']._read_group(
            [('employee_id', 'in', self.ids)],
            ['employee_id'],
            ['__count'],
        )
        overtime_map = {emp.id: count for emp, count in overtime}
        payslip_map = {emp.id: count for emp, count in payslips}
        review_map = {emp.id: count for emp, count in reviews}
        for employee in self:
            employee.syg_overtime_count = overtime_map.get(employee.id, 0)
            employee.syg_payslip_count = payslip_map.get(employee.id, 0)
            employee.syg_review_count = review_map.get(employee.id, 0)

    def action_open_syg_overtime(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Overtime"),
            'res_model': 'syg.overtime.request',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_open_syg_payslips(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Payslips"),
            'res_model': 'syg.payslip',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_open_syg_reviews(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Performance"),
            'res_model': 'syg.performance.review',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
