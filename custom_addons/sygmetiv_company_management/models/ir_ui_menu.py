# -*- coding: utf-8 -*-

from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _syg_restrict_optional_menus(self):
        """Restrict optional app menus when those apps are installed.

        Website is not a hard dependency. Contacts is visible to every internal
        user in standard Odoo because its groups are combined with OR; keep it
        for users who have the Contact Creation right only.
        """
        manager = self.env.ref('sygmetiv_company_management.group_company_manager')
        website = self.env.ref('website.menu_website_configuration', raise_if_not_found=False)
        if website:
            website.write({'group_ids': [(6, 0, [manager.id])]})
        contact_creation = self.env.ref('base.group_partner_manager')
        for xmlid in (
            'contacts.menu_contacts',
            'contacts.res_partner_menu_contacts',
        ):
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu:
                menu.write({'group_ids': [(6, 0, [contact_creation.id])]})
        return True
