import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState } from "@odoo/owl";

function parsePayload(raw) {
    if (!raw) {
        return { lines: [], title: "", period: "", symbol: "", compare: false, aged: false, trial: false };
    }
    try {
        return typeof raw === "string" ? JSON.parse(raw) : raw;
    } catch {
        return { lines: [] };
    }
}

export class SygMisBoardField extends Component {
    static template = "sygmetiv_accounting.SygMisBoardField";
    static props = { ...standardFieldProps };

    setup() {
        this.state = useState({ folded: {}, unfoldAll: true });
    }

    get data() {
        return parsePayload(this.props.record.data[this.props.name]);
    }

    visibleLines() {
        const lines = this.data.lines || [];
        const visible = [];
        let skipUntil = null;
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const level = line.level || 0;
            if (skipUntil !== null) {
                if (level > skipUntil) {
                    continue;
                }
                skipUntil = null;
            }
            visible.push({ ...line, index: i });
            if (line.type === "section" && this.isFolded(i)) {
                skipUntil = level;
            }
        }
        return visible;
    }

    isFolded(index) {
        return Boolean(this.state.folded[index]);
    }

    toggleFold(index, ev) {
        ev.stopPropagation();
        this.state.unfoldAll = false;
        this.state.folded[index] = !this.state.folded[index];
    }

    toggleUnfold() {
        if (this.state.unfoldAll) {
            const folded = {};
            (this.data.lines || []).forEach((line, i) => {
                if (line.type === "section") {
                    folded[i] = true;
                }
            });
            this.state.folded = folded;
            this.state.unfoldAll = false;
        } else {
            this.state.folded = {};
            this.state.unfoldAll = true;
        }
    }

    formatAmount(value) {
        const number = Number(value) || 0;
        if (!number) {
            return "0.00";
        }
        const formatted = Math.abs(number).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        return number < 0 ? `(${formatted})` : formatted;
    }

    formatPercent(value) {
        const number = Number(value) || 0;
        return `${number.toFixed(1)}%`;
    }

    isNegative(value) {
        return Number(value) < 0;
    }

    async openLine(line) {
        if (!line.account_id && !line.partner_id) {
            return;
        }
        const action = await this.env.services.orm.call(
            "syg.mis.report",
            "action_open_move_lines",
            [this.props.record.resId, line.account_id || false, line.partner_id || false]
        );
        if (action) {
            await this.env.services.action.doAction(action);
        }
    }
}

registry.category("fields").add("syg_mis_board", {
    component: SygMisBoardField,
    supportedTypes: ["text", "char", "html"],
});
