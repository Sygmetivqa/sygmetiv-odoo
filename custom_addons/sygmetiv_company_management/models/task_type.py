# -*- coding: utf-8 -*-

from odoo import fields, models


class SygTaskType(models.Model):
    _name = 'syg.task.type'
    _description = 'Task Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer()
    active = fields.Boolean(default=True)
    is_meeting = fields.Boolean(
        string="Meeting related",
        help="Demo, training and meeting types require attendees and a role type. Presentation time is optional and only for presenter roles.",
    )
    description = fields.Text()
