# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID

from odoo.addons.sygmetiv_company_management.hooks import remove_legacy_dashboard_menus


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    remove_legacy_dashboard_menus(env)
