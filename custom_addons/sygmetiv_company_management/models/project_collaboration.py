# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SygProjectDocument(models.Model):
    _name = 'syg.project.document'
    _description = 'Project Document'
    _order = 'date desc, id desc'

    name = fields.Char(required=True)
    project_id = fields.Many2one(
        'project.project',
        required=True,
        ondelete='cascade',
        index=True,
    )
    document_type = fields.Selection(
        [
            ('contract', 'Contract'),
            ('sow', 'Scope of Work'),
            ('design', 'Design'),
            ('meeting', 'Meeting'),
            ('handover', 'Handover'),
            ('other', 'Other'),
        ],
        default='other',
        required=True,
        index=True,
    )
    date = fields.Date(default=fields.Date.context_today, required=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True)
    datas = fields.Binary(string="File", required=True, attachment=True)
    datas_fname = fields.Char(string="Filename")
    note = fields.Text()
    company_id = fields.Many2one(related='project_id.company_id', store=True)


class SygProjectNote(models.Model):
    _name = 'syg.project.note'
    _description = 'Project Note'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(required=True, tracking=True)
    project_id = fields.Many2one(
        'project.project',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
    )
    note_type = fields.Selection(
        [
            ('meeting', 'Meeting Minutes'),
            ('call', 'Call Notes'),
            ('followup', 'Follow-up Notes'),
            ('other', 'Other'),
        ],
        default='meeting',
        required=True,
        index=True,
        tracking=True,
    )
    date = fields.Datetime(default=fields.Datetime.now, required=True, tracking=True)
    employee_id = fields.Many2one(
        'hr.employee',
        default=lambda self: self.env.user.employee_id,
        tracking=True,
    )
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True)
    attendees = fields.Char()
    body = fields.Html(required=True)
    company_id = fields.Many2one(related='project_id.company_id', store=True)
    attachment_ids = fields.Many2many('ir.attachment', string="Attachments")
