# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


class SygPerformanceGoal(models.Model):
    _name = 'syg.performance.goal'
    _description = 'Performance Goal'
    _inherit = ['mail.thread']
    _order = 'deadline, id'

    name = fields.Char(required=True, tracking=True)
    employee_id = fields.Many2one(
        'hr.employee',
        required=True,
        default=lambda self: self.env.user.employee_id,
        index=True,
        tracking=True,
    )
    manager_id = fields.Many2one(related='employee_id.parent_id', store=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True, index=True)
    review_id = fields.Many2one('syg.performance.review', ondelete='set null')
    project_id = fields.Many2one('project.project')
    task_id = fields.Many2one('project.task', domain="[('project_id', '=', project_id)]")
    deadline = fields.Date()
    progress = fields.Float(string="Progress (%)", default=0.0)
    state = fields.Selection(
        [
            ('open', 'In Progress'),
            ('done', 'Achieved'),
            ('cancel', 'Cancelled'),
        ],
        default='open',
        tracking=True,
    )
    description = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group('sygmetiv_company_management.group_company_manager'):
            review_ids = [vals.get('review_id') for vals in vals_list if vals.get('review_id')]
            reviews = self.env['syg.performance.review'].browse(review_ids)
            if any(review.state != 'draft' for review in reviews):
                raise AccessError(self.env._("You cannot change a review after it is submitted."))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.user.has_group('sygmetiv_company_management.group_company_manager'):
            locked = self.filtered(lambda goal: goal.review_id and goal.review_id.state != 'draft')
            if locked:
                raise AccessError(self.env._("You cannot change a review after it is submitted."))
        return super().write(vals)

    def action_done(self):
        self.write({'state': 'done', 'progress': 100.0})
        return True

    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True


class SygPerformanceReview(models.Model):
    _name = 'syg.performance.review'
    _description = 'Performance Review'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'syg.notify.mixin']
    _order = 'date_end desc, id desc'

    name = fields.Char(required=True, copy=False, default='New', tracking=True)
    employee_id = fields.Many2one(
        'hr.employee',
        required=True,
        default=lambda self: self.env.user.employee_id,
        tracking=True,
        index=True,
    )
    manager_id = fields.Many2one(
        'hr.employee',
        related='employee_id.parent_id',
        store=True,
    )
    company_id = fields.Many2one(related='employee_id.company_id', store=True, index=True)
    date_start = fields.Date(required=True)
    date_end = fields.Date(required=True)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Self Assessment'),
            ('reviewed', 'Manager Review'),
            ('done', 'Done'),
        ],
        default='draft',
        tracking=True,
        copy=False,
        index=True,
    )
    quality_score = fields.Integer(string="Quality (1-5)", default=3)
    delivery_score = fields.Integer(string="Delivery (1-5)", default=3)
    teamwork_score = fields.Integer(string="Teamwork (1-5)", default=3)
    timesheet_score = fields.Integer(string="Time Discipline (1-5)", default=3)
    overall_score = fields.Float(compute='_compute_overall_score', store=True)
    employee_comment = fields.Text()
    manager_comment = fields.Text()
    goal_ids = fields.One2many('syg.performance.goal', 'review_id', string="Goals")
    timesheet_hours = fields.Float(compute='_compute_period_metrics', store=True)
    overtime_hours = fields.Float(compute='_compute_period_metrics', store=True)
    task_count = fields.Integer(compute='_compute_period_metrics', store=True)
    is_manager = fields.Boolean(compute='_compute_is_manager')

    @api.depends_context('uid')
    def _compute_is_manager(self):
        allowed = self.env.user.has_group('sygmetiv_company_management.group_company_manager')
        for rec in self:
            rec.is_manager = allowed

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        today = fields.Date.context_today(self)
        defaults.setdefault('date_start', today.replace(day=1))
        defaults.setdefault('date_end', today + relativedelta(day=31))
        return defaults

    @api.depends('quality_score', 'delivery_score', 'teamwork_score', 'timesheet_score')
    def _compute_overall_score(self):
        for rec in self:
            rec.overall_score = (
                rec.quality_score + rec.delivery_score + rec.teamwork_score + rec.timesheet_score
            ) / 4.0

    @api.depends('employee_id', 'date_start', 'date_end')
    def _compute_period_metrics(self):
        Task = self.env['project.task']
        Timesheet = self.env['account.analytic.line']
        Overtime = self.env['syg.overtime.request']
        for rec in self:
            if not (rec.employee_id and rec.date_start and rec.date_end):
                rec.timesheet_hours = 0.0
                rec.overtime_hours = 0.0
                rec.task_count = 0
                continue
            user = rec.employee_id.user_id
            rec.timesheet_hours = sum(Timesheet.search([
                ('employee_id', '=', rec.employee_id.id),
                ('date', '>=', rec.date_start),
                ('date', '<=', rec.date_end),
                ('project_id', '!=', False),
            ]).mapped('unit_amount'))
            rec.overtime_hours = sum(Overtime.search([
                ('employee_id', '=', rec.employee_id.id),
                ('date', '>=', rec.date_start),
                ('date', '<=', rec.date_end),
                ('state', '=', 'approved'),
            ]).mapped('hours'))
            rec.task_count = Task.search_count([
                ('user_ids', 'in', user.ids),
                ('date_last_stage_update', '>=', rec.date_start),
                ('date_last_stage_update', '<=', rec.date_end),
            ]) if user else 0

    @api.constrains('quality_score', 'delivery_score', 'teamwork_score', 'timesheet_score')
    def _check_scores(self):
        for rec in self:
            for score in (rec.quality_score, rec.delivery_score, rec.teamwork_score, rec.timesheet_score):
                if score < 1 or score > 5:
                    raise UserError(self.env._("Scores must be between 1 and 5."))

    @api.model_create_multi
    def create(self, vals_list):
        manager = self.env.user.has_group('sygmetiv_company_management.group_company_manager')
        employee = self.env.user.employee_id
        for vals in vals_list:
            if not manager:
                vals['employee_id'] = employee.id
                vals['state'] = 'draft'
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('syg.performance.review') or 'New'
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.user.has_group('sygmetiv_company_management.group_company_manager'):
            if any(rec.state != 'draft' for rec in self):
                raise AccessError(self.env._("You cannot change a review after it is submitted."))
            employee = self.env.user.employee_id
            if vals.get('employee_id') and vals['employee_id'] != employee.id:
                raise AccessError(self.env._("You can only submit your own review."))
        return super().write(vals)

    def action_submit(self):
        if not self.env.user.has_group('sygmetiv_company_management.group_company_manager'):
            if any(rec.employee_id.user_id != self.env.user for rec in self):
                raise AccessError(self.env._("You can only submit your own review."))
        self.write({'state': 'submitted'})
        for rec in self:
            manager_user = rec.sudo().manager_id.user_id
            if manager_user:
                rec._syg_notify_users(
                    manager_user,
                    self.env._("Performance review submitted"),
                    self.env._("%s submitted a self assessment.", rec.employee_id.name),
                    'sygmetiv_company_management.mail_template_performance_review',
                )
        return True

    def action_manager_review(self):
        self.write({'state': 'reviewed'})
        return True

    def action_done(self):
        self.write({'state': 'done'})
        for rec in self:
            if rec.employee_id.user_id:
                rec._syg_notify_users(
                    rec.employee_id.user_id,
                    self.env._("Performance review completed"),
                    self.env._(
                        "%(review)s overall score: %(score)s / 5.",
                        review=rec.name,
                        score=rec.overall_score,
                    ),
                    'sygmetiv_company_management.mail_template_performance_review',
                )
        return True

    def action_draft(self):
        self.write({'state': 'draft'})
        return True
