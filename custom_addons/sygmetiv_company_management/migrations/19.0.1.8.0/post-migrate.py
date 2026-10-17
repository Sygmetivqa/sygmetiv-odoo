# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID

from odoo.addons.sygmetiv_company_management.hooks import deactivate_legacy_rules


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    deactivate_legacy_rules(env)
