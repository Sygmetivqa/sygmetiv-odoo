# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo.tests import tagged, TransactionCase

from odoo.addons.sygmetiv_attendance.models.attendance_geofence import distance_meters


@tagged('post_install', '-at_install')
class TestAttendanceGeofence(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({'name': 'Geofence Employee'})
        cls.office = cls.env['syg.attendance.geofence'].create({
            'name': 'Doha Office',
            'latitude': 25.285447,
            'longitude': 51.531040,
            'radius': 200,
            'employee_ids': [(4, cls.employee.id)],
        })

    def test_distance_is_short_inside_the_radius(self):
        distance = distance_meters(25.285447, 51.531040, 25.286000, 51.531040)
        self.assertLess(distance, 200)
        self.assertGreater(distance, 50)

    def test_zero_coordinates_are_not_a_gps_fix(self):
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'in_mode': 'kiosk',
            'in_latitude': 0.0,
            'in_longitude': 0.0,
        })
        self.assertFalse(attendance.syg_in_has_gps)
        self.assertEqual(attendance.syg_in_geofence_state, 'missing')
        with self.assertRaises(UserError):
            attendance.action_in_attendance_maps()

    def test_maps_link_uses_the_recorded_fix(self):
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'in_mode': 'kiosk',
            'in_latitude': 25.286000,
            'in_longitude': 51.531040,
        })
        self.assertTrue(attendance.syg_in_has_gps)
        action = attendance.action_in_attendance_maps()
        self.assertIn('maps.google.com', action['url'])
        self.assertIn('25.28', action['url'])
        self.assertIn('51.53', action['url'])

    def test_check_in_inside_location(self):
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'in_mode': 'systray',
            'in_latitude': 25.286000,
            'in_longitude': 51.531040,
        })
        self.assertEqual(attendance.syg_in_geofence_state, 'inside')
        self.assertEqual(attendance.syg_in_geofence_id, self.office)
        self.assertLess(attendance.syg_in_distance, 200)

    def test_check_in_outside_is_recorded(self):
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'in_mode': 'systray',
            'in_latitude': 25.320000,
            'in_longitude': 51.531040,
        })
        self.assertEqual(attendance.syg_in_geofence_state, 'outside')
        self.assertEqual(attendance.syg_in_geofence_id, self.office)
        self.assertGreater(attendance.syg_in_distance, 200)

    def test_block_policy_refuses_outside_systray(self):
        self.env.company.syg_attendance_geofence_policy = 'block'
        with self.assertRaises(UserError):
            self.env['hr.attendance'].create({
                'employee_id': self.employee.id,
                'in_mode': 'systray',
                'in_latitude': 25.320000,
                'in_longitude': 51.531040,
            })

    def test_manual_attendance_outside_is_not_blocked(self):
        self.env.company.syg_attendance_geofence_policy = 'block'
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'in_mode': 'manual',
            'in_latitude': 25.320000,
            'in_longitude': 51.531040,
        })
        self.assertEqual(attendance.syg_in_geofence_state, 'outside')

    def test_employee_without_location_is_unassigned(self):
        other = self.env['hr.employee'].create({'name': 'No Location'})
        attendance = self.env['hr.attendance'].create({
            'employee_id': other.id,
            'in_mode': 'systray',
            'in_latitude': 25.286000,
            'in_longitude': 51.531040,
        })
        self.assertEqual(attendance.syg_in_geofence_state, 'unassigned')
