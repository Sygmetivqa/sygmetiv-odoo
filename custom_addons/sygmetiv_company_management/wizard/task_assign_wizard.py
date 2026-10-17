# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.exceptions import AccessError, UserError
from odoo.fields import Command


class SygTaskAssignWizard(models.TransientModel):
    _name = 'syg.task.assign.wizard'
    _description = 'Assign Task'

    project_id = fields.Many2one('project.project', required=True)
    name = fields.Char(string="Task Title", required=True)
    user_ids = fields.Many2many('res.users', string="Assignees", required=True, domain="[('share', '=', False)]")
    date_deadline = fields.Datetime(string="Deadline")
    allocated_hours = fields.Float()
    description = fields.Html()

    def action_assign(self):
        self.ensure_one()
        if not self.env.user.has_group('sygmetiv_company_management.group_company_manager'):
            raise AccessError(self.env._("You do not have access to assign tasks."))
        if not self.project_id:
            raise UserError(self.env._("Select a project."))
        task = self.env['project.task'].create({
            'name': self.name,
            'project_id': self.project_id.id,
            'user_ids': [Command.set(self.user_ids.ids)],
            'date_deadline': self.date_deadline,
            'allocated_hours': self.allocated_hours,
            'description': self.description,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'res_id': task.id,
            'view_mode': 'form',
        }
