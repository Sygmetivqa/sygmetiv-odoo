# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class SygProjectGoLiveWizardLine(models.TransientModel):
    _name = 'syg.project.go.live.wizard.line'
    _description = 'Go-Live Wizard Line'
    _order = 'sequence, id'

    wizard_id = fields.Many2one('syg.project.go.live.wizard', required=True, ondelete='cascade')
    item_id = fields.Many2one('syg.live.checklist.item')
    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    mandatory = fields.Boolean()
    done = fields.Boolean()


class SygProjectGoLiveWizard(models.TransientModel):
    _name = 'syg.project.go.live.wizard'
    _description = 'Go Live'

    project_id = fields.Many2one('project.project', required=True)
    line_ids = fields.One2many('syg.project.go.live.wizard.line', 'wizard_id')

    def _load_checklist(self):
        self.ensure_one()
        items = self.env['syg.live.checklist.item'].search([('active', '=', True)])
        if not items:
            raise UserError(self.env._("Add live checklist items under Project → Configuration first."))
        self.line_ids.unlink()
        self.line_ids = [
            Command.create({
                'item_id': item.id,
                'name': item.name,
                'sequence': item.sequence,
                'mandatory': item.mandatory,
            })
            for item in items
        ]

    def action_confirm(self):
        self.ensure_one()
        missing = self.line_ids.filtered(lambda line: line.mandatory and not line.done)
        if missing:
            raise UserError(self.env._(
                "Tick every mandatory checklist item before going live:\n%s",
                '\n'.join(missing.mapped('name')),
            ))
        project = self.project_id
        project.syg_live_check_ids.unlink()
        project.write({
            'syg_is_live': True,
            'syg_go_live_date': fields.Datetime.now(),
            'syg_live_check_ids': [
                Command.create({
                    'item_id': line.item_id.id,
                    'name': line.name,
                    'sequence': line.sequence,
                    'mandatory': line.mandatory,
                    'done': line.done,
                    'user_id': self.env.user.id if line.done else False,
                    'done_date': fields.Datetime.now() if line.done else False,
                })
                for line in self.line_ids
            ],
        })
        project.message_post(body=self.env._("Project marked live."))
        return {'type': 'ir.actions.act_window_close'}
