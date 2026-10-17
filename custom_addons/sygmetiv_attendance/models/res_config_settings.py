# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    syg_attendance_geofence_policy = fields.Selection(
        related='company_id.syg_attendance_geofence_policy',
        readonly=False,
    )
