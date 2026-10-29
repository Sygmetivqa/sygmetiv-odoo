# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class ProjectProject(models.Model):
    _inherit = 'project.project'

    syg_is_amc = fields.Boolean(
        string="AMC Project",
        help="Mark this project as an Annual Maintenance Contract (AMC) project.",
        default=False,
    )
    syg_hosting_type_id = fields.Many2one(
        'syg.hosting.type',
        string="Hosting Type",
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True,
    )
    syg_implementation_type_ids = fields.Many2many(
        'syg.implementation.type',
        'syg_project_implementation_type_rel',
        'project_id',
        'implementation_type_id',
        string="Implementation Types",
        required=True,
        tracking=True,
    )
    syg_is_live = fields.Boolean(string="Live", copy=False, tracking=True)
    syg_go_live_date = fields.Datetime(readonly=True, copy=False)
    syg_live_check_ids = fields.One2many(
        'syg.project.live.check',
        'project_id',
        string="Go-Live Checklist",
    )
    syg_document_ids = fields.One2many(
        'syg.project.document',
        'project_id',
        string="Project Documents",
    )
    syg_note_ids = fields.One2many(
        'syg.project.note',
        'project_id',
        string="Project Notes",
    )
    syg_credential_ids = fields.One2many(
        'syg.credential',
        'project_id',
        string="Credentials",
    )
    syg_document_count = fields.Integer(compute='_compute_syg_project_counts')
    syg_note_count = fields.Integer(compute='_compute_syg_project_counts')
    syg_credential_count = fields.Integer(compute='_compute_syg_project_counts')
    syg_hours_status = fields.Char(compute='_compute_syg_hours_status')

    @api.depends('syg_document_ids', 'syg_note_ids', 'syg_credential_ids')
    def _compute_syg_project_counts(self):
        for project in self:
            project.syg_document_count = len(project.syg_document_ids)
            project.syg_note_count = len(project.syg_note_ids)
            project.syg_credential_count = len(project.syg_credential_ids)

    @api.depends('allocated_hours', 'effective_hours', 'allow_timesheets')
    def _compute_syg_hours_status(self):
        for project in self:
            if not project.allow_timesheets or not project.allocated_hours:
                project.syg_hours_status = ''
            elif project.effective_hours > project.allocated_hours:
                project.syg_hours_status = self.env._("Over estimate")
            else:
                project.syg_hours_status = self.env._("On estimate")

    def action_open_syg_project_dashboard(self):
        self.ensure_one()
        return self.env['syg.project.dashboard'].action_open(self)

    def action_open_syg_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Documents"),
            'res_model': 'syg.project.document',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_open_syg_credentials(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Credentials"),
            'res_model': 'syg.credential',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_open_syg_notes(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Notes"),
            'res_model': 'syg.project.note',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_open_go_live(self):
        self.ensure_one()
        if self.syg_is_live:
            raise UserError(self.env._("This project is already live."))
        wizard = self.env['syg.project.go.live.wizard'].create({
            'project_id': self.id,
        })
        wizard._load_checklist()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Go Live"),
            'res_model': 'syg.project.go.live.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_email_customer(self):
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            raise UserError(self.env._("Set a customer on the project first."))
        wizard = self.env['syg.project.email.wizard'].create({
            'project_id': self.id,
            'partner_id': partner.id,
            'subject': self.env._("%s — update", self.display_name),
        })
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Email Customer"),
            'res_model': 'syg.project.email.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }
