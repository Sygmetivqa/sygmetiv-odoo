# -*- coding: utf-8 -*-

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    syg_geofence_ids = fields.Many2many(
        'syg.attendance.geofence',
        'syg_employee_attendance_geofence_rel',
        'employee_id',
        'geofence_id',
        string="Attendance Locations",
        domain="[('company_id', 'in', [False, company_id])]",
        help="Check-in and check-out GPS coordinates are compared with these locations.",
    )
