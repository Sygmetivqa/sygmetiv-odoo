# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID

from odoo.addons.sygmetiv_company_management.hooks import ensure_meeting_task_types


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    ensure_meeting_task_types(env)
