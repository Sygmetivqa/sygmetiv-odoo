# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class SygTaskRequest(models.Model):
    _name = 'syg.task.request'
    _description = 'Task Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'syg.meeting.details.mixin']
    _order = 'planned_date asc, id desc'

    name = fields.Char(required=True, tracking=True)
    employee_id = fields.Many2one(
        'hr.employee',
        required=True,
        default=lambda self: self.env.user.employee_id,
        tracking=True,
        index=True,
    )
    user_id = fields.Many2one(related='employee_id.user_id', store=True)
    project_id = fields.Many2one('project.project', tracking=True)
    syg_attendee_ids = fields.Many2many(
        'hr.employee',
        'syg_task_request_attendee_rel',
        'request_id',
        'employee_id',
        string="Attendees",
    )
    partner_id = fields.Many2one(
        'res.partner',
        string="Customer",
        tracking=True,
        index=True,
    )
    vendor_id = fields.Many2one(
        'res.partner',
        string="Vendor",
        domain="[('supplier_rank', '>', 0)]",
        tracking=True,
        index=True,
    )
    planned_date = fields.Datetime(string="When", default=fields.Datetime.now, tracking=True)
    deadline = fields.Datetime(tracking=True)
    estimated_hours = fields.Float(tracking=True)
    time_spent = fields.Float(string="Hours Worked", tracking=True)
    description = fields.Html()
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('converted', 'Task Created'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        required=True,
        tracking=True,
        copy=False,
        index=True,
    )
    task_id = fields.Many2one('project.task', readonly=True, copy=False)
    task_link_name = fields.Char(related='task_id.display_name', string="Project Task")
    timesheet_id = fields.Many2one('account.analytic.line', readonly=True, copy=False)
    can_create_task = fields.Boolean(compute='_compute_can_create_task')
    company_id = fields.Many2one(
        related='employee_id.company_id',
        store=True,
        index=True,
    )

    @api.onchange('syg_task_type_id')
    def _onchange_syg_task_type_meeting(self):
        if self.syg_task_type_id.is_meeting and self.employee_id and not self.syg_attendee_ids:
            self.syg_attendee_ids = self.employee_id

    @api.constrains('syg_task_type_id', 'syg_attendee_ids', 'syg_role', 'syg_presentation_time')
    def _check_syg_meeting_details(self):
        self._check_syg_meeting_values()

    @api.depends('project_id', 'state', 'task_id')
    def _compute_can_create_task(self):
        for rec in self:
            rec.can_create_task = bool(
                rec.project_id and not rec.task_id and rec.state == 'submitted'
            )

    def action_submit(self):
        self.filtered(lambda rec: rec.state == 'draft').write({'state': 'submitted'})

    def action_cancel(self):
        self.filtered(lambda rec: rec.state in ('draft', 'submitted')).write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.filtered(lambda rec: rec.state == 'cancelled').write({'state': 'draft'})

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('active_model') == 'project.task':
            raise UserError(self.env._(
                "A task request cannot be created from a project task. Create the project task from the task request."
            ))
        return super().create(vals_list)

    @api.model
    def name_create(self, name):
        if self.env.context.get('active_model') == 'project.task':
            raise UserError(self.env._(
                "A task request cannot be created from a project task. Create the project task from the task request."
            ))
        return super().name_create(name)

    def action_create_task(self):
        Task = self.env['project.task']
        created = self.env['project.task']
        for rec in self:
            if rec.task_id:
                created |= rec.task_id
                continue
            if rec.state != 'submitted':
                raise UserError(self.env._("Submit the request before creating the task."))
            if not rec.project_id:
                raise UserError(self.env._("Set a project before creating the task."))
            values = {
                'name': rec.name,
                'project_id': rec.project_id.id,
                'description': rec.description or False,
                'date_deadline': rec.deadline or rec.planned_date,
                'syg_task_type_id': rec.syg_task_type_id.id,
                'syg_attendee_ids': [Command.set(rec.syg_attendee_ids.ids)],
                'syg_role': rec.syg_role,
                'syg_presentation_time': rec.syg_presentation_time,
                'partner_id': rec.partner_id.id,
                'syg_vendor_id': rec.vendor_id.id,
                'syg_task_request_id': rec.id,
            }
            if rec.user_id:
                values['user_ids'] = [Command.set(rec.user_id.ids)]
            if rec.estimated_hours:
                values['allocated_hours'] = rec.estimated_hours
            task = Task.create(values)
            timesheet = rec._create_timesheet(task)
            rec.write({
                'task_id': task.id,
                'timesheet_id': timesheet.id if timesheet else False,
                'state': 'converted',
            })
            rec.message_post(body=self.env._("Task %s created.", task.display_name))
            created |= task
        if len(created) == 1:
            return self._open_record('project.task', created.id, self.env._("Task"))
        return True

    def _create_timesheet(self, task):
        self.ensure_one()
        hours = self.time_spent or 0.0
        if not hours:
            return self.env['account.analytic.line']
        values = {
            'name': self.name,
            'project_id': self.project_id.id,
            'task_id': task.id,
            'employee_id': self.employee_id.id,
            'date': (self.planned_date or fields.Datetime.now()).date(),
            'unit_amount': hours,
        }
        if self.user_id:
            values['user_id'] = self.user_id.id
        return self.env['account.analytic.line'].with_context(is_timesheet=True).create(values)

    def action_open_task(self):
        self.ensure_one()
        if not self.task_id:
            return True
        return self._open_record('project.task', self.task_id.id, self.env._("Task"))

    def _open_record(self, model, res_id, name):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'res_id': res_id,
            'view_mode': 'form',
            'target': 'current',
        }
