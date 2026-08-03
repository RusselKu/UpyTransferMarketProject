/* main.js
 * Bootstrap de la aplicación: descarga los JSON de datos, los expone como
 * variables globales que consumen ui.js/network.js/charts.js, e inicializa
 * la red UNA VEZ que los datos ligeros (clubs-network.json) están listos.
 *
 * hetero-network.json es pesado (nodos de club + nodos de jugador) y solo se
 * descarga on-demand la primera vez que el usuario cambia a la vista
 * "Clubes + Jugadores" (ver ensureHeteroDataLoaded / setViewMode en network.js).
 *
 * charts.js (Chart.js) tampoco se carga en el <head>: se inyecta dinámicamente
 * la primera vez que se abre el Analytics Hub (ver loadChartsModuleAndRender).
 */

// ---- Datos globales (poblados tras el fetch) ----
let clubNodes = [];
let clubEdges = [];
let heteroNodes = [];
let heteroEdges = [];
let clubStats = {};
let starTransfers = [];

let heteroDataLoaded = false;
let heteroDataLoadingPromise = null;
let chartsModuleLoaded = false;

const DATA_BASE_PATH = 'data/';

async function fetchJSON(path) {
    const res = await fetch(DATA_BASE_PATH + path, { cache: 'force-cache' });
    if (!res.ok) {
        throw new Error(`No se pudo cargar ${path}: HTTP ${res.status}`);
    }
    return res.json();
}

// Descarga hetero-network.json solo la primera vez que se necesita (modo "hetero").
async function ensureHeteroDataLoaded() {
    if (heteroDataLoaded) return;
    if (heteroDataLoadingPromise) return heteroDataLoadingPromise;

    heteroDataLoadingPromise = fetchJSON('hetero-network.json').then(hetero => {
        heteroNodes = hetero.nodes;
        heteroEdges = hetero.edges;
        heteroDataLoaded = true;
    }).catch(err => {
        console.error('Error cargando hetero-network.json', err);
        // Reintentar en la próxima llamada.
        heteroDataLoadingPromise = null;
    });

    return heteroDataLoadingPromise;
}
window.ensureHeteroDataLoaded = ensureHeteroDataLoaded;

// Inyecta un <script> y devuelve una promesa que resuelve cuando carga.
function injectScript(src) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.onload = resolve;
        script.onerror = () => reject(new Error(`No se pudo cargar ${src}`));
        document.body.appendChild(script);
    });
}

// Inyecta Chart.js (CDN) + charts.js dinámicamente (no bloquean el <head>) y
// renderiza los 4 gráficos. Solo se descargan la primera vez que se abre el
// Analytics Hub; llamadas posteriores solo vuelven a renderizar.
async function loadChartsModuleAndRender() {
    if (chartsModuleLoaded) {
        if (typeof renderAnalyticsCharts === 'function') renderAnalyticsCharts();
        return;
    }

    try {
        if (typeof Chart === 'undefined') {
            await injectScript('assets/js/vendor/chart.min.js');
        }
        await injectScript('assets/js/charts.js');
        chartsModuleLoaded = true;
        if (typeof renderAnalyticsCharts === 'function') renderAnalyticsCharts();
    } catch (err) {
        console.error('Error cargando el módulo de gráficas (charts.js):', err);
    }
}
window.loadChartsModuleAndRender = loadChartsModuleAndRender;

// Aplica los valores de meta.json (conteos y métricas agregadas) al DOM estático.
function applyMetaToDOM(meta) {
    window.__META__ = meta;

    const setText = (id, text) => {
        const el = document.getElementById(id);
        if (el) el.innerText = text;
    };

    setText('stat-total-clubs', `${meta.total_clubs} Clubes`);
    setText('stat-hetero-nodes', `${meta.total_hetero_nodes} nodos heterogéneos`);
    setText('stat-total-transfers', `${meta.total_transfers.toLocaleString('es-ES')} Traspasos`);
    setText('stat-homophily', (meta.assortativity >= 0 ? '+' : '') + meta.assortativity.toFixed(4));
    setText('stat-money-moved', `${meta.total_market_money.toFixed(1)} M€`);
    setText('nodes-count', meta.total_clubs);
    setText('edges-count', meta.total_transfers);
    setText('ficha-node-edge-summary', `${meta.total_clubs} nodos de clubes (${meta.total_hetero_nodes} total heterogéneo), ${meta.total_transfers} traspasos`);
}

async function bootstrap() {
    try {
        const [clubsNet, clubStatsData, starTransfersData, meta] = await Promise.all([
            fetchJSON('clubs-network.json'),
            fetchJSON('club-stats.json'),
            fetchJSON('star-transfers.json'),
            fetchJSON('meta.json')
        ]);

        clubNodes = clubsNet.nodes;
        clubEdges = clubsNet.edges;
        clubStats = clubStatsData;
        starTransfers = starTransfersData;

        applyMetaToDOM(meta);

        initNetwork();
    } catch (err) {
        console.error('Error inicializando el dashboard:', err);
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.innerHTML = '<div class="text-red-400 text-sm font-bold px-6 text-center">Error cargando los datos del dashboard. Revisa la consola.</div>';
        }
    }
}

bootstrap();
