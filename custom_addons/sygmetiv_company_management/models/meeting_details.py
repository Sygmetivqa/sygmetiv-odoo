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
    syg_role_type_id = fields.Many2one(
        'syg.role.type',
        string="Role Type",
        help="Role of the employee in this demo, training or meeting.",
        tracking=True,
    )
    syg_role_requires_presentation = fields.Boolean(
        related='syg_role_type_id.requires_presentation',
    )
    syg_presentation_time = fields.Float(
        string="Presentation Time",
        help="Optional length of the presentation. Only presenter roles use this.",
    )

    @api.depends('syg_task_type_id.is_meeting')
    def _compute_syg_is_meeting(self):
        for rec in self:
            rec.syg_is_meeting = bool(rec.syg_task_type_id.is_meeting)

    @api.onchange('syg_role_type_id')
    def _onchange_syg_role_type_id(self):
        if not self.syg_role_type_id.requires_presentation:
            self.syg_presentation_time = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._clear_unused_presentation_time()
        return records

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('syg_skip_presentation_cleanup') and (
            'syg_role_type_id' in vals or 'syg_presentation_time' in vals
        ):
            self._clear_unused_presentation_time()
        return res

    def _clear_unused_presentation_time(self):
        to_clear = self.filtered(
            lambda rec: rec.syg_presentation_time and not rec.syg_role_type_id.requires_presentation
        )
        if to_clear:
            to_clear.with_context(syg_skip_presentation_cleanup=True).write({
                'syg_presentation_time': 0.0,
            })

    def _check_syg_meeting_values(self):
        for rec in self:
            if not rec.syg_is_meeting:
                continue
            if not rec.syg_attendee_ids or not rec.syg_role_type_id:
                raise ValidationError(self.env._(
                    "Demo, training and meeting tasks need attendees and a role type."
                ))
