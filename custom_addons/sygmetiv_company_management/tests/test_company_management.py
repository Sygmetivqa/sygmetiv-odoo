# -*- coding: utf-8 -*-

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestCompanyManagement(TransactionCase):

    def test_overtime_flow(self):
        employee = self.env['hr.employee'].create({'name': 'OT Employee'})
        overtime = self.env['syg.overtime.request'].create({
            'employee_id': employee.id,
            'hours': 2.0,
            'reason': 'Month-end close',
        })
        overtime.action_submit()
        self.assertEqual(overtime.state, 'submitted')
        overtime.action_approve()
        self.assertEqual(overtime.state, 'approved')

    def test_payslip_compute(self):
        employee = self.env['hr.employee'].create({'name': 'Payroll Employee'})
        slip = self.env['syg.payslip'].create({'employee_id': employee.id})
        slip.action_compute_sheet()
        self.assertEqual(slip.state, 'computed')
        self.assertIn('NET', slip.line_ids.mapped('code'))

    def test_credential_visibility_and_project_link(self):
        group = self.env.ref('sygmetiv_company_management.group_company_user')
        user_a = self.env['res.users'].create({
            'name': 'Credential User A',
            'login': 'syg_cred_user_a',
            'group_ids': [Command.set([group.id])],
        })
        user_b = self.env['res.users'].create({
            'name': 'Credential User B',
            'login': 'syg_cred_user_b',
            'group_ids': [Command.set([group.id])],
        })
        project = self.env['project.project'].create({'name': 'Credential Project'})
        credential = self.env['syg.credential'].create({
            'name': 'App login',
            'username': 'app',
            'password': 'secret',
            'project_id': project.id,
            'user_ids': [Command.set(user_a.ids)],
            'allowed_user_ids': [Command.clear()],
        })
        Credential = self.env['syg.credential']
        self.assertEqual(
            Credential.with_user(user_a).search([('id', '=', credential.id)]).ids,
            credential.ids,
        )
        self.assertFalse(Credential.with_user(user_b).search([('id', '=', credential.id)]))
        credential.write({'allowed_user_ids': [Command.link(user_b.id)]})
        self.assertEqual(
            Credential.with_user(user_b).search([('id', '=', credential.id)]).ids,
            credential.ids,
        )
        action = project.action_open_syg_credentials()
        self.assertEqual(action['domain'], [('project_id', '=', project.id)])
        self.assertEqual(project.syg_credential_count, 1)

    def test_meeting_task_requires_attendees_role_and_presentation_time(self):
        project = self.env['project.project'].create({'name': 'Meeting Project'})
        meeting = self.env['syg.task.type'].create({'name': 'Client Demo', 'is_meeting': True})
        regular = self.env['syg.task.type'].create({'name': 'Development Work', 'is_meeting': False})
        self.env['project.task'].create({
            'name': 'Build feature',
            'project_id': project.id,
            'syg_task_type_id': regular.id,
        })
        employee = self.env['hr.employee'].create({'name': 'Demo Host'})
        with self.assertRaises(ValidationError):
            self.env['project.task'].create({
                'name': 'Product demo',
                'project_id': project.id,
                'syg_task_type_id': meeting.id,
            })
        request = self.env['syg.task.request'].create({
            'name': 'Training session',
            'employee_id': employee.id,
            'project_id': project.id,
            'syg_task_type_id': meeting.id,
            'syg_attendee_ids': [Command.set(employee.ids)],
            'syg_role': 'Trainer',
            'syg_presentation_time': 1.0,
            'description': '<p>Agenda for the session</p>',
        })
        request.action_submit()
        request.action_create_task()
        task = request.task_id
        self.assertEqual(task.syg_role, 'Trainer')
        self.assertEqual(task.syg_attendee_ids, employee)
        self.assertEqual(task.syg_presentation_time, 1.0)
        self.assertIn('Agenda', task.description or '')
