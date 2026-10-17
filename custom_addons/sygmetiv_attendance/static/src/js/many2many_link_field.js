import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2ManyTagsField, many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";

export class SygMany2ManyLinksField extends Many2ManyTagsField {
    static template = "sygmetiv_attendance.Many2ManyLinksField";

    setup() {
        super.setup();
        this.action = useService("action");
    }

    onLinkClick(tag) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: tag.text,
            res_model: this.relation,
            res_id: tag.resId,
            views: [[false, "form"]],
            view_mode: "form",
            target: "current",
        });
    }
}

registry.category("fields").add("syg_many2many_links", {
    ...many2ManyTagsField,
    component: SygMany2ManyLinksField,
});
