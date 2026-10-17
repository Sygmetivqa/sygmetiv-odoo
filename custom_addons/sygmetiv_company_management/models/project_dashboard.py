# -*- coding: utf-8 -*-

from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class SygProjectDashboard(models.TransientModel):
    _name = 'syg.project.dashboard'
    _inherit = 'syg.dashboard.mixin'
    _description = 'Project Dashboard'

    name = fields.Char(readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    project_id = fields.Many2one('project.project', readonly=True)
    period_start = fields.Date()
    period_end = fields.Date()
    d_period = fields.Char(compute='_compute_kpis')

    project_count = fields.Integer(compute='_compute_kpis')
    amc_count = fields.Integer(compute='_compute_kpis')
    at_risk_count = fields.Integer(compute='_compute_kpis')
    task_count = fields.Integer(compute='_compute_kpis')
    open_task_count = fields.Integer(compute='_compute_kpis')
    closed_task_count = fields.Integer(compute='_compute_kpis')
    timesheet_hours = fields.Float(compute='_compute_kpis')
    assignee_count = fields.Integer(compute='_compute_kpis')

    d_projects = fields.Char(compute='_compute_kpis')
    d_amc = fields.Char(compute='_compute_kpis')
    d_at_risk = fields.Char(compute='_compute_kpis')
    d_tasks = fields.Char(compute='_compute_kpis')
    d_open_tasks = fields.Char(compute='_compute_kpis')
    d_closed_tasks = fields.Char(compute='_compute_kpis')
    d_timesheet = fields.Char(compute='_compute_kpis')
    d_assignees = fields.Char(compute='_compute_kpis')
    project_status = fields.Char(compute='_compute_kpis')
    estimated_hours = fields.Float(compute='_compute_kpis')
    remaining_man_hours = fields.Float(compute='_compute_kpis')
    hours_over = fields.Boolean(compute='_compute_kpis')
    d_allocated = fields.Char(compute='_compute_kpis')
    d_spent = fields.Char(compute='_compute_kpis')
    d_remaining = fields.Char(compute='_compute_kpis')
    d_hours_status = fields.Char(compute='_compute_kpis')

    graph_status = fields.Text(compute='_compute_kpis')
    graph_tasks = fields.Text(compute='_compute_kpis')
    graph_hours = fields.Text(compute='_compute_kpis')
    graph_amc = fields.Text(compute='_compute_kpis')

    @api.model
    def action_open(self, project=None, period_start=None, period_end=None):
        today = fields.Date.context_today(self)
        dash = self.create({
            'name': project.display_name if project else self.env._("Project Dashboard"),
            'company_id': (project.company_id or self.env.company).id if project else self.env.company.id,
            'project_id': project.id if project else False,
            'period_start': period_start or today.replace(day=1),
            'period_end': period_end or (today + relativedelta(day=31)),
        })
        view = (
            'sygmetiv_company_management.view_syg_project_detail_dashboard_form'
            if project else
            'sygmetiv_company_management.view_syg_project_dashboard_form'
        )
        return {
            'type': 'ir.actions.act_window',
            'name': dash.name,
            'res_model': 'syg.project.dashboard',
            'res_id': dash.id,
            'view_mode': 'form',
            'views': [(self.env.ref(view).id, 'form')],
            'target': 'current',
            'context': self._dashboard_form_context(),
        }

    @api.model
    def action_open_company(self):
        return self.action_open()

    def action_refresh(self):
        self.ensure_one()
        return self.action_open(self.project_id, self.period_start, self.period_end)

    def action_open_projects(self):
        return self.env.ref('project.open_view_project_all').sudo().read()[0]

    def action_open_tasks(self):
        action = self.env.ref('project.action_view_task').sudo().read()[0]
        if self.project_id:
            action['domain'] = [('project_id', '=', self.project_id.id)]
            action['context'] = {'default_project_id': self.project_id.id}
        return action

    def action_open_timesheets(self):
        action = self.env.ref('hr_timesheet.act_hr_timesheet_line').sudo().read()[0]
        domain = [('project_id', '!=', False)]
        if self.project_id:
            domain = [('project_id', '=', self.project_id.id)]
        elif self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        action['domain'] = domain
        return action

    @api.depends('company_id', 'project_id', 'period_start', 'period_end')
    def _compute_kpis(self):
        Project = self.env['project.project']
        Task = self.env['project.task']
        Timesheet = self.env['account.analytic.line']
        for dash in self:
            start, end = dash.period_start, dash.period_end
            if start and end:
                dash.d_period = '%s – %s' % (start.strftime('%d %b'), end.strftime('%d %b %Y'))
            else:
                dash.d_period = ''
            company = dash.company_id
            project_domain = [('company_id', '=', company.id)] if company else []
            if dash.project_id:
                project_domain = [('id', '=', dash.project_id.id)]
            projects = Project.search(project_domain)
            task_domain = [('project_id', 'in', projects.ids)] if projects else [('id', '=', 0)]
            dash.project_count = len(projects)
            dash.amc_count = len(projects.filtered('syg_is_amc')) if 'syg_is_amc' in Project._fields else 0
            dash.at_risk_count = len(projects.filtered(
                lambda p: p.last_update_status in ('at_risk', 'off_track')
            )) if 'last_update_status' in Project._fields else 0
            dash.task_count = Task.search_count(task_domain)
            dash.open_task_count = Task.search_count(task_domain + [('is_closed', '=', False)])
            dash.closed_task_count = dash.task_count - dash.open_task_count
            ts_domain = [('project_id', 'in', projects.ids)]
            if start and end:
                ts_domain += [('date', '>=', start), ('date', '<=', end)]
            timesheets = Timesheet.search(ts_domain)
            dash.timesheet_hours = sum(timesheets.mapped('unit_amount'))
            dash.assignee_count = len(set(
                Task.search(task_domain).mapped('user_ids').ids
            )) if 'user_ids' in Task._fields else 0
            dash.d_projects = str(dash.project_count)
            dash.d_amc = str(dash.amc_count)
            dash.d_at_risk = str(dash.at_risk_count)
            dash.d_tasks = str(dash.task_count)
            dash.d_open_tasks = str(dash.open_task_count)
            dash.d_closed_tasks = str(dash.closed_task_count)
            dash.d_timesheet = dash._hours_label(dash.timesheet_hours)
            dash.d_assignees = str(dash.assignee_count)
            estimated = sum(projects.mapped('allocated_hours')) if 'allocated_hours' in Project._fields else 0.0
            spent = sum(projects.mapped('effective_hours')) if 'effective_hours' in Project._fields else dash.timesheet_hours
            dash.estimated_hours = estimated
            dash.remaining_man_hours = estimated - spent
            dash.hours_over = bool(estimated and spent > estimated)
            dash.d_allocated = dash._hours_label(estimated)
            dash.d_spent = dash._hours_label(spent)
            dash.d_remaining = dash._hours_label(estimated - spent)
            dash.d_hours_status = self.env._("Over estimate") if dash.hours_over else self.env._("On estimate")
            if dash.project_id:
                dash.project_status = self._selection_map('project.project', 'last_update_status').get(
                    dash.project_id.last_update_status
                ) or '—'
            else:
                dash.project_status = company.display_name if company else ''
            dash.graph_status = dash._graph_status(projects)
            dash.graph_tasks = dash._graph_tasks(projects)
            dash.graph_hours = dash._graph_hours(projects, start, end)
            dash.graph_amc = dash._graph_amc(projects)

    def _graph_status(self, projects):
        counts = defaultdict(int)
        selection = self._selection_map('project.project', 'last_update_status')
        for project in projects:
            key = selection.get(project.last_update_status) or self.env._("Undefined")
            counts[key] += 1
        values = [{'label': label, 'value': count, 'type': 'past'} for label, count in counts.items()]
        return self._graph_json(values, self.env._("Project status"))

    def _graph_tasks(self, projects):
        grouped = self.env['project.task']._read_group(
            [('project_id', 'in', projects.ids)],
            ['stage_id'],
            ['__count'],
        )
        values = []
        for stage, count in grouped:
            values.append({
                'label': stage.display_name if stage else self.env._("No stage"),
                'value': count,
                'type': 'past',
            })
        return self._graph_json(values[:8], self.env._("Tasks by stage"))

    def _graph_hours(self, projects, start, end):
        hours_by_day = defaultdict(float)
        domain = [('project_id', 'in', projects.ids)]
        if start and end:
            domain += [('date', '>=', start), ('date', '<=', end)]
        for line in self.env['account.analytic.line'].search(domain):
            hours_by_day[line.date] += line.unit_amount or 0.0
        values = []
        if start and end:
            day = start
            while day <= end:
                values.append({
                    'label': day.strftime('%d %b'),
                    'value': round(hours_by_day.get(day, 0.0), 1),
                    'type': 'past',
                })
                day += relativedelta(days=1)
            step = max(1, len(values) // 12)
            if step > 1:
                values = values[::step]
        return self._graph_json(values, self.env._("Timesheet hours"))

    def _graph_amc(self, projects):
        amc = len(projects.filtered('syg_is_amc')) if 'syg_is_amc' in projects._fields else 0
        values = [
            {'label': self.env._("AMC"), 'value': amc, 'type': 'future'},
            {'label': self.env._("Standard"), 'value': max(len(projects) - amc, 0), 'type': 'past'},
        ]
        return self._graph_json(values, self.env._("Project mix"))
