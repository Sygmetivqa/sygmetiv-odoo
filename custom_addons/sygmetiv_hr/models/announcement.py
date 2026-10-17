# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext, html_escape


class SygAnnouncement(models.Model):
    _name = 'syg.announcement'
    _description = 'Announcement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'is_pinned desc, date_start desc, id desc'

    name = fields.Char(string="Title", required=True, tracking=True)
    body = fields.Html(string="Message", sanitize=True)
    preview = fields.Char(compute='_compute_preview')
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    audience = fields.Selection(
        [
            ('all', 'Everyone'),
            ('employee', 'Employees'),
            ('manager', 'Managers only'),
        ],
        required=True,
        default='all',
        tracking=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('published', 'Published'),
            ('archived', 'Archived'),
        ],
        default='draft',
        tracking=True,
        copy=False,
        index=True,
    )
    date_start = fields.Date(
        string="Visible From",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    date_end = fields.Date(string="Visible Until", tracking=True)
    is_pinned = fields.Boolean(string="Pinned", tracking=True)
    color = fields.Integer()
    published_by = fields.Many2one('res.users', readonly=True, copy=False)
    published_date = fields.Datetime(readonly=True, copy=False)
    user_id = fields.Many2one(
        'res.users',
        string="Author",
        default=lambda self: self.env.user,
        tracking=True,
    )

    @api.depends('body')
    def _compute_preview(self):
        for rec in self:
            text = html2plaintext(rec.body or '').strip()
            rec.preview = (text[:180] + '…') if len(text) > 180 else text

    def _audience_users(self):
        self.ensure_one()
        users = self.env['res.users'].sudo().search([
            ('share', '=', False),
            ('active', '=', True),
            ('company_ids', 'in', self.company_id.ids),
        ])
        users = users.filtered(lambda user: user.has_group(
            'sygmetiv_hr.group_announcement_user'
        ))
        if self.audience == 'manager':
            users = users.filtered(lambda user: user.has_group(
                'sygmetiv_hr.group_announcement_manager'
            ))
        return users

    def _notify_audience(self):
        template = self.env.ref(
            'sygmetiv_hr.mail_template_announcement_published',
            raise_if_not_found=False,
        )
        for rec in self:
            users = rec._audience_users()
            if not users:
                continue
            url = f'{rec.get_base_url()}/odoo/syg.announcement/{rec.id}'
            action = {
                'type': 'ir.actions.act_window',
                'res_model': 'syg.announcement',
                'res_id': rec.id,
                'views': [(False, 'form')],
                'target': 'current',
            }
            users.sudo().notify_info(
                message=f'{rec.name}\n{url}',
                title=self.env._("New announcement"),
                sticky=True,
                action=action,
            )
            if not template:
                continue
            for user in users.filtered('email'):
                template.send_mail(
                    rec.id,
                    force_send=True,
                    email_values={
                        'email_to': user.email_formatted,
                        'recipient_ids': [],
                    },
                )

    def action_publish(self):
        if not self.env.user.has_group('sygmetiv_hr.group_announcement_manager'):
            raise UserError(self.env._("Only announcement managers can publish."))
        to_notify = self.env['syg.announcement']
        for rec in self:
            if rec.state == 'published':
                continue
            rec.write({
                'state': 'published',
                'published_by': self.env.user.id,
                'published_date': fields.Datetime.now(),
            })
            rec.message_post(body=self.env._("Announcement published."))
            to_notify |= rec
        to_notify._notify_audience()
        return True

    def action_archive_announcement(self):
        self.write({'state': 'archived', 'is_pinned': False})
        return True

    def action_draft(self):
        self.write({
            'state': 'draft',
            'published_by': False,
            'published_date': False,
        })
        return True

    @api.model
    def _for_dashboard(self):
        today = fields.Date.context_today(self)
        domain = [
            ('state', '=', 'published'),
            ('date_start', '<=', today),
            '|',
            ('date_end', '=', False),
            ('date_end', '>=', today),
            ('company_id', 'in', self.env.companies.ids),
        ]
        if not self.env.user.has_group('sygmetiv_hr.group_announcement_manager'):
            domain.append(('audience', 'in', ('all', 'employee')))
        return self.search(domain, limit=8)

    def _dashboard_board_html(self):
        if not self:
            return (
                '<div class="o_syg_announce_empty">'
                '<i class="fa fa-bullhorn"/>'
                '<span>No announcements right now.</span>'
                '</div>'
            )
        cards = []
        for rec in self:
            pin = ' o_syg_announce_pinned' if rec.is_pinned else ''
            badge = '<span class="o_syg_announce_pin">Pinned</span>' if rec.is_pinned else ''
            date_label = rec.date_start.strftime('%d %b %Y') if rec.date_start else ''
            cards.append(
                '<article class="o_syg_announce_card%s">'
                '<div class="o_syg_announce_meta">'
                '<span>%s</span>%s'
                '</div>'
                '<h3>%s</h3>'
                '<p>%s</p>'
                '</article>'
                % (
                    pin,
                    html_escape(date_label),
                    badge,
                    html_escape(rec.name or ''),
                    html_escape(rec.preview or ''),
                )
            )
        return '<div class="o_syg_announce_list">%s</div>' % ''.join(cards)
