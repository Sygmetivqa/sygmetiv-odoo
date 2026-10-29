# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = ['project.task', 'syg.meeting.details.mixin']

    syg_attendee_ids = fields.Many2many(
        'hr.employee',
        'project_task_syg_attendee_rel',
        'task_id',
        'employee_id',
        string="Attendees",
    )
    syg_vendor_id = fields.Many2one(
        'res.partner',
        string="Vendor",
        domain="[('supplier_rank', '>', 0)]",
        index=True,
        tracking=True,
    )
    syg_task_request_id = fields.Many2one(
        'syg.task.request',
        string="Task Request",
        readonly=True,
        copy=False,
        index=True,
    )
    syg_task_request_name = fields.Char(related='syg_task_request_id.display_name', string="Task Request")

    @api.constrains('syg_task_type_id', 'syg_attendee_ids', 'syg_role_type_id')
    def _check_syg_meeting_details(self):
        self._check_syg_meeting_values()

    def action_open_subtasks(self):
        """Open sub-tasks for task forms that still call this button.

        The installed project form uses an object button named
        action_open_subtasks. Current Odoo opens the same list with a window
        action, so the method is no longer on project.task and view validation
        fails while upgrading this module.
        """
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'project.project_task_action_sub_task'
        )
        action['domain'] = [('id', 'child_of', self.id), ('id', '!=', self.id)]
        action['context'] = {
            **self.env.context,
            'show_project_update': False,
            'default_parent_id': self.id,
        }
        return action

    def action_open_task_request(self):
        self.ensure_one()
        if not self.syg_task_request_id:
            return True
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Task Request"),
            'res_model': 'syg.task.request',
            'res_id': self.syg_task_request_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
