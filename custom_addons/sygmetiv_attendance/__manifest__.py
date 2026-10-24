# -*- coding: utf-8 -*-
{
    'name': 'Sygmetiv Attendance',
    'version': '19.0.1.5.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Match attendance check-in and check-out to each employee location',
    'description': """
Geofencing for attendance
=========================

* Each employee is assigned one or more attendance locations
* Check-in and check-out GPS coordinates are compared with those locations
* The nearest location, the distance and whether the employee was inside are stored on the attendance
* Optionally block systray and kiosk check-in or check-out when the employee is outside
* Kiosk check-in, including badge scan, stores the browser GPS position
* A missing fix is shown as No GPS. Coordinates 0,0 are not treated as a place

Device and location tracking in Attendances settings must be enabled, and the browser must allow location access.
    """,
    'author': 'Sygmetiv Business Solutions',
    'website': 'https://sygmetiv.qa',
    'license': 'LGPL-3',
    'depends': [
        'hr',
        'hr_attendance',
    ],
    'data': [
        'security/attendance_security.xml',
        'security/ir.model.access.csv',
        'views/attendance_geofence_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_attendance_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'assets': {
        'web.assets_backend': [
            'sygmetiv_attendance/static/src/js/device_coordinates.js',
            'sygmetiv_attendance/static/src/js/systray_geolocation.js',
            'sygmetiv_attendance/static/src/js/many2many_link_field.js',
            'sygmetiv_attendance/static/src/xml/many2many_link_field.xml',
        ],
        'hr_attendance.assets_public_attendance': [
            'sygmetiv_attendance/static/src/js/device_coordinates.js',
            'sygmetiv_attendance/static/src/js/kiosk_geolocation.js',
        ],
    },
}
