# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class SygOvertimeRequest(models.Model):
    _name = 'syg.overtime.request'
    _description = 'Overtime Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'syg.notify.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(required=True, copy=False, default='New', tracking=True)
    employee_id = fields.Many2one(
        'hr.employee',
        required=True,
        default=lambda self: self.env.user.employee_id,
        tracking=True,
        index=True,
    )
    user_id = fields.Many2one(related='employee_id.user_id', store=True)
    manager_id = fields.Many2one(
        related='employee_id.parent_id',
        store=True,
        string="Manager",
    )
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    company_id = fields.Many2one(
        related='employee_id.company_id',
        store=True,
        index=True,
    )
    date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    hours = fields.Float(required=True, tracking=True)
    reason = fields.Text(required=True)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='draft',
        tracking=True,
        copy=False,
        index=True,
    )
    project_id = fields.Many2one('project.project', string="Project")
    task_id = fields.Many2one(
        'project.task',
        string="Task",
        domain="[('project_id', '=', project_id)]",
    )
    approved_by = fields.Many2one('res.users', readonly=True, copy=False)
    approved_date = fields.Datetime(readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('syg.overtime.request') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if rec.hours <= 0:
                raise UserError(self.env._("Overtime hours must be greater than zero."))
            rec.state = 'submitted'
            rec.message_post(body=self.env._("Overtime submitted."))
            recipients = rec.manager_id.user_id
            if not recipients:
                group = self.env.ref('hr.group_hr_user', raise_if_not_found=False)
                recipients = group.all_user_ids if group else self.env['res.users']
            rec._syg_notify_users(
                recipients,
                self.env._("Overtime to approve"),
                self.env._(
                    "%(employee)s requested %(hours)s hours on %(date)s.",
                    employee=rec.employee_id.name,
                    hours=rec.hours,
                    date=rec.date,
                ),
                'sygmetiv_company_management.mail_template_overtime_request',
            )
        return True

    def action_approve(self):
        if not self.env.user.has_group('sygmetiv_company_management.group_company_manager'):
            raise UserError(self.env._("Only a Sygmetiv manager can approve overtime."))
        for rec in self:
            rec.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })
            rec.message_post(body=self.env._("Overtime approved."))
            if rec.user_id:
                rec._syg_notify_users(
                    rec.user_id,
                    self.env._("Overtime approved"),
                    self.env._("%s has been approved.", rec.name),
                    'sygmetiv_company_management.mail_template_overtime_done',
                )
        return True

    def action_reject(self):
        if not self.env.user.has_group('sygmetiv_company_management.group_company_manager'):
            raise UserError(self.env._("Only a Sygmetiv manager can reject overtime."))
        for rec in self:
            rec.state = 'rejected'
            rec.message_post(body=self.env._("Overtime rejected."))
            if rec.user_id:
                rec._syg_notify_users(
                    rec.user_id,
                    self.env._("Overtime rejected"),
                    self.env._("%s was rejected.", rec.name),
                    'sygmetiv_company_management.mail_template_overtime_done',
                )
        return True

    def action_draft(self):
        self.write({
            'state': 'draft',
            'approved_by': False,
            'approved_date': False,
        })
        return True
