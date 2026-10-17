# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SygCredential(models.Model):
    _name = 'syg.credential'
    _description = 'Credential'
    _inherit = ['mail.thread']
    _order = 'name, id'

    name = fields.Char(required=True, tracking=True)
    url = fields.Char(string="URL", tracking=True)
    username = fields.Char(tracking=True)
    password = fields.Char()
    project_id = fields.Many2one(
        'project.project',
        string="Project",
        ondelete='set null',
        index=True,
        check_company=True,
        tracking=True,
    )
    user_ids = fields.Many2many(
        'res.users',
        'syg_credential_user_rel',
        'credential_id',
        'user_id',
        string="Users",
        default=lambda self: self.env.user,
        domain="[('share', '=', False)]",
        tracking=True,
    )
    allowed_user_ids = fields.Many2many(
        'res.users',
        'syg_credential_allowed_user_rel',
        'credential_id',
        'user_id',
        string="Allowed Users",
        domain="[('share', '=', False)]",
        tracking=True,
    )
    note = fields.Text()
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'syg_credential_attachment_rel',
        'credential_id',
        'attachment_id',
        string="Documents",
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    active = fields.Boolean(default=True)

    def _link_attachments(self):
        for credential in self:
            attachments = credential.attachment_ids.filtered(
                lambda attachment: not attachment.res_model or (
                    attachment.res_model == credential._name
                    and attachment.res_id in (False, 0, credential.id)
                )
            )
            attachments.sudo().write({
                'res_model': credential._name,
                'res_id': credential.id,
            })

    @api.model_create_multi
    def create(self, vals_list):
        credentials = super().create(vals_list)
        credentials._link_attachments()
        return credentials

    def write(self, vals):
        res = super().write(vals)
        if 'attachment_ids' in vals:
            self._link_attachments()
        return res

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id.company_id:
            self.company_id = self.project_id.company_id

    @api.constrains('user_ids', 'allowed_user_ids')
    def _check_visibility_users(self):
        for credential in self:
            if not credential.user_ids and not credential.allowed_user_ids:
                raise ValidationError(self.env._(
                    "Set at least one User or Allowed User so this credential stays visible."
                ))
