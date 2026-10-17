# -*- coding: utf-8 -*-

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestPurchaseApproval(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_approver = cls.env.ref('sygmetiv_purchase.group_purchase_approver')
        cls.buyer = cls.env['res.users'].create({
            'name': 'Buyer',
            'login': 'purchase_approval_buyer',
            'email': 'buyer@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('purchase.group_purchase_user').id,
            ])],
        })
        cls.approver = cls.env['res.users'].create({
            'name': 'Purchase Approver',
            'login': 'purchase_approval_approver',
            'email': 'po-approver@example.com',
            'group_ids': [(6, 0, [cls.group_approver.id])],
        })
        cls.purchase_order = cls.env['purchase.order'].create({
            'partner_id': cls.partner_a.id,
            'user_id': cls.buyer.id,
            'order_line': [Command.create({
                'product_id': cls.product_a.id,
                'product_qty': 1,
                'price_unit': 10,
            })],
        })

    def test_buyer_request_approval_instead_of_confirm(self):
        order = self.purchase_order.with_user(self.buyer)
        order.button_confirm()
        self.assertEqual(order.state, 'to approve')
        self.assertEqual(order.approval_requested_by, self.buyer)

    def test_approver_confirms_directly(self):
        order = self.purchase_order.with_user(self.approver)
        order.button_confirm()
        self.assertEqual(order.state, 'purchase')

    def test_approver_approves_waiting_rfq(self):
        self.purchase_order.with_user(self.buyer).button_confirm()
        self.purchase_order.with_user(self.approver).button_approve()
        self.assertEqual(self.purchase_order.state, 'purchase')
        self.assertEqual(self.purchase_order.approved_by, self.approver)

    def test_buyer_cannot_approve_waiting_rfq(self):
        self.purchase_order.with_user(self.buyer).button_confirm()
        self.purchase_order.with_user(self.buyer).button_approve()
        self.assertEqual(self.purchase_order.state, 'to approve')

    def test_reject_sets_rfq_back_to_draft(self):
        self.purchase_order.with_user(self.buyer).button_confirm()
        self.purchase_order.with_user(self.approver).action_reject_approval()
        self.assertEqual(self.purchase_order.state, 'draft')
