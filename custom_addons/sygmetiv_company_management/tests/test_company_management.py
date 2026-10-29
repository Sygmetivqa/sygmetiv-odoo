# -*- coding: utf-8 -*-

from lxml import etree

from odoo import Command, fields
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

    def test_meeting_task_requires_attendees_and_role_type(self):
        project = self.env['project.project'].create({'name': 'Meeting Project'})
        meeting = self.env['syg.task.type'].create({'name': 'Client Demo', 'is_meeting': True})
        regular = self.env['syg.task.type'].create({'name': 'Development Work', 'is_meeting': False})
        attendee = self.env['syg.role.type'].create({'name': 'Listener', 'requires_presentation': False})
        presenter = self.env['syg.role.type'].create({'name': 'Trainer', 'requires_presentation': True})
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
        attending = self.env['project.task'].create({
            'name': 'Sit in on the demo',
            'project_id': project.id,
            'syg_task_type_id': meeting.id,
            'syg_attendee_ids': [Command.set(employee.ids)],
            'syg_role_type_id': attendee.id,
            'syg_presentation_time': 2.0,
        })
        self.assertEqual(attending.syg_presentation_time, 0.0)
        request = self.env['syg.task.request'].create({
            'name': 'Training session',
            'employee_id': employee.id,
            'project_id': project.id,
            'syg_task_type_id': meeting.id,
            'syg_attendee_ids': [Command.set(employee.ids)],
            'syg_role_type_id': presenter.id,
            'description': '<p>Agenda for the session</p>',
        })
        self.assertFalse(request.syg_presentation_time)
        request.syg_presentation_time = 1.0
        request.action_submit()
        request.action_create_task()
        task = request.task_id
        self.assertEqual(task.syg_role_type_id, presenter)
        self.assertEqual(task.syg_attendee_ids, employee)
        self.assertEqual(task.syg_presentation_time, 1.0)
        self.assertIn('Agenda', task.description or '')

    def test_employee_user_sees_own_hr_documents(self):
        group = self.env.ref('sygmetiv_company_management.group_company_user')
        user_a = self.env['res.users'].create({
            'name': 'HR Own A',
            'login': 'syg_hr_own_a',
            'group_ids': [Command.set([group.id])],
        })
        user_b = self.env['res.users'].create({
            'name': 'HR Own B',
            'login': 'syg_hr_own_b',
            'group_ids': [Command.set([group.id])],
        })
        manager = self.env['hr.employee'].create({'name': 'HR Own Manager'})
        department = self.env['hr.department'].create({'name': 'HR Own Dept'})
        job = self.env['hr.job'].create({'name': 'HR Own Job'})
        employee_a = self.env['hr.employee'].search([('user_id', '=', user_a.id)], limit=1)
        employee_b = self.env['hr.employee'].search([('user_id', '=', user_b.id)], limit=1)
        if not employee_a:
            employee_a = self.env['hr.employee'].create({
                'name': 'HR Own A',
                'user_id': user_a.id,
            })
        if not employee_b:
            employee_b = self.env['hr.employee'].create({
                'name': 'HR Own B',
                'user_id': user_b.id,
            })
        employee_a.parent_id = manager
        employee_b.write({
            'parent_id': manager.id,
            'department_id': department.id,
            'job_id': job.id,
        })
        outsider = self.env['hr.employee'].create({'name': 'HR Outsider'})

        visible = self.env['hr.employee'].with_user(user_b).search([])
        self.assertIn(employee_b, visible)
        self.assertIn(manager, visible)
        self.assertNotIn(employee_a, visible)
        self.assertNotIn(outsider, visible)
        profile = employee_b.with_user(user_b).read([
            'name', 'department_id', 'job_id', 'job_title', 'parent_id',
            'current_leave_id', 'current_leave_state', 'leave_date_from',
        ])[0]
        self.assertEqual(profile['department_id'][0], department.id)
        self.assertEqual(profile['job_id'][0], job.id)
        self.assertEqual(employee_b.with_user(user_b).parent_id.display_name, manager.name)

        leave_type = self.env['hr.leave.type'].create({
            'name': 'Own Leave',
            'requires_allocation': False,
            'request_unit': 'day',
        })
        today = fields.Date.today()
        leave_b = self.env['hr.leave'].create({
            'name': 'Own day off',
            'employee_id': employee_b.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': today,
            'request_date_to': today,
        })
        leave_a = self.env['hr.leave'].create({
            'name': 'Other day off',
            'employee_id': employee_a.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': today,
            'request_date_to': today,
        })
        leaves = self.env['hr.leave'].with_user(user_b).search([
            ('id', 'in', (leave_a | leave_b).ids),
        ])
        self.assertEqual(leaves, leave_b)
        self.assertEqual(
            leave_b.with_user(user_b).read(['employee_id'])[0]['employee_id'][0],
            employee_b.id,
        )

        attendance_b = self.env['hr.attendance'].create({
            'employee_id': employee_b.id,
            'check_in': fields.Datetime.now(),
        })
        attendance_a = self.env['hr.attendance'].create({
            'employee_id': employee_a.id,
            'check_in': fields.Datetime.now(),
        })
        attendances = self.env['hr.attendance'].with_user(user_b).search([
            ('id', 'in', (attendance_a | attendance_b).ids),
        ])
        self.assertEqual(attendances, attendance_b)
        self.assertEqual(
            attendance_b.with_user(user_b).read(['employee_id', 'check_in'])[0]['employee_id'][0],
            employee_b.id,
        )

        dashboard = self.env['syg.workplace.dashboard'].with_user(user_b)
        self.assertEqual(dashboard.action_menu_timeoff()['res_model'], 'hr.leave')
        attendance_action = dashboard.action_menu_attendance()
        self.assertEqual(attendance_action['res_model'], 'hr.attendance')
        self.assertIn(('employee_id.user_id', '=', user_b.id), attendance_action['domain'])

    def test_employee_user_opens_employee_views(self):
        """Employees menu is the standard hr.employee kanban, which reads
        officer-only fields while drawing presence and the public birthday.
        """
        group = self.env.ref('sygmetiv_company_management.group_company_user')
        user = self.env['res.users'].create({
            'name': 'Employee Views',
            'login': 'syg_employee_views',
            'group_ids': [Command.set([group.id])],
        })
        employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
        if not employee:
            employee = self.env['hr.employee'].create({
                'name': 'Employee Views',
                'user_id': user.id,
            })
        address = self.env['res.partner'].create({
            'name': 'Main Office Address',
            'company_id': self.env.company.id,
        })
        location = self.env['hr.work.location'].create({
            'name': 'Main Office',
            'location_type': 'office',
            'address_id': address.id,
        })
        employee[employee._get_current_day_location_field()] = location

        Employee = self.env['hr.employee'].with_user(user)
        field_names = set()
        views = Employee.get_views([(False, view_type) for view_type in ('kanban', 'list', 'form')])
        form_arch = etree.fromstring(views['views']['form']['arch'])
        self.assertFalse(form_arch.xpath('//chatter'))
        for view in views['views'].values():
            tree = etree.fromstring(view['arch'])
            for node in tree.xpath('//field[@name]'):
                if node.xpath('ancestor::field'):
                    continue
                field_names.add(node.get('name'))
        # Presence widgets request these even when they are not in the arch.
        field_names.update([
            'hr_icon_display', 'show_hr_icon_display', 'hr_presence_state',
            'work_location_name', 'work_location_type',
            'leave_date_to', 'current_leave_id', 'current_leave_state', 'leave_date_from',
            'is_absent', 'birthday_public_display_string',
            'hours_last_month', 'hours_last_month_overtime',
            'hours_today', 'hours_previously_today', 'last_attendance_worked_hours',
            'attendance_state', 'last_check_in',
        ])
        field_names = [name for name in field_names if name in Employee._fields]
        employee.tz = employee.tz or 'UTC'
        profile = employee.with_user(user).read(field_names)[0]
        self.assertEqual(profile['work_location_name'], 'Main Office')
        self.assertEqual(profile['work_location_type'], 'office')
        self.assertEqual(profile['birthday_public_display_string'], 'hidden')
        self.assertTrue(profile['hr_icon_display'])
        self.assertEqual(profile['hours_last_month'], 0)
        self.assertEqual(profile['attendance_state'], 'checked_out')
        from odoo.addons.hr_attendance.controllers.main import HrAttendance
        systray = HrAttendance._get_user_attendance_data(employee.with_user(user))
        self.assertEqual(systray['attendance_state'], 'checked_out')
        self.assertEqual(systray['hours_today'], 0)
        action = self.env.ref('sygmetiv_company_management.action_syg_employees')
        self.assertEqual(action.view_mode, 'kanban,list,form')

    def test_contacts_menu_requires_contact_creation(self):
        self.env['ir.ui.menu']._syg_restrict_optional_menus()
        menu = self.env.ref('contacts.menu_contacts', raise_if_not_found=False)
        if not menu:
            return
        creation = self.env.ref('base.group_partner_manager')
        self.assertEqual(menu.group_ids, creation)
        user = self.env['res.users'].create({
            'name': 'No Contact Create',
            'login': 'syg_no_contact_create',
            'group_ids': [Command.set([self.env.ref('base.group_user').id])],
        })
        self.assertFalse(menu.with_user(user)._filter_visible_menus())
        user.write({'group_ids': [Command.link(creation.id)]})
        self.assertEqual(menu.with_user(user)._filter_visible_menus(), menu)
