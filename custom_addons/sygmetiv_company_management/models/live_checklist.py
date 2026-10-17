# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SygLiveChecklistItem(models.Model):
    _name = 'syg.live.checklist.item'
    _description = 'Go-Live Checklist Item'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    mandatory = fields.Boolean(default=True)
    active = fields.Boolean(default=True)
    description = fields.Text()


class SygProjectLiveCheck(models.Model):
    _name = 'syg.project.live.check'
    _description = 'Project Go-Live Checklist Line'
    _order = 'sequence, id'

    project_id = fields.Many2one('project.project', required=True, ondelete='cascade', index=True)
    item_id = fields.Many2one('syg.live.checklist.item', ondelete='set null')
    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    mandatory = fields.Boolean()
    done = fields.Boolean()
    user_id = fields.Many2one('res.users')
    done_date = fields.Datetime()

    @api.onchange('done')
    def _onchange_done(self):
        if self.done:
            self.user_id = self.env.user
            self.done_date = fields.Datetime.now()
        else:
            self.user_id = False
            self.done_date = False
