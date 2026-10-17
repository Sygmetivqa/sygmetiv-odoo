# -*- coding: utf-8 -*-

from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class SygPerformanceDashboard(models.TransientModel):
    _name = 'syg.performance.dashboard'
    _inherit = 'syg.dashboard.mixin'
    _description = 'Performance Dashboard'

    name = fields.Char(readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    employee_id = fields.Many2one('hr.employee', string="Employee")
    include_project_task = fields.Boolean(string="Project task", default=True)
    include_task_request = fields.Boolean(string="Task request", default=True)
    period_start = fields.Date()
    period_end = fields.Date()
    d_period = fields.Char(compute='_compute_kpis')

    hours_worked = fields.Float(compute='_compute_kpis')
    timesheet_hours = fields.Float(compute='_compute_kpis')
    request_hours = fields.Float(compute='_compute_kpis')
    employee_count = fields.Integer(compute='_compute_kpis')
    project_count = fields.Integer(compute='_compute_kpis')
    task_count = fields.Integer(compute='_compute_kpis')
    request_count = fields.Integer(compute='_compute_kpis')
    task_type_count = fields.Integer(compute='_compute_kpis')

    d_hours = fields.Char(compute='_compute_kpis')
    d_timesheet = fields.Char(compute='_compute_kpis')
    d_request_hours = fields.Char(compute='_compute_kpis')
    d_employees = fields.Char(compute='_compute_kpis')
    d_projects = fields.Char(compute='_compute_kpis')
    d_tasks = fields.Char(compute='_compute_kpis')
    d_requests = fields.Char(compute='_compute_kpis')
    d_types = fields.Char(compute='_compute_kpis')

    graph_employee_hours = fields.Text(compute='_compute_kpis')
    graph_task_type = fields.Text(compute='_compute_kpis')
    graph_projects = fields.Text(compute='_compute_kpis')
    graph_type_projects = fields.Text(compute='_compute_kpis')
    graph_employee_work = fields.Text(compute='_compute_kpis')

    is_manager = fields.Boolean(compute='_compute_is_manager')

    @api.depends_context('uid')
    def _compute_is_manager(self):
        allowed = self.env.user.has_group('sygmetiv_company_management.group_company_manager')
        for dash in self:
            dash.is_manager = allowed

    def _scoped_employee(self, employee=None):
        if self.env.user.has_group('sygmetiv_company_management.group_company_manager'):
            return employee
        return self.env.user.employee_id

    @api.model
    def action_open(self, period_start=None, period_end=None, employee=None, include_project_task=True, include_task_request=True):
        today = fields.Date.context_today(self)
        employee = self._scoped_employee(employee)
        dash = self.create({
            'name': self.env._("Performance Dashboard"),
            'company_id': self.env.company.id,
            'employee_id': employee.id if employee else False,
            'include_project_task': include_project_task,
            'include_task_request': include_task_request,
            'period_start': period_start or today.replace(day=1),
            'period_end': period_end or (today + relativedelta(day=31)),
        })
        return {
            'type': 'ir.actions.act_window',
            'name': dash.name,
            'res_model': 'syg.performance.dashboard',
            'res_id': dash.id,
            'view_mode': 'form',
            'views': [(self.env.ref('sygmetiv_company_management.view_syg_performance_dashboard_form').id, 'form')],
            'target': 'current',
            'context': self._dashboard_form_context(),
        }

    def action_refresh(self):
        self.ensure_one()
        return self.action_open(
            self.period_start,
            self.period_end,
            self._scoped_employee(self.employee_id),
            self.include_project_task,
            self.include_task_request,
        )

    def _employee_domain(self):
        domain = [('company_id', '=', self.company_id.id)] if self.company_id else []
        employee = self._scoped_employee(self.employee_id)
        if employee:
            domain.append(('id', '=', employee.id))
        elif not self.env.user.has_group('sygmetiv_company_management.group_company_manager'):
            domain.append(('id', '=', 0))
        return domain

    def _date_bounds(self):
        start = self.period_start
        end = self.period_end
        dt_start = fields.Datetime.to_datetime(start) if start else False
        dt_end = fields.Datetime.to_datetime(end) if end else False
        if dt_end:
            dt_end = dt_end + relativedelta(days=1, seconds=-1)
        return start, end, dt_start, dt_end

    @api.depends('company_id', 'employee_id', 'period_start', 'period_end', 'include_project_task', 'include_task_request')
    def _compute_kpis(self):
        Timesheet = self.env['account.analytic.line']
        Task = self.env['project.task']
        Request = self.env['syg.task.request']
        for dash in self:
            start, end, dt_start, dt_end = dash._date_bounds()
            employees = self.env['hr.employee'].search(dash._employee_domain())
            emp_ids = employees.ids
            ts_domain = [('project_id', '!=', False)]
            task_domain = []
            req_domain = [('state', '!=', 'cancelled')]
            if dash.company_id:
                ts_domain.append(('company_id', '=', dash.company_id.id))
                task_domain.append(('company_id', '=', dash.company_id.id))
                req_domain.append(('company_id', '=', dash.company_id.id))
            if emp_ids:
                ts_domain.append(('employee_id', 'in', emp_ids))
                user_ids = employees.mapped('user_id').ids
                if user_ids:
                    task_domain.append(('user_ids', 'in', user_ids))
                req_domain.append(('employee_id', 'in', emp_ids))
            if start and end:
                ts_domain += [('date', '>=', start), ('date', '<=', end)]
                req_domain += [('planned_date', '>=', dt_start), ('planned_date', '<=', dt_end)]
            timesheets = Timesheet.search(ts_domain)
            requests = Request.search(req_domain)
            tasks = Task.search(task_domain)
            ts_hours = sum(timesheets.mapped('unit_amount'))
            open_request_hours = sum(
                requests.filtered(lambda rec: not rec.timesheet_id).mapped('time_spent')
            )
            dash.timesheet_hours = ts_hours
            dash.request_hours = open_request_hours
            dash.hours_worked = ts_hours + open_request_hours
            dash.employee_count = len(employees)
            dash.project_count = len((tasks.mapped('project_id') | requests.mapped('project_id')).filtered('id'))
            dash.task_count = len(tasks)
            dash.request_count = len(requests)
            types = tasks.mapped('syg_task_type_id') | requests.mapped('syg_task_type_id')
            dash.task_type_count = len(types)
            dash.d_period = '%s – %s' % (
                start.strftime('%d %b %Y') if start else '',
                end.strftime('%d %b %Y') if end else '',
            )
            dash.d_hours = dash._hours_label(dash.hours_worked)
            dash.d_timesheet = dash._hours_label(ts_hours)
            dash.d_request_hours = dash._hours_label(open_request_hours)
            dash.d_employees = str(dash.employee_count)
            dash.d_projects = str(dash.project_count)
            dash.d_tasks = str(dash.task_count)
            dash.d_requests = str(dash.request_count)
            dash.d_types = str(dash.task_type_count)

            graph_timesheets = timesheets if dash.include_project_task else Timesheet.browse()
            graph_tasks = tasks if dash.include_project_task else Task.browse()
            graph_requests = requests if dash.include_task_request else Request.browse()

            hours_by_emp = defaultdict(float)
            for line in graph_timesheets:
                if line.employee_id:
                    hours_by_emp[line.employee_id] += line.unit_amount or 0.0
            for rec in graph_requests.filtered(lambda r: not r.timesheet_id):
                if rec.employee_id:
                    hours_by_emp[rec.employee_id] += rec.time_spent or 0.0
            emp_values = [
                {'label': emp.name, 'value': round(hours, 1), 'type': 'past'}
                for emp, hours in sorted(hours_by_emp.items(), key=lambda item: item[1], reverse=True)[:12]
            ]
            type_hours = defaultdict(float)
            for line in graph_timesheets:
                ttype = line.task_id.syg_task_type_id
                type_hours[ttype.name if ttype else dash.env._("No type")] += line.unit_amount or 0.0
            for rec in graph_requests.filtered(lambda r: not r.timesheet_id):
                type_hours[rec.syg_task_type_id.name if rec.syg_task_type_id else dash.env._("No type")] += rec.time_spent or 0.0
            type_values = [
                {'label': name, 'value': round(hours, 1), 'type': 'past'}
                for name, hours in sorted(type_hours.items(), key=lambda item: item[1], reverse=True)[:12]
            ]
            project_hours = defaultdict(float)
            for line in graph_timesheets:
                project_hours[line.project_id.display_name or dash.env._("No project")] += line.unit_amount or 0.0
            for rec in graph_requests.filtered(lambda r: not r.timesheet_id and r.project_id):
                project_hours[rec.project_id.display_name] += rec.time_spent or 0.0
            project_values = [
                {'label': name, 'value': round(hours, 1), 'type': 'past'}
                for name, hours in sorted(project_hours.items(), key=lambda item: item[1], reverse=True)[:12]
            ]
            projects_by_type = defaultdict(set)
            for task in graph_tasks:
                if task.project_id:
                    label = task.syg_task_type_id.name if task.syg_task_type_id else dash.env._("No type")
                    projects_by_type[label].add(task.project_id.id)
            for rec in graph_requests:
                if rec.project_id:
                    label = rec.syg_task_type_id.name if rec.syg_task_type_id else dash.env._("No type")
                    projects_by_type[label].add(rec.project_id.id)
            type_project_values = [
                {'label': name, 'value': len(project_ids), 'type': 'past'}
                for name, project_ids in sorted(projects_by_type.items(), key=lambda item: len(item[1]), reverse=True)[:12]
            ]
            dash.graph_employee_hours = dash._graph_json(emp_values, dash.env._("Hours by employee"))
            dash.graph_task_type = dash._graph_json(type_values, dash.env._("Hours by task type"))
            dash.graph_projects = dash._graph_json(project_values, dash.env._("Hours by project"))
            dash.graph_type_projects = dash._graph_json(type_project_values, dash.env._("Projects by task type"))
            dash.graph_employee_work = dash._employee_project_type_graph(graph_timesheets, graph_requests)

    def _employee_project_type_graph(self, timesheets, requests):
        """Hours on each project, from tasks and task requests, stacked by task type."""
        buckets = defaultdict(lambda: defaultdict(float))

        def add(employee, project, task_type, hours):
            hours = hours or 0.0
            if not hours or not project:
                return
            employee_name = employee.name if employee else self.env._("Unassigned")
            type_name = task_type.name if task_type else self.env._("No type")
            project_name = project.display_name or self.env._("No project")
            buckets[(employee_name, project_name)][type_name] += hours

        for line in timesheets:
            add(line.employee_id, line.project_id, line.task_id.syg_task_type_id, line.unit_amount)
        for rec in requests.filtered(lambda request: not request.timesheet_id):
            add(rec.employee_id, rec.project_id, rec.syg_task_type_id, rec.time_spent)

        ranked = sorted(
            buckets.items(),
            key=lambda item: sum(item[1].values()),
            reverse=True,
        )[:12]
        type_names = []
        seen = set()
        for _key, hours_by_type in ranked:
            for type_name in hours_by_type:
                if type_name not in seen:
                    seen.add(type_name)
                    type_names.append(type_name)
        series = []
        for type_name in type_names:
            values = []
            for (employee_name, project_name), hours_by_type in ranked:
                values.append({
                    'label': '%s · %s' % (employee_name, project_name),
                    'value': round(hours_by_type.get(type_name, 0.0), 1),
                    'type': 'past',
                })
            series.append((type_name, values))
        return self._graph_series_json(series)

    def action_open_timesheets(self):
        start, end, _dt_start, _dt_end = self._date_bounds()
        domain = [('project_id', '!=', False)]
        if self.employee_id:
            domain.append(('employee_id', '=', self.employee_id.id))
        if start and end:
            domain += [('date', '>=', start), ('date', '<=', end)]
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Timesheets"),
            'res_model': 'account.analytic.line',
            'view_mode': 'list,form',
            'domain': domain,
        }

    def action_open_requests(self):
        domain = [('state', '!=', 'cancelled')]
        if self.employee_id:
            domain.append(('employee_id', '=', self.employee_id.id))
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Task Requests"),
            'res_model': 'syg.task.request',
            'view_mode': 'list,form',
            'domain': domain,
        }

    def action_open_tasks(self):
        domain = []
        if self.employee_id and self.employee_id.user_id:
            domain.append(('user_ids', 'in', self.employee_id.user_id.ids))
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Tasks"),
            'res_model': 'project.task',
            'view_mode': 'list,form',
            'domain': domain,
        }

    def action_open_projects(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Projects"),
            'res_model': 'project.project',
            'view_mode': 'kanban,list,form',
        }
