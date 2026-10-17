# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.exceptions import UserError


class SygProjectEmailWizard(models.TransientModel):
    _name = 'syg.project.email.wizard'
    _description = 'Email Project Customer'

    project_id = fields.Many2one('project.project', required=True)
    partner_id = fields.Many2one('res.partner', string="Customer", required=True)
    subject = fields.Char(required=True)
    body = fields.Html()
    attachment_ids = fields.Many2many('ir.attachment', string="Attachments")

    def action_send(self):
        self.ensure_one()
        partner = self.partner_id
        if not self.body:
            raise UserError(self.env._("Write the email before sending."))
        if not partner.email:
            raise UserError(self.env._("The customer has no email address."))
        mail = self.env['mail.mail'].sudo().create({
            'subject': self.subject,
            'body_html': self.body or '',
            'email_to': partner.email,
            'recipient_ids': [(4, partner.id)],
            'attachment_ids': [(6, 0, self.attachment_ids.ids)],
            'model': 'project.project',
            'res_id': self.project_id.id,
            'auto_delete': True,
        })
        mail.send()
        self.project_id.message_post(
            body=self.body or self.subject,
            subject=self.subject,
            partner_ids=partner.ids,
            attachment_ids=self.attachment_ids.ids,
        )
        return {'type': 'ir.actions.act_window_close'}
