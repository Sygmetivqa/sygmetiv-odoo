# -*- coding: utf-8 -*-

import secrets
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command


class SygKpiEvaluationConfigLine(models.Model):
    _name = 'syg.kpi.evaluation.config.line'
    _description = 'KPI Evaluation Evaluator'
    _order = 'id'

    config_id = fields.Many2one('syg.kpi.evaluation.config', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string="Evaluator", required=True)
    criteria_ids = fields.Many2many('syg.kpi.criteria', string="Criteria", required=True)
    company_id = fields.Many2one(related='config_id.company_id', store=True)

    _evaluator_unique = models.Constraint(
        'unique(config_id, user_id)',
        'Each evaluator can be added only once.',
    )


class SygKpiEvaluationConfig(models.Model):
    _name = 'syg.kpi.evaluation.config'
    _description = 'KPI Evaluation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'employee_id, evaluation_type'

    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True, index=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True, index=True)
    evaluation_type = fields.Selection(
        [
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly'),
        ],
        required=True,
        default='monthly',
        tracking=True,
    )
    grace_days = fields.Integer(
        string="Grace Period (days)",
        default=7,
        help="Days after the period ends during which evaluators can still enter scores.",
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
        ],
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    line_ids = fields.One2many('syg.kpi.evaluation.config.line', 'config_id', string="Evaluators")
    active = fields.Boolean(default=True)
    evaluation_ids = fields.One2many('syg.kpi.evaluation', 'config_id', string="Generated Evaluations")
    evaluation_count = fields.Integer(compute='_compute_evaluation_count')

    _employee_type_unique = models.Constraint(
        'unique(employee_id, evaluation_type)',
        'This employee already has a KPI evaluation of that type.',
    )

    @api.depends('employee_id', 'evaluation_type')
    def _compute_name(self):
        labels = dict(self._fields['evaluation_type'].selection)
        for rec in self:
            kind = labels.get(rec.evaluation_type, '')
            who = rec.employee_id.name or self.env._("Employee")
            rec.name = ' '.join(part for part in (who, kind) if part)

    @api.depends('evaluation_ids')
    def _compute_evaluation_count(self):
        for rec in self:
            rec.evaluation_count = len(rec.evaluation_ids)

    @api.constrains('grace_days', 'line_ids')
    def _check_config(self):
        for rec in self:
            if rec.grace_days < 0:
                raise ValidationError(self.env._("Grace period cannot be negative."))

    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(self.env._("Only a draft KPI evaluation can be submitted."))
            if not rec.employee_id:
                raise UserError(self.env._("Select the employee to evaluate."))
            if not rec.line_ids:
                raise UserError(self.env._("Add at least one evaluator."))
            if any(not line.criteria_ids for line in rec.line_ids):
                raise UserError(self.env._("Each evaluator needs at least one criteria."))
        self.write({'state': 'submitted'})
        created = self._generate_due_evaluations()
        created._notify_evaluators()
        for rec in self:
            rec.message_post(body=self.env._(
                "KPI evaluation submitted. Period records are created automatically. Evaluators receive an email with a link to enter scores."
            ))
        return True

    def action_reset_draft(self):
        if not self.env.user.has_group('sygmetiv_kpi.group_kpi_manager'):
            raise UserError(self.env._("Only a KPI manager can reset an evaluation."))
        self.filtered(lambda rec: rec.state == 'submitted').write({'state': 'draft'})
        return True

    def action_open_evaluations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("KPI Evaluations"),
            'res_model': 'syg.kpi.evaluation',
            'view_mode': 'list,form',
            'domain': [('config_id', '=', self.id)],
            'context': {'create': False},
        }

    def _previous_period(self, today=None):
        self.ensure_one()
        today = today or fields.Date.context_today(self)
        if self.evaluation_type == 'weekly':
            this_monday = today - timedelta(days=today.weekday())
            start = this_monday - timedelta(days=7)
            end = this_monday - timedelta(days=1)
        elif self.evaluation_type == 'yearly':
            start = today.replace(year=today.year - 1, month=1, day=1)
            end = today.replace(year=today.year - 1, month=12, day=31)
        else:
            first_this_month = today.replace(day=1)
            end = first_this_month - timedelta(days=1)
            start = end.replace(day=1)
        return start, end

    def _generate_due_evaluations(self):
        Evaluation = self.env['syg.kpi.evaluation']
        created = Evaluation
        for config in self.filtered(lambda rec: rec.state == 'submitted' and rec.active and rec.employee_id.active):
            start, end = config._previous_period()
            existing = Evaluation.search([
                ('employee_id', '=', config.employee_id.id),
                ('evaluation_type', '=', config.evaluation_type),
                ('date_start', '=', start),
                ('date_end', '=', end),
            ], limit=1)
            if existing:
                continue
            created |= config._create_period_evaluation(start, end)
        return created

    def _create_period_evaluation(self, start, end):
        self.ensure_one()
        line_commands = []
        score_commands = []
        for line in self.line_ids:
            line_commands.append(Command.create({
                'user_id': line.user_id.id,
                'criteria_ids': [Command.set(line.criteria_ids.ids)],
            }))
            for criteria in line.criteria_ids:
                score_commands.append(Command.create({
                    'user_id': line.user_id.id,
                    'criteria_id': criteria.id,
                    'score': 0.0,
                }))
        return self.env['syg.kpi.evaluation'].create({
            'employee_id': self.employee_id.id,
            'evaluation_type': self.evaluation_type,
            'date_start': start,
            'date_end': end,
            'grace_days': self.grace_days,
            'config_id': self.id,
            'state': 'submitted',
            'line_ids': line_commands,
            'score_line_ids': score_commands,
        })

    @api.model
    def _cron_generate_evaluations(self):
        configs = self.search([('state', '=', 'submitted'), ('active', '=', True)])
        created = configs._generate_due_evaluations()
        created._notify_evaluators()


class SygKpiEvaluatorAccess(models.Model):
    _name = 'syg.kpi.evaluator.access'
    _description = 'KPI Evaluator Portal Access'

    user_id = fields.Many2one('res.users', string="Evaluator", required=True)
    evaluation_ids = fields.Many2many(
        'syg.kpi.evaluation',
        'syg_kpi_access_evaluation_rel',
        'access_id',
        'evaluation_id',
        string="Evaluations",
    )
    token = fields.Char(required=True, copy=False, index=True)
    sent = fields.Boolean(default=False)

    _token_unique = models.Constraint(
        'unique(token)',
        'The portal token must be unique.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault('token', secrets.token_urlsafe(32))
        return super().create(vals_list)

    def _get_score_portal_url(self):
        self.ensure_one()
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')
        return '%s/kpi/score?token=%s' % (base, self.token)
