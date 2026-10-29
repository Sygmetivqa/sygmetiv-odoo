# -*- coding: utf-8 -*-
{
    'name': 'Sygmetiv Company Management',
    'version': '19.0.1.53.0',
    'category': 'Human Resources',
    'summary': 'Employee dashboard, projects, timesheets, overtime, payroll and performance',
    'description': """
Company lifecycle for Odoo Community
====================================

Unifies day-to-day company operations:

* Employee and manager workplace dashboards
* Company announcements on both dashboards
* Project and task assignment
* Timesheets, attendance and time off (standard apps)
* Overtime requests with email and web_notify
* Community payroll (payslips from wage, timesheets and overtime)
* Performance goals and reviews
    """,
    'author': 'Sygmetiv Business Solutions',
    'website': 'https://sygmetiv.qa',
    'license': 'LGPL-3',
    'depends': [
        'hr',
        'hr_homeworking',
        'hr_org_chart',
        'hr_attendance',
        'hr_holidays',
        'hr_expense',
        'hr_recruitment',
        'hr_skills',
        'project',
        'hr_timesheet',
        'account',
        'mail',
        'web_notify',
        'sygmetiv_hr',
        'sygmetiv_attendance',
    ],
    'data': [
        'security/company_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/mail_template_data.xml',
        'views/res_config_settings_views.xml',
        'views/hr_employee_views.xml',
        'views/project_views.xml',
        'views/project_collaboration_views.xml',
        'views/credential_views.xml',
        'views/task_views.xml',
        'views/task_request_views.xml',
        'views/task_type_views.xml',
        'views/role_type_views.xml',
        'views/implementation_type_views.xml',
        'views/hosting_type_views.xml',
        'views/overtime_views.xml',
        'views/payslip_views.xml',
        'views/performance_views.xml',
        'views/performance_dashboard_views.xml',
        'views/live_checklist_views.xml',
        'views/project_wizard_views.xml',
        'views/task_assign_wizard_views.xml',
        'views/payslip_generate_wizard_views.xml',
        'views/dashboard_views.xml',
        'views/project_dashboard_views.xml',
        'report/payslip_report.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'post_init_hook': 'post_init_hook',
    'assets': {
        'web.assets_backend': [
            'sygmetiv_company_management/static/src/js/dashboard_graph.js',
            'sygmetiv_company_management/static/src/xml/dashboard_graph.xml',
            'sygmetiv_company_management/static/src/scss/dashboard.scss',
        ],
    },
}
