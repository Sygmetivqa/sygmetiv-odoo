# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    state = fields.Selection(
        selection_add=[('waiting_approval', "Waiting Approval")],
        ondelete={'waiting_approval': 'set default'},
    )
    is_sale_approver = fields.Boolean(
        compute='_compute_is_sale_approver',
    )
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
    def _compute_is_sale_approver(self):
        is_approver = self.env.user.has_group(
            'sygmetiv_sales.group_sale_approver'
        )
        for order in self:
            order.is_sale_approver = is_approver

    def _user_is_sale_approver(self):
        return self.env.su or self.env.user.has_group(
            'sygmetiv_sales.group_sale_approver'
        )

    def _get_sale_approver_users(self):
        self.ensure_one()
        group = self.env.ref(
            'sygmetiv_sales.group_sale_approver',
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

    def _sale_order_backend_url(self):
        self.ensure_one()
        return f'{self.get_base_url()}/odoo/sale.order/{self.id}'

    def _sale_approval_action(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'current',
        }

    def _notify_users_email_and_web(self, users, title, message, template_xmlid):
        self.ensure_one()
        users = users.filtered(lambda user: user.active and not user.share)
        if not users:
            return
        url = self._sale_order_backend_url()
        action = self._sale_approval_action()
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

    def _action_request_sale_approval(self):
        for order in self:
            error_msg = order._confirmation_error_message()
            if error_msg:
                raise UserError(error_msg)
            approvers = order._get_sale_approver_users()
            if not approvers:
                raise UserError(
                    self.env._(
                        "No Sales Approver is assigned. "
                        "Add at least one user to the Sales Approver group."
                    )
                )
            order.write({
                'state': 'waiting_approval',
                'approval_requested_by': self.env.user.id,
                'approval_requested_date': fields.Datetime.now(),
                'approved_by': False,
                'approved_date': False,
            })
            order.message_post(
                body=self.env._(
                    "Quotation submitted for approval by %s.",
                    self.env.user.display_name,
                )
            )
            title = self.env._("Sales quotation to approve")
            message = self.env._(
                "%(order)s for %(customer)s is waiting for your approval.",
                order=order.name,
                customer=order.partner_id.display_name,
            )
            order._notify_users_email_and_web(
                approvers,
                title,
                message,
                'sygmetiv_sales.mail_template_sale_approval_request',
            )
        return True

    def action_request_approval(self):
        return self._action_request_sale_approval()

    def action_confirm(self):
        if self.env.context.get('sale_skip_approval'):
            return super().action_confirm()

        to_request = self.env['sale.order']
        to_confirm = self.env['sale.order']
        is_approver = self._user_is_sale_approver()
        for order in self:
            if order.state == 'waiting_approval':
                if not is_approver:
                    raise UserError(
                        self.env._(
                            "Only a Sales Approver can confirm a quotation "
                            "that is waiting for approval."
                        )
                    )
                to_confirm |= order
            elif is_approver:
                to_confirm |= order
            else:
                to_request |= order

        if to_request:
            to_request._action_request_sale_approval()
        if to_confirm:
            super(SaleOrder, to_confirm).action_confirm()
        return True

    def action_approve(self):
        if not self._user_is_sale_approver():
            raise UserError(
                self.env._("Only a Sales Approver can approve quotations.")
            )
        if any(order.state != 'waiting_approval' for order in self):
            raise UserError(
                self.env._("Only quotations waiting for approval can be approved.")
            )
        self.write({
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })
        for order in self:
            order.message_post(
                body=self.env._("Quotation approved by %s.", self.env.user.display_name)
            )
            salesperson = order.user_id
            if salesperson:
                title = self.env._("Sales quotation approved")
                message = self.env._(
                    "%(order)s has been approved and confirmed.",
                    order=order.name,
                )
                order._notify_users_email_and_web(
                    salesperson,
                    title,
                    message,
                    'sygmetiv_sales.mail_template_sale_approval_done',
                )
        return self.with_context(sale_skip_approval=True).action_confirm()

    def action_reject_approval(self):
        if not self._user_is_sale_approver():
            raise UserError(
                self.env._("Only a Sales Approver can reject quotations.")
            )
        if any(order.state != 'waiting_approval' for order in self):
            raise UserError(
                self.env._("Only quotations waiting for approval can be rejected.")
            )
        for order in self:
            salesperson = order.user_id
            order.message_post(
                body=self.env._("Quotation rejected by %s.", self.env.user.display_name)
            )
            if salesperson:
                title = self.env._("Sales quotation rejected")
                message = self.env._(
                    "%(order)s was rejected and set back to quotation.",
                    order=order.name,
                )
                order._notify_users_email_and_web(
                    salesperson,
                    title,
                    message,
                    'sygmetiv_sales.mail_template_sale_approval_rejected',
                )
        self.write({
            'state': 'draft',
            'approval_requested_by': False,
            'approval_requested_date': False,
            'approved_by': False,
            'approved_date': False,
        })
        return True

    def action_draft(self):
        waiting = self.filtered(lambda order: order.state == 'waiting_approval')
        if waiting:
            waiting.write({
                'state': 'draft',
                'approval_requested_by': False,
                'approval_requested_date': False,
                'approved_by': False,
                'approved_date': False,
            })
        return super(SaleOrder, self - waiting).action_draft()

    def _confirmation_error_message(self):
        self.ensure_one()
        if (
            self.state == 'waiting_approval'
            and self._user_is_sale_approver()
        ):
            if any(
                not line.display_type
                and not line.is_downpayment
                and not line.product_id
                for line in self.order_line
            ):
                return self.env._(
                    "Some order lines are missing a product, you need to "
                    "correct them before going further."
                )
            return False
        return super()._confirmation_error_message()
