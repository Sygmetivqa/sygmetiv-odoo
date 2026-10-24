# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID

from odoo.addons.sygmetiv_company_management.hooks import ensure_role_types


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    ensure_role_types(env)
    role_type = env['syg.role.type'].sudo()
    for table in ('project_task', 'syg_task_request'):
        cr.execute("""
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = %s
               AND column_name = 'syg_role_legacy'
        """, (table,))
        if not cr.fetchone():
            continue
        cr.execute(
            f"SELECT id, syg_role_legacy FROM {table} "
            "WHERE syg_role_legacy IS NOT NULL AND btrim(syg_role_legacy) <> ''"
        )
        for rec_id, name in cr.fetchall():
            label = name.strip()
            role = role_type.with_context(lang='en_US').search(
                [('name', '=ilike', label)], limit=1
            )
            if not role:
                role = role_type.create({'name': label})
            cr.execute(
                f"UPDATE {table} SET syg_role_type_id = %s "
                "WHERE id = %s AND syg_role_type_id IS NULL",
                (role.id, rec_id),
            )
        cr.execute(f'ALTER TABLE {table} DROP COLUMN IF EXISTS syg_role_legacy')
