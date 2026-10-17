import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { getColor, hexToRGBA } from "@web/core/colors/colors";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onWillStart, useEffect, useRef } from "@odoo/owl";
import { cookie } from "@web/core/browser/cookie";

function parseGraphData(raw) {
    if (!raw) {
        return null;
    }
    try {
        const data = typeof raw === "string" ? JSON.parse(raw) : raw;
        if (Array.isArray(data) && data[0] && Array.isArray(data[0].values)) {
            return data;
        }
    } catch {
        return null;
    }
    return null;
}

export class SygDashboardGraphField extends Component {
    static template = "sygmetiv_company_management.SygDashboardGraphField";
    static props = {
        ...standardFieldProps,
        graphType: { type: String, optional: true },
        colorOffset: { type: Number, optional: true },
    };

    setup() {
        this.chart = null;
        this.canvasRef = useRef("canvas");
        onWillStart(async () => await loadBundle("web.chartjs_lib"));
        useEffect(
            () => {
                this.renderChart();
                return () => {
                    if (this.chart) {
                        this.chart.destroy();
                        this.chart = null;
                    }
                };
            },
            () => [this.props.record.data[this.props.name], this.graphType]
        );
    }

    get graphType() {
        return this.props.graphType || "bar";
    }

    get colorOffset() {
        return this.props.colorOffset || 0;
    }

    barColor(index) {
        return getColor(((index + this.colorOffset) % 9) + 1, cookie.get("color_scheme"), "odoo");
    }

    chartLabel(raw) {
        const text = raw || "";
        return text.includes("\n") ? text.split("\n") : text;
    }

    labelText(label) {
        return Array.isArray(label) ? label.filter(Boolean).join(" · ") : String(label || "");
    }

    fitCategoryAxis(options, labels) {
        const longest = Math.max(0, ...labels.map((label) => this.labelText(label).length));
        if (labels.length < 6 && longest < 16) {
            return;
        }
        options.layout.autoPadding = true;
        options.layout.padding = { top: 4, right: 12, bottom: 4, left: 4 };
        options.scales.x.ticks.maxRotation = 45;
        options.scales.x.ticks.minRotation = 45;
        options.scales.x.ticks.autoSkip = false;
        options.scales.x.ticks.font = { size: 11 };
        const self = this;
        options.scales.x.ticks.callback = function (value) {
            const text = self.labelText(this.getLabelForValue(value));
            return text.length > 32 ? `${text.slice(0, 31)}…` : text;
        };
    }

    get graphData() {
        return parseGraphData(this.props.record.data[this.props.name]);
    }

    sizeCanvas(height = 200) {
        const canvas = this.canvasRef.el;
        if (!canvas || !canvas.parentElement) {
            return;
        }
        const width = Math.max(canvas.parentElement.clientWidth || 280, 160);
        canvas.width = width;
        canvas.height = height;
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;
    }

    commonOptions(label) {
        return {
            responsive: false,
            maintainAspectRatio: false,
            resizeDelay: 0,
            animation: false,
            animations: false,
            layout: {
                autoPadding: false,
                padding: 8,
            },
            interaction: {
                mode: "nearest",
                intersect: true,
                axis: "xy",
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    enabled: true,
                    animation: false,
                    intersect: true,
                    mode: "nearest",
                    position: "nearest",
                    displayColors: false,
                    padding: 8,
                    caretPadding: 4,
                    callbacks: {
                        title: (items) => (items[0] && items[0].label) || "",
                        label: (item) => `${label}: ${item.formattedValue}`,
                    },
                },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0 },
                    grace: 0,
                },
                x: {
                    ticks: {
                        maxRotation: 0,
                        minRotation: 0,
                        autoSkip: false,
                        font: { size: 11 },
                    },
                    grid: { display: false },
                },
            },
        };
    }

    renderChart() {
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
        const canvas = this.canvasRef.el;
        const data = this.graphData;
        if (!canvas || typeof Chart === "undefined" || !data) {
            return;
        }
        const stacked = this.graphType === "stacked" || data.length > 1;
        const wide = Boolean(canvas.parentElement?.closest(".o_syg_chart_wide"));
        this.sizeCanvas(stacked || wide ? 380 : 200);
        const config = this.graphType === "line"
            ? this.getLineChartConfig(data)
            : stacked
                ? this.getStackedBarChartConfig(data)
                : this.getBarChartConfig(data);
        this.chart = new Chart(canvas, config);
    }

    getStackedBarChartConfig(data) {
        const labels = (data[0].values || []).map((pt) => this.chartLabel(pt.label || pt.x || ""));
        const datasets = data.map((series, index) => ({
            label: series.key || "",
            data: (series.values || []).map((pt) => pt.value ?? pt.y ?? 0),
            backgroundColor: this.barColor(index),
            borderWidth: 0,
            hoverBorderWidth: 0,
            maxBarThickness: 36,
        }));
        if (datasets.length === 1) {
            datasets[0].backgroundColor = labels.map((_label, index) => this.barColor(index));
        }
        const flat = datasets.flatMap((dataset) => dataset.data);
        const options = this.commonOptions("");
        options.scales.x.stacked = true;
        options.scales.y.stacked = true;
        options.scales.y.suggestedMax = Math.max(...flat, 1);
        options.layout.autoPadding = true;
        options.layout.padding = { top: 4, right: 8, bottom: 4, left: 4 };
        options.scales.x.ticks.maxRotation = 45;
        options.scales.x.ticks.minRotation = 45;
        options.scales.x.ticks.font = { size: 11 };
        options.scales.x.ticks.callback = function (value) {
            const label = this.getLabelForValue(value);
            const text = Array.isArray(label) ? label.filter(Boolean).join(" · ") : String(label || "");
            return text.length > 24 ? `${text.slice(0, 23)}…` : text;
        };
        options.plugins.legend.display = datasets.length > 1;
        options.plugins.legend.position = "bottom";
        options.plugins.tooltip.displayColors = true;
        options.plugins.tooltip.mode = "index";
        options.plugins.tooltip.intersect = false;
        options.plugins.tooltip.callbacks.title = (items) => {
            const label = items[0] && items[0].label;
            return Array.isArray(label) ? label.join(" · ") : label || "";
        };
        options.plugins.tooltip.callbacks.label = (item) => `${item.dataset.label}: ${item.formattedValue}`;
        return {
            type: "bar",
            data: { labels, datasets },
            options,
        };
    }

    getBarChartConfig(data) {
        const series = data[0];
        const labels = [];
        const values = [];
        const backgroundColor = [];
        series.values.forEach((pt, index) => {
            labels.push(this.chartLabel(pt.label || pt.x || ""));
            values.push(pt.value ?? pt.y ?? 0);
            backgroundColor.push(pt.type === "future" ? this.barColor(index + 3) : this.barColor(index));
        });
        const options = this.commonOptions(series.key || "");
        options.scales.y.suggestedMax = Math.max(...values, 1);
        this.fitCategoryAxis(options, labels);
        return {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        backgroundColor,
                        data: values,
                        label: series.key || "",
                        borderWidth: 0,
                        hoverBorderWidth: 0,
                        maxBarThickness: 28,
                    },
                ],
            },
            options,
        };
    }

    getLineChartConfig(data) {
        const series = data[0];
        const labels = [];
        const values = [];
        for (const pt of series.values) {
            labels.push(pt.x || pt.label || "");
            values.push(pt.y ?? pt.value ?? 0);
        }
        const color = getColor(3, cookie.get("color_scheme"), "odoo");
        const options = this.commonOptions(series.key || "");
        options.scales.y.suggestedMax = Math.max(...values, 1);
        options.elements = {
            point: { radius: 3, hoverRadius: 3, hitRadius: 10, hoverBorderWidth: 1 },
            line: { tension: 0, borderWidth: 2 },
        };
        return {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        backgroundColor: hexToRGBA(color, 0.12),
                        borderColor: color,
                        data: values,
                        fill: false,
                        spanGaps: true,
                        label: series.key || "",
                        borderWidth: 2,
                        pointRadius: 3,
                        pointHoverRadius: 3,
                        pointHitRadius: 10,
                        tension: 0,
                    },
                ],
            },
            options,
        };
    }
}

export const sygDashboardGraphField = {
    component: SygDashboardGraphField,
    supportedTypes: ["text", "char", "html"],
    extractProps: ({ attrs, options }) => ({
        graphType: (options && options.graph_type) || (attrs && attrs.graph_type) || "bar",
        colorOffset: Number((options && options.color_offset) || 0),
    }),
};

registry.category("fields").add("syg_dashboard_graph", sygDashboardGraphField);
