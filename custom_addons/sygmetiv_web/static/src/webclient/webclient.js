import { WebClient } from "@web/webclient/webclient";
import { useService } from "@web/core/utils/hooks";
import { HomeNavBar } from "./navbar/navbar";

export class WebClientHomeMenu extends WebClient {
    static components = {
        ...WebClient.components,
        NavBar: HomeNavBar,
    };

    setup() {
        super.setup();
        this.hm = useService("home_menu");
    }

    _loadDefaultApp() {
        return this.hm.toggle(true);
    }
}
