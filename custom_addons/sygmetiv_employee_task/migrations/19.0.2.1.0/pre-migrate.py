def migrate(cr, version):
    """Copy any employee.task rows that were not moved yet.

    The employee.task model is removed on this upgrade. Odoo drops that table
    after migrations, so remaining rows must land on syg.task.request first.
    """
    cr.execute("SELECT to_regclass('public.employee_task')")
    if not cr.fetchone()[0]:
        return
    cr.execute("SELECT to_regclass('public.syg_task_request')")
    if not cr.fetchone()[0]:
        return
    cr.execute("""
        INSERT INTO syg_task_request (
            name, employee_id, user_id, project_id, planned_date, estimated_hours,
            time_spent, description, state, task_id, timesheet_id, company_id,
            create_uid, write_uid, create_date, write_date
        )
        SELECT
            COALESCE(et.name, 'Task request'),
            et.employee_id,
            et.user_id,
            et.project_id,
            COALESCE(et.date::timestamp, NOW()),
            et.time_spent,
            et.time_spent,
            CASE
                WHEN et.description IS NULL THEN NULL
                ELSE CONCAT('<p>', REPLACE(REPLACE(et.description, '&', '&amp;'), '<', '&lt;'), '</p>')
            END,
            CASE
                WHEN et.task_id IS NOT NULL THEN 'converted'
                WHEN et.stage = 'cancelled' THEN 'cancelled'
                WHEN et.stage IN ('in_progress', 'done') THEN 'submitted'
                ELSE 'draft'
            END,
            et.task_id,
            et.timesheet_id,
            et.company_id,
            et.create_uid,
            et.write_uid,
            et.create_date,
            et.write_date
        FROM employee_task et
        WHERE NOT EXISTS (
            SELECT 1 FROM syg_task_request req
            WHERE (et.task_id IS NOT NULL AND req.task_id = et.task_id)
               OR (
                    req.employee_id = et.employee_id
                    AND req.name = COALESCE(et.name, 'Task request')
                    AND req.create_date = et.create_date
               )
        )
    """)
    cr.execute("""
        UPDATE project_task AS task
           SET syg_task_request_id = req.id
          FROM syg_task_request AS req
         WHERE req.task_id = task.id
           AND task.syg_task_request_id IS NULL
    """)
