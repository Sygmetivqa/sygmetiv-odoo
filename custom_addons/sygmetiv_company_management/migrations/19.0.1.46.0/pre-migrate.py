# -*- coding: utf-8 -*-


def migrate(cr, version):
    cr.execute("""
        SELECT table_name
          FROM information_schema.columns
         WHERE column_name = 'syg_role'
           AND table_name IN ('project_task', 'syg_task_request')
    """)
    for table, in cr.fetchall():
        cr.execute(
            f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS syg_role_legacy varchar'
        )
        cr.execute(
            f"UPDATE {table} SET syg_role_legacy = syg_role "
            "WHERE syg_role_legacy IS NULL AND syg_role IS NOT NULL"
        )
