# -*- coding: utf-8 -*-

from odoo import models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _syg_is_company_wide(self):
        self.ensure_one()
        return self.has_group('sygmetiv_company_management.group_company_manager')

    def _syg_employee_domain(self):
        """Employees this user is allowed to see in Sygmetiv."""
        self.ensure_one()
        if self._syg_is_company_wide():
            return [('company_id', 'in', self.company_ids.ids)]
        employee = self.employee_id
        if employee:
            return [('id', '=', employee.id)]
        return [('id', '=', False)]
