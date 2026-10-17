# -*- coding: utf-8 -*-
{
    'name': 'Sygmetiv Accounting',
    'version': '19.0.1.2.1',
    'category': 'Accounting/Accounting',
    'summary': 'Sygmetiv accounting dashboard and Community MIS reports',
    'license': 'LGPL-3',
    'author': 'Sygmetiv Business Solutions',
    'website': 'https://sygmetiv.qa',
    'depends': [
        'account',
        'analytic',
        'sygmetiv_company_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/accounting_dashboard_views.xml',
        'views/mis_report_views.xml',
        'report/mis_report_templates.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'sygmetiv_accounting/static/src/js/mis_report.js',
            'sygmetiv_accounting/static/src/xml/mis_report.xml',
            'sygmetiv_accounting/static/src/scss/mis_report.scss',
        ],
    },
}
