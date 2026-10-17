# -*- coding: utf-8 -*-
{
    'name': 'Sygmetiv HR',
    'version': '19.0.1.2.0',
    'category': 'Human Resources',
    'summary': 'Company announcements with email and web notify',
    'description': """
Publish company announcements to employees and managers.

* Draft, publish and archive
* Audience: everyone, employees, or managers only
* Optional start and end dates, pin important notes
* Email and web_notify on publish
    """,
    'author': 'Sygmetiv Business Solutions',
    'website': 'https://sygmetiv.qa',
    'license': 'LGPL-3',
    'depends': [
        'mail',
        'web_notify',
    ],
    'data': [
        'security/announcement_security.xml',
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'views/announcement_views.xml',
    ],
    'installable': True,
    'application': True,
    'pre_init_hook': 'pre_init_hook',
}
