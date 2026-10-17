# -*- coding: utf-8 -*-

from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _syg_restrict_optional_menus(self):
        """Website is not a hard dependency. Restrict its app menu when it is installed."""
        group = self.env.ref('sygmetiv_company_management.group_company_manager')
        menu = self.env.ref('website.menu_website_configuration', raise_if_not_found=False)
        if menu:
            menu.write({'group_ids': [(6, 0, [group.id])]})
        return True
