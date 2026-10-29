# -*- coding: utf-8 -*-
{
    'name': 'Sygmetiv Web',
    'version': '19.0.1.2.0',
    'category': 'Hidden',
    'summary': 'Enterprise-style app home menu for Odoo Community',
    'description': """
Replaces the Community apps dropdown with a full-screen app launcher
similar to Odoo Enterprise: large icons, search, and a 9-dot home button.
    """,
    'author': 'Sygmetiv Business Solutions',
    'website': 'https://sygmetiv.qa',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [
        'views/report_templates.xml',
    ],
    'installable': True,
    'auto_install': ['web'],
    'pre_init_hook': 'pre_init_hook',
    'assets': {
        'web._assets_primary_variables': [
            ('before', 'web/static/src/scss/primary_variables.scss', 'sygmetiv_web/static/src/scss/primary_variables.scss'),
            ('after', 'web/static/src/scss/primary_variables.scss', 'sygmetiv_web/static/src/scss/navbar.variables.scss'),
        ],
        'web._assets_backend_helpers': [
            ('before', 'web/static/src/scss/bootstrap_overridden.scss', 'sygmetiv_web/static/src/scss/bootstrap_overridden.scss'),
        ],
        'web.assets_backend': [
            'sygmetiv_web/static/src/webclient/**/*.scss',
            'sygmetiv_web/static/src/webclient/**/*.js',
            'sygmetiv_web/static/src/webclient/**/*.xml',
        ],
        'web.assets_web': [
            (
                'replace',
                'web/static/src/main.js',
                'sygmetiv_web/static/src/main.js',
            ),
        ],
    },
}
