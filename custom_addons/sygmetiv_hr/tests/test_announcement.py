# -*- coding: utf-8 -*-

from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestAnnouncement(TransactionCase):

    def test_publish_and_dashboard(self):
        rec = self.env['syg.announcement'].create({
            'name': 'Office closed Friday',
            'body': '<p>Use the extra day to rest.</p>',
            'audience': 'all',
        })
        rec.action_publish()
        self.assertEqual(rec.state, 'published')
        self.assertTrue(rec.preview)
        board = rec._for_dashboard()
        self.assertIn(rec, board)
