/* ui.js
 * Todo lo que no es lógica de red (vis-network) ni de gráficas (Chart.js):
 * tema visual, sidebar, drawer de detalle, búsqueda/autocomplete, tours
 * guiados, comparador, camino más corto, simulador what-if, guía y ficha A4.
 *
 * Depende de variables globales pobladas por main.js (clubNodes, clubEdges,
 * heteroNodes, heteroEdges, clubStats, starTransfers) y de la lógica de red
 * definida en network.js (network, nodesDataset, edgesDataset, updateNetworkData,
 * setViewMode, highlightEgoNetwork, resetEgoHighlight, fitNetwork, etc).
 */

// ---- Tema visual ----
function changeTheme(themeKey) {
    const body = document.getElementById('main-body');
    body.classList.remove('theme-cyberpunk', 'theme-light');
    if (themeKey === 'cyberpunk') body.classList.add('theme-cyberpunk');
    else if (themeKey === 'light') body.classList.add('theme-light');
}

// ---- Sidebar ----
function toggleSidebar() {
    const sidebar = document.getElementById('left-sidebar');
    const showBtn = document.getElementById('btn-show-sidebar');
    const isMobile = window.innerWidth <= 768;
    
    if (isMobile) {
        const isShown = sidebar.classList.toggle('show-mobile');
        if (showBtn) {
            showBtn.style.display = isShown ? 'none' : 'flex';
        }
    } else {
        const isHidden = sidebar.classList.toggle('hidden');
        if (showBtn) {
            showBtn.style.display = isHidden ? 'flex' : 'none';
        }
    }
    setTimeout(() => { if (network) network.fit({ animation: true }); }, 200);
}

function initSidebarResponsive() {
    const isMobile = window.innerWidth <= 768;
    const sidebar = document.getElementById('left-sidebar');
    const showBtn = document.getElementById('btn-show-sidebar');
    
    if (!sidebar) return;
    
    if (isMobile) {
        sidebar.classList.remove('hidden');
        sidebar.classList.remove('show-mobile');
        if (showBtn) {
            showBtn.style.display = 'flex';
        }
    } else {
        sidebar.classList.remove('hidden');
        sidebar.classList.remove('show-mobile');
        if (showBtn) {
            showBtn.style.display = 'none';
        }
    }
}

window.addEventListener('DOMContentLoaded', initSidebarResponsive);
window.addEventListener('resize', initSidebarResponsive);
window.initSidebarResponsive = initSidebarResponsive;

// ---- Drawer de detalle ----
function openDrawer() {
    document.getElementById('right-drawer').classList.remove('translate-x-full');
}

function closeDrawer() {
    document.getElementById('right-drawer').classList.add('translate-x-full');
    currentlySelectedNodeId = null;
}

function resetGlobalView() {
    // Parar la reproducción del timeline si está activa antes de limpiar filtros
    if (typeof stopTimeline === 'function') {
        stopTimeline();
    }

    viewMode = 'clubs_only';
    selectedSeason = 'all';
    selectedDivision = 'all';
    minFinancialCost = 0;
    nodeScalingMetric = 'degree';
    showPlayerLabels = false;
    if (typeof clearFocus === 'function') clearFocus();
    focusMode = false;

    // Helper de reseteo defensivo para evitar caídas de script si algún elemento no está en el DOM
    const safeSetChecked = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.checked = val;
    };
    const safeSetValue = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.value = val;
    };
    const safeSetText = (id, txt) => {
        const el = document.getElementById(id);
        if (el) el.innerText = txt;
    };

    safeSetChecked('toggle-player-labels', false);
    safeSetChecked('toggle-focus-mode', false);
    
    const focusHint = document.getElementById('focus-mode-hint');
    if (focusHint) focusHint.classList.add('hidden');
    
    safeSetValue('select-division-filter', 'all');
    safeSetValue('select-scaling', 'degree');
    safeSetValue('select-financial', '0');
    safeSetValue('select-season', 'all');
    safeSetValue('search-input', '');
    safeSetValue('timeline-slider', 0);
    safeSetText('timeline-label', 'Todas');

    if (typeof setViewMode === 'function') setViewMode('clubs_only');
    closeDrawer();
    if (typeof resetEgoHighlight === 'function') resetEgoHighlight();
    if (typeof fitNetwork === 'function') fitNetwork();
}

// ---- Búsqueda predictiva / autocomplete ----
function handleSearchInput(query) {
    const box = document.getElementById('search-suggestions');
    if (!query || !query.trim()) {
        box.classList.add('hidden');
        box.innerHTML = '';
        return;
    }

    const q = query.toLowerCase().trim();
    const activeNodes = (viewMode === 'clubs_only') ? clubNodes : heteroNodes;

    const matches = activeNodes.filter(n => n.label.toLowerCase().includes(q)).slice(0, 8);

    if (matches.length === 0) {
        box.innerHTML = `<div class="p-2.5 text-slate-500 text-[11px] text-center font-medium">Sin resultados coincidentes</div>`;
        box.classList.remove('hidden');
        return;
    }

    box.innerHTML = '';
    matches.forEach(m => {
        const isPlayer = (m.group === 'Jugador');
        const typeBadge = isPlayer
            ? '<span class="bg-amber-950/80 text-amber-300 px-1.5 py-0.5 rounded text-[9px] font-bold border border-amber-800/60">👤 Jugador</span>'
            : `<span class="bg-sky-950/80 text-sky-300 px-1.5 py-0.5 rounded text-[9px] font-bold border border-sky-800/60">⚽ ${m.group}</span>`;

        box.innerHTML += `
            <div onclick="selectSearchResult('${m.id}')" class="p-2.5 hover:bg-slate-800 cursor-pointer border-b border-slate-800/60 last:border-none flex justify-between items-center transition">
                <span class="font-bold text-slate-200 text-xs">${m.label}</span>
                ${typeBadge}
            </div>
        `;
    });
    box.classList.remove('hidden');
}

async function selectSearchResult(nodeId) {
    document.getElementById('search-suggestions').classList.add('hidden');

    if (viewMode === 'clubs_only') {
        const clubMatch = clubNodes.find(n => n.id === nodeId);
        if (!clubMatch && typeof ensureHeteroDataLoaded === 'function') {
            // Podría ser un nodo de jugador: aseguramos que la data hetero esté cargada.
            await ensureHeteroDataLoaded();
        }
    }

    const allNodes = (viewMode === 'clubs_only') ? clubNodes : heteroNodes;
    let node = allNodes.find(n => n.id === nodeId);

    if (!node && typeof heteroNodes !== 'undefined') {
        node = heteroNodes.find(n => n.id === nodeId);
    }

    if (node && network) {
        if (node.group === 'Jugador' && viewMode === 'clubs_only') {
            await setViewMode('hetero');
        }

        document.getElementById('search-input').value = node.label;
        currentlySelectedNodeId = nodeId;
        network.focus(nodeId, { scale: 1.2, animation: true });
        network.selectNodes([nodeId]);
        showNodeDetails(nodeId);
        applyNodeEmphasis(nodeId);
        openDrawer();
    }
}

// Ocultar el desplegable de búsqueda al hacer click fuera
document.addEventListener('click', function (e) {
    const searchBox = document.getElementById('search-suggestions');
    const searchInput = document.getElementById('search-input');
    if (searchBox && !searchBox.contains(e.target) && e.target !== searchInput) {
        searchBox.classList.add('hidden');
    }
});

// ---- Panel de detalle (club o jugador) ----
function showNodeDetails(nodeId) {
    const node = (nodesDataset ? nodesDataset.get(nodeId) : null) || heteroNodes.find(n => n.id === nodeId) || clubNodes.find(n => n.id === nodeId);
    if (!node) return;

    document.getElementById('detail-name').innerText = node.label;
    document.getElementById('detail-type').innerText = node.group;

    const isPlayerNode = (node.group === 'Jugador');
    const clubFinanceBox = document.getElementById('drawer-club-finance-box');
    const playerScoutingBox = document.getElementById('drawer-player-scouting-box');
    const listsContainer = document.getElementById('drawer-lists-container');

    if (isPlayerNode) {
        clubFinanceBox.classList.add('hidden');
        listsContainer.classList.add('hidden');
        playerScoutingBox.classList.remove('hidden');

        document.getElementById('detail-profile').innerText = (node.cost_val === 0) ? 'Traspaso Libre / Cesión 🆓' : (node.cost_val > 15 ? 'Fichaje Galáctico / Millonario 💎' : 'Traspaso Monetario Regular ⚽');
        document.getElementById('detail-role').innerText = `De: ${node.source_node} ➔ A: ${node.target_node}`;
        document.getElementById('detail-context-badge').innerText = `Temp. ${node.season.replace('-', '/')}`;

        document.getElementById('player-card-age').innerText = `${node.age} años`;
        document.getElementById('player-card-cost').innerText = node.cost_raw || 'Gratis / Cesión';
        document.getElementById('player-card-from').innerText = node.source_node;
        document.getElementById('player-card-to').innerText = node.target_node;
        document.getElementById('player-card-desc').innerText = `Operación oficial registrada para la Temporada ${node.season.replace('-', '/')}. Importe: ${node.cost_raw}.`;
        return;
    }

    playerScoutingBox.classList.add('hidden');
    clubFinanceBox.classList.remove('hidden');
    listsContainer.classList.remove('hidden');

    document.getElementById('detail-profile').innerText = node.fin_profile || "Balance Equilibrado 🔵";
    document.getElementById('detail-role').innerText = node.role_desc || "⚽ Club Participante";

    const seasonText = (selectedSeason === 'all') ? 'Todas las Temporadas' : `Temp. ${selectedSeason.replace('-', '/')}`;
    const costText = (minFinancialCost > 0) ? ` (> ${minFinancialCost}M€)` : '';
    document.getElementById('detail-context-badge').innerText = `${seasonText}${costText}`;

    const arrUl = document.getElementById('arrivals-list');
    const depUl = document.getElementById('departures-list');
    arrUl.innerHTML = '';
    depUl.innerHTML = '';

    const stats = clubStats[nodeId];
    if (!stats) {
        arrUl.innerHTML = '<li class="text-slate-500">Sin datos de altas</li>';
        depUl.innerHTML = '<li class="text-slate-500">Sin datos de bajas</li>';
        document.getElementById('count-arrivals').innerText = '0';
        document.getElementById('count-departures').innerText = '0';
        document.getElementById('detail-spent').innerText = '0.00 M€';
        document.getElementById('detail-earned').innerText = '0.00 M€';
        return;
    }

    let arrivals = [];
    let departures = [];

    if (selectedSeason === 'all') {
        arrivals = [
            ...stats['2025-2026'].arrivals.map(a => ({ ...a, season: '2025-2026' })),
            ...stats['2026-2027'].arrivals.map(a => ({ ...a, season: '2026-2027' }))
        ];
        departures = [
            ...stats['2025-2026'].departures.map(d => ({ ...d, season: '2025-2026' })),
            ...stats['2026-2027'].departures.map(d => ({ ...d, season: '2026-2027' }))
        ];
    } else if (stats[selectedSeason]) {
        arrivals = stats[selectedSeason].arrivals.map(a => ({ ...a, season: selectedSeason }));
        departures = stats[selectedSeason].departures.map(d => ({ ...d, season: selectedSeason }));
    }

    if (minFinancialCost > 0) {
        arrivals = arrivals.filter(a => a.cost_val >= minFinancialCost);
        departures = departures.filter(d => d.cost_val >= minFinancialCost);
    }

    const dynamicSpent = arrivals.reduce((acc, a) => acc + a.cost_val, 0);
    const dynamicEarned = departures.reduce((acc, d) => acc + d.cost_val, 0);
    const maxVal = Math.max(dynamicSpent, dynamicEarned, 1.0);

    document.getElementById('detail-spent').innerText = `${dynamicSpent.toFixed(2)} M€`;
    document.getElementById('detail-earned').innerText = `${dynamicEarned.toFixed(2)} M€`;

    document.getElementById('bar-spent').style.width = `${Math.min((dynamicSpent / maxVal) * 100, 100)}%`;
    document.getElementById('bar-earned').style.width = `${Math.min((dynamicEarned / maxVal) * 100, 100)}%`;

    document.getElementById('count-arrivals').innerText = arrivals.length;
    document.getElementById('count-departures').innerText = departures.length;

    if (arrivals.length === 0) {
        arrUl.innerHTML = '<li class="text-slate-500 py-1">Sin altas para este filtro</li>';
    } else {
        arrivals.forEach(a => {
            const sBadge = (a.season === '2025-2026') ? '25/26' : '26/27';
            arrUl.innerHTML += `
                <li class="bg-slate-950 p-2 rounded-xl border border-slate-800 flex justify-between items-center gap-1">
                    <div>
                        <b>${a.player}</b> <span class="text-emerald-400 font-bold">(${a.cost})</span>
                        <div class="text-slate-400 text-[10px]">desde ${a.from}</div>
                    </div>
                    <span class="bg-violet-950/80 text-violet-300 text-[9px] px-1.5 py-0.5 rounded-lg border border-violet-800/50 font-bold shrink-0">${sBadge}</span>
                </li>
            `;
        });
    }

    if (departures.length === 0) {
        depUl.innerHTML = '<li class="text-slate-500 py-1">Sin bajas para este filtro</li>';
    } else {
        departures.forEach(d => {
            const sBadge = (d.season === '2025-2026') ? '25/26' : '26/27';
            depUl.innerHTML += `
                <li class="bg-slate-950 p-2 rounded-xl border border-slate-800 flex justify-between items-center gap-1">
                    <div>
                        <b>${d.player}</b> <span class="text-red-400 font-bold">(${d.cost})</span>
                        <div class="text-slate-400 text-[10px]">hacia ${d.to}</div>
                    </div>
                    <span class="bg-violet-950/80 text-violet-300 text-[9px] px-1.5 py-0.5 rounded-lg border border-violet-800/50 font-bold shrink-0">${sBadge}</span>
                </li>
            `;
        });
    }
}

// ---- Tours guiados ----
async function playStory(num) {
    if (!network) return;
    if (num === 1) {
        currentlySelectedNodeId = 'Alavés';
        network.focus('Alavés', { scale: 1.1, animation: true });
        network.selectNodes(['Alavés', 'Espanyol', 'Mirandés']);
        showNodeDetails('Alavés');
        highlightEgoNetwork('Alavés');
        openDrawer();
    } else if (num === 2) {
        currentlySelectedNodeId = 'Resto del mundo';
        network.focus('Resto del mundo', { scale: 1.0, animation: true });
        network.selectNodes(['Resto del mundo', 'Premier League']);
        showNodeDetails('Resto del mundo');
        highlightEgoNetwork('Resto del mundo');
        openDrawer();
    } else if (num === 3) {
        setDivisionFilter('Cantera / Filial');
        fitNetwork();
    }
}

// ---- Barra flotante de fichajes estrella ----
function renderStarTransfers() {
    const container = document.getElementById('star-transfers-container');
    container.innerHTML = '';
    starTransfers.slice(0, 5).forEach(st => {
        container.innerHTML += `
            <button onclick="focusStarTransfer('${st.from}', '${st.to}')" class="bg-slate-950 hover:bg-slate-800 text-slate-200 text-[10px] px-2.5 py-1 rounded-lg border border-slate-800 whitespace-nowrap font-bold">
                <span class="text-amber-300">${st.player}</span> (${st.cost})
            </button>
        `;
    });
}

function focusStarTransfer(src, tgt) {
    if (network) {
        currentlySelectedNodeId = src;
        network.selectNodes([src, tgt]);
        network.focus(src, { scale: 1.1, animation: true });
        showNodeDetails(src);
        applyNodeEmphasis(src);
        openDrawer();
    }
}

// ---- Modales: abrir/cerrar ----
function openGuideModal() { document.getElementById('modal-guide').classList.remove('hidden'); }
function closeGuideModal() { document.getElementById('modal-guide').classList.add('hidden'); }
function openPathModal() { document.getElementById('modal-path').classList.remove('hidden'); }
function closePathModal() { document.getElementById('modal-path').classList.add('hidden'); }
function openWhatIfModal() { document.getElementById('modal-whatif').classList.remove('hidden'); }
function closeWhatIfModal() { document.getElementById('modal-whatif').classList.add('hidden'); }
function openCompareModal() { document.getElementById('modal-compare').classList.remove('hidden'); updateCompareView(); }
function closeCompareModal() { document.getElementById('modal-compare').classList.add('hidden'); }

function openAnalyticsModal() {
    document.getElementById('modal-analytics').classList.remove('hidden');
    if (typeof loadChartsModuleAndRender === 'function') {
        loadChartsModuleAndRender();
    } else if (typeof renderAnalyticsCharts === 'function') {
        renderAnalyticsCharts();
    }
}
function closeAnalyticsModal() { document.getElementById('modal-analytics').classList.add('hidden'); }
function openFichaModal() { document.getElementById('modal-ficha').classList.remove('hidden'); }
function closeFichaModal() { document.getElementById('modal-ficha').classList.add('hidden'); }

// ---- Selects de los modales (Camino, WhatIf, Comparador) ----
function populateDropdowns() {
    const clubsSorted = [...clubNodes].sort((a, b) => a.label.localeCompare(b.label));
    ['path-select-a', 'path-select-b', 'whatif-select-a', 'whatif-select-b', 'compare-select-a', 'compare-select-b'].forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        el.innerHTML = '';
        clubsSorted.forEach((c, idx) => {
            el.innerHTML += `<option value="${c.id}" ${idx === 0 ? 'selected' : ''}>${c.label}</option>`;
        });
    });
}

// ---- Camino más corto (grados de separación) ----
function findAndHighlightPath() {
    const src = document.getElementById('path-select-a').value;
    const tgt = document.getElementById('path-select-b').value;
    if (src === tgt) return;

    let queue = [[src]];
    let visited = new Set([src]);
    let foundPath = null;

    while (queue.length > 0) {
        let path = queue.shift();
        let lastNode = path[path.length - 1];

        if (lastNode === tgt) {
            foundPath = path;
            break;
        }

        let neighbors = clubEdges.filter(e => e.from === lastNode || e.to === lastNode).map(e => e.from === lastNode ? e.to : e.from);
        for (let n of neighbors) {
            if (!visited.has(n)) {
                visited.add(n);
                queue.push([...path, n]);
            }
        }
    }

    const box = document.getElementById('path-result-box');
    box.classList.remove('hidden');

    if (foundPath) {
        box.innerHTML = `<span class="text-emerald-400 font-bold">¡Camino encontrado (${foundPath.length - 1} pasos de distancia)!</span><br><br>` + foundPath.join(' ➔ ');
        network.selectNodes(foundPath);
        network.focus(src, { scale: 1.0, animation: true });
    } else {
        box.innerHTML = `<span class="text-red-400 font-bold">No se encontró un camino directo en la muestra de datos.</span>`;
    }
}

// ---- Simulador "Qué pasa si..." ----
function simulateWhatIfTransfer() {
    const src = document.getElementById('whatif-select-a').value;
    const tgt = document.getElementById('whatif-select-b').value;

    const tempId = `temp_edge_${Date.now()}`;
    edgesDataset.add({
        id: tempId, from: src, to: tgt, label: "Fichaje Simulado",
        color: { color: '#34d399' }, width: 4, dashes: true, arrows: "to"
    });

    const box = document.getElementById('whatif-result-box');
    box.classList.remove('hidden');
    box.innerHTML = `<span class="text-emerald-400 font-bold">¡Fichaje Simulado Añadido!</span><br>Se ha dibujado un enlace temporal verde desde <b>${src}</b> hasta <b>${tgt}</b>. Observa cómo cambia la estructura de la red.`;

    network.focus(src, { scale: 1.1, animation: true });
}

// ---- Comparador de clubes cara a cara ----
function updateCompareView() {
    const idA = document.getElementById('compare-select-a').value;
    const idB = document.getElementById('compare-select-b').value;

    const nodeA = clubNodes.find(n => n.id === idA);
    const nodeB = clubNodes.find(n => n.id === idB);

    if (!nodeA || !nodeB) return;

    const directEdges = clubEdges.filter(e =>
        (e.from === idA && e.to === idB) || (e.from === idB && e.to === idA)
    );

    let directText = "Sin traspasos directos entre estos dos clubes.";
    if (directEdges.length > 0) {
        directText = directEdges.map(e => `${e.from} ➔ ${e.to}: ${e.weight} traspaso(s) (${e.cost_total} M€)`).join('<br>');
    }

    const container = document.getElementById('compare-cards-container');
    container.innerHTML = `
        <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800 flex flex-col gap-2">
            <h3 class="text-base font-extrabold text-sky-400">${nodeA.label}</h3>
            <span class="text-[10px] bg-slate-900 px-2 py-0.5 rounded w-max text-slate-300 font-bold">${nodeA.group}</span>
            <p class="text-xs text-amber-300 font-semibold">${nodeA.role_desc}</p>
            <div class="grid grid-cols-2 gap-2 text-xs mt-2 text-slate-300">
                <div>Grado Total: <b>${nodeA.degree}</b></div>
                <div>Betweenness: <b>${nodeA.betweenness}</b></div>
                <div>PageRank: <b>${nodeA.pagerank}</b></div>
                <div>Gasto: <b class="text-red-400">${nodeA.spent_m} M€</b></div>
                <div>Ventas: <b class="text-emerald-400">${nodeA.earned_m} M€</b></div>
            </div>
        </div>

        <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800 flex flex-col gap-2">
            <h3 class="text-base font-extrabold text-emerald-400">${nodeB.label}</h3>
            <span class="text-[10px] bg-slate-900 px-2 py-0.5 rounded w-max text-slate-300 font-bold">${nodeB.group}</span>
            <p class="text-xs text-amber-300 font-semibold">${nodeB.role_desc}</p>
            <div class="grid grid-cols-2 gap-2 text-xs mt-2 text-slate-300">
                <div>Grado Total: <b>${nodeB.degree}</b></div>
                <div>Betweenness: <b>${nodeB.betweenness}</b></div>
                <div>PageRank: <b>${nodeB.pagerank}</b></div>
                <div>Gasto: <b class="text-red-400">${nodeB.spent_m} M€</b></div>
                <div>Ventas: <b class="text-emerald-400">${nodeB.earned_m} M€</b></div>
            </div>
        </div>

        <div class="col-span-1 md:col-span-2 bg-slate-950 p-3 rounded-xl border border-slate-800 text-xs text-slate-300 text-center">
            <span class="font-bold text-amber-400 uppercase tracking-wider text-[10px] block mb-1">Conexión Directa Entre Ambos Clubes</span>
            <div>${directText}</div>
        </div>
    `;
}

// Expuestas globalmente para los atributos onclick/onchange del HTML.
window.changeTheme = changeTheme;
window.toggleSidebar = toggleSidebar;
window.openDrawer = openDrawer;
window.closeDrawer = closeDrawer;
window.resetGlobalView = resetGlobalView;
window.handleSearchInput = handleSearchInput;
window.selectSearchResult = selectSearchResult;
window.showNodeDetails = showNodeDetails;
window.playStory = playStory;
window.renderStarTransfers = renderStarTransfers;
window.focusStarTransfer = focusStarTransfer;
window.openGuideModal = openGuideModal;
window.closeGuideModal = closeGuideModal;
window.openPathModal = openPathModal;
window.closePathModal = closePathModal;
window.openWhatIfModal = openWhatIfModal;
window.closeWhatIfModal = closeWhatIfModal;
window.openCompareModal = openCompareModal;
window.closeCompareModal = closeCompareModal;
window.openAnalyticsModal = openAnalyticsModal;
window.closeAnalyticsModal = closeAnalyticsModal;
window.openFichaModal = openFichaModal;
window.closeFichaModal = closeFichaModal;
window.populateDropdowns = populateDropdowns;
window.findAndHighlightPath = findAndHighlightPath;
window.simulateWhatIfTransfer = simulateWhatIfTransfer;
window.updateCompareView = updateCompareView;
