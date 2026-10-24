import { onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { isIosApp } from "@web/core/browser/feature_detection";
import kioskApp from "@hr_attendance/public_kiosk/public_kiosk_app";

import { getDeviceCoordinates, locationBlockReason } from "./device_coordinates";

patch(kioskApp.kioskAttendanceApp.prototype, {
    setup() {
        super.setup();
        onWillStart(() => this._sygReadCoordinates());
    },

    _sygWarnLocation(message) {
        if (this._sygLocationWarned === message) {
            return;
        }
        this._sygLocationWarned = message;
        this.displayNotification(message);
    },

    async _sygReadCoordinates() {
        if (!this.props.deviceTrackingEnabled || isIosApp()) {
            return null;
        }
        if (locationBlockReason() === "insecure") {
            this._sygWarnLocation(_t(
                "This address is not allowed to use location, so Chrome will not ask Allow or Block. Open the kiosk as https://, or as http://127.0.0.1 or http://localhost."
            ));
            return null;
        }
        const coords = await getDeviceCoordinates();
        if (!coords) {
            this._sygWarnLocation(_t(
                "GPS position was not available. If no Allow prompt appeared, open the lock icon in the address bar and set Location to Allow."
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
