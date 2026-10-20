# -*- coding: utf-8 -*-
{
    'name': 'Sygmetiv Sales',
    'version': '19.0.1.2.0',
    'category': 'Sales/Sales',
    'summary': 'Sygmetiv sales dashboard, quotation approval, CRM and sales reports',
    'license': 'LGPL-3',
    'author': 'Sygmetiv Business Solutions',
    'website': 'https://sygmetiv.qa',
    'depends': [
        'crm',
        'sale_management',
        'mail',
        'web_notify',
        'sygmetiv_company_management',
    ],
    'data': [
        'security/sale_approval_security.xml',
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'views/sale_order_views.xml',
        'views/sales_dashboard_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'pre_init_hook': 'pre_init_hook',
}
