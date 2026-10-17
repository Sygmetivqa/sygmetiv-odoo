# -*- coding: utf-8 -*-

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    state = fields.Selection(
        selection_add=[('waiting_approval', "Waiting Approval")],
        ondelete={'waiting_approval': 'cascade'},
    )
