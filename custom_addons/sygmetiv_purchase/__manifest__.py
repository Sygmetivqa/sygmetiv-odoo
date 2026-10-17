# -*- coding: utf-8 -*-
{
    'name': 'Sygmetiv Purchase',
    'version': '19.0.1.1.0',
    'category': 'Inventory/Purchase',
    'summary': 'Sygmetiv purchase menus, RFQ approval, PO and purchase analysis',
    'license': 'LGPL-3',
    'author': 'Sygmetiv Business Solutions',
    'website': 'https://sygmetiv.qa',
    'depends': [
        'purchase',
        'mail',
        'web_notify',
        'sygmetiv_company_management',
    ],
    'data': [
        'security/purchase_approval_security.xml',
        'data/mail_template_data.xml',
        'views/purchase_order_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'pre_init_hook': 'pre_init_hook',
}
