# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError

from .attendance_geofence import coordinates_present, distance_meters

GPS_MODES = ('systray', 'kiosk')
GEOFENCE_SELECTION = [
    ('inside', 'Inside'),
    ('outside', 'Outside'),
    ('missing', 'No GPS'),
    ('unassigned', 'No location'),
    ('skipped', 'Not checked'),
]


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    syg_in_geofence_id = fields.Many2one(
        'syg.attendance.geofence',
        string="Check-in Location",
        readonly=True,
        copy=False,
    )
    syg_out_geofence_id = fields.Many2one(
        'syg.attendance.geofence',
        string="Check-out Location",
        readonly=True,
        copy=False,
    )
    syg_in_distance = fields.Float(
        string="Check-in Distance (m)",
        readonly=True,
        copy=False,
        digits=(16, 1),
    )
    syg_out_distance = fields.Float(
        string="Check-out Distance (m)",
        readonly=True,
        copy=False,
        digits=(16, 1),
    )
    syg_in_geofence_state = fields.Selection(
        GEOFENCE_SELECTION,
        string="Check-in Geofence",
        readonly=True,
        copy=False,
        index=True,
    )
    syg_out_geofence_state = fields.Selection(
        GEOFENCE_SELECTION,
        string="Check-out Geofence",
        readonly=True,
        copy=False,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get('syg_skip_geofence'):
            records._syg_match_geofence()
        return records

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('syg_skip_geofence'):
            return res
        watched = {
            'employee_id', 'check_out',
            'in_latitude', 'in_longitude', 'in_mode',
            'out_latitude', 'out_longitude', 'out_mode',
        }
        if watched & set(vals):
            self._syg_match_geofence()
        return res

    def _syg_match_geofence(self):
        fields_to_refresh = [
            'syg_in_geofence_state', 'syg_in_geofence_id', 'syg_in_distance',
            'syg_out_geofence_state', 'syg_out_geofence_id', 'syg_out_distance',
        ]
        for attendance in self:
            check_in = attendance._syg_geofence_side('in')
            check_out = attendance._syg_geofence_side('out')
            attendance.sudo().with_context(syg_skip_geofence=True).write({
                'syg_in_geofence_state': check_in['state'],
                'syg_in_geofence_id': check_in['geofence_id'],
                'syg_in_distance': check_in['distance'],
                'syg_out_geofence_state': check_out['state'],
                'syg_out_geofence_id': check_out['geofence_id'],
                'syg_out_distance': check_out['distance'],
            })
            attendance.invalidate_recordset(fields_to_refresh)
            attendance._syg_enforce_geofence(check_in, check_out)

    def _syg_geofence_side(self, side):
        self.ensure_one()
        if side == 'out' and not self.check_out:
            return {'state': False, 'geofence_id': False, 'distance': 0.0}
        latitude = self.in_latitude if side == 'in' else self.out_latitude
        longitude = self.in_longitude if side == 'in' else self.out_longitude
        mode = self.in_mode if side == 'in' else self.out_mode
        fences = self.employee_id.syg_geofence_ids.filtered('active')
        if not fences:
            return {'state': 'unassigned', 'geofence_id': False, 'distance': 0.0}
        if not coordinates_present(latitude, longitude):
            state = 'missing' if mode in GPS_MODES else 'skipped'
            return {'state': state, 'geofence_id': False, 'distance': 0.0}
        closest = fences[0]
        closest_distance = distance_meters(
            latitude, longitude, closest.latitude, closest.longitude,
        )
        for fence in fences:
            dist = distance_meters(latitude, longitude, fence.latitude, fence.longitude)
            if dist < closest_distance:
                closest = fence
                closest_distance = dist
        return {
            'state': 'inside' if closest_distance <= closest.radius else 'outside',
            'geofence_id': closest.id,
            'distance': closest_distance,
        }

    def _syg_enforce_geofence(self, check_in, check_out):
        self.ensure_one()
        company = self.employee_id.company_id or self.env.company
        if company.syg_attendance_geofence_policy != 'block':
            return
        if not self.employee_id.syg_geofence_ids:
            return
        self._syg_raise_if_blocked('in', check_in)
        if self.check_out:
            self._syg_raise_if_blocked('out', check_out)

    def _syg_raise_if_blocked(self, side, result):
        self.ensure_one()
        mode = self.in_mode if side == 'in' else self.out_mode
        if mode not in GPS_MODES:
            return
        state = result['state']
        action = self.env._("check in") if side == 'in' else self.env._("check out")
        employee = self.employee_id.name
        if state == 'missing':
            raise UserError(self.env._(
                "%(employee)s cannot %(action)s without a GPS position. "
                "The employee must be inside an assigned attendance location.",
                employee=employee,
                action=action,
            ))
        if state != 'outside':
            return
        location = self.env['syg.attendance.geofence'].browse(result['geofence_id'])
        raise UserError(self.env._(
            "%(employee)s cannot %(action)s. The position is %(distance)s m from %(location)s, "
            "outside the %(radius)s m geofence.",
            employee=employee,
            action=action,
            distance=int(round(result['distance'] or 0.0)),
            location=location.display_name,
            radius=location.radius,
        ))
