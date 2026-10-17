# -*- coding: utf-8 -*-

from odoo.addons.sygmetiv_purchase.hooks import absorb_module


def migrate(cr, version):
    absorb_module(cr, 'sygmetiv_purchase_approval', 'sygmetiv_purchase')
