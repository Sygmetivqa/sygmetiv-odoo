# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SygKpiCriteria(models.Model):
    _name = 'syg.kpi.criteria'
    _description = 'KPI Criteria'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    max_score = fields.Float(required=True, default=10.0)
    description = fields.Text()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, index=True)

    @api.constrains('max_score')
    def _check_max_score(self):
        for rec in self:
            if rec.max_score <= 0:
                raise ValidationError(self.env._("Max score must be greater than zero."))


class SygKpiStatus(models.Model):
    _name = 'syg.kpi.status'
    _description = 'KPI Score Band'
    _order = 'from_score desc'

    name = fields.Char(required=True, translate=True)
    from_score = fields.Float(required=True)
    to_score = fields.Float(required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, index=True)
    active = fields.Boolean(default=True)

    @api.constrains('from_score', 'to_score')
    def _check_range(self):
        for rec in self:
            if rec.to_score < rec.from_score:
                raise ValidationError(self.env._("To score must be greater than or equal to from score."))

    @api.model
    def status_for_score(self, score, company):
        domain = [
            ('from_score', '<=', score),
            ('to_score', '>=', score),
            ('active', '=', True),
        ]
        if company:
            domain = ['|', ('company_id', '=', False), ('company_id', '=', company.id)] + domain
        return self.search(domain, limit=1, order='from_score desc')
