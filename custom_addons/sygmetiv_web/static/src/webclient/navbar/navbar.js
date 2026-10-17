import { NavBar } from "@web/webclient/navbar/navbar";
import { useBus, useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { useEffect, useRef } from "@odoo/owl";

export class HomeNavBar extends NavBar {
    static template = "sygmetiv_web.NavBar";

    setup() {
        super.setup();
        this.hm = useService("home_menu");
        this.menuAppsRef = useRef("menuApps");
        this.navRef = useRef("nav");
        useBus(this.env.bus, "HOME-MENU:TOGGLED", () => this._updateMenuAppsIcon());
        useEffect(() => this._updateMenuAppsIcon());
    }

    get hasBackgroundAction() {
        return this.hm.hasBackgroundAction;
    }

    get isInApp() {
        return !this.hm.hasHomeMenu;
    }

    _openAppMenuSidebar() {
        if (this.hm.hasHomeMenu) {
            this.hm.toggle(false);
        } else {
            this.state.isAppMenuSidebarOpened = true;
        }
    }

    onAllAppsBtnClick() {
        super.onAllAppsBtnClick();
        this.hm.toggle(true);
        this._closeAppMenuSidebar();
    }

    _updateMenuAppsIcon() {
        const menuAppsEl = this.menuAppsRef.el;
        if (!menuAppsEl) {
            return;
        }
        menuAppsEl.classList.toggle("o_hidden", !this.isInApp && !this.hasBackgroundAction);
        menuAppsEl.classList.toggle("o_menu_toggle_back", !this.isInApp && this.hasBackgroundAction);
        const title =
            !this.isInApp && this.hasBackgroundAction ? _t("Previous view") : _t("Home menu");
        menuAppsEl.title = title;
        menuAppsEl.ariaLabel = title;

        const navEl = this.navRef.el;
        if (!navEl) {
            return;
        }
        navEl.querySelector(".o_menu_brand")?.classList.toggle("o_hidden", !this.isInApp);
        navEl.querySelector(".o_menu_brand_icon")?.classList.toggle("o_hidden", !this.isInApp);
        this.appSubMenus.el?.classList.toggle("o_hidden", !this.isInApp);
        navEl.querySelector(".o_breadcrumb")?.classList.toggle("o_hidden", !this.isInApp);
        navEl.querySelector(".o_navbar_breadcrumbs")?.classList.toggle("o_hidden", !this.isInApp);
    }
}
