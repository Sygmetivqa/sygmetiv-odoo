# -*- coding: utf-8 -*-
{
    'name': 'Sygmetiv KPI',
    'version': '19.0.1.6.1',
    'category': 'Human Resources',
    'summary': 'KPI criteria, multi-evaluator scoring and email on submit',
    'license': 'LGPL-3',
    'author': 'Sygmetiv Business Solutions',
    'website': 'https://sygmetiv.qa',
    'depends': [
        'hr',
        'mail',
        'sygmetiv_company_management',
    ],
    'data': [
        'security/kpi_security.xml',
        'security/ir.model.access.csv',
        'data/kpi_status_data.xml',
        'data/mail_template_data.xml',
        'data/kpi_cron.xml',
        'views/kpi_criteria_views.xml',
        'views/kpi_config_views.xml',
        'views/kpi_evaluation_views.xml',
        'views/portal_templates.xml',
        'views/evaluation_dashboard_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sygmetiv_kpi/static/src/css/kpi_dashboard.css',
        ],
    },
    'installable': True,
    'application': False,
}
