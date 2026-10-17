# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import fields, http
from odoo.http import request


class SygKpiScorePortal(http.Controller):

    def _period_closed(self, evaluation):
        if not evaluation.date_end:
            return True
        deadline = evaluation.date_end + timedelta(days=evaluation.grace_days or 0)
        return fields.Date.context_today(evaluation) > deadline

    @http.route('/kpi/score', type='http', auth='public', website=False)
    def kpi_score_portal(self, token=None, **kwargs):
        if not token:
            return request.render('sygmetiv_kpi.portal_score_no_token')
        access = request.env['syg.kpi.evaluator.access'].sudo().search([('token', '=', token)], limit=1)
        if not access:
            return request.render('sygmetiv_kpi.portal_score_invalid_token')
        evaluations = access.evaluation_ids
        editable_ids = {
            evaluation.id
            for evaluation in evaluations
            if evaluation.state == 'submitted' and not self._period_closed(evaluation)
        }
        return request.render('sygmetiv_kpi.portal_score_form', {
            'access': access,
            'evaluations': evaluations,
            'editable_ids': editable_ids,
        })

    @http.route('/kpi/score/thank-you', type='http', auth='public', website=False)
    def kpi_score_thank_you(self, token=None, **kwargs):
        return request.render('sygmetiv_kpi.portal_score_thank_you')

    @http.route('/kpi/score/submit', type='http', auth='public', methods=['POST'], website=False, csrf=True)
    def kpi_score_submit(self, **post):
        token = post.get('token')
        if not token:
            return request.redirect('/kpi/score')
        access = request.env['syg.kpi.evaluator.access'].sudo().search([('token', '=', token)], limit=1)
        if not access:
            return request.redirect('/kpi/score')
        ScoreLine = request.env['syg.kpi.score.line'].sudo()
        for key, value in post.items():
            if not key.startswith('score_') or value in (None, ''):
                continue
            try:
                line = ScoreLine.browse(int(key.split('_', 1)[1]))
            except (ValueError, TypeError):
                continue
            if not line.exists() or line.user_id != access.user_id:
                continue
            evaluation = line.evaluation_id
            if evaluation.state != 'submitted' or self._period_closed(evaluation):
                continue
            try:
                score = float(value)
            except (ValueError, TypeError):
                continue
            max_score = line.criteria_id.max_score or 0.0
            if 0 <= score <= max_score:
                line.write({'score': score})
        return request.redirect('/kpi/score/thank-you?token=%s' % token)
