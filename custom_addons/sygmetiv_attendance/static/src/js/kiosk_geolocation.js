import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { isIosApp } from "@web/core/browser/feature_detection";
import kioskApp from "@hr_attendance/public_kiosk/public_kiosk_app";

import { getDeviceCoordinates } from "./device_coordinates";

patch(kioskApp.kioskAttendanceApp.prototype, {
    async _sygReadCoordinates() {
        if (!this.props.deviceTrackingEnabled || isIosApp()) {
            return null;
        }
        const coords = await getDeviceCoordinates();
        if (!coords) {
            this.displayNotification(_t(
                "GPS position was not available. Allow location access for this site, then try again."
            ));
        }
        return coords;
    },

    async makeRpcWithGeolocation(route, params) {
        const coords = await this._sygReadCoordinates();
        return rpc(route, { ...params, ...(coords || {}) });
    },

    async onBarcodeScanned(barcode) {
        if (this.lockScanner || this.state.active_display !== "main") {
            return;
        }
        this.lockScanner = true;
        let result;
        try {
            const coords = await this._sygReadCoordinates();
            this.ui.block();
            result = await rpc("attendance_barcode_scanned", {
                barcode,
                token: this.props.token,
                ...(coords || {}),
            });
            if (result && result.employee_name) {
                this.employeeData = result;
                this.switchDisplay("greet");
            } else {
                this.displayNotification(
                    _t("No employee corresponding to Badge ID '%(barcode)s.'", { barcode })
                );
            }
        } catch (error) {
            const message = error && error.data && error.data.message;
            if (message) {
                this.displayNotification(message);
            }
        } finally {
            this.lockScanner = false;
            this.ui.unblock();
        }
    },
});
