import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { ActivityMenu } from "@hr_attendance/components/attendance_menu/attendance_menu";

import { getDeviceCoordinates } from "./device_coordinates";

patch(ActivityMenu.prototype, {
    async signInOut() {
        this.dropdown.close();
        const trackingEnabled = this.employee && this.employee.device_tracking_enabled;
        const coords = trackingEnabled ? await getDeviceCoordinates() : null;
        this.employee = await rpc("/hr_attendance/systray_check_in_out", coords || {});
        this._searchReadEmployeeFill();
    },
});
