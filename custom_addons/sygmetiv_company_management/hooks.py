# -*- coding: utf-8 -*-


OLD_RULES = [
    'sygmetiv_company_management.rule_overtime_employee',
    'sygmetiv_company_management.rule_overtime_manager',
    'sygmetiv_company_management.rule_payslip_employee',
    'sygmetiv_company_management.rule_payslip_manager',
    'sygmetiv_company_management.rule_review_employee',
    'sygmetiv_company_management.rule_review_hr',
    'sygmetiv_company_management.rule_goal_employee',
    'sygmetiv_company_management.rule_goal_hr',
]


def deactivate_legacy_rules(env):
    for xmlid in OLD_RULES:
        rule = env.ref(xmlid, raise_if_not_found=False)
        if rule:
            rule.active = False


def remove_legacy_dashboard_menus(env):
    root = env.ref('sygmetiv_company_management.menu_syg_company_root', raise_if_not_found=False)
    workplace = env.ref('sygmetiv_company_management.menu_syg_workplace', raise_if_not_found=False)
    if workplace:
        workplace.unlink()
    dashboard = env.ref(
        'sygmetiv_company_management.menu_syg_employee_dashboard', raise_if_not_found=False
    )
    if dashboard:
        dashboard.write({
            'name': 'Dashboard',
            'group_ids': [(5, 0, 0)],
        })
    if root:
        leftovers = env['ir.ui.menu'].search([
            ('parent_id', '=', root.id),
            ('name', 'in', ['Employee Dashboard', 'Manager Dashboard']),
        ])
        leftovers.unlink()


def remove_obsolete_dashboard_groups(env):
    company_user = env.ref(
        'sygmetiv_company_management.group_company_user', raise_if_not_found=False
    )
    extra = env.ref(
        'sygmetiv_company_management.group_syg_dashboard', raise_if_not_found=False
    )
    if company_user and extra:
        company_user.write({'implied_ids': [(3, extra.id)]})
    for xmlid in (
        'sygmetiv_company_management.group_syg_show_employee_dashboard',
        'sygmetiv_company_management.group_syg_dashboard',
        'sygmetiv_company_management.privilege_syg_dashboard_view',
    ):
        rec = env.ref(xmlid, raise_if_not_found=False)
        if rec:
            rec.unlink()


def ensure_role_types(env):
    role_type = env['syg.role.type'].sudo()
    defaults = (
        ('Attendee', False),
        ('Presenter', True),
    )
    for name, requires_presentation in defaults:
        matches = role_type.with_context(lang='en_US').search([('name', '=ilike', name)])
        if matches:
            continue
        role_type.create({
            'name': name,
            'requires_presentation': requires_presentation,
        })


def ensure_meeting_task_types(env):
    task_type = env['syg.task.type'].sudo()
    for name in ('Demo', 'Training', 'Meeting'):
        matches = task_type.with_context(lang='en_US').search([('name', '=ilike', name)])
        if matches:
            matches.filtered(lambda rec: not rec.is_meeting).write({'is_meeting': True})
        else:
            task_type.create({'name': name, 'is_meeting': True})


def post_init_hook(env):
    deactivate_legacy_rules(env)
    remove_legacy_dashboard_menus(env)
    remove_obsolete_dashboard_groups(env)
    ensure_meeting_task_types(env)
    ensure_role_types(env)
