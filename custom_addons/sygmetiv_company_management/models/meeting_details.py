# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SygMeetingDetailsMixin(models.AbstractModel):
    _name = 'syg.meeting.details.mixin'
    _description = 'Meeting details for demo, training and meeting tasks'

    syg_task_type_id = fields.Many2one(
        'syg.task.type',
        string="Task Type",
        index=True,
        tracking=True,
    )
    syg_is_meeting = fields.Boolean(compute='_compute_syg_is_meeting')
    syg_role = fields.Char(
        string="Role in the Task",
        help="Role of the employee in this demo, training or meeting.",
    )
    syg_presentation_time = fields.Float(
        string="Presentation Time",
        help="How long the presentation lasts. This is separate from the description.",
    )

    @api.depends('syg_task_type_id.is_meeting')
    def _compute_syg_is_meeting(self):
        for rec in self:
            rec.syg_is_meeting = bool(rec.syg_task_type_id.is_meeting)

    def _check_syg_meeting_values(self):
        for rec in self:
            if not rec.syg_is_meeting:
                continue
            if not rec.syg_attendee_ids or not (rec.syg_role or '').strip() or not rec.syg_presentation_time:
                raise ValidationError(self.env._(
                    "Demo, training and meeting tasks need attendees, a role in the task, and a presentation time."
                ))
