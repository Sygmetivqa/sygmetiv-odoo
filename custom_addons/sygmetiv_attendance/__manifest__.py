# -*- coding: utf-8 -*-
{
    'name': 'Sygmetiv Attendance',
    'version': '19.0.1.1.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Match attendance check-in and check-out to each employee location',
    'description': """
Geofencing for attendance
=========================

* Each employee is assigned one or more attendance locations
* Check-in and check-out GPS coordinates are compared with those locations
* The nearest location, the distance and whether the employee was inside are stored on the attendance
* Optionally block systray and kiosk check-in or check-out when the employee is outside

Device and location tracking in Attendances settings must be enabled so Odoo collects GPS coordinates.
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
            'sygmetiv_attendance/static/src/js/many2many_link_field.js',
            'sygmetiv_attendance/static/src/xml/many2many_link_field.xml',
        ],
    },
}
