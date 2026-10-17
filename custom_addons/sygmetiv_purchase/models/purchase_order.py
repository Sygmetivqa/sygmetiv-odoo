# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_purchase_approver = fields.Boolean(compute='_compute_is_purchase_approver')
    approval_requested_by = fields.Many2one(
        'res.users',
        string="Approval Requested By",
        copy=False,
        readonly=True,
        tracking=True,
    )
    approval_requested_date = fields.Datetime(
        string="Approval Requested On",
        copy=False,
        readonly=True,
        tracking=True,
    )
    approved_by = fields.Many2one(
        'res.users',
        string="Approved By",
        copy=False,
        readonly=True,
        tracking=True,
    )
    approved_date = fields.Datetime(
        string="Approved On",
        copy=False,
        readonly=True,
        tracking=True,
    )

    @api.depends_context('uid')
    def _compute_is_purchase_approver(self):
        is_approver = self._user_is_purchase_approver()
        for order in self:
            order.is_purchase_approver = is_approver

    def _user_is_purchase_approver(self):
        return self.env.su or self.env.user.has_group(
            'sygmetiv_purchase.group_purchase_approver'
        )

    def _approval_allowed(self):
        self.ensure_one()
        return self._user_is_purchase_approver()

    def _get_purchase_approver_users(self):
        self.ensure_one()
        group = self.env.ref(
            'sygmetiv_purchase.group_purchase_approver',
            raise_if_not_found=False,
        )
        if not group:
            return self.env['res.users']
        company = self.company_id
        return group.sudo().all_user_ids.filtered(
            lambda user: user.active
            and not user.share
            and company in user.company_ids
        )

    def _purchase_order_backend_url(self):
        self.ensure_one()
        return f'{self.get_base_url()}/odoo/purchase.order/{self.id}'

    def _purchase_approval_action(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'current',
        }

    def _notify_users_email_and_web(self, users, title, message, template_xmlid):
        self.ensure_one()
        users = users.filtered(lambda user: user.active and not user.share)
        if not users:
            return
        url = self._purchase_order_backend_url()
        action = self._purchase_approval_action()
        users.sudo().notify_info(
            message=f'{message}\n{url}',
            title=title,
            sticky=True,
            action=action,
        )
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
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

    def _action_request_purchase_approval(self):
        for order in self:
            error_msg = order._confirmation_error_message()
            if error_msg:
                raise UserError(error_msg)
            approvers = order._get_purchase_approver_users()
            if not approvers:
                raise UserError(
                    self.env._(
                        "No Purchase Approver is assigned. "
                        "Add at least one user to the Purchase Approver group."
                    )
                )
            order.write({
                'state': 'to approve',
                'approval_requested_by': self.env.user.id,
                'approval_requested_date': fields.Datetime.now(),
                'approved_by': False,
                'approved_date': False,
            })
            order.message_post(
                body=self.env._(
                    "RFQ submitted for approval by %s.",
                    self.env.user.display_name,
                )
            )
            title = self.env._("Purchase order to approve")
            message = self.env._(
                "%(order)s for %(vendor)s is waiting for your approval.",
                order=order.name,
                vendor=order.partner_id.display_name,
            )
            order._notify_users_email_and_web(
                approvers,
                title,
                message,
                'sygmetiv_purchase.mail_template_purchase_approval_request',
            )
        return True

    def action_request_approval(self):
        return self.button_confirm()

    def button_confirm(self):
        for order in self:
            if order.state not in ['draft', 'sent']:
                continue
            error_msg = order._confirmation_error_message()
            if error_msg:
                raise UserError(error_msg)
            order.order_line._validate_analytic_distribution()
            order._add_supplier_to_product()
            if order._approval_allowed():
                order.button_approve()
            else:
                order._action_request_purchase_approval()
        return True

    def button_approve(self, force=False):
        to_notify = self.filtered(lambda order: order.state == 'to approve')
        result = super().button_approve(force=force)
        approved = to_notify.filtered(lambda order: order.state == 'purchase')
        if approved:
            approved.write({
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })
        for order in approved:
            order.message_post(
                body=self.env._("Purchase order approved by %s.", self.env.user.display_name)
            )
            buyer = order.user_id
            if buyer:
                title = self.env._("Purchase order approved")
                message = self.env._(
                    "%(order)s has been approved and confirmed.",
                    order=order.name,
                )
                order._notify_users_email_and_web(
                    buyer,
                    title,
                    message,
                    'sygmetiv_purchase.mail_template_purchase_approval_done',
                )
        return result

    def action_reject_approval(self):
        if not self._user_is_purchase_approver():
            raise UserError(
                self.env._("Only a Purchase Approver can reject RFQs.")
            )
        if any(order.state != 'to approve' for order in self):
            raise UserError(
                self.env._("Only RFQs waiting for approval can be rejected.")
            )
        for order in self:
            buyer = order.user_id
            order.message_post(
                body=self.env._("RFQ rejected by %s.", self.env.user.display_name)
            )
            if buyer:
                title = self.env._("Purchase RFQ rejected")
                message = self.env._(
                    "%(order)s was rejected and set back to RFQ.",
                    order=order.name,
                )
                order._notify_users_email_and_web(
                    buyer,
                    title,
                    message,
                    'sygmetiv_purchase.mail_template_purchase_approval_rejected',
                )
        self.write({
            'approval_requested_by': False,
            'approval_requested_date': False,
            'approved_by': False,
            'approved_date': False,
        })
        return self.button_draft()
