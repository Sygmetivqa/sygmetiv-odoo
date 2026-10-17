# -*- coding: utf-8 -*-

import json
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.tools import html_escape


class SygWorkplaceDashboard(models.TransientModel):
    _name = 'syg.workplace.dashboard'
    _inherit = 'syg.dashboard.mixin'
    _description = 'Manager Dashboard'

    name = fields.Char(default="Manager Dashboard", readonly=True)
    employee_id = fields.Many2one('hr.employee', readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    is_manager = fields.Boolean(compute='_compute_kpis')
    show_manager_dashboard = fields.Boolean(compute='_compute_dashboard_flags')
    period_start = fields.Date()
    period_end = fields.Date()
    employee_image = fields.Binary(compute='_compute_employee_profile')
    employee_job = fields.Char(compute='_compute_employee_profile')
    employee_department = fields.Char(compute='_compute_employee_profile')
    d_join_date = fields.Char(compute='_compute_employee_profile')
    d_birth_date = fields.Char(compute='_compute_employee_profile')
    d_gender = fields.Char(compute='_compute_employee_profile')

    my_task_count = fields.Integer(compute='_compute_kpis')
    my_open_task_count = fields.Integer(compute='_compute_kpis')
    my_timesheet_hours = fields.Float(compute='_compute_kpis')
    my_overtime_hours = fields.Float(compute='_compute_kpis')
    my_leave_count = fields.Integer(compute='_compute_kpis')
    my_leave_days = fields.Float(compute='_compute_kpis')
    my_leave_pending = fields.Integer(compute='_compute_kpis')
    my_attendance_hours = fields.Float(compute='_compute_kpis')
    my_attendance_days = fields.Integer(compute='_compute_kpis')
    my_checked_in = fields.Boolean(compute='_compute_kpis')
    my_expense_count = fields.Integer(compute='_compute_kpis')
    my_review_score = fields.Float(compute='_compute_kpis')
    my_goal_open_count = fields.Integer(compute='_compute_kpis')

    task_request_count = fields.Integer(compute='_compute_task_request_kpis')
    task_request_pending_count = fields.Integer(compute='_compute_task_request_kpis')
    d_task_requests = fields.Char(compute='_compute_task_request_kpis')
    d_task_requests_pending = fields.Char(compute='_compute_task_request_kpis')

    employee_count = fields.Integer(compute='_compute_kpis')
    project_count = fields.Integer(compute='_compute_kpis')
    open_task_company_count = fields.Integer(compute='_compute_kpis')
    amc_project_count = fields.Integer(compute='_compute_kpis')
    project_at_risk_count = fields.Integer(compute='_compute_kpis')
    overtime_to_approve_count = fields.Integer(compute='_compute_kpis')
    review_pending_count = fields.Integer(compute='_compute_kpis')
    payslip_draft_count = fields.Integer(compute='_compute_kpis')
    income_amount = fields.Monetary(currency_field='currency_id', compute='_compute_kpis')
    expense_amount = fields.Monetary(currency_field='currency_id', compute='_compute_kpis')
    profit_amount = fields.Monetary(currency_field='currency_id', compute='_compute_kpis')
    receivable_amount = fields.Monetary(currency_field='currency_id', compute='_compute_kpis')
    payable_amount = fields.Monetary(currency_field='currency_id', compute='_compute_kpis')

    d_period = fields.Char(compute='_compute_display_labels')
    d_open_tasks = fields.Char(compute='_compute_display_labels')
    d_timesheet = fields.Char(compute='_compute_display_labels')
    d_overtime = fields.Char(compute='_compute_display_labels')
    d_leave = fields.Char(compute='_compute_display_labels')
    d_leave_days = fields.Char(compute='_compute_display_labels')
    d_leave_pending = fields.Char(compute='_compute_display_labels')
    d_attendance = fields.Char(compute='_compute_display_labels')
    d_attendance_days = fields.Char(compute='_compute_display_labels')
    d_checked_in = fields.Char(compute='_compute_display_labels')
    d_expense = fields.Char(compute='_compute_display_labels')
    d_goals = fields.Char(compute='_compute_display_labels')
    d_tasks = fields.Char(compute='_compute_display_labels')
    d_score = fields.Char(compute='_compute_display_labels')
    d_employees = fields.Char(compute='_compute_display_labels')
    d_projects = fields.Char(compute='_compute_display_labels')
    d_open_tasks_company = fields.Char(compute='_compute_display_labels')
    d_amc_projects = fields.Char(compute='_compute_display_labels')
    d_at_risk = fields.Char(compute='_compute_display_labels')
    d_ot_approve = fields.Char(compute='_compute_display_labels')
    d_reviews = fields.Char(compute='_compute_display_labels')
    d_payslips = fields.Char(compute='_compute_display_labels')
    d_income = fields.Char(compute='_compute_display_labels')
    d_expense_amt = fields.Char(compute='_compute_display_labels')
    d_profit = fields.Char(compute='_compute_display_labels')
    d_receivable = fields.Char(compute='_compute_display_labels')
    d_payable = fields.Char(compute='_compute_display_labels')

    department_count = fields.Integer(compute='_compute_manager_stats')
    team_count = fields.Integer(compute='_compute_manager_stats')
    on_leave_count = fields.Integer(compute='_compute_manager_stats')
    team_timesheet_hours = fields.Float(compute='_compute_manager_stats')
    team_overtime_hours = fields.Float(compute='_compute_manager_stats')
    d_departments = fields.Char(compute='_compute_manager_stats')
    d_team = fields.Char(compute='_compute_manager_stats')
    d_on_leave = fields.Char(compute='_compute_manager_stats')
    d_team_timesheet = fields.Char(compute='_compute_manager_stats')
    d_team_overtime = fields.Char(compute='_compute_manager_stats')
    graph_headcount = fields.Text(compute='_compute_manager_stats')
    graph_timesheet = fields.Text(compute='_compute_manager_stats')
    graph_overtime = fields.Text(compute='_compute_manager_stats')
    graph_projects = fields.Text(compute='_compute_manager_stats')
    graph_profit = fields.Text(compute='_compute_manager_stats')
    graph_my_timesheet = fields.Text(compute='_compute_employee_graphs')
    graph_my_overtime = fields.Text(compute='_compute_employee_graphs')
    graph_my_activity = fields.Text(compute='_compute_employee_graphs')
    graph_my_attendance = fields.Text(compute='_compute_employee_graphs')
    graph_my_leave = fields.Text(compute='_compute_employee_graphs')
    welcome_label = fields.Char(compute='_compute_welcome')
    role_label = fields.Char(compute='_compute_welcome')
    announcement_board = fields.Html(compute='_compute_announcement_board', sanitize=True)
    leave_today_board = fields.Html(compute='_compute_leave_today_board', sanitize=False)

    @api.model
    def action_open(self, period_start=None, period_end=None):
        if self._can_open_manager_dashboard():
            return self._action_open_dashboard(
                self.env._("Manager Dashboard"),
                'sygmetiv_company_management.view_syg_workplace_dashboard_form',
                period_start=period_start,
                period_end=period_end,
                extra_context={'syg_dashboard': 'manager'},
            )
        return self.action_open_employee(period_start, period_end)

    @api.model
    def action_open_employee(self, period_start=None, period_end=None):
        return self._action_open_dashboard(
            self.env._("Dashboard"),
            'sygmetiv_company_management.view_syg_employee_dashboard_form',
            period_start=period_start,
            period_end=period_end,
            extra_context={'syg_dashboard': 'employee'},
        )

    def _can_open_manager_dashboard(self):
        return self.env.user.has_group('sygmetiv_company_management.group_company_manager')

    @api.model
    def action_menu_timesheets(self):
        xmlid = (
            'hr_timesheet.timesheet_action_all'
            if self._can_open_manager_dashboard()
            else 'hr_timesheet.act_hr_timesheet_line'
        )
        return self.env.ref(xmlid).sudo().read()[0]

    @api.model
    def action_menu_timeoff(self):
        xmlid = (
            'hr_holidays.hr_leave_action_action_approve_department'
            if self._can_open_manager_dashboard()
            else 'hr_holidays.hr_leave_action_new_request'
        )
        return self.env.ref(xmlid).sudo().read()[0]

    @api.model
    def action_menu_attendance(self):
        domain = []
        if not self._can_open_manager_dashboard():
            domain = [('employee_id.user_id', '=', self.env.uid)]
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Attendances"),
            'res_model': 'hr.attendance',
            'view_mode': 'list,form',
            'domain': domain,
        }

    @api.depends_context('uid')
    def _compute_dashboard_flags(self):
        can_manager = self._can_open_manager_dashboard()
        for dash in self:
            dash.show_manager_dashboard = can_manager

    @api.model
    def _action_open_dashboard(self, title, view_xmlid, period_start=None, period_end=None, extra_context=None):
        today = fields.Date.context_today(self)
        dash = self.create({
            'name': title,
            'period_start': period_start or today.replace(day=1),
            'period_end': period_end or (today + relativedelta(day=31)),
            'employee_id': self.env.user.employee_id.id,
        })
        context = {
            'syg_dashboard': 'employee' if 'employee' in view_xmlid else 'manager',
        }
        if extra_context:
            context.update(extra_context)
        return {
            'type': 'ir.actions.act_window',
            'name': title,
            'res_model': 'syg.workplace.dashboard',
            'res_id': dash.id,
            'view_mode': 'form',
            'views': [(self.env.ref(view_xmlid).id, 'form')],
            'target': 'current',
            'context': self._dashboard_form_context(context),
        }

    def _refresh_kpis(self):
        self.invalidate_recordset()
        return True

    @api.depends('employee_id', 'period_start', 'period_end', 'company_id')
    def _compute_kpis(self):
        for dash in self:
            user = self.env.user
            employee = dash.employee_id
            start, end = dash.period_start, dash.period_end
            is_manager = user.has_group('sygmetiv_company_management.group_company_manager')
            Task = self.env['project.task']
            my_tasks = Task.search([('user_ids', 'in', user.ids)]) if user else Task.browse()
            timesheets = self.env['account.analytic.line']
            overtime = self.env['syg.overtime.request']
            dash.is_manager = is_manager
            dash.my_task_count = len(my_tasks)
            dash.my_open_task_count = len(my_tasks.filtered(lambda t: not t.is_closed))
            if employee and start and end:
                dash.my_timesheet_hours = sum(timesheets.search([
                    ('employee_id', '=', employee.id),
                    ('date', '>=', start),
                    ('date', '<=', end),
                    ('project_id', '!=', False),
                ]).mapped('unit_amount'))
                dash.my_overtime_hours = sum(overtime.search([
                    ('employee_id', '=', employee.id),
                    ('date', '>=', start),
                    ('date', '<=', end),
                    ('state', '=', 'approved'),
                ]).mapped('hours'))
                leaves = self.env['hr.leave'].search([
                    ('employee_id', '=', employee.id),
                    ('state', '=', 'validate'),
                    ('request_date_from', '<=', end),
                    ('request_date_to', '>=', start),
                ])
                dash.my_leave_count = len(leaves)
                dash.my_leave_days = sum(leaves.mapped('number_of_days'))
                dash.my_leave_pending = self.env['hr.leave'].search_count([
                    ('employee_id', '=', employee.id),
                    ('state', 'in', ('confirm', 'validate1')),
                ])
                attendances = self.env['hr.attendance'].search([
                    ('employee_id', '=', employee.id),
                    ('date', '>=', start),
                    ('date', '<=', end),
                ])
                dash.my_attendance_hours = sum(attendances.mapped('worked_hours'))
                dash.my_attendance_days = len(set(attendances.mapped('date')))
                today = fields.Date.context_today(self)
                dash.my_checked_in = bool(self.env['hr.attendance'].search_count([
                    ('employee_id', '=', employee.id),
                    ('date', '=', today),
                    ('check_out', '=', False),
                ]))
                dash.my_expense_count = self.env['hr.expense'].search_count([
                    ('employee_id', '=', employee.id),
                    ('date', '>=', start),
                    ('date', '<=', end),
                ])
                last_review = self.env['syg.performance.review'].search([
                    ('employee_id', '=', employee.id),
                    ('state', '=', 'done'),
                ], limit=1)
                dash.my_review_score = last_review.overall_score if last_review else 0.0
                dash.my_goal_open_count = self.env['syg.performance.goal'].search_count([
                    ('employee_id', '=', employee.id),
                    ('state', '=', 'open'),
                ])
            else:
                dash.my_timesheet_hours = 0.0
                dash.my_overtime_hours = 0.0
                dash.my_leave_count = 0
                dash.my_leave_days = 0.0
                dash.my_leave_pending = 0
                dash.my_attendance_hours = 0.0
                dash.my_attendance_days = 0
                dash.my_checked_in = False
                dash.my_expense_count = 0
                dash.my_review_score = 0.0
                dash.my_goal_open_count = 0

            dash.employee_count = self.env['hr.employee'].search_count(
                self.env.user._syg_employee_domain()
            )
            Project = self.env['project.project']
            project_domain = [('company_id', '=', dash.company_id.id)] if dash.company_id else []
            dash.project_count = Project.search_count(project_domain)
            dash.amc_project_count = Project.search_count(project_domain + [('syg_is_amc', '=', True)]) if 'syg_is_amc' in Project._fields else 0
            dash.project_at_risk_count = Project.search_count(project_domain + [('last_update_status', 'in', ('at_risk', 'off_track'))])
            dash.open_task_company_count = Task.search_count(
                ([('project_id.company_id', '=', dash.company_id.id)] if dash.company_id else []) + [('is_closed', '=', False)]
            )
            visible_employees = self.env['hr.employee'].search(self.env.user._syg_employee_domain())
            dash.overtime_to_approve_count = overtime.search_count([
                ('state', '=', 'submitted'),
                ('employee_id', 'in', visible_employees.ids),
            ])
            dash.review_pending_count = self.env['syg.performance.review'].search_count([
                ('state', 'in', ('submitted', 'reviewed')),
                ('employee_id', 'in', visible_employees.ids),
            ])
            dash.payslip_draft_count = self.env['syg.payslip'].search_count([
                ('state', 'in', ('draft', 'computed')),
                ('employee_id', 'in', visible_employees.ids),
            ])
            moves = self.env['account.move.line'].sudo()
            if start and end and (
                is_manager or user.has_group('account.group_account_readonly')
            ):
                totals = dash._accounting_totals()
                dash.income_amount = totals['income']
                dash.expense_amount = totals['expense']
                dash.profit_amount = totals['profit']
                dash.receivable_amount = totals['receivable']
                dash.payable_amount = totals['payable']
            else:
                dash.income_amount = dash.expense_amount = dash.profit_amount = 0.0
                dash.receivable_amount = dash.payable_amount = 0.0

    @api.depends('employee_id', 'is_manager')
    def _compute_welcome(self):
        for dash in self:
            name = dash.employee_id.name or self.env.user.name
            dash.welcome_label = self.env._("Hi, %s", name)
            job = dash.employee_id.job_title or dash.employee_id.department_id.display_name or ''
            if dash.is_manager:
                dash.role_label = job or self.env._("Manager")
            else:
                dash.role_label = job or self.env._("Employee")

    @api.depends('employee_id')
    def _compute_employee_profile(self):
        gender_labels = self._selection_map('hr.employee', 'sex')
        for dash in self:
            employee = (dash.employee_id or self.env.user.employee_id).sudo()
            dash.employee_image = employee.image_1920 or employee.avatar_128 or False
            dash.employee_job = employee.job_title or employee.job_id.display_name or ''
            dash.employee_department = employee.department_id.display_name or ''
            join_date = employee.contract_date_start or fields.Date.to_date(employee.create_date)
            dash.d_join_date = dash._date_label(join_date)
            dash.d_birth_date = dash._date_label(employee.birthday)
            dash.d_gender = gender_labels.get(employee.sex) or '—'

    @api.depends('company_id')
    def _compute_announcement_board(self):
        announcements = self.env['syg.announcement']._for_dashboard()
        html = announcements._dashboard_board_html()
        for dash in self:
            dash.announcement_board = html

    def action_announcements(self):
        return self.env.ref('sygmetiv_hr.action_syg_announcement').sudo().read()[0]

    @api.depends('company_id', 'employee_id')
    def _compute_leave_today_board(self):
        today = fields.Date.context_today(self)
        leaves = self.env['hr.leave'].sudo().search([
            ('state', '=', 'validate'),
            ('request_date_from', '<=', today),
            ('request_date_to', '>=', today),
            ('employee_id.active', '=', True),
            ('employee_company_id', 'in', self.env.companies.ids),
        ], order='employee_id')
        for dash in self:
            dash.leave_today_board = dash._leave_today_board_html(leaves, today)

    def _leave_today_span_label(self, leave, today):
        start = leave.request_date_from
        end = leave.request_date_to
        morning = self.env._("Morning")
        afternoon = self.env._("Afternoon")
        if leave.request_unit_hours and start == today:
            return self.env._("Hours")
        if start == end == today and leave.request_unit_half:
            return afternoon if leave.request_date_from_period == 'pm' else morning
        if start == today and leave.request_date_from_period == 'pm' and end and end > today:
            return afternoon
        if end == today and leave.request_date_to_period == 'am' and start and start < today:
            return morning
        return self.env._("All day")

    def _leave_today_board_html(self, leaves, today):
        title = html_escape(self.env._("On leave today"))
        kicker = html_escape(self.env._("Today"))
        if not leaves:
            empty = html_escape(self.env._("Everyone is in today."))
            return (
                '<div class="o_syg_leave_panel">'
                '<div class="o_syg_announce_head">'
                '<div>'
                '<div class="o_syg_dash_kicker">%s</div>'
                '<div class="o_syg_section_title">%s</div>'
                '</div>'
                '</div>'
                '<div class="o_syg_announce_empty">'
                '<i class="fa fa-users"></i>'
                '<span>%s</span>'
                '</div>'
                '</div>'
            ) % (kicker, title, empty)
        cards = []
        seen = set()
        for leave in leaves:
            employee = leave.employee_id
            if not employee or employee.id in seen:
                continue
            seen.add(employee.id)
            bits = []
            if employee.department_id:
                bits.append(employee.department_id.name)
            if leave.holiday_status_id:
                bits.append(leave.holiday_status_id.name)
            bits.append(self._leave_today_span_label(leave, today))
            you = ''
            if employee == self.employee_id or employee.user_id == self.env.user:
                you = '<span class="o_syg_leave_you">%s</span>' % html_escape(self.env._("You"))
            cards.append(
                '<article class="o_syg_leave_card">'
                '<div class="o_syg_leave_name"><i class="fa fa-plane"></i>'
                '<span>%s</span>%s</div>'
                '<div class="o_syg_leave_meta">%s</div>'
                '</article>'
                % (
                    html_escape(employee.name or ''),
                    you,
                    html_escape(' · '.join(bits)),
                )
            )
        count = html_escape(str(len(cards)))
        return (
            '<div class="o_syg_leave_panel o_syg_leave_panel_active">'
            '<div class="o_syg_announce_head">'
            '<div>'
            '<div class="o_syg_dash_kicker">%s</div>'
            '<div class="o_syg_section_title">%s</div>'
            '</div>'
            '<span class="o_syg_leave_count">%s</span>'
            '</div>'
            '<div class="o_syg_leave_list">%s</div>'
            '</div>'
        ) % (kicker, title, count, ''.join(cards))

    def action_open_employee_dashboard(self):
        self.ensure_one()
        return self.action_open_employee(self.period_start, self.period_end)

    def action_open_manager_dashboard(self):
        self.ensure_one()
        if not self._can_open_manager_dashboard():
            raise AccessError(self.env._("You do not have access to the manager dashboard."))
        return self.action_open(self.period_start, self.period_end)

    def _accounting_totals(self):
        self.ensure_one()
        empty = {
            'income': 0.0,
            'expense': 0.0,
            'profit': 0.0,
            'receivable': 0.0,
            'payable': 0.0,
        }
        start, end, company = self.period_start, self.period_end, self.company_id
        if not (start and end and company):
            return empty
        moves = self.env['account.move.line'].sudo()
        income = sum(moves.search([
            ('company_id', '=', company.id),
            ('date', '>=', start),
            ('date', '<=', end),
            ('parent_state', '=', 'posted'),
            ('account_id.account_type', 'in', ('income', 'income_other')),
        ]).mapped('balance')) * -1
        expense = sum(moves.search([
            ('company_id', '=', company.id),
            ('date', '>=', start),
            ('date', '<=', end),
            ('parent_state', '=', 'posted'),
            ('account_id.account_type', 'in', ('expense', 'expense_other', 'expense_direct_cost', 'expense_depreciation')),
        ]).mapped('balance'))
        receivable = sum(moves.search([
            ('company_id', '=', company.id),
            ('parent_state', '=', 'posted'),
            ('account_id.account_type', '=', 'asset_receivable'),
        ]).mapped('amount_residual'))
        payable = sum(moves.search([
            ('company_id', '=', company.id),
            ('parent_state', '=', 'posted'),
            ('account_id.account_type', '=', 'liability_payable'),
        ]).mapped('amount_residual'))
        return {
            'income': income,
            'expense': expense,
            'profit': income - expense,
            'receivable': receivable,
            'payable': abs(payable),
        }

    def _hours_label(self, hours):
        total_minutes = int(round((hours or 0.0) * 60))
        sign = '-' if total_minutes < 0 else ''
        hours_part, minutes = divmod(abs(total_minutes), 60)
        return '%s%d:%02d' % (sign, hours_part, minutes)

    def _score_label(self, score):
        if not score:
            return '—'
        return ('%.1f' % score).rstrip('0').rstrip('.')

    def _money_label(self, amount):
        currency = self.currency_id
        if currency:
            return currency.format(amount or 0.0)
        return '%.2f' % (amount or 0.0)

    @api.depends(
        'period_start', 'period_end', 'currency_id',
        'my_open_task_count', 'my_timesheet_hours', 'my_overtime_hours',
        'my_leave_count', 'my_leave_days', 'my_leave_pending',
        'my_attendance_hours', 'my_attendance_days', 'my_checked_in',
        'my_expense_count', 'my_goal_open_count',
        'my_task_count', 'my_review_score', 'employee_count', 'project_count',
        'open_task_company_count', 'amc_project_count', 'project_at_risk_count',
        'overtime_to_approve_count', 'review_pending_count', 'payslip_draft_count',
        'income_amount', 'expense_amount', 'profit_amount',
        'receivable_amount', 'payable_amount',
    )
    def _compute_display_labels(self):
        for dash in self:
            start, end = dash.period_start, dash.period_end
            if start and end:
                dash.d_period = '%s – %s' % (
                    start.strftime('%d %b'),
                    end.strftime('%d %b %Y'),
                )
            else:
                dash.d_period = ''
            dash.d_open_tasks = str(dash.my_open_task_count or 0)
            dash.d_timesheet = dash._hours_label(dash.my_timesheet_hours)
            dash.d_overtime = dash._hours_label(dash.my_overtime_hours)
            dash.d_leave = str(dash.my_leave_count or 0)
            dash.d_leave_days = ('%.1f' % (dash.my_leave_days or 0)).rstrip('0').rstrip('.')
            dash.d_leave_pending = str(dash.my_leave_pending or 0)
            dash.d_attendance = dash._hours_label(dash.my_attendance_hours)
            dash.d_attendance_days = str(dash.my_attendance_days or 0)
            dash.d_checked_in = self.env._("Checked in") if dash.my_checked_in else self.env._("Out")
            dash.d_expense = str(dash.my_expense_count or 0)
            dash.d_goals = str(dash.my_goal_open_count or 0)
            dash.d_tasks = str(dash.my_task_count or 0)
            dash.d_score = dash._score_label(dash.my_review_score)
            dash.d_employees = str(dash.employee_count or 0)
            dash.d_projects = str(dash.project_count or 0)
            dash.d_open_tasks_company = str(dash.open_task_company_count or 0)
            dash.d_amc_projects = str(dash.amc_project_count or 0)
            dash.d_at_risk = str(dash.project_at_risk_count or 0)
            dash.d_ot_approve = str(dash.overtime_to_approve_count or 0)
            dash.d_reviews = str(dash.review_pending_count or 0)
            dash.d_payslips = str(dash.payslip_draft_count or 0)
            dash.d_income = dash._money_label(dash.income_amount)
            dash.d_expense_amt = dash._money_label(dash.expense_amount)
            dash.d_profit = dash._money_label(dash.profit_amount)
            dash.d_receivable = dash._money_label(dash.receivable_amount)
            dash.d_payable = dash._money_label(dash.payable_amount)

    def _visible_employee_ids(self):
        return self.env['hr.employee'].search(self.env.user._syg_employee_domain()).ids

    @api.depends('period_start', 'period_end', 'company_id', 'employee_id')
    def _compute_manager_stats(self):
        Employee = self.env['hr.employee']
        Department = self.env['hr.department']
        Leave = self.env['hr.leave']
        Timesheet = self.env['account.analytic.line']
        Overtime = self.env['syg.overtime.request']
        for dash in self:
            company = dash.company_id
            start, end = dash.period_start, dash.period_end
            employee = dash.employee_id
            visible_ids = dash._visible_employee_ids()
            dept_count = Department.search_count([('company_id', '=', company.id)]) if company else 0
            team_count = Employee.search_count([('parent_id', '=', employee.id)]) if employee else 0
            on_leave = 0
            team_ts = 0.0
            team_ot = 0.0
            if company and start and end and visible_ids:
                on_leave = Leave.search_count([
                    ('employee_id', 'in', visible_ids),
                    ('state', '=', 'validate'),
                    ('request_date_from', '<=', end),
                    ('request_date_to', '>=', start),
                ])
                team_ts = sum(Timesheet.search([
                    ('employee_id', 'in', visible_ids),
                    ('date', '>=', start),
                    ('date', '<=', end),
                    ('project_id', '!=', False),
                ]).mapped('unit_amount'))
                team_ot = sum(Overtime.search([
                    ('employee_id', 'in', visible_ids),
                    ('date', '>=', start),
                    ('date', '<=', end),
                    ('state', '=', 'approved'),
                ]).mapped('hours'))
            dash.department_count = dept_count
            dash.team_count = team_count
            dash.on_leave_count = on_leave
            dash.team_timesheet_hours = team_ts
            dash.team_overtime_hours = team_ot
            dash.d_departments = str(dept_count or 0)
            dash.d_team = str(team_count or 0)
            dash.d_on_leave = str(on_leave or 0)
            dash.d_team_timesheet = dash._hours_label(team_ts)
            dash.d_team_overtime = dash._hours_label(team_ot)
            dash.graph_headcount = json.dumps(dash._graph_headcount())
            dash.graph_timesheet = json.dumps(dash._graph_timesheet())
            dash.graph_overtime = json.dumps(dash._graph_overtime())
            dash.graph_projects = json.dumps(dash._graph_projects())
            dash.graph_profit = json.dumps(dash._graph_profit())

    def _graph_headcount(self):
        self.ensure_one()
        grouped = self.env['hr.employee']._read_group(
            self.env.user._syg_employee_domain(),
            ['department_id'],
            ['__count'],
        )
        values = []
        for department, count in grouped:
            values.append({
                'label': department.display_name if department else self.env._("No department"),
                'value': count,
                'type': 'past',
            })
        values = values[:8] or [{'label': self.env._("No data"), 'value': 0, 'type': 'past'}]
        return [{
            'values': values,
            'key': self.env._("Headcount"),
            'is_sample_data': False,
        }]

    def _graph_timesheet(self):
        self.ensure_one()
        start, end = self.period_start, self.period_end
        values = []
        if start and end and self.company_id:
            hours_by_dept = defaultdict(float)
            lines = self.env['account.analytic.line'].search([
                ('employee_id', 'in', self._visible_employee_ids()),
                ('date', '>=', start),
                ('date', '<=', end),
                ('project_id', '!=', False),
            ])
            for line in lines:
                label = line.employee_id.department_id.display_name or self.env._("No department")
                hours_by_dept[label] += line.unit_amount or 0.0
            values = [{
                'label': name,
                'value': round(hours, 1),
                'type': 'past',
            } for name, hours in sorted(hours_by_dept.items(), key=lambda item: item[1], reverse=True)[:8]]
        values = values or [{'label': self.env._("No data"), 'value': 0, 'type': 'past'}]
        return [{
            'values': values,
            'key': self.env._("Timesheet hours"),
            'is_sample_data': False,
        }]

    def _graph_overtime(self):
        self.ensure_one()
        start, end = self.period_start, self.period_end
        hours_by_day = defaultdict(float)
        if start and end and self.company_id:
            requests = self.env['syg.overtime.request'].search([
                ('employee_id', 'in', self._visible_employee_ids()),
                ('date', '>=', start),
                ('date', '<=', end),
                ('state', '=', 'approved'),
            ])
            for rec in requests:
                hours_by_day[rec.date] += rec.hours or 0.0
        points = self._points_from_hours_by_day(hours_by_day) or [{'x': self.env._("No data"), 'y': 0}]
        return [{
            'values': points,
            'key': self.env._("Approved overtime"),
            'is_sample_data': False,
        }]

    def _graph_projects(self):
        self.ensure_one()
        start, end = self.period_start, self.period_end
        hours_by_project = defaultdict(float)
        if start and end:
            lines = self.env['account.analytic.line'].search([
                ('employee_id', 'in', self._visible_employee_ids()),
                ('date', '>=', start),
                ('date', '<=', end),
                ('project_id', '!=', False),
            ])
            for line in lines:
                hours_by_project[line.project_id.display_name] += line.unit_amount or 0.0
        values = [{
            'label': name[:22],
            'value': round(hours, 1),
            'type': 'past',
        } for name, hours in sorted(hours_by_project.items(), key=lambda item: item[1], reverse=True)[:8]]
        values = values or [{'label': self.env._("No data"), 'value': 0, 'type': 'past'}]
        return [{
            'values': values,
            'key': self.env._("Hours by project"),
            'is_sample_data': False,
        }]

    def _graph_profit(self):
        self.ensure_one()
        totals = self._accounting_totals()
        return [{
            'values': [
                {'label': self.env._("Income"), 'value': round(totals['income'], 2), 'type': 'past'},
                {'label': self.env._("Expense"), 'value': round(totals['expense'], 2), 'type': 'future'},
                {'label': self.env._("Profit"), 'value': round(totals['profit'], 2), 'type': 'past'},
            ],
            'key': self.env._("Profit"),
            'is_sample_data': False,
        }]

    def _points_from_hours_by_day(self, hours_by_day):
        start, end = self.period_start, self.period_end
        if not start or not end:
            return [{'x': self.env._("No data"), 'y': 0}]
        points = []
        bucket_start = start
        while bucket_start <= end:
            bucket_end = min(bucket_start + relativedelta(days=6), end)
            total = 0.0
            day = bucket_start
            while day <= bucket_end:
                total += hours_by_day.get(day, 0.0)
                day += relativedelta(days=1)
            points.append({
                'x': bucket_start.strftime('%d %b'),
                'y': round(total, 1),
            })
            bucket_start = bucket_end + relativedelta(days=1)
        return points or [{'x': self.env._("No data"), 'y': 0}]

    @api.depends(
        'period_start', 'period_end', 'employee_id',
        'my_open_task_count', 'my_timesheet_hours', 'my_attendance_hours',
        'my_leave_days', 'my_leave_count', 'my_expense_count', 'my_goal_open_count',
    )
    def _compute_employee_graphs(self):
        Timesheet = self.env['account.analytic.line'].sudo()
        Overtime = self.env['syg.overtime.request'].sudo()
        Attendance = self.env['hr.attendance'].sudo()
        Leave = self.env['hr.leave'].sudo()
        for dash in self:
            start, end, employee = dash.period_start, dash.period_end, dash.employee_id
            ts_by_day = defaultdict(float)
            ot_by_day = defaultdict(float)
            att_by_day = defaultdict(float)
            leave_by_type = defaultdict(float)
            if employee and start and end:
                for line in Timesheet.search([
                    ('employee_id', '=', employee.id),
                    ('date', '>=', start),
                    ('date', '<=', end),
                    ('project_id', '!=', False),
                ]):
                    ts_by_day[line.date] += line.unit_amount or 0.0
                for rec in Overtime.search([
                    ('employee_id', '=', employee.id),
                    ('date', '>=', start),
                    ('date', '<=', end),
                    ('state', '=', 'approved'),
                ]):
                    ot_by_day[rec.date] += rec.hours or 0.0
                for rec in Attendance.search([
                    ('employee_id', '=', employee.id),
                    ('date', '>=', start),
                    ('date', '<=', end),
                ]):
                    att_by_day[rec.date] += rec.worked_hours or 0.0
                for rec in Leave.search([
                    ('employee_id', '=', employee.id),
                    ('state', '=', 'validate'),
                    ('request_date_from', '<=', end),
                    ('request_date_to', '>=', start),
                ]):
                    leave_by_type[rec.holiday_status_id.display_name or self.env._("Time Off")] += rec.number_of_days or 0.0
            ts_points = dash._points_from_hours_by_day(ts_by_day) or [{'x': self.env._("No data"), 'y': 0}]
            ot_points = dash._points_from_hours_by_day(ot_by_day) or [{'x': self.env._("No data"), 'y': 0}]
            att_points = dash._points_from_hours_by_day(att_by_day) or [{'x': self.env._("No data"), 'y': 0}]
            leave_values = [{
                'label': name,
                'value': round(days, 1),
                'type': 'past',
            } for name, days in sorted(leave_by_type.items(), key=lambda item: item[1], reverse=True)[:8]]
            leave_values = leave_values or [{'label': self.env._("No leave"), 'value': 0, 'type': 'past'}]
            dash.graph_my_timesheet = json.dumps([{
                'values': ts_points,
                'key': self.env._("My timesheet hours"),
                'is_sample_data': False,
            }])
            dash.graph_my_overtime = json.dumps([{
                'values': ot_points,
                'key': self.env._("My overtime hours"),
                'is_sample_data': False,
            }])
            dash.graph_my_attendance = json.dumps([{
                'values': att_points,
                'key': self.env._("My attendance hours"),
                'is_sample_data': False,
            }])
            dash.graph_my_leave = json.dumps([{
                'values': leave_values,
                'key': self.env._("Leave taken"),
                'is_sample_data': False,
            }])
            dash.graph_my_activity = json.dumps([{
                'values': [
                    {'label': self.env._("Timesheet"), 'value': round(dash.my_timesheet_hours or 0.0, 1), 'type': 'past'},
                    {'label': self.env._("Attendance"), 'value': round(dash.my_attendance_hours or 0.0, 1), 'type': 'past'},
                    {'label': self.env._("Leave days"), 'value': round(dash.my_leave_days or 0.0, 1), 'type': 'future'},
                    {'label': self.env._("Open Tasks"), 'value': dash.my_open_task_count or 0, 'type': 'future'},
                ],
                'key': self.env._("My activity"),
                'is_sample_data': False,
            }])

    def action_refresh(self):
        self.ensure_one()
        start, end = self.period_start, self.period_end
        if self.env.context.get('syg_dashboard') == 'employee':
            return self.action_open_employee(start, end)
        if self.env.context.get('syg_dashboard') == 'manager':
            return self.action_open(start, end)
        if self._can_open_manager_dashboard():
            return self.action_open(start, end)
        return self.action_open_employee(start, end)

    def _act(self, model, name, domain=None, context=None, view_mode='list,form'):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'view_mode': view_mode,
            'domain': domain or [],
            'context': context or {},
        }

    def action_my_tasks(self):
        return self._act('project.task', self.env._("My Tasks"), [('user_ids', 'in', self.env.uid)])

    @api.depends('employee_id', 'period_start', 'period_end')
    def _compute_task_request_kpis(self):
        Request = self.env['syg.task.request']
        for dash in self:
            domain = [('state', '!=', 'cancelled')]
            if dash.employee_id:
                domain.append(('employee_id', '=', dash.employee_id.id))
            if dash.period_start and dash.period_end:
                start = fields.Datetime.to_datetime(dash.period_start)
                end = fields.Datetime.to_datetime(dash.period_end) + relativedelta(days=1, seconds=-1)
                domain += [('planned_date', '>=', start), ('planned_date', '<=', end)]
            records = Request.search(domain)
            dash.task_request_count = len(records)
            dash.task_request_pending_count = len(records.filtered(lambda rec: not rec.task_id))
            dash.d_task_requests = str(dash.task_request_count)
            dash.d_task_requests_pending = str(dash.task_request_pending_count)

    def action_task_requests(self):
        domain = [('state', '!=', 'cancelled')]
        context = {}
        if self.employee_id:
            domain.append(('employee_id', '=', self.employee_id.id))
            context = {'default_employee_id': self.employee_id.id, 'search_default_mine': 1}
        return self._act('syg.task.request', self.env._("Task Requests"), domain, context)

    def action_task_requests_pending(self):
        domain = [('task_id', '=', False), ('state', 'in', ('draft', 'submitted'))]
        context = {'search_default_waiting': 1}
        if self.employee_id and self.env.context.get('syg_dashboard') != 'manager':
            domain.append(('employee_id', '=', self.employee_id.id))
            context['search_default_mine'] = 1
        return self._act('syg.task.request', self.env._("Task Requests"), domain, context)

    def action_performance_dashboard(self):
        employee = False if self._can_open_manager_dashboard() else self.employee_id
        return self.env['syg.performance.dashboard'].action_open(
            self.period_start, self.period_end, employee,
        )

    def action_my_timesheets(self):
        employee = self.employee_id
        domain = [('employee_id', '=', employee.id)] if employee else [('user_id', '=', self.env.uid)]
        return self._act('account.analytic.line', self.env._("My Timesheets"), domain)

    def action_my_overtime(self):
        employee = self.employee_id
        return self._act(
            'syg.overtime.request',
            self.env._("My Overtime"),
            [('employee_id', '=', employee.id)] if employee else [],
            {'default_employee_id': employee.id if employee else False},
        )

    def action_my_leaves(self):
        return self.env.ref('hr_holidays.hr_leave_action_my').sudo().read()[0]

    def action_my_attendance(self):
        employee = self.employee_id
        domain = [('employee_id', '=', employee.id)] if employee else [('employee_id.user_id', '=', self.env.uid)]
        return self._act('hr.attendance', self.env._("My Attendance"), domain)

    def action_open_company_tasks(self):
        domain = [('is_closed', '=', False)]
        if self.company_id:
            domain.append(('project_id.company_id', '=', self.company_id.id))
        return self._act('project.task', self.env._("Open Tasks"), domain)

    def action_amc_projects(self):
        domain = [('syg_is_amc', '=', True)]
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        return self._act('project.project', self.env._("AMC Projects"), domain, view_mode='kanban,list,form')

    def action_at_risk_projects(self):
        domain = [('last_update_status', 'in', ('at_risk', 'off_track'))]
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        return self._act('project.project', self.env._("Projects at Risk"), domain, view_mode='kanban,list,form')

    def action_my_expenses(self):
        return self.env.ref('hr_expense.hr_expense_actions_my_all').sudo().read()[0]

    def action_my_goals(self):
        employee = self.employee_id
        return self._act(
            'syg.performance.goal',
            self.env._("My Goals"),
            [('employee_id', '=', employee.id)] if employee else [],
        )

    def action_departments(self):
        return self.env.ref('hr.hr_department_kanban_action').sudo().read()[0]

    def action_employees(self):
        return self.env.ref('hr.open_view_employee_list_my').sudo().read()[0]

    def action_team(self):
        employee = self.employee_id
        return self._act(
            'hr.employee',
            self.env._("Direct Reports"),
            [('parent_id', '=', employee.id)] if employee else [('id', '=', False)],
        )

    def action_team_timesheets(self):
        domain = [('project_id', '!=', False)]
        if self.period_start:
            domain.append(('date', '>=', self.period_start))
        if self.period_end:
            domain.append(('date', '<=', self.period_end))
        if self.company_id:
            domain.append(('employee_id.company_id', '=', self.company_id.id))
        return self._act('account.analytic.line', self.env._("Team Timesheets"), domain)

    def action_on_leave(self):
        domain = [('state', '=', 'validate')]
        if self.period_end:
            domain.append(('request_date_from', '<=', self.period_end))
        if self.period_start:
            domain.append(('request_date_to', '>=', self.period_start))
        visible_ids = self._visible_employee_ids()
        if visible_ids:
            domain.append(('employee_id', 'in', visible_ids))
        return self._act('hr.leave', self.env._("Time Off This Period"), domain)

    def action_projects(self):
        return self.env.ref('project.open_view_project_all').sudo().read()[0]

    def action_overtime_to_approve(self):
        return self._act('syg.overtime.request', self.env._("Overtime to Approve"), [('state', '=', 'submitted')])

    def action_reviews_pending(self):
        return self._act(
            'syg.performance.review',
            self.env._("Pending Reviews"),
            [('state', 'in', ('submitted', 'reviewed'))],
        )

    def action_payslips(self):
        return self._act('syg.payslip', self.env._("Payslips"), [('state', 'in', ('draft', 'computed'))])

    def action_invoice_analysis(self):
        return self.env.ref('account.action_account_invoice_report_all').sudo().read()[0]

    def action_analytic_report(self):
        return self.env.ref('account.action_analytic_reporting').sudo().read()[0]

    def action_assign_task(self):
        if not self.env.user.has_group('sygmetiv_company_management.group_company_manager'):
            raise AccessError(self.env._("You do not have access to assign tasks."))
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Assign Task"),
            'res_model': 'syg.task.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_generate_payslips(self):
        if not self.env.user.has_group('sygmetiv_company_management.group_company_manager'):
            raise AccessError(self.env._("You do not have access to generate payslips."))
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Generate Payslips"),
            'res_model': 'syg.payslip.generate.wizard',
            'view_mode': 'form',
            'target': 'new',
        }
