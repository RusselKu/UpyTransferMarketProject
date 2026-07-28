/* charts.js
 * Toda la lógica de Chart.js (Analytics Hub). Este archivo se inyecta
 * dinámicamente la primera vez que se abre el modal de Analytics
 * (ver loadChartsModuleAndRender en main.js) para no bloquear la carga inicial.
 */

let chartDegree = null;
let chartBetweenness = null;
let chartFinancials = null;
let chartDivisions = null;

function renderAnalyticsCharts() {
    const clubsOnly = clubNodes;

    // Chart 1: Degree Distribution with explicit X and Y axis labels
    if (chartDegree) chartDegree.destroy();
    const degreeCounts = {};
    clubsOnly.forEach(n => { degreeCounts[n.degree] = (degreeCounts[n.degree] || 0) + 1; });
    const degLabels = Object.keys(degreeCounts).sort((a, b) => a - b);
    const degData = degLabels.map(k => degreeCounts[k]);

    const ctxDegree = document.getElementById('chart-degree').getContext('2d');
    const gradientDegree = ctxDegree.createLinearGradient(0, 0, 0, 200);
    gradientDegree.addColorStop(0, 'rgba(124, 58, 237, 0.7)');
    gradientDegree.addColorStop(1, 'rgba(124, 58, 237, 0.05)');

    chartDegree = new Chart(ctxDegree, {
        type: 'bar',
        data: {
            labels: degLabels.map(l => `${l} Traspasos`),
            datasets: [
                {
                    type: 'line',
                    label: 'Curva Ley de Potencia (Scale-Free)',
                    data: degData,
                    borderColor: '#a855f7',
                    borderWidth: 3,
                    tension: 0.4,
                    pointBackgroundColor: '#c084fc',
                    pointRadius: 4,
                    fill: false
                },
                {
                    type: 'bar',
                    label: 'Frecuencia (Nº de Clubes)',
                    data: degData,
                    backgroundColor: gradientDegree,
                    borderColor: '#7c3aed',
                    borderWidth: 1,
                    borderRadius: 8
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#cbd5e1', font: { family: 'Outfit', size: 10 } } }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Eje X: Número de Traspasos por Club (Grado K)', color: '#94a3b8', font: { family: 'Outfit', size: 10, weight: 'bold' } },
                    ticks: { color: '#94a3b8', font: { size: 9 } }, grid: { color: '#1e293b' }
                },
                y: {
                    title: { display: true, text: 'Eje Y: Frecuencia (Cantidad de Clubes)', color: '#94a3b8', font: { family: 'Outfit', size: 10, weight: 'bold' } },
                    ticks: { color: '#94a3b8', font: { size: 9 } }, grid: { color: '#1e293b' }
                }
            }
        }
    });

    // Chart 2: Betweenness with explicit X and Y axis labels
    if (chartBetweenness) chartBetweenness.destroy();
    const topBet = [...clubsOnly].sort((a, b) => b.betweenness - a.betweenness).slice(0, 8);

    const ctxBet = document.getElementById('chart-betweenness').getContext('2d');
    const gradientBet = ctxBet.createLinearGradient(0, 0, 300, 0);
    gradientBet.addColorStop(0, '#0284c7');
    gradientBet.addColorStop(1, '#8b5cf6');

    chartBetweenness = new Chart(ctxBet, {
        type: 'bar',
        data: {
            labels: topBet.map(n => n.label),
            datasets: [{
                label: 'Puntaje de Intermediación (Rol Puente)',
                data: topBet.map(n => n.betweenness),
                backgroundColor: gradientBet,
                borderRadius: 6
            }]
        },
        options: {
            indexAxis: 'y', responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: true, labels: { color: '#cbd5e1', font: { family: 'Outfit', size: 10 } } } },
            scales: {
                x: {
                    title: { display: true, text: 'Eje X: Puntaje de Intermediación (0.00 a 1.00)', color: '#94a3b8', font: { family: 'Outfit', size: 10, weight: 'bold' } },
                    ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' }
                },
                y: {
                    title: { display: true, text: 'Eje Y: Club Conector', color: '#94a3b8', font: { family: 'Outfit', size: 10, weight: 'bold' } },
                    ticks: { color: '#f8fafc', font: { weight: 'bold' } }, grid: { color: '#1e293b' }
                }
            }
        }
    });

    // Chart 3: Financials with explicit X and Y axis labels
    if (chartFinancials) chartFinancials.destroy();
    const topSpenders = [...clubsOnly].sort((a, b) => b.spent_m - a.spent_m).slice(0, 8);
    const netBalances = topSpenders.map(n => n.earned_m - n.spent_m);

    chartFinancials = new Chart(document.getElementById('chart-financials'), {
        type: 'bar',
        data: {
            labels: topSpenders.map(n => n.label),
            datasets: [
                {
                    type: 'line',
                    label: 'Balance Neto (Ventas - Gasto)',
                    data: netBalances,
                    borderColor: '#fbbf24',
                    borderWidth: 2.5,
                    pointBackgroundColor: '#f59e0b',
                    fill: false
                },
                {
                    label: 'Gasto en Compras (€ M)',
                    data: topSpenders.map(n => n.spent_m),
                    backgroundColor: 'rgba(239, 68, 68, 0.85)',
                    borderRadius: 6
                },
                {
                    label: 'Ingresos por Ventas (€ M)',
                    data: topSpenders.map(n => n.earned_m),
                    backgroundColor: 'rgba(52, 211, 153, 0.85)',
                    borderRadius: 6
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#cbd5e1', font: { family: 'Outfit', size: 10 } } } },
            scales: {
                x: {
                    title: { display: true, text: 'Eje X: Clubes Principales', color: '#94a3b8', font: { family: 'Outfit', size: 10, weight: 'bold' } },
                    ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' }
                },
                y: {
                    title: { display: true, text: 'Eje Y: Dinero en Millones de Euros (€ M)', color: '#94a3b8', font: { family: 'Outfit', size: 10, weight: 'bold' } },
                    ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' }
                }
            }
        }
    });

    // Chart 4: Categories Doughnut
    if (chartDivisions) chartDivisions.destroy();
    const divCounts = { 'Primera División': 0, 'Segunda División': 0, 'Liga Internacional': 0, 'Cantera / Filial': 0 };
    clubsOnly.forEach(n => { divCounts[n.group] = (divCounts[n.group] || 0) + 1; });

    chartDivisions = new Chart(document.getElementById('chart-divisions'), {
        type: 'doughnut',
        data: {
            labels: Object.keys(divCounts).map(k => `${k} (${divCounts[k]} clubes)`),
            datasets: [{
                data: Object.values(divCounts),
                backgroundColor: ['#38bdf8', '#34d399', '#ef4444', '#a855f7'],
                borderWidth: 2,
                borderColor: '#0b0f19'
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'right', labels: { color: '#cbd5e1', font: { family: 'Outfit', size: 10 } } } }
        }
    });
}

window.renderAnalyticsCharts = renderAnalyticsCharts;
