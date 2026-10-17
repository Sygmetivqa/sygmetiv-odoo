# -*- coding: utf-8 -*-


def rename_module(cr, old_name, new_name):
    cr.execute("SELECT 1 FROM ir_module_module WHERE name = %s", (old_name,))
    if not cr.fetchone():
        return
    cr.execute("SELECT id FROM ir_module_module WHERE name = %s", (new_name,))
    new_row = cr.fetchone()
    if new_row:
        cr.execute(
            "UPDATE ir_model_data SET module = %s WHERE module = %s",
            (new_name, old_name),
        )
        cr.execute(
            "UPDATE ir_module_module_dependency SET name = %s WHERE name = %s",
            (new_name, old_name),
        )
        cr.execute(
            """
            DELETE FROM ir_module_module_dependency
            WHERE module_id IN (SELECT id FROM ir_module_module WHERE name = %s)
            """,
            (old_name,),
        )
        cr.execute(
            "DELETE FROM ir_model_data WHERE module = 'base' AND name = %s",
            ('module_%s' % old_name,),
        )
        cr.execute("DELETE FROM ir_module_module WHERE name = %s", (old_name,))
        return
    cr.execute(
        "UPDATE ir_module_module SET name = %s WHERE name = %s",
        (new_name, old_name),
    )
    cr.execute(
        "UPDATE ir_model_data SET name = %s WHERE module = 'base' AND name = %s",
        ('module_%s' % new_name, 'module_%s' % old_name),
    )
    cr.execute(
        "UPDATE ir_model_data SET module = %s WHERE module = %s",
        (new_name, old_name),
    )
    cr.execute(
        "UPDATE ir_module_module_dependency SET name = %s WHERE name = %s",
        (new_name, old_name),
    )


def pre_init_hook(env):
    rename_module(env.cr, 'sygmetiv_announcement', 'sygmetiv_hr')
