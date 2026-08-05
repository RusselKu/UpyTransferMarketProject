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
let focusedNodeId = null;     // qué nodo está aislado (para poder recomponerlo tras un cambio de filtro)

let timelinePlaying = false;
let timelineInterval = null;

// Helper para convertir strings de HTML en nodos DOM y evitar tooltips nativos del navegador
function htmlTitle(html) {
    const container = document.createElement("div");
    container.innerHTML = html;
    return container;
}

let nodesDataset = null;
let edgesDataset = null;

const timelineSteps = [
    { value: 0, season: 'all', label: 'Todas las Temporadas' },
    { value: 1, season: '2025-2026', label: 'Temporada 2025/2026' },
    { value: 2, season: '2026-2027', label: 'Temporada 2026/2027' }
];

function formatNodeCopy(n) {
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
        if (!showPlayerLabels) copy.label = undefined;
    }
    if (copy.title && typeof copy.title === 'string') {
        copy.title = htmlTitle(copy.title);
    }
    return copy;
}

function getActiveEdges() {
    let baseEdges = (viewMode === 'clubs_only') ? clubEdges : heteroEdges;
    return baseEdges.filter(e => {
        if (selectedSeason !== 'all' && e.season !== selectedSeason) return false;
        if (minFinancialCost > 0) {
            let c = e.cost_total || e.cost_val || 0;
            if (c < minFinancialCost) return false;
        }
        
        // FILTRO INTELIGENTE DE DIVISION/LIGA:
        if (selectedDivision !== 'all') {
            if (viewMode === 'clubs_only') {
                const fromNode = clubNodes.find(n => n.id === e.from);
                const toNode = clubNodes.find(n => n.id === e.to);
                const fromGroup = fromNode ? fromNode.group : '';
                const toGroup = toNode ? toNode.group : '';
                if (fromGroup !== selectedDivision && toGroup !== selectedDivision) return false;
            } else {
                // En modo hetero, cada arista conecta un Jugador con un Club.
                const fromNode = heteroNodes.find(n => n.id === e.from);
                const toNode = heteroNodes.find(n => n.id === e.to);
                
                const playerNode = (fromNode && fromNode.group === 'Jugador') ? fromNode : 
                                   ((toNode && toNode.group === 'Jugador') ? toNode : null);
                
                if (playerNode) {
                    const pFromClub = clubNodes.find(c => c.id === playerNode.from_club);
                    const pToClub = clubNodes.find(c => c.id === playerNode.to_club);
                    const pFromGroup = pFromClub ? pFromClub.group : '';
                    const pToGroup = pToClub ? pToClub.group : '';
                    if (pFromGroup !== selectedDivision && pToGroup !== selectedDivision) return false;
                } else {
                    const fromGroup = fromNode ? fromNode.group : '';
                    const toGroup = toNode ? toNode.group : '';
                    if (fromGroup !== selectedDivision && toGroup !== selectedDivision) return false;
                }
            }
        }
        return true;
    }).map(e => {
        let copy = Object.assign({}, e);
        if (copy.title && typeof copy.title === 'string') {
            copy.title = htmlTitle(copy.title);
        }
        return copy;
    });
}

function getActiveNodes() {
    let baseNodes = (viewMode === 'clubs_only') ? clubNodes : heteroNodes;
    
    if (selectedDivision !== 'all') {
        const activeEdges = getActiveEdges();
        const activeNodeIds = new Set();
        activeEdges.forEach(e => {
            activeNodeIds.add(e.from);
            activeNodeIds.add(e.to);
        });
        
        // Incluir los clubes de la división seleccionada por si hay nodos huérfanos/aislados
        baseNodes.forEach(n => {
            if (n.group === selectedDivision) {
                activeNodeIds.add(n.id);
            }
        });

        return baseNodes.filter(n => activeNodeIds.has(n.id)).map(n => formatNodeCopy(n));
    }

    return baseNodes.map(n => formatNodeCopy(n));
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

    setCounters(nodesDataset.length, totalEdgeCountLabel(edgesDataset.get()));

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

            // El ENFOQUE va primero y aislado en su propio try: si el panel de
            // detalle fallara con algún nodo, el aislamiento debe ocurrir igual.
            try {
                applyNodeEmphasis(selectedId);
            } catch (err) {
                console.error('Fallo al enfocar el nodo', selectedId, err);
            }

            try {
                showNodeDetails(selectedId);
                openDrawer();
            } catch (err) {
                console.error('Fallo al pintar el panel de detalle de', selectedId, err);
            }
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

// Helper para obtener vecinos de un nodo desde el grafo original (sin importar el estado de filtrado actual)
function getFullNeighborhood(nodeId) {
    const neighbors = new Set();
    neighbors.add(nodeId);
    
    const baseEdges = (viewMode === 'clubs_only') ? clubEdges : heteroEdges;
    baseEdges.forEach(e => {
        if (e.from === nodeId) neighbors.add(e.to);
        if (e.to === nodeId) neighbors.add(e.from);
    });
    return neighbors;
}

// Aplica énfasis a un nodo segun el modo activo: aislar (enfoque) o normal.
function applyNodeEmphasis(nodeId) {
    if (focusMode) {
        focusOnNode(nodeId);
    } else {
        // En modo normal, no atenuamos ni aislamos nada al hacer clic en un club/jugador
        resetEgoHighlight();
    }
}

// ---- Chrome de UI del Modo Enfoque (badge + botón de salida) ----
// Debe ejecutarse SIEMPRE que cambie isFocused: si no, el botón "Ver todo el
// grafo" nunca aparece y el usuario queda encerrado en la vista aislada.
function updateFocusChrome(nodeCount, edgeCount) {
    const btn = document.getElementById('btn-clear-focus');
    if (btn) btn.classList.toggle('hidden', !isFocused);

    const badge = document.getElementById('focus-badge');
    if (badge) {
        badge.classList.toggle('hidden', !isFocused);
        if (isFocused) {
            const neighbors = Math.max((nodeCount || 1) - 1, 0);
            badge.innerHTML = `🎯 <b class="text-white">${focusedNodeId}</b>` +
                `<span class="text-cyan-200/70"> · ${neighbors} vecino${neighbors === 1 ? '' : 's'} · ${edgeCount || 0} enlaces</span>`;
        }
    }
}

function setCounters(nodeCount, edgeCount) {
    const n = document.getElementById('nodes-count');
    const e = document.getElementById('edges-count');
    if (n) n.innerText = nodeCount;
    if (e) e.innerText = edgeCount;
}

function totalEdgeCountLabel(activeEdges) {
    // En la vista de clubes las aristas están agregadas (una por par de clubes),
    // así que mostramos el total real de traspasos que viene de meta.json.
    if (viewMode === 'clubs_only' && selectedSeason === 'all' && selectedDivision === 'all' && minFinancialCost === 0) {
        return window.__META__ ? window.__META__.total_transfers : clubEdges.length;
    }
    return activeEdges.length;
}

// ---- Modo Enfoque: aislar un nodo y su vecindario (ocultar el resto) ----
function focusOnNode(nodeId) {
    if (!network || !nodesDataset || !edgesDataset) return;

    // La vecindad SIEMPRE se calcula sobre los arreglos globales (clubEdges /
    // heteroEdges), nunca sobre lo que hay en el canvas: si se calculara con
    // network.getConnectedNodes() la red se encogería en cada clic sucesivo.
    const neighborhood = getFullNeighborhood(nodeId);

    isFocused = true;
    focusedNodeId = nodeId;

    // Mantener SOLO el nodo y sus vecinos, resaltando el nodo raíz.
    const filteredNodes = getActiveNodes()
        .filter(n => neighborhood.has(n.id))
        .map(n => (n.id !== nodeId) ? n : Object.assign({}, n, {
            borderWidth: 5,
            shadow: { enabled: true, color: 'rgba(34,211,238,0.9)', size: 28, x: 0, y: 0 }
        }));

    // Aristas incidentes al nodo raíz en cian y gruesas; las aristas entre
    // vecinos (subgrafo inducido) quedan tenues para no robar atención.
    const filteredEdges = getActiveEdges()
        .filter(e => neighborhood.has(e.from) && neighborhood.has(e.to))
        .map(e => Object.assign({}, e, (e.from === nodeId || e.to === nodeId)
            ? { width: 3, color: { color: '#22d3ee', highlight: '#67e8f9', opacity: 1, inherit: false } }
            : { width: 0.6, color: { color: '#475569', opacity: 0.35, inherit: false } }));

    // Con physics:false, .update({hidden:true}) NO repinta el canvas estático:
    // hay que reemplazar el contenido del DataSet (clear + add) para forzar el
    // redibujado inmediato del motor.
    nodesDataset.clear();
    nodesDataset.add(filteredNodes);

    edgesDataset.clear();
    edgesDataset.add(filteredEdges);

    setCounters(filteredNodes.length, filteredEdges.length);
    updateFocusChrome(filteredNodes.length, filteredEdges.length);

    network.selectNodes([nodeId]);

    // Encuadrar SOLO con ids que existen realmente en el dataset: los ids de la
    // vecindad que quedaron fuera por los filtros harían que fit() calculara un
    // encuadre imposible (zoom disparado / grafo "encogido").
    const presentIds = filteredNodes.map(n => n.id);
    const anim = { duration: 500, easingFunction: 'easeInOutQuad' };
    if (presentIds.length > 1) {
        network.fit({ nodes: presentIds, maxZoomLevel: 1.6, animation: anim });
    } else {
        const root = filteredNodes[0];
        const pos = (root && typeof root.x === 'number')
            ? { x: root.x, y: root.y }
            : network.getPositions([nodeId])[nodeId];
        if (pos) network.moveTo({ position: pos, scale: 1.1, animation: anim });
    }
}

function clearFocus() {
    isFocused = false;
    focusedNodeId = null;
    updateFocusChrome();

    if (!nodesDataset || !edgesDataset) return;

    // Cargar todos los nodos y aristas activos según los filtros normales
    const activeNodes = getActiveNodes();
    const activeEdges = getActiveEdges();

    nodesDataset.clear();
    nodesDataset.add(activeNodes);

    edgesDataset.clear();
    edgesDataset.add(activeEdges);

    setCounters(activeNodes.length, totalEdgeCountLabel(activeEdges));

    resetEgoHighlight();
    if (network) {
        network.unselectAll();
        network.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
    }
}

function setFocusMode(on) {
    focusMode = !!on;
    const hint = document.getElementById('focus-mode-hint');
    if (hint) hint.classList.toggle('hidden', !focusMode);

    // Mantener el checkbox sincronizado aunque se llame desde código (Escape,
    // reset global, tours): así el control nunca queda "invertido".
    const toggle = document.getElementById('toggle-focus-mode');
    if (toggle) toggle.checked = focusMode;

    const state = document.getElementById('focus-mode-state');
    if (state) {
        state.innerText = focusMode ? 'On' : 'Off';
        state.className = 'text-[9px] font-extrabold uppercase tracking-wider ' + (focusMode ? 'text-cyan-300' : 'text-slate-500');
    }

    if (focusMode) {
        // El toggle SOLO arma el modo: no aísla el nodo que estuviera
        // seleccionado de antes. El aislamiento ocurre con el clic siguiente,
        // sobre cualquier nodo. (Auto-aislar al activar se sentía "invertido".)
        if (typeof showToast === 'function') {
            showToast('🎯 Modo Enfoque <b>activo</b>: toca cualquier nodo para aislar su red.');
        }
    } else {
        // Al desactivar, la red vuelve al 100% de color/opacidad y sin aislamiento.
        clearFocus();
    }
}

function updateNetworkData(options) {
    if (!nodesDataset || !edgesDataset) return;
    const preserveFocus = !(options && options.preserveFocus === false);

    // Si había un nodo aislado, intentamos recomponer el enfoque con los nuevos
    // filtros en vez de expulsar al usuario de la vista enfocada.
    const refocusId = (preserveFocus && isFocused && focusMode) ? focusedNodeId : null;
    isFocused = false;
    focusedNodeId = null;
    updateFocusChrome();

    nodesDataset.clear();
    edgesDataset.clear();
    const activeNodes = getActiveNodes();
    const activeEdges = getActiveEdges();
    nodesDataset.add(activeNodes);
    edgesDataset.add(activeEdges);

    setCounters(activeNodes.length, totalEdgeCountLabel(activeEdges));

    if (refocusId && nodesDataset.get(refocusId)) {
        focusOnNode(refocusId);
    }

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

// Atenúa todo lo que no es el ego-network del nodo. OJO: esto NO se dispara al
// hacer clic (eso confundía al usuario porque parecía un aislamiento a medias);
// solo lo usan los tours guiados, que sí quieren un efecto de reflector.
function highlightEgoNetwork(selectedId) {
    if (!nodesDataset) return;
    // Vecindad desde los datos globales, no desde el canvas: así funciona
    // igual aunque haya filtros activos o una vista previamente reducida.
    const neighborhood = getFullNeighborhood(selectedId);
    const updateNodes = nodesDataset.get().map(n => ({
        id: n.id,
        opacity: neighborhood.has(n.id) ? 1.0 : 0.15
    }));
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

function resetFiltersAndVariables() {
    selectedSeason = 'all';
    selectedDivision = 'all';
    minFinancialCost = 0;
    nodeScalingMetric = 'degree';
    currentlySelectedNodeId = null;
    showPlayerLabels = false;
    focusMode = false;
    isFocused = false;
    focusedNodeId = null;
    updateFocusChrome();
}

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
window.resetFiltersAndVariables = resetFiltersAndVariables;
window.updateFocusChrome = updateFocusChrome;
window.isNetworkFocused = () => isFocused;
