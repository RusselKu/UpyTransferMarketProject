/* network.js
 * Todo lo relacionado con vis-network: inicialización, datasets activos,
 * filtros de escala/financiero/división/temporada, timeline animado,
 * modo de vista (clubs / hetero) y resaltado de ego-network.
 *
 * Depende de variables globales pobladas por main.js (clubNodes, clubEdges,
 * heteroNodes, heteroEdges) y de utilidades UI definidas en ui.js
 * (openDrawer/closeDrawer/showNodeDetails/populateDropdowns/renderStarTransfers).
 */

// ---- Estado compartido de la red y de los filtros ----
let network = null;
let viewMode = 'clubs_only';
let selectedSeason = 'all';
let selectedDivision = 'all';
let minFinancialCost = 0;
let nodeScalingMetric = 'degree';
let currentlySelectedNodeId = null;
let showPlayerLabels = false; // en vista hetero, ocultar los ~1034 nombres de jugador por defecto (anti-hairball)
let focusMode = false;        // si está activo, al hacer clic se aísla el nodo y su vecindario
let isFocused = false;        // hay actualmente un nodo aislado

let timelinePlaying = false;
let timelineInterval = null;

let nodesDataset = null;
let edgesDataset = null;

const timelineSteps = [
    { value: 0, season: 'all', label: 'Todas las Temporadas' },
    { value: 1, season: '2025-2026', label: 'Temporada 2025/2026' },
    { value: 2, season: '2026-2027', label: 'Temporada 2026/2027' }
];

function getActiveNodes() {
    let baseNodes = (viewMode === 'clubs_only') ? clubNodes : heteroNodes;
    return baseNodes.filter(n => {
        if (selectedDivision !== 'all') {
            if (n.group !== 'Jugador' && n.group !== selectedDivision) return false;
        }
        if (viewMode === 'hetero' && n.group === 'Jugador') {
            if (selectedSeason !== 'all' && n.season !== selectedSeason) return false;
            if (minFinancialCost > 0 && n.cost_val < minFinancialCost) return false;
        }
        return true;
    }).map(n => {
        let copy = Object.assign({}, n);
        if (n.group !== 'Jugador') {
            if (nodeScalingMetric === 'betweenness') {
                copy.value = 12 + Math.min(copy.betweenness * 400, 45);
            } else if (nodeScalingMetric === 'spent_m') {
                copy.value = 12 + Math.min(copy.spent_m * 0.5, 45);
            } else {
                copy.value = 12 + Math.min(copy.degree * 1.2, 35);
            }
        } else {
            copy.value = 6;
            // Ocultar el nombre del jugador salvo que el usuario lo active.
            // El nombre sigue disponible en el tooltip (title) y en el panel
            // de detalle al hacer clic, evitando el solapamiento masivo.
            if (!showPlayerLabels) copy.label = undefined;
        }
        return copy;
    });
}

function getActiveEdges() {
    let baseEdges = (viewMode === 'clubs_only') ? clubEdges : heteroEdges;
    return baseEdges.filter(e => {
        if (selectedSeason !== 'all' && e.season !== selectedSeason) return false;
        if (minFinancialCost > 0) {
            let c = e.cost_total || e.cost_val || 0;
            if (c < minFinancialCost) return false;
        }
        return true;
    });
}

function showLoadingOverlay() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.remove('hidden');
        overlay.offsetWidth; // trigger reflow
        overlay.classList.remove('opacity-0', 'pointer-events-none');
    }
}

function hideLoadingOverlay() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.add('opacity-0', 'pointer-events-none');
        setTimeout(() => {
            if (overlay.classList.contains('opacity-0')) {
                overlay.classList.add('hidden');
            }
        }, 300);
    }
}

function initNetwork() {
    showLoadingOverlay();
    const container = document.getElementById('network-canvas');

    nodesDataset = new vis.DataSet(getActiveNodes());
    edgesDataset = new vis.DataSet(getActiveEdges());

    document.getElementById('nodes-count').innerText = nodesDataset.length;
    document.getElementById('edges-count').innerText = (viewMode === 'clubs_only') ? (window.__META__ ? window.__META__.total_transfers : clubEdges.length) : edgesDataset.length;

    const data = { nodes: nodesDataset, edges: edgesDataset };

    // Los nodos ya traen posiciones x,y precalculadas (spring_layout) desde
    // el generador Python, así que deshabilitamos la simulación de físicas
    // para que la red se dibuje instantáneamente sin "warm-up".
    const hasPrecomputedLayout = nodesDataset.get().every(n => typeof n.x === 'number' && typeof n.y === 'number');

    const heteroMode = (viewMode === 'hetero');

    const options = {
        nodes: {
            font: { color: '#f8fafc', face: 'Outfit', size: 14, strokeWidth: 4, strokeColor: '#090d16' },
            borderWidth: 2, shadow: true,
            // El tamaño de la etiqueta escala con la importancia del nodo y con
            // el zoom: los nodos pequeños ocultan su texto hasta acercarse
            // (drawThreshold), descongestionando la vista alejada.
            scaling: {
                label: { enabled: true, min: 13, max: 30, drawThreshold: 4, maxVisible: 44 }
            }
        },
        edges: {
            width: heteroMode ? 0.5 : 1.5,
            smooth: { type: 'continuous', roundness: 0.25 },
            color: { inherit: false, opacity: heteroMode ? 0.35 : 0.75 },
            hoverWidth: 1.5, selectionWidth: 2
        },
        physics: hasPrecomputedLayout ? { enabled: false } : {
            solver: 'forceAtlas2Based',
            forceAtlas2Based: { gravConstant: -30, centralGravity: 0.01, springLength: 90, springConstant: 0.08 },
            stabilization: { iterations: 120 }
        },
        interaction: { hover: true, tooltipDelay: 80, zoomView: true, hideEdgesOnZoom: heteroMode }
    };

    network = new vis.Network(container, data, options);

    if (hasPrecomputedLayout) {
        // Sin físicas: el dibujado es inmediato, no hay evento que esperar.
        hideLoadingOverlay();
    } else {
        network.on("stabilizationIterationsDone", hideLoadingOverlay);
        // Fallback duro por si el evento no dispara (p.ej. grafo ya estable).
        setTimeout(hideLoadingOverlay, 3000);
    }

    network.on("click", function (params) {
        if (params.nodes.length > 0) {
            const selectedId = params.nodes[0];
            currentlySelectedNodeId = selectedId;
            showNodeDetails(selectedId);
            openDrawer();
            applyNodeEmphasis(selectedId);
        } else {
            closeDrawer();
            if (focusMode && isFocused) {
                clearFocus();
            } else {
                resetEgoHighlight();
            }
        }
    });

    populateDropdowns();
    renderStarTransfers();
}

// Aplica énfasis a un nodo segun el modo activo: aislar (enfoque) o atenuar.
function applyNodeEmphasis(nodeId) {
    if (focusMode) focusOnNode(nodeId);
    else highlightEgoNetwork(nodeId);
}

// ---- Modo Enfoque: aislar un nodo y su vecindario (ocultar el resto) ----
function focusOnNode(nodeId) {
    if (!network || !nodesDataset) return;
    const neighborhood = new Set(network.getConnectedNodes(nodeId));
    neighborhood.add(nodeId);

    const nodeUpdates = nodesDataset.get().map(n => ({ id: n.id, hidden: !neighborhood.has(n.id) }));
    nodesDataset.update(nodeUpdates);

    // Ocultar aristas que no conecten dos nodos visibles.
    const edgeUpdates = edgesDataset.get().map(e => ({
        id: e.id,
        hidden: !(neighborhood.has(e.from) && neighborhood.has(e.to))
    }));
    edgesDataset.update(edgeUpdates);

    isFocused = true;
    const btn = document.getElementById('btn-clear-focus');
    if (btn) btn.classList.remove('hidden');

    network.fit({ nodes: Array.from(neighborhood), animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
}

function clearFocus() {
    isFocused = false;
    const btn = document.getElementById('btn-clear-focus');
    if (btn) btn.classList.add('hidden');
    if (!nodesDataset) return;
    nodesDataset.update(nodesDataset.get().map(n => ({ id: n.id, hidden: false })));
    edgesDataset.update(edgesDataset.get().map(e => ({ id: e.id, hidden: false })));
    resetEgoHighlight();
    if (network) network.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
}

function setFocusMode(on) {
    focusMode = !!on;
    if (!focusMode && isFocused) clearFocus();
    const hint = document.getElementById('focus-mode-hint');
    if (hint) hint.classList.toggle('hidden', !focusMode);
}

function updateNetworkData() {
    if (!nodesDataset || !edgesDataset) return;
    // Cualquier cambio de filtro/vista reconstruye el dataset y sale del enfoque.
    if (isFocused) {
        isFocused = false;
        const btn = document.getElementById('btn-clear-focus');
        if (btn) btn.classList.add('hidden');
    }
    nodesDataset.clear();
    edgesDataset.clear();
    nodesDataset.add(getActiveNodes());
    edgesDataset.add(getActiveEdges());

    document.getElementById('nodes-count').innerText = nodesDataset.length;
    document.getElementById('edges-count').innerText = (viewMode === 'clubs_only') ? (window.__META__ ? window.__META__.total_transfers : clubEdges.length) : edgesDataset.length;

    if (currentlySelectedNodeId) {
        showNodeDetails(currentlySelectedNodeId);
    }
}

async function setViewMode(mode) {
    if (mode === 'hetero' && !heteroDataLoaded && typeof ensureHeteroDataLoaded === 'function') {
        showLoadingOverlay();
        await ensureHeteroDataLoaded();
        hideLoadingOverlay();
    }

    viewMode = mode;
    if (mode === 'clubs_only') {
        document.getElementById('btn-view-clubs').className = "py-1.5 px-2 rounded-lg font-bold text-center bg-violet-600 text-white shadow";
        document.getElementById('btn-view-hetero').className = "py-1.5 px-2 rounded-lg font-bold text-center text-slate-400 hover:text-white transition";
    } else {
        document.getElementById('btn-view-hetero').className = "py-1.5 px-2 rounded-lg font-bold text-center bg-violet-600 text-white shadow";
        document.getElementById('btn-view-clubs').className = "py-1.5 px-2 rounded-lg font-bold text-center text-slate-400 hover:text-white transition";
    }

    applyEdgeStyleForMode();
    updateNetworkData();
    if (network) {
        network.fit({ animation: true });
    }
}

// Aplica el estilo de aristas/interacción segun la vista activa (aristas muy
// tenues y finas en hetero para reducir el "espagueti"; normales en clubes).
function applyEdgeStyleForMode() {
    if (!network) return;
    const heteroMode = (viewMode === 'hetero');
    network.setOptions({
        edges: {
            width: heteroMode ? 0.5 : 1.5,
            color: { inherit: false, opacity: heteroMode ? 0.35 : 0.75 }
        },
        interaction: { hideEdgesOnZoom: heteroMode }
    });
}

// Toggle desde el checkbox de la barra lateral: mostrar/ocultar nombres de jugador.
function setPlayerLabels(show) {
    showPlayerLabels = !!show;
    updateNetworkData();
}

function highlightEgoNetwork(selectedId) {
    if (!network) return;
    const connectedNodes = network.getConnectedNodes(selectedId);
    connectedNodes.push(selectedId);

    const allNodes = nodesDataset.get();
    const updateNodes = allNodes.map(n => {
        if (connectedNodes.includes(n.id)) {
            return { id: n.id, opacity: 1.0 };
        } else {
            return { id: n.id, opacity: 0.15 };
        }
    });
    nodesDataset.update(updateNodes);
}

function resetEgoHighlight() {
    if (!nodesDataset) return;
    const allNodes = nodesDataset.get();
    const updateNodes = allNodes.map(n => ({ id: n.id, opacity: 1.0 }));
    nodesDataset.update(updateNodes);
}

function setNodeScaling(metric) { nodeScalingMetric = metric; updateNetworkData(); }
function setFinancialFilter(val) {
    if (val === 'paid') minFinancialCost = 0.01;
    else minFinancialCost = parseFloat(val);
    updateNetworkData();
}
function setDivisionFilter(div) { selectedDivision = div; updateNetworkData(); }
function setSeason(season) {
    selectedSeason = season;
    document.getElementById('select-season').value = season;
    updateNetworkData();
}

function onSeasonDropdownChange(val) {
    selectedSeason = val;
    let sliderVal = 0;
    if (val === '2025-2026') sliderVal = 1;
    else if (val === '2026-2027') sliderVal = 2;
    const slider = document.getElementById('timeline-slider');
    if (slider) slider.value = sliderVal;
    const label = document.getElementById('timeline-label');
    if (label) label.innerText = (val === 'all') ? 'Todas' : (val === '2025-2026' ? '2025/26' : '2026/27');
    updateNetworkData();
}

function onTimelineStep(val) {
    const step = timelineSteps[val];
    if (step) {
        const label = document.getElementById('timeline-label');
        if (label) label.innerText = step.label;
        setSeason(step.season);
    }
}

function toggleTimelinePlay() {
    timelinePlaying = !timelinePlaying;
    const btnIcon = document.getElementById('icon-play');
    const slider = document.getElementById('timeline-slider');
    if (timelinePlaying) {
        if (btnIcon) btnIcon.innerHTML = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6" />`;
        let currentVal = slider ? parseInt(slider.value) : 0;
        timelineInterval = setInterval(() => {
            currentVal = (currentVal + 1) % 3;
            if (slider) slider.value = currentVal;
            onTimelineStep(currentVal);
        }, 1800);
    } else {
        if (btnIcon) btnIcon.innerHTML = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />`;
        clearInterval(timelineInterval);
    }
}

function stopTimeline() {
    if (timelinePlaying) {
        toggleTimelinePlay();
    }
}

function fitNetwork() { if (network) network.fit({ animation: true }); }

// Expuestas globalmente para los atributos onclick/onchange del HTML.
window.getActiveNodes = getActiveNodes;
window.getActiveEdges = getActiveEdges;
window.initNetwork = initNetwork;
window.updateNetworkData = updateNetworkData;
window.setViewMode = setViewMode;
window.setPlayerLabels = setPlayerLabels;
window.setFocusMode = setFocusMode;
window.focusOnNode = focusOnNode;
window.clearFocus = clearFocus;
window.applyNodeEmphasis = applyNodeEmphasis;
window.highlightEgoNetwork = highlightEgoNetwork;
window.resetEgoHighlight = resetEgoHighlight;
window.setNodeScaling = setNodeScaling;
window.setFinancialFilter = setFinancialFilter;
window.setDivisionFilter = setDivisionFilter;
window.setSeason = setSeason;
window.onSeasonDropdownChange = onSeasonDropdownChange;
window.onTimelineStep = onTimelineStep;
window.toggleTimelinePlay = toggleTimelinePlay;
window.stopTimeline = stopTimeline;
window.fitNetwork = fitNetwork;
