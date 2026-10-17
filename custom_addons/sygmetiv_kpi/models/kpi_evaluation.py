# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command


class SygKpiEvaluationLine(models.Model):
    _name = 'syg.kpi.evaluation.line'
    _description = 'KPI Evaluator'
    _order = 'id'

    evaluation_id = fields.Many2one('syg.kpi.evaluation', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string="Evaluator", required=True)
    criteria_ids = fields.Many2many('syg.kpi.criteria', string="Criteria", required=True)
    company_id = fields.Many2one(related='evaluation_id.company_id', store=True)

    _evaluator_unique = models.Constraint(
        'unique(evaluation_id, user_id)',
        'Each evaluator can be added only once on an evaluation.',
    )


class SygKpiScoreLine(models.Model):
    _name = 'syg.kpi.score.line'
    _description = 'KPI Score'
    _order = 'user_id, criteria_id'

    evaluation_id = fields.Many2one('syg.kpi.evaluation', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string="Evaluator", required=True)
    criteria_id = fields.Many2one('syg.kpi.criteria', string="Criteria", required=True)
    max_score = fields.Float(related='criteria_id.max_score')
    score = fields.Float()
    can_edit_score = fields.Boolean(compute='_compute_can_edit_score')
    company_id = fields.Many2one(related='evaluation_id.company_id', store=True)

    _score_unique = models.Constraint(
        'unique(evaluation_id, user_id, criteria_id)',
        'This evaluator already has a score for that criteria.',
    )

    @api.depends('user_id')
    def _compute_can_edit_score(self):
        manager = self.env.user.has_group('sygmetiv_kpi.group_kpi_manager')
        for line in self:
            subject = line.evaluation_id.employee_id.user_id == self.env.user
            line.can_edit_score = manager or (line.user_id == self.env.user and not subject)

    @api.constrains('score', 'criteria_id')
    def _check_score(self):
        for line in self:
            if line.score < 0 or (line.criteria_id and line.score > line.criteria_id.max_score):
                raise ValidationError(self.env._(
                    "Score for %s must be between 0 and %s.",
                    line.criteria_id.display_name,
                    line.criteria_id.max_score,
                ))

    def write(self, vals):
        if not self.env.user.has_group('sygmetiv_kpi.group_kpi_manager'):
            if any(line.evaluation_id.employee_id.user_id == self.env.user for line in self):
                raise AccessError(self.env._("You can view your evaluation scores but not change them."))
            if set(vals) - {'score'}:
                raise AccessError(self.env._("You can only enter your own score."))
            if any(line.user_id != self.env.user for line in self):
                raise AccessError(self.env._("You can only score the criteria assigned to you."))
            if any(line.evaluation_id.state != 'submitted' for line in self):
                raise AccessError(self.env._("Scores can be entered after the evaluation is submitted."))
        return super().write(vals)


class SygKpiEvaluation(models.Model):
    _name = 'syg.kpi.evaluation'
    _description = 'KPI Evaluation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True, index=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True, index=True)
    config_id = fields.Many2one('syg.kpi.evaluation.config', string="KPI Setup", ondelete='set null', copy=False, index=True)
    evaluation_type = fields.Selection(
        [
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly'),
        ],
        required=True,
        default='monthly',
        tracking=True,
    )
    date_start = fields.Date(required=True, default=lambda self: self._period_bounds('monthly')[0], tracking=True)
    date_end = fields.Date(required=True, default=lambda self: self._period_bounds('monthly')[1], tracking=True)
    grace_days = fields.Integer(string="Grace Period (days)", default=7)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('done', 'Done'),
        ],
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    line_ids = fields.One2many('syg.kpi.evaluation.line', 'evaluation_id', string="Evaluators")
    score_line_ids = fields.One2many('syg.kpi.score.line', 'evaluation_id', string="Scores", copy=False)
    net_score = fields.Float(compute='_compute_net_score', store=True)
    max_score = fields.Float(compute='_compute_net_score', store=True)
    status_id = fields.Many2one('syg.kpi.status', string="Score Band", compute='_compute_status', store=True)
    is_manager = fields.Boolean(compute='_compute_is_manager')

    @api.depends('employee_id', 'evaluation_type', 'date_start')
    def _compute_name(self):
        labels = dict(self._fields['evaluation_type'].selection)
        for rec in self:
            kind = labels.get(rec.evaluation_type, '')
            who = rec.employee_id.name or self.env._("Employee")
            when = rec.date_start.strftime('%b %Y') if rec.date_start else ''
            rec.name = ' '.join(part for part in (who, kind, when) if part)

    @api.depends('score_line_ids.score', 'score_line_ids.criteria_id.max_score')
    def _compute_net_score(self):
        for rec in self:
            rec.net_score = sum(rec.score_line_ids.mapped('score'))
            rec.max_score = sum(rec.score_line_ids.mapped('max_score'))

    @api.depends('net_score', 'company_id')
    def _compute_status(self):
        Status = self.env['syg.kpi.status']
        for rec in self:
            rec.status_id = Status.status_for_score(rec.net_score, rec.company_id) if rec.score_line_ids else False

    def _compute_is_manager(self):
        manager = self.env.user.has_group('sygmetiv_kpi.group_kpi_manager')
        for rec in self:
            rec.is_manager = manager

    @api.model
    def _period_bounds(self, kind, today=None):
        today = today or fields.Date.context_today(self)
        if kind == 'yearly':
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
        elif kind == 'quarterly':
            quarter = (today.month - 1) // 3
            start = today.replace(month=quarter * 3 + 1, day=1)
            end = start + relativedelta(months=3, days=-1)
        elif kind == 'weekly':
            start = today - relativedelta(days=today.weekday())
            end = start + relativedelta(days=6)
        else:
            start = today.replace(day=1)
            end = start + relativedelta(months=1, days=-1)
        return start, end

    @api.onchange('evaluation_type')
    def _onchange_evaluation_type(self):
        if self.evaluation_type and self.state == 'draft':
            self.date_start, self.date_end = self._period_bounds(self.evaluation_type)

    @api.constrains('date_start', 'date_end', 'line_ids')
    def _check_evaluation(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end < rec.date_start:
                raise ValidationError(self.env._("Period end must be on or after the start."))

    def action_submit(self):
        template = self.env.ref('sygmetiv_kpi.mail_template_kpi_evaluation', raise_if_not_found=False)
        for rec in self:
            if rec.state != 'draft':
                raise UserError(self.env._("Only a draft evaluation can be submitted."))
            if not rec.line_ids:
                raise UserError(self.env._("Add at least one evaluator."))
            if any(not line.criteria_ids for line in rec.line_ids):
                raise UserError(self.env._("Each evaluator needs at least one criteria."))
            start, end = rec._period_bounds(rec.evaluation_type)
            commands = [Command.clear()]
            for line in rec.line_ids:
                for criteria in line.criteria_ids:
                    commands.append(Command.create({
                        'user_id': line.user_id.id,
                        'criteria_id': criteria.id,
                        'score': 0.0,
                    }))
            rec.write({
                'date_start': rec.date_start or start,
                'date_end': rec.date_end or end,
                'state': 'submitted',
                'score_line_ids': commands,
            })
            rec._send_evaluator_emails(template)
        return True

    def _send_evaluator_emails(self, template):
        self.ensure_one()
        if not template:
            return
        for user in self.line_ids.mapped('user_id'):
            email = user.email or (user.partner_id.email if user.partner_id else False)
            if not email:
                self.message_post(body=self.env._("No email address for %s.", user.display_name))
                continue
            template.send_mail(self.id, force_send=True, email_values={'email_to': email})
        self.message_post(body=self.env._("Evaluation submitted. Evaluators were emailed to enter scores."))

    def _notify_evaluators(self):
        if not self:
            return
        Access = self.env['syg.kpi.evaluator.access'].sudo()
        template = self.env.ref('sygmetiv_kpi.mail_template_kpi_evaluator_portal', raise_if_not_found=False)
        for user in self.mapped('line_ids.user_id'):
            evaluations = self.filtered(lambda rec: user in rec.line_ids.user_id)
            access = Access.create({
                'user_id': user.id,
                'evaluation_ids': [Command.set(evaluations.ids)],
            })
            email = user.email or (user.partner_id.email if user.partner_id else False)
            if not email or not template:
                for evaluation in evaluations:
                    evaluation.message_post(body=self.env._("No email address for %s.", user.display_name))
                continue
            try:
                template.send_mail(access.id, force_send=True)
                access.sent = True
            except Exception:
                for evaluation in evaluations:
                    evaluation.message_post(body=self.env._(
                        "The evaluation was created, but the score email to %s could not be sent.",
                        user.display_name,
                    ))

    def action_done(self):
        drafts = self.filtered(lambda rec: rec.state != 'submitted')
        if drafts:
            raise UserError(self.env._("Mark done only after the evaluation is submitted."))
        self.write({'state': 'done'})
        return True

    def action_reset_draft(self):
        if not self.env.user.has_group('sygmetiv_kpi.group_kpi_manager'):
            raise AccessError(self.env._("Only a KPI manager can reset an evaluation."))
        self.write({'state': 'draft', 'score_line_ids': [Command.clear()]})
        return True

    def write(self, vals):
        if not self.env.user.has_group('sygmetiv_kpi.group_kpi_manager'):
            if any(rec.employee_id.user_id == self.env.user for rec in self):
                raise AccessError(self.env._("You can view your evaluation scores but not change them."))
            if set(vals) - {'score_line_ids'}:
                raise AccessError(self.env._("You can only enter scores on this evaluation."))
        return super().write(vals)
