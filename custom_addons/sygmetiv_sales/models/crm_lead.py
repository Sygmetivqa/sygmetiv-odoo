# -*- coding: utf-8 -*-

from odoo import api, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        leads._notify_lead_arrival()
        return leads

    def _notify_lead_arrival(self):
        group = self.env.ref('sygmetiv_sales.group_crm_lead_notify', raise_if_not_found=False)
        if not group:
            return
        users = self.env['res.users'].search([
            ('group_ids', 'in', group.ids),
            ('share', '=', False),
        ])
        if not users:
            return
        for lead in self:
            parts = [lead.contact_name or lead.name or 'New lead']
            if lead.email_from:
                parts.append(lead.email_from)
            if lead.phone:
                parts.append(lead.phone)
            if lead.team_id:
                parts.append(lead.team_id.name)
            users.sudo().notify_info(
                message='\n'.join(parts),
                title='New lead',
                sticky=True,
                action={
                    'type': 'ir.actions.act_window',
                    'res_model': 'crm.lead',
                    'res_id': lead.id,
                    'views': [(False, 'form')],
                    'target': 'current',
                },
            )
