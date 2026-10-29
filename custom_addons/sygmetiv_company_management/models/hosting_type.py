# -*- coding: utf-8 -*-

from odoo import fields, models


class SygHostingType(models.Model):
    _name = 'syg.hosting.type'
    _description = 'Hosting Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text()
