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

export function locationBlockReason() {
    // Chrome and Firefox never show Allow/Block on plain http, except
    // localhost and 127.0.0.1. The site setting stays disabled.
    if (!window.isSecureContext) {
        return "insecure";
    }
    if (isIosApp() || !navigator.geolocation) {
        return "unavailable";
    }
    return null;
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
    if (locationBlockReason()) {
        return null;
    }
    const permission = await permissionState();
    // A previous Block does not show the dialog again. Ask anyway when the
    // browser still says it will prompt.
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
