# -*- coding: utf-8 -*-

from odoo import models


class SygNotifyMixin(models.AbstractModel):
    _name = 'syg.notify.mixin'
    _description = 'Email and web_notify helper'

    def _syg_record_url(self):
        self.ensure_one()
        return f'{self.get_base_url()}/odoo/{self._name}/{self.id}'

    def _syg_notify_users(self, users, title, message, template_xmlid=False):
        self.ensure_one()
        users = users.filtered(lambda user: user.active and not user.share)
        if not users:
            return
        url = self._syg_record_url()
        action = {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'current',
        }
        users.sudo().notify_info(
            message=f'{message}\n{url}',
            title=title,
            sticky=True,
            action=action,
        )
        template = template_xmlid and self.env.ref(template_xmlid, raise_if_not_found=False)
        if not template:
            return
        for user in users:
            if not user.email:
                continue
            template.send_mail(
                self.id,
                force_send=True,
                email_values={
                    'email_to': user.email_formatted,
                    'recipient_ids': [],
                },
            )
