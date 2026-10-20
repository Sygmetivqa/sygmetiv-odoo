# -*- coding: utf-8 -*-

from unittest.mock import patch

from odoo.tests import tagged
from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestLeadNotification(SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = cls.env.ref('sygmetiv_sales.group_crm_lead_notify')
        cls.watcher = cls.env['res.users'].create({
            'name': 'Lead Watcher',
            'login': 'lead_notify_watcher',
            'email': 'lead.notify@example.com',
            'group_ids': [(6, 0, [cls.group.id])],
        })

    def test_new_lead_notifies_group_members(self):
        with patch(
            'odoo.addons.web_notify.models.res_users.ResUsers.notify_info',
            autospec=True,
        ) as notify:
            lead = self.env['crm.lead'].create({
                'name': 'FB Demo – Test Person',
                'contact_name': 'Test Person',
                'email_from': 'test.person@example.com',
                'phone': '+97400000000',
                'type': 'lead',
            })
        notified = notify.call_args.args[0]
        self.assertIn(self.watcher, notified)
        self.assertEqual(notify.call_args.kwargs['title'], 'New lead')
        self.assertIn('Test Person', notify.call_args.kwargs['message'])
        self.assertEqual(notify.call_args.kwargs['action']['res_id'], lead.id)
