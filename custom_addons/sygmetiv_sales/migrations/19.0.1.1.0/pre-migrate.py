# -*- coding: utf-8 -*-

from odoo.addons.sygmetiv_sales.hooks import absorb_module


def migrate(cr, version):
    absorb_module(cr, 'sygmetiv_sale_approval', 'sygmetiv_sales')
