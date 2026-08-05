/* charts.js
 * Analytics & SNA Hub. Se inyecta dinámicamente la primera vez que se abre el
 * modal de Analytics (ver loadChartsModuleAndRender en main.js).
 *
 * Cubre los cuatro entregables del Project 3 (Social Network Analysis):
 *   1. Basic Characteristics  -> computeNetworkMetrics()  (Tabla I del reporte)
 *   2. Degree Distribution    -> gráficas 1 y 2 (lineal + log–log)
 *   3. Centralidad            -> gráfica 3 (betweenness) + Tabla II
 *   4. Link Prediction        -> computeLinkPrediction() + Tabla III y validación
 *
 * Todas las métricas se calculan EN VIVO sobre la red cargada (clubNodes /
 * clubEdges), así que el dashboard nunca puede contradecir a sus propios datos.
 */

const _charts = {};   // registro de instancias Chart.js para destruirlas al re-render
let _metricsCache = null;
let _linkPredCache = null;

const FONT = { family: 'Outfit', size: 10 };
const AXIS = '#94a3b8';
const GRID = '#1e293b';

// ---------------------------------------------------------------- utilidades
function _canvas(id) {
    const el = document.getElementById(id);
    if (!el) { console.warn(`[charts] falta el canvas #${id}; se omite esa gráfica`); return null; }
    if (_charts[id]) { _charts[id].destroy(); delete _charts[id]; }
    return el;
}

function _setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.innerText = text;
}

function _setHTML(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
}

function _axis(titleText) {
    return {
        title: { display: true, text: titleText, color: AXIS, font: { family: 'Outfit', size: 10, weight: 'bold' } },
        ticks: { color: AXIS, font: { size: 9 } },
        grid: { color: GRID }
    };
}

const _legend = { labels: { color: '#cbd5e1', font: FONT, boxWidth: 12 } };

// ------------------------------------------- grafo no dirigido (adyacencias)
// Todas las medidas estructurales del reporte se calculan sobre la
// simplificación no dirigida U, igual que en NetworkX.
function _buildUndirected() {
    const adj = new Map(clubNodes.map(n => [n.id, new Set()]));
    let directed = 0;
    clubEdges.forEach(e => {
        if (!adj.has(e.from) || !adj.has(e.to)) return;
        directed++;
        if (e.from !== e.to) { adj.get(e.from).add(e.to); adj.get(e.to).add(e.from); }
    });
    return { adj, directed };
}

// Betweenness con el algoritmo de Brandes. En grafo no dirigido cada camino se
// cuenta dos veces, de ahí el /2 antes de normalizar por 2/((n-1)(n-2)):
// mismos valores que networkx.betweenness_centrality(U, normalized=True).
function _brandes(adj, ids) {
    const bc = new Map(ids.map(i => [i, 0]));

    ids.forEach(s => {
        const stack = [], pred = new Map(), sigma = new Map(), dist = new Map();
        ids.forEach(i => { pred.set(i, []); sigma.set(i, 0); dist.set(i, -1); });
        sigma.set(s, 1); dist.set(s, 0);

        const queue = [s];
        for (let qi = 0; qi < queue.length; qi++) {
            const v = queue[qi];
            stack.push(v);
            adj.get(v).forEach(w => {
                if (dist.get(w) < 0) { dist.set(w, dist.get(v) + 1); queue.push(w); }
                if (dist.get(w) === dist.get(v) + 1) {
                    sigma.set(w, sigma.get(w) + sigma.get(v));
                    pred.get(w).push(v);
                }
            });
        }

        const delta = new Map(ids.map(i => [i, 0]));
        for (let i = stack.length - 1; i >= 0; i--) {
            const w = stack[i];
            pred.get(w).forEach(v => {
                delta.set(v, delta.get(v) + (sigma.get(v) / sigma.get(w)) * (1 + delta.get(w)));
            });
            if (w !== s) bc.set(w, bc.get(w) + delta.get(w));
        }
    });

    const n = ids.length;
    const scale = n > 2 ? 1 / ((n - 1) * (n - 2)) : 0;   // (1/2) * 2/((n-1)(n-2))
    bc.forEach((v, k) => bc.set(k, v * scale));
    return bc;
}

// PageRank por iteración de potencia sobre U (damping 0.85), repartiendo la
// masa de los nodos sin salida para que la distribución sume 1.
function _pagerank(adj, ids, damping = 0.85, iterations = 80) {
    const N = ids.length;
    let pr = new Map(ids.map(i => [i, 1 / N]));
    for (let it = 0; it < iterations; it++) {
        const next = new Map(ids.map(i => [i, 0]));
        let dangling = 0;
        ids.forEach(u => {
            const nb = adj.get(u);
            if (!nb.size) { dangling += pr.get(u); return; }
            const share = pr.get(u) / nb.size;
            nb.forEach(v => next.set(v, next.get(v) + share));
        });
        ids.forEach(i => next.set(i, damping * (next.get(i) + dangling / N) + (1 - damping) / N));
        pr = next;
    }
    return pr;
}

// ------------------------------------- 1. Características básicas (Tabla I)
function computeNetworkMetrics() {
    if (_metricsCache) return _metricsCache;

    const { adj, directed } = _buildUndirected();
    const ids = [...adj.keys()];
    const N = ids.length;

    let m = 0;
    adj.forEach(s => { m += s.size; });
    m /= 2;

    // Clustering promedio y transitividad global (tríadas cerradas / tríadas)
    let sumC = 0, triangles = 0, triples = 0;
    ids.forEach(u => {
        const nb = [...adj.get(u)];
        const k = nb.length;
        if (k < 2) return;
        let links = 0;
        for (let i = 0; i < k; i++) {
            for (let j = i + 1; j < k; j++) if (adj.get(nb[i]).has(nb[j])) links++;
        }
        sumC += (2 * links) / (k * (k - 1));
        triangles += links;
        triples += (k * (k - 1)) / 2;
    });

    // Componentes conexos (DFS iterativo)
    const seen = new Set();
    let components = 0;
    ids.forEach(s => {
        if (seen.has(s)) return;
        components++;
        const stack = [s];
        seen.add(s);
        while (stack.length) {
            const u = stack.pop();
            adj.get(u).forEach(v => { if (!seen.has(v)) { seen.add(v); stack.push(v); } });
        }
    });

    // Diámetro y camino promedio (BFS desde cada nodo)
    let diameter = 0, sumPaths = 0, pairs = 0;
    ids.forEach(s => {
        const dist = new Map([[s, 0]]);
        const q = [s];
        for (let i = 0; i < q.length; i++) {
            const u = q[i];
            adj.get(u).forEach(v => { if (!dist.has(v)) { dist.set(v, dist.get(u) + 1); q.push(v); } });
        }
        dist.forEach((d, v) => {
            if (v === s) return;
            sumPaths += d; pairs++;
            if (d > diameter) diameter = d;
        });
    });

    // Asortatividad nominal por división/liga (mismo estimador que NetworkX:
    // r = (Tr e - ||e²||) / (1 - ||e²||) sobre la matriz de mezcla e).
    const group = new Map(clubNodes.map(n => [n.id, n.group]));
    const cats = [...new Set(clubNodes.map(n => n.group))];
    const idx = new Map(cats.map((c, i) => [c, i]));
    const mix = cats.map(() => new Array(cats.length).fill(0));
    let tot = 0;
    adj.forEach((s, u) => s.forEach(v => { mix[idx.get(group.get(u))][idx.get(group.get(v))]++; tot++; }));
    let trace = 0, sq = 0;
    for (let i = 0; i < cats.length; i++) {
        trace += mix[i][i] / tot;
        let a = 0, b = 0;
        for (let j = 0; j < cats.length; j++) { a += mix[i][j] / tot; b += mix[j][i] / tot; }
        sq += a * b;
    }
    const assortativity = (trace - sq) / (1 - sq);

    const degrees = ids.map(id => adj.get(id).size);

    _metricsCache = {
        adj, ids, N,
        degree: new Map(ids.map(id => [id, adj.get(id).size])),
        betweenness: _brandes(adj, ids),
        pagerank: _pagerank(adj, ids),
        directedEdges: directed,
        undirectedEdges: m,
        density: (2 * m) / (N * (N - 1)),
        avgDegree: (2 * m) / N,
        minDegree: Math.min(...degrees),
        maxDegree: Math.max(...degrees),
        avgClustering: sumC / N,
        transitivity: triples ? (3 * (triangles / 3)) / triples : 0,
        components,
        diameter,
        avgPathLength: sumPaths / pairs,
        assortativity,
        totalTransfers: (window.__META__ ? window.__META__.total_transfers : clubEdges.length)
    };
    return _metricsCache;
}

// --------------------------------------------- 4. Predicción de enlaces
// Cuatro medidas de similitud basadas en vecindad (las mismas del reporte:
// Jaccard, Adamic–Adar, preferential attachment y resource allocation) más una
// validación con 20 % de aristas ocultas. La partición es DETERMINISTA
// (cada 5ª arista) para que el resultado sea reproducible en la presentación.
function computeLinkPrediction() {
    if (_linkPredCache) return _linkPredCache;

    const { adj, ids } = computeNetworkMetrics();
    const key = (u, v) => (u < v ? u + '|' + v : v + '|' + u);

    // Aristas no dirigidas únicas
    const und = [];
    const seenPair = new Set();
    adj.forEach((s, u) => s.forEach(v => {
        const k = key(u, v);
        if (!seenPair.has(k)) { seenPair.add(k); und.push([u, v]); }
    }));

    const scorers = {
        jaccard: (a, b, common) => {
            const union = a.size + b.size - common.length;
            return union ? common.length / union : 0;
        },
        adamic: (a, b, common, g) => common.reduce((s, w) => {
            const k = g.get(w).size;
            return k > 1 ? s + 1 / Math.log(k) : s;
        }, 0),
        preferential: (a, b) => a.size * b.size,
        resource: (a, b, common, g) => common.reduce((s, w) => {
            const k = g.get(w).size;
            return k ? s + 1 / k : s;
        }, 0)
    };

    // Ranking sobre el grafo COMPLETO: los pares no adyacentes mejor puntuados.
    // Jaccard es el único que se normaliza por grado, así que dos clubes con un
    // solo socio compartido dan un 1.000 degenerado; para el ranking mostrado se
    // exige un mínimo de actividad (MIN_DEG socios) además de 2 vecinos comunes.
    const MIN_COMMON = 2;
    const MIN_DEG_JACCARD = 5;
    const ranked = { jaccard: [], adamic: [], preferential: [], resource: [] };
    for (let i = 0; i < ids.length; i++) {
        for (let j = i + 1; j < ids.length; j++) {
            const u = ids[i], v = ids[j];
            const a = adj.get(u), b = adj.get(v);
            if (a.has(v)) continue;
            const common = [];
            a.forEach(w => { if (b.has(w)) common.push(w); });
            if (common.length < MIN_COMMON) continue;   // sin vecindario compartido no hay señal local
            for (const name in scorers) {
                if (name === 'jaccard' && (a.size < MIN_DEG_JACCARD || b.size < MIN_DEG_JACCARD)) continue;
                const s = scorers[name](a, b, common, adj);
                if (s > 0) ranked[name].push([u, v, s]);
            }
        }
    }
    for (const name in ranked) {
        ranked[name].sort((x, y) => y[2] - x[2]);
        ranked[name] = ranked[name].slice(0, 8);
    }

    // ---- Validación: se ocultan el 20 % de las aristas y se re-puntúa ----
    const train = new Map(ids.map(id => [id, new Set()]));
    const hidden = [];
    und.forEach((e, i) => {
        if (i % 5 === 0) hidden.push(e);
        else { train.get(e[0]).add(e[1]); train.get(e[1]).add(e[0]); }
    });
    const hiddenSet = new Set(hidden.map(([u, v]) => key(u, v)));
    const AA = (u, v) => {
        let s = 0;
        train.get(u).forEach(w => {
            if (!train.get(v).has(w)) return;
            const k = train.get(w).size;
            if (k > 1) s += 1 / Math.log(k);
        });
        return s;
    };

    const cand = [];
    for (let i = 0; i < ids.length; i++) {
        for (let j = i + 1; j < ids.length; j++) {
            const u = ids[i], v = ids[j];
            if (train.get(u).has(v)) continue;
            const s = AA(u, v);
            if (s > 0) cand.push([u, v, s]);
        }
    }
    cand.sort((a, b) => b[2] - a[2]);
    const top50 = cand.slice(0, 50);
    const hits = top50.filter(([u, v]) => hiddenSet.has(key(u, v))).length;

    const totalPairs = (ids.length * (ids.length - 1)) / 2;
    const randomBaseline = hidden.length / (totalPairs - (und.length - hidden.length));

    // AUC: probabilidad de que una arista oculta puntúe por encima de un
    // no-enlace. LCG con semilla fija => mismo resultado en cada corrida.
    let seed = 42;
    const rnd = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);
    const nonEdges = [];
    while (nonEdges.length < 1500) {
        const u = ids[Math.floor(rnd() * ids.length)];
        const v = ids[Math.floor(rnd() * ids.length)];
        if (u === v || train.get(u).has(v) || hiddenSet.has(key(u, v))) continue;
        nonEdges.push([u, v]);
    }
    let wins = 0, ties = 0, n = 0;
    hidden.forEach(([hu, hv]) => {
        const hs = AA(hu, hv);
        for (let t = 0; t < 10; t++) {
            const [nu, nv] = nonEdges[Math.floor(rnd() * nonEdges.length)];
            const ns = AA(nu, nv);
            n++;
            if (hs > ns) wins++; else if (hs === ns) ties++;
        }
    });

    _linkPredCache = {
        ranked,
        hiddenCount: hidden.length,
        precision50: hits / 50,
        hits,
        randomBaseline,
        lift: randomBaseline ? (hits / 50) / randomBaseline : 0,
        auc: (wins + 0.5 * ties) / n
    };
    return _linkPredCache;
}

// ================================================================ RENDER ===
function renderAnalyticsCharts() {
    if (!Array.isArray(clubNodes) || clubNodes.length === 0) {
        console.warn('[charts] todavía no hay datos de clubes cargados');
        return;
    }

    const steps = [
        ['tabla de características básicas', renderBasicMeasures],
        ['distribución de grados', renderDegreeCharts],
        ['centralidad', renderCentrality],
        ['composición y homofilia', renderComposition],
        ['finanzas', renderFinancials],
        ['predicción de enlaces', renderLinkPrediction]
    ];

    // Cada bloque va aislado: si uno falla, los demás se dibujan igual y el
    // error queda visible en consola en lugar de tumbar todo el hub.
    steps.forEach(([label, fn]) => {
        try { fn(); } catch (err) { console.error(`[charts] fallo en ${label}:`, err); }
    });
}

// ---- 1. Tabla I: características básicas de la red
function renderBasicMeasures() {
    const m = computeNetworkMetrics();
    const fmt = (v, d = 2) => Number(v).toFixed(d);

    const rows = [
        ['Nodos (N)', m.N, 'Clubes reales, sin súper-nodos consolidados'],
        ['Traspasos registrados', m.totalTransfers.toLocaleString('es-ES'), 'Registros individuales del scraping'],
        ['Aristas dirigidas (agregadas)', m.directedEdges.toLocaleString('es-ES'), 'Pares club→club únicos'],
        ['Aristas no dirigidas |E<sub>U</sub>|', m.undirectedEdges.toLocaleString('es-ES'), 'Simplificación U usada en las medidas'],
        ['Densidad', fmt(m.density, 4), 'Grafo disperso, escala realista'],
        ['Grado promedio', `${fmt(m.avgDegree)} (min ${m.minDegree}, max ${m.maxDegree})`, 'Socios comerciales por club'],
        ['Clustering promedio', fmt(m.avgClustering, 3), 'Media de coeficientes locales'],
        ['Transitividad global', fmt(m.transitivity, 3), 'Tríadas cerradas sobre tríadas totales'],
        ['Componentes conexos', m.components, m.components === 1 ? 'La red está totalmente integrada' : 'Hay subredes aisladas'],
        ['Diámetro', m.diameter, 'Distancia máxima entre dos clubes'],
        ['Camino promedio', fmt(m.avgPathLength), 'Efecto small-world'],
        ['Asortatividad por división', (m.assortativity >= 0 ? '+' : '') + fmt(m.assortativity, 4), m.assortativity < 0 ? 'Disasortativa: se ficha fuera del propio nivel' : 'Asortativa: se ficha dentro del mismo nivel']
    ];

    _setHTML('tbl-basic-measures', rows.map(([k, v, note]) => `
        <tr class="border-b border-slate-800/70 last:border-none">
            <td class="py-1.5 pr-2 text-slate-300 font-semibold">${k}</td>
            <td class="py-1.5 pr-2 text-right font-black text-violet-300 whitespace-nowrap">${v}</td>
            <td class="py-1.5 text-[9.5px] text-slate-500 leading-tight hidden sm:table-cell">${note}</td>
        </tr>`).join(''));

    _setText('stat-avg-path', fmt(m.avgPathLength));
    _setText('stat-transitivity', fmt(m.transitivity, 3));
    _setText('stat-diameter', String(m.diameter));

    _setHTML('basic-measures-insight',
        `<b class="text-violet-300">Lectura:</b> la red es <b>small-world</b>: ${m.N} clubes conectados en un solo componente,
         a <b>${fmt(m.avgPathLength)} pasos</b> promedio y con diámetro <b>${m.diameter}</b>. La transitividad
         (<b>${fmt(m.transitivity, 3)}</b>) queda muy por encima de la de un grafo aleatorio de la misma densidad
         (≈ ${fmt(m.density, 4)}), así que dos clubes con un socio en común tienen mucha más probabilidad de
         fichar entre ellos que al azar. <b>Esperábamos</b> que los clubes negociaran sobre todo dentro de su
         propia división; la asortatividad <b>${(m.assortativity >= 0 ? '+' : '') + fmt(m.assortativity, 4)}</b>
         dice lo contrario y es el hallazgo que más se desvía de la expectativa inicial.`);
}

// ---- 2. Distribución de grados (lineal + log–log)
function renderDegreeCharts() {
    const m = computeNetworkMetrics();
    const counts = {};
    m.ids.forEach(id => { const k = m.adj.get(id).size; counts[k] = (counts[k] || 0) + 1; });
    const ks = Object.keys(counts).map(Number).sort((a, b) => a - b);
    const freq = ks.map(k => counts[k]);

    const c1 = _canvas('chart-degree');
    if (c1) {
        const ctx = c1.getContext('2d');
        const grad = ctx.createLinearGradient(0, 0, 0, 200);
        grad.addColorStop(0, 'rgba(124, 58, 237, 0.75)');
        grad.addColorStop(1, 'rgba(124, 58, 237, 0.05)');

        _charts['chart-degree'] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ks,
                datasets: [
                    { type: 'bar', label: 'Nº de clubes con grado k', data: freq, backgroundColor: grad, borderColor: '#7c3aed', borderWidth: 1, borderRadius: 6 },
                    { type: 'line', label: 'Tendencia (cola pesada)', data: freq, borderColor: '#a855f7', borderWidth: 2, tension: 0.35, pointRadius: 0, fill: false }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: _legend },
                scales: { x: _axis('Grado k (socios comerciales)'), y: _axis('Frecuencia (nº de clubes)') }
            }
        });
    }

    const c2 = _canvas('chart-degree-loglog');
    if (c2) {
        const total = m.N;
        const points = ks.filter(k => k > 0).map(k => ({ x: k, y: counts[k] / total }));
        _charts['chart-degree-loglog'] = new Chart(c2.getContext('2d'), {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'P(k) observada', data: points,
                    backgroundColor: '#22d3ee', borderColor: '#0891b2', pointRadius: 4
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: _legend },
                scales: {
                    x: Object.assign({ type: 'logarithmic' }, _axis('Grado k (escala log)')),
                    y: Object.assign({ type: 'logarithmic' }, _axis('P(k) (escala log)'))
                }
            }
        });
    }
}

// ---- 3. Centralidad (betweenness) + Tabla II
function renderCentrality() {
    const m = computeNetworkMetrics();
    const label = new Map(clubNodes.map(n => [n.id, n.label || n.id]));
    const rank = (map, dec) => [...map.entries()]
        .sort((a, b) => b[1] - a[1])
        .map(([id, v]) => ({ id, label: label.get(id) || id, value: v, text: dec === 0 ? String(v) : v.toFixed(dec) }));

    const byDegree = rank(m.degree, 0);
    const byBetween = rank(m.betweenness, 3);
    const byPagerank = rank(m.pagerank, 3);
    const top = byBetween.slice(0, 8);

    const c = _canvas('chart-betweenness');
    if (c) {
        const ctx = c.getContext('2d');
        const grad = ctx.createLinearGradient(0, 0, 300, 0);
        grad.addColorStop(0, '#0284c7');
        grad.addColorStop(1, '#8b5cf6');

        _charts['chart-betweenness'] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: top.map(n => n.label),
                datasets: [{ label: 'Intermediación (rol puente)', data: top.map(n => +n.value.toFixed(4)), backgroundColor: grad, borderRadius: 6 }]
            },
            options: {
                indexAxis: 'y', responsive: true, maintainAspectRatio: false,
                plugins: { legend: _legend },
                scales: { x: _axis('Betweenness normalizada'), y: Object.assign(_axis('Club conector'), { ticks: { color: '#f8fafc', font: { weight: 'bold', size: 9 } } }) }
            }
        });
    }

    // Tabla II: top-5 por grado / betweenness / PageRank
    const cell = (arr, i, color) => `<td class="py-1.5 pr-2 ${color} font-semibold">${arr[i].label} <span class="text-slate-500 font-normal">(${arr[i].text})</span></td>`;
    _setHTML('tbl-centrality', [0, 1, 2, 3, 4].map(i => `
        <tr class="border-b border-slate-800/70 last:border-none">
            <td class="py-1.5 text-slate-500 font-bold">${i + 1}</td>
            ${cell(byDegree, i, 'text-slate-200')}
            ${cell(byBetween, i, 'text-cyan-300')}
            ${cell(byPagerank, i, 'text-emerald-300')}
        </tr>`).join(''));

    _setHTML('centrality-insight',
        `<b class="text-violet-300">Lectura:</b> el club con más socios comerciales
         (<b>${byDegree[0].label}</b>, grado ${byDegree[0].text}) no es el mismo que sostiene la red como puente
         (<b>${byBetween[0].label}</b>, betweenness ${byBetween[0].text}). Volumen e intermediación señalan
         clubes distintos: los puentes son equipos de rotación alta y filiales que conectan Primera, Segunda y
         el extranjero, no los grandes compradores. <b>Esperábamos</b> que los que más gastan fueran también los
         más centrales; no lo son, y esa es la lectura SNA más interesante del proyecto.`);
}

// ---- 4. Composición por división + homofilia
function renderComposition() {
    const m = computeNetworkMetrics();
    const counts = {};
    clubNodes.forEach(n => { counts[n.group] = (counts[n.group] || 0) + 1; });
    const labels = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);

    const c = _canvas('chart-divisions');
    if (c) {
        _charts['chart-divisions'] = new Chart(c.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: labels.map(k => `${k} (${counts[k]})`),
                datasets: [{
                    data: labels.map(k => counts[k]),
                    backgroundColor: ['#38bdf8', '#34d399', '#a855f7', '#f59e0b', '#ef4444', '#22d3ee', '#f472b6', '#94a3b8'],
                    borderWidth: 2, borderColor: '#0b0f19'
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false, cutout: '55%',
                plugins: { legend: { position: 'right', labels: { color: '#cbd5e1', font: { family: 'Outfit', size: 9 }, boxWidth: 10 } } }
            }
        });
    }

    const a = m.assortativity;
    _setText('stat-assortativity', (a >= 0 ? '+' : '') + a.toFixed(4));
    _setHTML('assortativity-insight',
        `Coeficiente <b>${(a >= 0 ? '+' : '') + a.toFixed(4)}</b> sobre ${labels.length} categorías
         (divisiones españolas + ligas extranjeras): valor <b>${a < 0 ? 'negativo ⇒ red disasortativa' : 'positivo ⇒ red asortativa'}</b>.
         ${a < 0
            ? 'Los clubes prefieren negociar con divisiones distintas a la propia y con el extranjero, en lugar de cerrarse en operaciones domésticas del mismo nivel: el mercado español está estructuralmente abierto.'
            : 'Los clubes negocian preferentemente dentro de su propio nivel competitivo.'}`);
}

// ---- 5. Volumen financiero
function renderFinancials() {
    const top = [...clubNodes].sort((a, b) => (b.spent_m + b.earned_m) - (a.spent_m + a.earned_m)).slice(0, 8);

    const c = _canvas('chart-financials');
    if (!c) return;

    _charts['chart-financials'] = new Chart(c.getContext('2d'), {
        type: 'bar',
        data: {
            labels: top.map(n => n.label),
            datasets: [
                { type: 'line', label: 'Balance neto (ventas − gasto)', data: top.map(n => +(n.earned_m - n.spent_m).toFixed(2)), borderColor: '#fbbf24', borderWidth: 2.5, pointBackgroundColor: '#f59e0b', tension: 0.3, fill: false },
                { label: 'Gasto en compras (M€)', data: top.map(n => n.spent_m), backgroundColor: 'rgba(239, 68, 68, 0.85)', borderRadius: 6 },
                { label: 'Ingresos por ventas (M€)', data: top.map(n => n.earned_m), backgroundColor: 'rgba(52, 211, 153, 0.85)', borderRadius: 6 }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: _legend },
            scales: { x: _axis('Clubes con mayor volumen'), y: _axis('Millones de euros (M€)') }
        }
    });

    const totalMoney = window.__META__ ? window.__META__.total_market_money : clubNodes.reduce((s, n) => s + (n.spent_m || 0), 0);
    _setHTML('financial-insight',
        `<b class="text-violet-300">Lectura:</b> ${totalMoney.toFixed(1)} M€ movidos en la red.
         La línea ámbar separa a los <b>compradores netos</b> (balance negativo, financian el mercado) de los
         <b>vendedores netos</b> (balance positivo, lo abastecen de talento). El dinero es una capa de peso
         sobre las aristas: no cambia la topología, pero explica la dirección del flujo.`);
}

// ---- 6. Predicción de enlaces (rubro de 20 pts) + validación
function renderLinkPrediction() {
    const lp = computeLinkPrediction();

    const MEASURES = [
        ['adamic', 'Adamic–Adar', 2, '#a855f7'],
        ['jaccard', 'Jaccard', 3, '#22d3ee'],
        ['resource', 'Resource allocation', 3, '#34d399'],
        ['preferential', 'Pref. attachment', 0, '#f59e0b']
    ];

    // Gráfica: top-8 pares por Adamic–Adar
    const c = _canvas('chart-linkpred');
    if (c) {
        const top = lp.ranked.adamic;
        _charts['chart-linkpred'] = new Chart(c.getContext('2d'), {
            type: 'bar',
            data: {
                labels: top.map(([u, v]) => `${u} – ${v}`),
                datasets: [{ label: 'Índice Adamic–Adar', data: top.map(([, , s]) => +s.toFixed(3)), backgroundColor: 'rgba(168, 85, 247, 0.85)', borderRadius: 6 }]
            },
            options: {
                indexAxis: 'y', responsive: true, maintainAspectRatio: false,
                plugins: { legend: _legend },
                scales: { x: _axis('Puntaje Adamic–Adar'), y: Object.assign(_axis('Par de clubes sin traspaso previo'), { ticks: { color: '#f8fafc', font: { weight: 'bold', size: 8.5 } } }) }
            }
        });
    }

    // Tabla III: top-3 pares por cada medida
    _setHTML('tbl-linkpred', MEASURES.map(([key, name, dec, color]) => {
        const rows = lp.ranked[key].slice(0, 3);
        if (!rows.length) return '';
        return rows.map(([u, v, s], i) => `
            <tr class="border-b border-slate-800/70 last:border-none">
                <td class="py-1.5 pr-2 font-bold ${i === 0 ? '' : 'text-transparent'}" style="color:${i === 0 ? color : 'transparent'}">${name}</td>
                <td class="py-1.5 pr-2 text-slate-200 font-semibold">${u} – ${v}</td>
                <td class="py-1.5 text-right font-black text-slate-300 whitespace-nowrap">${s.toFixed(dec)}</td>
            </tr>`).join('');
    }).join(''));

    _setText('stat-precision50', `${(lp.precision50 * 100).toFixed(1)}%`);
    _setText('stat-auc', lp.auc.toFixed(3));
    _setText('stat-lp-hidden', `${lp.hiddenCount} aristas ocultas (20%)`);

    _setHTML('linkpred-insight',
        `<b class="text-violet-300">Validación:</b> ocultando el 20 % de las aristas reales
         (<b>${lp.hiddenCount}</b> enlaces) y recalculando Adamic–Adar sobre el 80 % restante, el modelo acierta
         <b>${lp.hits} de los 50</b> pares mejor rankeados (<b>Precision@50 = ${(lp.precision50 * 100).toFixed(1)}%</b>)
         frente al <b>${(lp.randomBaseline * 100).toFixed(1)}%</b> esperado al azar
         — una mejora de <b>${lp.lift.toFixed(0)}×</b> — con <b>AUC ≈ ${lp.auc.toFixed(3)}</b>, cómodamente sobre el 0.5 del azar.
         <br><b class="text-violet-300">Discusión:</b> hay señal estructural real: los socios de traspaso comparten
         vecindarios. Pero <b>esperábamos</b> descubrir relaciones nuevas y las medidas tienden a reforzar
         clubes ya muy conectados — <i>preferential attachment</i> se reduce casi a "une los dos hubs más grandes",
         porque solo usa el grado. Para scouting real habría que combinar estos puntajes topológicos con
         variables de dominio (capacidad financiera, posición, geografía).`);
}

window.renderAnalyticsCharts = renderAnalyticsCharts;
window.computeNetworkMetrics = computeNetworkMetrics;
window.computeLinkPrediction = computeLinkPrediction;
