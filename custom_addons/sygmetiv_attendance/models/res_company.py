# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    syg_attendance_geofence_policy = fields.Selection(
        [
            ('record', 'Record the match'),
            ('block', 'Block check-in and check-out outside the location'),
        ],
        string="Attendance Geofence",
        default='record',
        required=True,
        help="Record stores whether the GPS position was inside an employee location. "
             "Block refuses systray and kiosk attendance when the position is missing or outside. "
             "Manual attendance entered by an officer is still allowed.",
    )
