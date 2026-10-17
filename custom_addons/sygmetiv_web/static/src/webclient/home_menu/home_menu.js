import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, useRef, useState } from "@odoo/owl";

export class HomeMenu extends Component {
    static template = "sygmetiv_web.HomeMenu";
    static props = {
        apps: { type: Array },
    };

    setup() {
        this.menus = useService("menu");
        this.homeMenuService = useService("home_menu");
        this.state = useState({
            focusedIndex: 0,
            query: "",
        });
        this.inputRef = useRef("input");

        useHotkey("Escape", () => this.homeMenuService.toggle(false));
        useHotkey("Enter", () => {
            const app = this.displayedApps[this.state.focusedIndex];
            if (app) {
                this.openApp(app);
            }
        });
        useHotkey("ArrowRight", () => this.moveFocus(1));
        useHotkey("ArrowLeft", () => this.moveFocus(-1));
        useHotkey("ArrowDown", () => this.moveFocus(6));
        useHotkey("ArrowUp", () => this.moveFocus(-6));

        onMounted(() => {
            this.inputRef.el?.focus({ preventScroll: true });
        });
    }

    get displayedApps() {
        const query = this.state.query.trim().toLowerCase();
        if (!query) {
            return this.props.apps;
        }
        return this.props.apps.filter((app) => (app.label || "").toLowerCase().includes(query));
    }

    moveFocus(delta) {
        const count = this.displayedApps.length;
        if (!count) {
            return;
        }
        this.state.focusedIndex = (this.state.focusedIndex + delta + count * 10) % count;
    }

    openApp(app) {
        return this.menus.selectMenu(app);
    }
}
