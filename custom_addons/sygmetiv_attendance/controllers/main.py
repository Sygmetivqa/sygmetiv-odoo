# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.hr_attendance.controllers.main import HrAttendance as AttendanceController
from odoo.addons.sygmetiv_attendance.models.attendance_geofence import coordinates_present


def _location_from_coordinates(latitude, longitude):
    """Place name for a browser GPS fix. IP geolocation is not used."""
    try:
        result = request.env['base.geocoder']._call_openstreetmap_reverse(latitude, longitude)
    except UserError:
        return _("Unknown")
    if not result or not (address := result.get('address')):
        return _("Unknown")
    country_code = address.get('country_code')
    city = (
        address.get('city_district')
        or address.get('town')
        or address.get('village')
        or address.get('city')
    )
    country = False
    if country_code:
        country = request.env['res.country'].sudo().search(
            [('code', '=', country_code.upper())], limit=1,
        )
    res = address.get('postcode') or ''
    if city:
        res = f"{res} {city}".strip() if res else city
    if country:
        res = f"{res}, {country.name}" if res else country.name
    return res or _("Unknown")


class SygHrAttendance(AttendanceController):

    @staticmethod
    def _get_geoip_response(mode, latitude=False, longitude=False, device_tracking_enabled=True):
        """Keep the browser GPS only.

        Odoo otherwise copies the IP geolocation into the GPS fields. On
        localhost that is 0,0, which is a point in the ocean, and on a real
        network it is the provider's city rather than the employee.
        """
        response = {'mode': mode}
        if not device_tracking_enabled:
            return response
        has_gps = coordinates_present(latitude, longitude)
        response.update({
            'location': _location_from_coordinates(latitude, longitude) if has_gps else _("Unknown"),
            'latitude': latitude if has_gps else False,
            'longitude': longitude if has_gps else False,
            'ip_address': request.geoip.ip,
            'browser': request.httprequest.user_agent.browser,
        })
        return response

    @http.route()
    def manual_selection(self, token, employee_id, pin_code, latitude=False, longitude=False):
        # Dispatch on this controller so the GPS response above is the one used.
        return super().manual_selection(
            token, employee_id, pin_code, latitude=latitude, longitude=longitude,
        )

    @http.route()
    def systray_attendance(self, latitude=False, longitude=False):
        return super().systray_attendance(latitude=latitude, longitude=longitude)

    @http.route()
    def scan_barcode(self, token, barcode, latitude=False, longitude=False):
        company = self._get_company(token)
        if company:
            employee = request.env['hr.employee'].sudo().search([
                ('barcode', '=', barcode),
                ('company_id', '=', company.id),
            ], limit=1)
            if employee:
                employee._attendance_action_change(self._get_geoip_response(
                    'kiosk',
                    latitude=latitude,
                    longitude=longitude,
                    device_tracking_enabled=company.attendance_device_tracking,
                ))
                return self._get_employee_info_response(employee)
        return {}
