import { isIosApp } from "@web/core/browser/feature_detection";

const ACCURATE_FIX = { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 };
const COARSE_FIX = { enableHighAccuracy: false, timeout: 10000, maximumAge: 15000 };
const PERMISSION_PROMPT = { enableHighAccuracy: true, timeout: 60000, maximumAge: 0 };

function coordinatesAreReal(latitude, longitude) {
    return Math.abs(latitude || 0) >= 1e-7 || Math.abs(longitude || 0) >= 1e-7;
}

function readPosition(options) {
    return new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(
            (position) => resolve(position.coords),
            (error) => reject(error),
            options,
        );
    });
}

async function permissionState() {
    if (!navigator.permissions || !navigator.permissions.query) {
        return "prompt";
    }
    try {
        const status = await navigator.permissions.query({ name: "geolocation" });
        return status.state || "prompt";
    } catch {
        return "prompt";
    }
}

/**
 * Browser GPS for attendance. A desktop often has no high-accuracy chip, so a
 * failed precise reading is followed by a network fix. 0,0 is discarded.
 */
export async function getDeviceCoordinates() {
    if (isIosApp() || !navigator.geolocation) {
        return null;
    }
    const permission = await permissionState();
    if (permission === "denied") {
        return null;
    }
    const attempts = permission === "granted"
        ? [ACCURATE_FIX, COARSE_FIX]
        : [PERMISSION_PROMPT, COARSE_FIX];
    for (const options of attempts) {
        try {
            const { latitude, longitude } = await readPosition(options);
            if (coordinatesAreReal(latitude, longitude)) {
                return { latitude, longitude };
            }
        } catch (error) {
            if (error && error.code === 1) {
                return null;
            }
        }
    }
    return null;
}
