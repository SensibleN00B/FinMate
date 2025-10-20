(function () {
    'use strict';

    const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
    const nf = new Intl.NumberFormat(undefined, {maximumFractionDigits: 0});

    function initTopCategoriesChart() {
        const el = document.getElementById('chart_top_expenses');
        const dataEl = document.getElementById('top-cats-data');
        if (!el || !dataEl || !window.Chart) return;

        let rows = [];
        try {
            rows = JSON.parse(dataEl.textContent || '[]');
        } catch (_) {
        }
        if (!rows.length) return;

        const labels = rows.map((r) => r.name || '—');
        const values = rows.map((r) => Number(r.total) || 0);
        const total = values.reduce((a, b) => a + b, 0) || 1;
        const MIN_PCT = 3;

        if (window.ChartDataLabels) Chart.register(window.ChartDataLabels);

        const legendColor = css('--bs-body-color') || '#334155';

        new Chart(el, {
            type: 'doughnut',
            data: {labels, datasets: [{data: values}]},
            options: {
                responsive: true,
                cutout: '55%',
                plugins: {
                    legend: {position: 'bottom', labels: {color: legendColor}},
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const v = ctx.parsed;
                                const pct = Math.round((v / total) * 100);
                                return `${ctx.label}: ${v.toLocaleString()} (${pct}%)`;
                            }
                        }
                    },
                    datalabels: window.ChartDataLabels ? {
                        color: '#fff',
                        font: {weight: '600', size: 12},
                        formatter: (v, ctx) => {
                            const pct = Math.round((v / total) * 100);
                            if (pct < MIN_PCT) return '';
                            const name = ctx.chart.data.labels[ctx.dataIndex] || '';
                            return `${name}\n${pct}%`;
                        },
                        anchor: 'center',
                        align: 'center',
                        clamp: true
                    } : undefined
                }
            }
        });
    }

    function initAccountsChart() {
        const host = document.getElementById('chart_accounts');
        const dataEl = document.getElementById('accounts-chart-data');
        if (!host || !dataEl || !window.Chart) return;

        let ac = {};
        try {
            ac = JSON.parse(dataEl.textContent || '{}');
        } catch (_) {
            ac = {};
        }
        if (!ac.labels || !ac.labels.length) return;

        const textColor = css('--bs-body-color') || '#1f2937';
        const gridColor = css('--bs-border-color') || '#e5e7eb';
        const onBarColor = '#f8fafc';

        const makePalette = (n, startHue = 210) =>
            Array.from({length: n}, (_, i) => {
                const h = (startHue + (360 / n) * i) % 360;
                return {bg: `hsl(${h} 70% 52% / .75)`, br: `hsl(${h} 70% 45% / 1)`};
            });
        const pal = makePalette(ac.values.length);

        const percentLabel = {
            id: 'percentLabel',
            afterDatasetsDraw(chart) {
                const ctx = chart.ctx;
                const ds = chart.data.datasets[0];
                const meta = chart.getDatasetMeta(0);
                const sum = ds.data.reduce((a, b) => a + b, 0) || 1;

                ctx.save();
                ctx.fillStyle = textColor;
                ctx.font = '12px system-ui,Segoe UI,Roboto,Inter,sans-serif';

                meta.data.forEach(function (bar, i) {
                    const v = ds.data[i];
                    const pct = Math.round((v / sum) * 100);
                    const p = bar.getProps(['x', 'y', 'base'], true);
                    ctx.textAlign = 'left';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(pct + '%', Math.max(p.x, p.base) + 8, p.y);
                });
                ctx.restore();
            }
        };

        new Chart(host.getContext('2d'), {
            type: 'bar',
            data: {
                labels: ac.labels,
                datasets: [{
                    data: ac.values,
                    backgroundColor: pal.map((p) => p.bg),
                    borderColor: pal.map((p) => p.br),
                    borderWidth: 1.5,
                    borderRadius: 10,
                    barPercentage: 0.75,
                    categoryPercentage: 0.8
                }]
            },
            options: {
                indexAxis: 'y',
                maintainAspectRatio: false,
                plugins: {
                    legend: {display: false},
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,.85)',
                        borderColor: gridColor,
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: (ctx) => {
                                const v = ctx.parsed.x || 0;
                                const pct = ac.total ? Math.round((v / ac.total) * 100) : 0;
                                return `${nf.format(v)} ${ac.currency || ''} — ${pct}%`;
                            }
                        }
                    },
                    datalabels: window.ChartDataLabels ? {
                        color: onBarColor,
                        formatter: (v) => nf.format(v),
                        anchor: 'center',
                        align: 'center',
                        clip: true,
                        font: {weight: 700},
                        textStrokeColor: 'rgba(0,0,0,.35)',
                        textStrokeWidth: 2
                    } : undefined
                },
                scales: {
                    x: {
                        ticks: {
                            color: textColor,
                            callback: (v) => nf.format(v) + (ac.currency ? ` ${ac.currency}` : '')
                        },
                        grid: {color: gridColor, drawTicks: false}
                    },
                    y: {ticks: {color: textColor}, grid: {display: false}}
                }
            },
            plugins: [percentLabel]
        });
    }

    function initCharts() {
        initTopCategoriesChart();
        initAccountsChart();
    }

    document.addEventListener('DOMContentLoaded', initCharts);

    const mo = new MutationObserver((records) => {
        for (const r of records) {
            if (r.type === 'attributes' && r.attributeName === 'data-bs-theme') {
                if (window.Chart && Chart.instances) {
                    Object.values(Chart.instances).forEach((inst) => inst.destroy());
                }
                initCharts();
            }
        }
    });
    mo.observe(document.documentElement, {attributes: true});
})();
