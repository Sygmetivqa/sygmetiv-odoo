# -*- coding: utf-8 -*-

from odoo import fields, models


class SygRoleType(models.Model):
    _name = 'syg.role.type'
    _description = 'Role Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    requires_presentation = fields.Boolean(
        string="Presenter",
        help="Presentation time is shown for this role. It stays optional. Leave this off for a normal attendee.",
    )
    description = fields.Text()
