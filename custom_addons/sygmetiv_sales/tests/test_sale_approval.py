# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestSaleApproval(SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_approver = cls.env.ref('sygmetiv_sales.group_sale_approver')
        cls.salesman = cls.env['res.users'].create({
            'name': 'Salesperson',
            'login': 'sale_approval_salesman',
            'email': 'salesman@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('sales_team.group_sale_salesman_all_leads').id,
            ])],
        })
        cls.sale_order.user_id = cls.salesman
        cls.approver = cls.env['res.users'].create({
            'name': 'Sales Approver',
            'login': 'sale_approval_approver',
            'email': 'approver@example.com',
            'group_ids': [(6, 0, [cls.group_approver.id])],
        })

    def test_salesperson_request_approval_instead_of_confirm(self):
        order = self.sale_order.with_user(self.salesman)
        order.action_confirm()
        self.assertEqual(order.state, 'waiting_approval')
        self.assertEqual(order.approval_requested_by, self.salesman)

    def test_approver_confirms_directly(self):
        order = self.sale_order.with_user(self.approver)
        order.action_confirm()
        self.assertEqual(order.state, 'sale')
        self.assertEqual(order.approved_by, False)

    def test_approver_approves_waiting_quotation(self):
        self.sale_order.with_user(self.salesman).action_confirm()
        self.sale_order.with_user(self.approver).action_approve()
        self.assertEqual(self.sale_order.state, 'sale')
        self.assertEqual(self.sale_order.approved_by, self.approver)

    def test_salesperson_cannot_confirm_waiting_quotation(self):
        self.sale_order.with_user(self.salesman).action_confirm()
        with self.assertRaises(UserError):
            self.sale_order.with_user(self.salesman).action_confirm()

    def test_reject_sets_quotation_back_to_draft(self):
        self.sale_order.with_user(self.salesman).action_confirm()
        self.sale_order.with_user(self.approver).action_reject_approval()
        self.assertEqual(self.sale_order.state, 'draft')
