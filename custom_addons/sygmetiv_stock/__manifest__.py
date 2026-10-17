# -*- coding: utf-8 -*-
{
    'name': 'Sygmetiv Stock',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Sygmetiv inventory menus for receipts, deliveries and stock',
    'license': 'LGPL-3',
    'author': 'Sygmetiv Business Solutions',
    'website': 'https://sygmetiv.qa',
    'depends': [
        'stock',
        'sygmetiv_company_management',
    ],
    'data': [
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
}
