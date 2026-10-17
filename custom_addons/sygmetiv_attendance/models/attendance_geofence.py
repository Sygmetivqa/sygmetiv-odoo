# -*- coding: utf-8 -*-

import math

from odoo import api, fields, models
from odoo.exceptions import ValidationError


def distance_meters(lat1, lon1, lat2, lon2):
    """Great-circle distance in meters between two WGS84 points."""
    earth_radius = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    chord = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    )
    return 2 * earth_radius * math.atan2(math.sqrt(chord), math.sqrt(max(0.0, 1.0 - chord)))


def coordinates_present(latitude, longitude):
    """Odoo stores a missing GPS fix as 0,0. Treat that as no coordinates."""
    return not (abs(latitude or 0.0) < 1e-7 and abs(longitude or 0.0) < 1e-7)


class SygAttendanceGeofence(models.Model):
    _name = 'syg.attendance.geofence'
    _description = 'Attendance Location'
    _order = 'name, id'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    latitude = fields.Float(required=True, digits=(10, 7))
    longitude = fields.Float(required=True, digits=(10, 7))
    radius = fields.Integer(
        string="Radius (m)",
        required=True,
        default=150,
        help="Check-in and check-out inside this distance, in meters, match the location.",
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        'syg_employee_attendance_geofence_rel',
        'geofence_id',
        'employee_id',
        string="Employees",
    )

    @api.constrains('latitude', 'longitude', 'radius')
    def _check_geofence_area(self):
        for rec in self:
            if not -90.0 <= rec.latitude <= 90.0 or not -180.0 <= rec.longitude <= 180.0:
                raise ValidationError(self.env._(
                    "Latitude must be between -90 and 90, and longitude between -180 and 180."
                ))
            if rec.radius <= 0:
                raise ValidationError(self.env._("The geofence radius must be greater than zero."))

    def contains(self, latitude, longitude):
        self.ensure_one()
        return distance_meters(latitude, longitude, self.latitude, self.longitude) <= self.radius
