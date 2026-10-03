/**
 * Simple Canvas-based Chart Renderer.
 * Draws line charts and bar charts for benchmark results.
 */

class SimpleChart {
    /**
     * @param {HTMLCanvasElement} canvas
     */
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.padding = { top: 40, right: 30, bottom: 50, left: 60 };
    }

    /**
     * Clear the canvas.
     */
    clear() {
        const ctx = this.ctx;
        ctx.fillStyle = '#12122a';
        ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }

    /**
     * Draw a line chart with multiple series.
     * @param {Object} data
     * @param {Array<number>} data.labels - X-axis labels
     * @param {Array<Object>} data.series - [{name, values, color}]
     * @param {string} data.title
     * @param {string} data.xLabel
     * @param {string} data.yLabel
     */
    drawLineChart(data) {
        this.clear();
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;
        const p = this.padding;

        const chartW = w - p.left - p.right;
        const chartH = h - p.top - p.bottom;

        // Find Y range
        let yMin = Infinity, yMax = -Infinity;
        for (const s of data.series) {
            for (const v of s.values) {
                if (v < yMin) yMin = v;
                if (v > yMax) yMax = v;
            }
        }
        if (yMin === yMax) { yMin -= 1; yMax += 1; }
        const yPad = (yMax - yMin) * 0.1;
        yMin -= yPad;
        yMax += yPad;
        if (yMin < 0) yMin = 0;

        // Draw axes
        ctx.strokeStyle = '#3a3a5e';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(p.left, p.top);
        ctx.lineTo(p.left, h - p.bottom);
        ctx.lineTo(w - p.right, h - p.bottom);
        ctx.stroke();

        // X labels
        ctx.fillStyle = '#8888aa';
        ctx.font = '11px Consolas, monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        const labels = data.labels;
        for (let i = 0; i < labels.length; i++) {
            const x = p.left + (i / (labels.length - 1 || 1)) * chartW;
            ctx.fillText(labels[i].toString(), x, h - p.bottom + 8);

            // Grid line
            ctx.strokeStyle = '#1e1e3e';
            ctx.beginPath();
            ctx.moveTo(x, p.top);
            ctx.lineTo(x, h - p.bottom);
            ctx.stroke();
        }

        // Y labels
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        const ySteps = 5;
        for (let i = 0; i <= ySteps; i++) {
            const val = yMin + (yMax - yMin) * (i / ySteps);
            const y = h - p.bottom - (i / ySteps) * chartH;
            ctx.fillStyle = '#8888aa';
            ctx.fillText(val.toFixed(1), p.left - 8, y);

            ctx.strokeStyle = '#1e1e3e';
            ctx.beginPath();
            ctx.moveTo(p.left, y);
            ctx.lineTo(w - p.right, y);
            ctx.stroke();
        }

        // Draw series
        for (const series of data.series) {
            ctx.strokeStyle = series.color;
            ctx.lineWidth = 2.5;
            ctx.beginPath();

            for (let i = 0; i < series.values.length; i++) {
                const x = p.left + (i / (labels.length - 1 || 1)) * chartW;
                const y = h - p.bottom - ((series.values[i] - yMin) / (yMax - yMin)) * chartH;

                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.stroke();

            // Data points
            for (let i = 0; i < series.values.length; i++) {
                const x = p.left + (i / (labels.length - 1 || 1)) * chartW;
                const y = h - p.bottom - ((series.values[i] - yMin) / (yMax - yMin)) * chartH;

                ctx.fillStyle = series.color;
                ctx.beginPath();
                ctx.arc(x, y, 4, 0, Math.PI * 2);
                ctx.fill();

                ctx.fillStyle = '#0a0a1a';
                ctx.beginPath();
                ctx.arc(x, y, 2, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        // Title
        ctx.fillStyle = '#e0e0ff';
        ctx.font = 'bold 14px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(data.title, w / 2, 8);

        // Axis labels
        ctx.fillStyle = '#8888aa';
        ctx.font = '12px Consolas, monospace';
        ctx.fillText(data.xLabel || '', w / 2, h - 12);

        ctx.save();
        ctx.translate(14, h / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillText(data.yLabel || '', 0, 0);
        ctx.restore();

        // Legend
        let legendX = p.left + 10;
        const legendY = p.top + 5;
        ctx.font = '11px Consolas, monospace';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        for (const series of data.series) {
            ctx.fillStyle = series.color;
            ctx.fillRect(legendX, legendY, 12, 3);
            ctx.fillStyle = '#c0c0e0';
            ctx.fillText(series.name, legendX + 16, legendY + 2);
            legendX += ctx.measureText(series.name).width + 30;
        }
    }

    /**
     * Draw a grouped bar chart.
     */
    drawBarChart(data) {
        this.clear();
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;
        const p = this.padding;

        const chartW = w - p.left - p.right;
        const chartH = h - p.top - p.bottom;

        const labels = data.labels;
        const numGroups = labels.length;
        const numSeries = data.series.length;
        const groupWidth = chartW / numGroups;
        const barWidth = (groupWidth * 0.7) / numSeries;

        // Find Y range
        let yMax = 0;
        for (const s of data.series) {
            for (const v of s.values) {
                if (v > yMax) yMax = v;
            }
        }
        yMax *= 1.15;
        if (yMax === 0) yMax = 1;

        // Draw axes
        ctx.strokeStyle = '#3a3a5e';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(p.left, p.top);
        ctx.lineTo(p.left, h - p.bottom);
        ctx.lineTo(w - p.right, h - p.bottom);
        ctx.stroke();

        // X labels
        ctx.fillStyle = '#8888aa';
        ctx.font = '11px Consolas, monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        for (let i = 0; i < numGroups; i++) {
            const x = p.left + (i + 0.5) * groupWidth;
            ctx.fillText(labels[i].toString(), x, h - p.bottom + 8);
        }

        // Y labels
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        const ySteps = 5;
        for (let i = 0; i <= ySteps; i++) {
            const val = (yMax * i) / ySteps;
            const y = h - p.bottom - (i / ySteps) * chartH;
            ctx.fillStyle = '#8888aa';
            ctx.fillText(val.toFixed(1), p.left - 8, y);
            ctx.strokeStyle = '#1e1e3e';
            ctx.beginPath();
            ctx.moveTo(p.left, y);
            ctx.lineTo(w - p.right, y);
            ctx.stroke();
        }

        // Draw bars
        for (let g = 0; g < numGroups; g++) {
            for (let s = 0; s < numSeries; s++) {
                const val = data.series[s].values[g];
                const barH = (val / yMax) * chartH;
                const x = p.left + g * groupWidth + (groupWidth * 0.15) + s * barWidth;
                const y = h - p.bottom - barH;

                // Solid 2000s bar
                ctx.fillStyle = data.series[s].color;
                ctx.fillRect(x, y, barWidth - 2, barH);
                ctx.strokeStyle = '#000000';
                ctx.lineWidth = 1;
                ctx.strokeRect(x, y, barWidth - 2, barH);

                // Value label
                ctx.fillStyle = '#c0c0e0';
                ctx.font = '10px Consolas, monospace';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'bottom';
                ctx.fillText(val.toFixed(1), x + barWidth / 2, y - 3);
            }
        }

        // Title
        ctx.fillStyle = '#e0e0ff';
        ctx.font = 'bold 14px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(data.title, w / 2, 8);

        // Axis labels
        ctx.fillStyle = '#8888aa';
        ctx.font = '12px Consolas, monospace';
        ctx.fillText(data.xLabel || '', w / 2, h - 12);

        // Legend
        let legendX = p.left + 10;
        const legendY = p.top + 5;
        ctx.font = '11px Consolas, monospace';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        for (const series of data.series) {
            ctx.fillStyle = series.color;
            ctx.fillRect(legendX, legendY, 12, 8);
            ctx.fillStyle = '#c0c0e0';
            ctx.fillText(series.name, legendX + 16, legendY + 4);
            legendX += ctx.measureText(series.name).width + 30;
        }
    }
}
