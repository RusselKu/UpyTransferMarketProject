import json
import os
import sys

# Reconfigure stdout for UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Division classifications of clubs
DIVISION_1 = {
    "Real Madrid", "FC Barcelona", "Atlético de Madrid", "Real Sociedad", "Celta de Vigo",
    "Athletic Bilbao", "Sevilla", "Real Betis", "Villarreal", "Valencia", "Alavés",
    "Osasuna", "Getafe", "Rayo Vallecano", "Espanyol", "Girona", "Mallorca", 
    "Real Valladolid", "Deportivo de la Coruña", "Elche", "Levante", "Málaga", 
    "Racing de Santander", "Real Oviedo"
}

def clean_cost(cost_str):
    if not cost_str:
        return "Gratis/Cesión"
    return cost_str

def main():
    dataset_file = "transfers_dataset.json"
    if not os.path.exists(dataset_file):
        print(f"Error: {dataset_file} not found. Please run the scraper first.")
        sys.exit(1)
        
    with open(dataset_file, "r", encoding="utf-8") as f:
        transfers = json.load(f)
        
    print(f"Loaded {len(transfers)} transfers from dataset. Building HTML Dashboard...")
    
    # Pre-compile transfer stats for each club to display in the side panel on click
    # Stats structure: { club: { season: { arrivals: [], departures: [] } } }
    club_stats = {}
    external_leagues = {"Premier League", "Bundesliga", "Ligue 1", "Serie A", "Resto del mundo"}
    
    # We will compute degrees for scaling sizes
    club_degrees = {}
    
    for t in transfers:
        src = t["source_node"]
        tgt = t["target_node"]
        player = t["player"]
        cost = clean_cost(t["cost"])
        season = t["season"]
        age = t["age"] or "N/D"
        
        # Track degree in club-only representation
        club_degrees[src] = club_degrees.get(src, 0) + 1
        club_degrees[tgt] = club_degrees.get(tgt, 0) + 1
        
        # Initialize stats dicts
        for node in [src, tgt]:
            if node not in club_stats:
                club_stats[node] = {
                    "2025-2026": {"arrivals": [], "departures": []},
                    "2026-2027": {"arrivals": [], "departures": []}
                }
                
        # Record details
        club_stats[src][season]["departures"].append({
            "player": player, "to": tgt, "cost": cost, "age": age
        })
        club_stats[tgt][season]["arrivals"].append({
            "player": player, "from": src, "cost": cost, "age": age
        })
        
    # Generate JavaScript lists for the HTML file
    # 1. Club-Only nodes & edges
    club_nodes_js = []
    seen_club_nodes = set()
    
    # Add external leagues explicitly
    for l in external_leagues:
        seen_club_nodes.add(l)
        deg = club_degrees.get(l, 1)
        val = 15 + min(deg, 30) # Scale size
        club_nodes_js.append({
            "id": l,
            "label": l,
            "group": "Liga Internacional",
            "value": val,
            "title": f"<b>{l}</b><br>Traspasos totales: {deg}"
        })
        
    # Add regular clubs
    for t in transfers:
        for node in [t["source_node"], t["target_node"]]:
            if node not in seen_club_nodes:
                seen_club_nodes.add(node)
                deg = club_degrees.get(node, 1)
                val = 12 + min(deg * 1.5, 35) # Scale size
                group = "Primera División" if node in DIVISION_1 else "Segunda División"
                club_nodes_js.append({
                    "id": node,
                    "label": node,
                    "group": group,
                    "value": val,
                    "title": f"<b>{node}</b> ({group})<br>Traspasos: {deg}"
                })
                
    club_edges_js = []
    for idx, t in enumerate(transfers):
        club_edges_js.append({
            "id": f"e_club_{idx}",
            "from": t["source_node"],
            "to": t["target_node"],
            "label": t["player"],
            "title": f"<b>{t['player']}</b> ({t['age']} años)<br>De: {t['source_node']}<br>A: {t['target_node']}<br>Coste: {t['cost']}<br>Temporada: {t['season']}",
            "season": t["season"],
            "arrows": "to"
        })
        
    # 2. Heterogeneous nodes & edges (Clubs + Players)
    hetero_nodes_js = []
    hetero_edges_js = []
    seen_hetero_clubs = set()
    
    # Add clubs to heterogeneous nodes
    for node in seen_club_nodes:
        group = "Liga Internacional" if node in external_leagues else ("Primera División" if node in DIVISION_1 else "Segunda División")
        deg = club_degrees.get(node, 1)
        val = 18 + min(deg, 35)
        hetero_nodes_js.append({
            "id": node,
            "label": node,
            "group": group,
            "value": val,
            "title": f"<b>{node}</b> ({group})"
        })
        
    # Add players as nodes and connect them with edges
    for idx, t in enumerate(transfers):
        player_node_id = f"pnode_{idx}"
        player = t["player"]
        cost = clean_cost(t["cost"])
        
        # Add Player Node
        hetero_nodes_js.append({
            "id": player_node_id,
            "label": player,
            "group": "Jugador",
            "value": 6,
            "title": f"<b>{player}</b> ({t['age']} años)<br>Coste: {cost}<br>Temporada: {t['season']}",
            "season": t["season"]
        })
        
        # Add edges: Source -> Player -> Target
        hetero_edges_js.append({
            "id": f"eh_src_{idx}",
            "from": t["source_node"],
            "to": player_node_id,
            "title": f"Salida de {t['source_node']}",
            "season": t["season"],
            "arrows": "to",
            "color": {"color": "rgba(239, 68, 68, 0.4)"} # Reddish for departures
        })
        hetero_edges_js.append({
            "id": f"eh_tgt_{idx}",
            "from": player_node_id,
            "to": t["target_node"],
            "title": f"Llegada a {t['target_node']}",
            "season": t["season"],
            "arrows": "to",
            "color": {"color": "rgba(16, 185, 129, 0.4)"} # Greenish for arrivals
        })

    # Read and construct HTML template
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard de Traspasos de LaLiga (2025-2027)</title>
    
    <!-- Tailwind CSS (CDN) -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- Vis.js Network CDN -->
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: #0f172a;
            color: #f1f5f9;
        }}
        /* Custom scrollbar */
        ::-webkit-scrollbar {{
            width: 6px;
        }}
        ::-webkit-scrollbar-track {{
            background: #1e293b;
        }}
        ::-webkit-scrollbar-thumb {{
            background: #475569;
            border-radius: 3px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #64748b;
        }}
        .glass {{
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}
    </style>
</head>
<body class="h-screen w-screen flex flex-col overflow-hidden">

    <!-- Header bar -->
    <header class="h-16 w-full glass px-6 flex justify-between items-center z-10 border-b border-slate-800">
        <div class="flex items-center gap-3">
            <div class="w-3 h-3 rounded-full bg-violet-500 animate-pulse"></div>
            <h1 class="text-xl font-bold tracking-tight bg-gradient-to-r from-violet-400 via-indigo-300 to-emerald-400 bg-clip-text text-transparent">
                LaLiga Transfer Network Explorer (2025-2027)
            </h1>
        </div>
        <div class="flex gap-4 text-sm text-slate-400">
            <div>Ficha Técnica Interactiva</div>
            <div>•</div>
            <div>Fuente: Fichajes.com</div>
        </div>
    </header>

    <!-- Main Workspace -->
    <main class="flex-1 flex w-full overflow-hidden">
        
        <!-- Left Sidebar: Controls & Stats -->
        <section class="w-80 h-full flex flex-col border-r border-slate-800 bg-slate-950 p-4 gap-4 overflow-y-auto">
            
            <!-- Quick metrics card -->
            <div class="glass p-3 rounded-xl flex flex-col gap-2">
                <h3 class="text-xs font-semibold uppercase tracking-wider text-slate-400">Estadísticas de la Red</h3>
                <div class="grid grid-cols-2 gap-2 mt-1">
                    <div class="bg-slate-900/50 p-2 rounded-lg border border-slate-800">
                        <span class="text-2xl font-bold text-violet-400" id="nodes-count">56</span>
                        <p class="text-[10px] text-slate-500 uppercase">Nodos</p>
                    </div>
                    <div class="bg-slate-900/50 p-2 rounded-lg border border-slate-800">
                        <span class="text-2xl font-bold text-emerald-400" id="edges-count">1034</span>
                        <p class="text-[10px] text-slate-500 uppercase">Traspasos</p>
                    </div>
                </div>
            </div>

            <!-- Controls Panel -->
            <div class="glass p-4 rounded-xl flex flex-col gap-4">
                <h3 class="text-xs font-semibold uppercase tracking-wider text-slate-400">Controles del Grafo</h3>
                
                <!-- View Mode Selection -->
                <div class="flex flex-col gap-1.5">
                    <label class="text-xs text-slate-400">Modelo de Red</label>
                    <div class="grid grid-cols-2 gap-1 bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs">
                        <button onclick="setViewMode('clubs_only')" id="btn-view-clubs" class="py-1.5 px-2 rounded-md font-medium text-center bg-violet-600 text-white">
                            Solo Clubes
                        </button>
                        <button onclick="setViewMode('hetero')" id="btn-view-hetero" class="py-1.5 px-2 rounded-md font-medium text-center text-slate-400 hover:text-white">
                            Clubes + Jugadores
                        </button>
                    </div>
                </div>

                <!-- Season Selection -->
                <div class="flex flex-col gap-1.5">
                    <label class="text-xs text-slate-400">Filtrar por Temporada</label>
                    <select onchange="setSeason(this.value)" class="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-white focus:outline-none focus:border-violet-500">
                        <option value="all">Todas las Temporadas</option>
                        <option value="2026-2027">2026 / 2027 (Actual)</option>
                        <option value="2025-2026">2025 / 2026 (Pasada)</option>
                    </select>
                </div>

                <!-- Search box -->
                <div class="flex flex-col gap-1.5">
                    <label class="text-xs text-slate-400">Buscar Club o Jugador</label>
                    <div class="relative">
                        <input type="text" oninput="searchNode(this.value)" placeholder="Escribe para buscar..." 
                               class="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 pl-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-violet-500">
                    </div>
                </div>
            </div>

            <!-- Detail stats panel (interactive on node click) -->
            <div class="flex-1 glass p-4 rounded-xl flex flex-col gap-3 min-h-[300px] overflow-hidden" id="details-container">
                <div class="h-full flex flex-col items-center justify-center text-center text-slate-500 gap-2" id="no-selection-view">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 stroke-current" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p class="text-xs">Haz clic en cualquier nodo del grafo para ver su ficha técnica detallada y lista de traspasos.</p>
                </div>
                
                <!-- Content view (Hidden by default) -->
                <div class="hidden h-full flex flex-col gap-3 overflow-hidden text-xs" id="selection-view">
                    <div class="border-b border-slate-800 pb-2">
                        <h2 class="text-sm font-bold text-violet-400" id="detail-name">Real Madrid</h2>
                        <span class="inline-block mt-1 bg-slate-800 px-2 py-0.5 rounded text-[10px] uppercase text-slate-300" id="detail-type">Primera División</span>
                    </div>
                    
                    <div class="flex flex-col gap-2 overflow-y-auto flex-1 pr-1" id="detail-lists">
                        <!-- Arrivals list -->
                        <div>
                            <h4 class="font-bold text-emerald-400 border-b border-slate-800/50 pb-1 mb-1.5 flex justify-between">
                                <span>Llegadas / Altas</span>
                                <span class="bg-emerald-950/50 text-emerald-400 px-1.5 py-0.2 rounded text-[10px]" id="count-arrivals">0</span>
                            </h4>
                            <ul class="flex flex-col gap-1.5" id="arrivals-list"></ul>
                        </div>
                        
                        <!-- Departures list -->
                        <div class="mt-2">
                            <h4 class="font-bold text-red-400 border-b border-slate-800/50 pb-1 mb-1.5 flex justify-between">
                                <span>Salidas / Bajas</span>
                                <span class="bg-red-950/50 text-red-400 px-1.5 py-0.2 rounded text-[10px]" id="count-departures">0</span>
                            </h4>
                            <ul class="flex flex-col gap-1.5" id="departures-list"></ul>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Right Graph Canvas -->
        <section class="flex-1 h-full relative bg-slate-900">
            <!-- Loading Indicator -->
            <div id="loading-overlay" class="absolute inset-0 bg-slate-950/80 flex items-center justify-center z-20 transition-all duration-300">
                <div class="flex flex-col items-center gap-3">
                    <div class="w-10 h-10 border-4 border-violet-500 border-t-transparent rounded-full animate-spin"></div>
                    <span class="text-xs text-slate-400 font-medium">Renderizando red de traspasos...</span>
                </div>
            </div>

            <!-- Network Canvas -->
            <div id="network-canvas" class="w-full h-full"></div>

            <!-- Visual Legend (Floating) -->
            <div class="absolute bottom-4 left-4 glass p-3 rounded-lg flex flex-col gap-1.5 text-[10px] z-10">
                <h4 class="font-semibold uppercase tracking-wider text-slate-400 mb-1">Leyenda del Grafo</h4>
                <div class="flex items-center gap-2">
                    <div class="w-3.5 h-3.5 rounded-full border-2 border-sky-600 bg-sky-400"></div>
                    <span>Primera División</span>
                </div>
                <div class="flex items-center gap-2">
                    <div class="w-3.5 h-3.5 rounded-full border-2 border-green-600 bg-green-400"></div>
                    <span>Segunda División</span>
                </div>
                <div class="flex items-center gap-2">
                    <div class="w-3.5 h-3.5 rounded-full border-2 border-red-600 bg-red-400"></div>
                    <span>Ligas Internacionales</span>
                </div>
                <div id="legend-player-row" class="hidden flex items-center gap-2">
                    <div class="w-3.5 h-3.5 rounded-full border-2 border-amber-600 bg-amber-400"></div>
                    <span>Jugador (Nodo Puente)</span>
                </div>
            </div>

            <!-- Canvas controls -->
            <div class="absolute bottom-4 right-4 flex gap-2 z-10">
                <button onclick="fitNetwork()" class="bg-slate-800 hover:bg-slate-700 text-white rounded-lg px-3 py-2 text-xs font-semibold transition-all border border-slate-700">
                    Ajustar Vista
                </button>
                <button onclick="togglePhysics()" id="btn-physics" class="bg-violet-600 hover:bg-violet-500 text-white rounded-lg px-3 py-2 text-xs font-semibold transition-all border border-violet-500">
                    Fijar Grafo
                </button>
            </div>
        </section>
        
    </main>

    <!-- Embedded Data & Scripts -->
    <script>
        // Data generated by Python Scraper
        const clubNodes = {json.dumps(club_nodes_js, ensure_ascii=False)};
        const clubEdges = {json.dumps(club_edges_js, ensure_ascii=False)};
        const heteroNodes = {json.dumps(hetero_nodes_js, ensure_ascii=False)};
        const heteroEdges = {json.dumps(hetero_edges_js, ensure_ascii=False)};
        const clubStats = {json.dumps(club_stats, ensure_ascii=False)};

        let network = null;
        let viewMode = 'clubs_only'; // 'clubs_only' or 'hetero'
        let selectedSeason = 'all';
        let searchQuery = '';
        let physicsEnabled = true;

        // vis network references
        let nodesDataset = null;
        let edgesDataset = null;

        function initNetwork() {{
            document.getElementById('loading-overlay').classList.remove('opacity-0', 'pointer-events-none');
            
            const container = document.getElementById('network-canvas');
            
            // Nodes & Edges selection based on mode
            let targetNodes = [];
            let targetEdges = [];
            
            if (viewMode === 'clubs_only') {{
                document.getElementById('legend-player-row').classList.add('hidden');
                
                // Filter edges by season
                targetEdges = clubEdges.filter(e => selectedSeason === 'all' || e.season === selectedSeason);
                
                // Only keep nodes that have active edges in this filter
                const activeNodeIds = new Set();
                targetEdges.forEach(e => {{
                    activeNodeIds.add(e.from);
                    activeNodeIds.add(e.to);
                }});
                
                targetNodes = clubNodes.filter(n => activeNodeIds.has(n.id));
                
            }} else {{
                document.getElementById('legend-player-row').classList.remove('hidden');
                
                // Heterogeneous filters: edges can go to/from player nodes.
                // Player nodes have 'season' attribute. Edges have 'season' too.
                const activePlayerIds = new Set();
                
                // Filter player nodes first
                hetero_player_nodes = heteroNodes.filter(n => {{
                    if (n.group !== 'Jugador') return true; // keep clubs
                    return selectedSeason === 'all' || n.season === selectedSeason;
                }});
                
                const keptPlayerIds = new Set(hetero_player_nodes.filter(n => n.group === 'Jugador').map(n => n.id));
                
                // Filter edges that connect to kept player nodes
                targetEdges = heteroEdges.filter(e => {{
                    return keptPlayerIds.has(e.from) || keptPlayerIds.has(e.to);
                }});
                
                // Find all active club and player node IDs
                const activeNodeIds = new Set();
                targetEdges.forEach(e => {{
                    activeNodeIds.add(e.from);
                    activeNodeIds.add(e.to);
                }});
                
                targetNodes = heteroNodes.filter(n => activeNodeIds.has(n.id));
            }}

            // Apply search query highlighting if any
            if (searchQuery.trim() !== '') {{
                const query = searchQuery.toLowerCase().trim();
                targetNodes = targetNodes.map(n => {{
                    const isMatched = n.label.toLowerCase().includes(query);
                    return {{
                        ...n,
                        borderWidth: isMatched ? 4 : 1,
                        color: isMatched ? {{ background: '#a78bfa', border: '#8b5cf6' }} : undefined
                    }};
                }});
            }}

            // Update stats displays
            document.getElementById('nodes-count').innerText = targetNodes.filter(n => n.group !== 'Jugador').length;
            document.getElementById('edges-count').innerText = viewMode === 'clubs_only' ? targetEdges.length : targetEdges.length / 2;

            nodesDataset = new vis.DataSet(targetNodes);
            edgesDataset = new vis.DataSet(targetEdges);

            const data = {{
                nodes: nodesDataset,
                edges: edgesDataset
            }};

            // Styling options
            const options = {{
                nodes: {{
                    shape: 'dot',
                    font: {{
                        color: '#f1f5f9',
                        size: 13,
                        face: 'Outfit'
                    }},
                    borderWidth: 2,
                    shadow: true
                }},
                edges: {{
                    width: 1.5,
                    color: {{
                        color: 'rgba(148, 163, 184, 0.25)',
                        highlight: '#8b5cf6',
                        hover: '#a78bfa'
                    }},
                    font: {{
                        color: '#cbd5e1',
                        size: 9,
                        face: 'Outfit',
                        strokeWidth: 0,
                        background: 'rgba(15, 23, 42, 0.8)'
                    }},
                    smooth: {{
                        type: 'continuous',
                        roundness: 0.5
                    }}
                }},
                groups: {{
                    'Primera División': {{
                        color: {{ background: '#0ea5e9', border: '#0284c7' }},
                        shape: 'dot'
                    }},
                    'Segunda División': {{
                        color: {{ background: '#10b981', border: '#059669' }},
                        shape: 'dot'
                    }},
                    'Liga Internacional': {{
                        color: {{ background: '#f43f5e', border: '#e11d48' }},
                        shape: 'dot'
                    }},
                    'Jugador': {{
                        color: {{ background: '#f59e0b', border: '#d97706' }},
                        shape: 'dot',
                        size: 6
                    }}
                }},
                physics: {{
                    solver: 'forceAtlas2Based',
                    forceAtlas2Based: {{
                        gravitationalConstant: -26,
                        centralGravity: 0.005,
                        springLength: 90,
                        springConstant: 0.18,
                        damping: 0.4
                    }},
                    stabilization: {{
                        enabled: true,
                        iterations: 150,
                        updateInterval: 25
                    }}
                }},
                interaction: {{
                    hover: true,
                    tooltipDelay: 200
                }}
            }};

            if (network) {{
                network.destroy();
            }}

            network = new vis.Network(container, data, options);

            // Handle stabilization completion
            network.on("stabilizationIterationsDone", function () {{
                document.getElementById('loading-overlay').classList.add('opacity-0', 'pointer-events-none');
            }});
            
            // Backup fallback loading overlay remover
            setTimeout(() => {{
                document.getElementById('loading-overlay').classList.add('opacity-0', 'pointer-events-none');
            }}, 2000);

            // Click listener for details panel
            network.on("click", function (params) {{
                if (params.nodes.length > 0) {{
                    const nodeId = params.nodes[0];
                    showNodeDetails(nodeId);
                }} else {{
                    clearNodeDetails();
                }}
            }});
        }}

        function setViewMode(mode) {{
            viewMode = mode;
            const btnClubs = document.getElementById('btn-view-clubs');
            const btnHetero = document.getElementById('btn-view-hetero');
            
            if (mode === 'clubs_only') {{
                btnClubs.className = 'py-1.5 px-2 rounded-md font-medium text-center bg-violet-600 text-white';
                btnHetero.className = 'py-1.5 px-2 rounded-md font-medium text-center text-slate-400 hover:text-white';
            }} else {{
                btnClubs.className = 'py-1.5 px-2 rounded-md font-medium text-center text-slate-400 hover:text-white';
                btnHetero.className = 'py-1.5 px-2 rounded-md font-medium text-center bg-violet-600 text-white';
            }}
            initNetwork();
        }}

        function setSeason(season) {{
            selectedSeason = season;
            initNetwork();
        }}

        function searchNode(query) {{
            searchQuery = query;
            initNetwork();
        }}

        function fitNetwork() {{
            if (network) network.fit({{ animation: true }});
        }}

        function togglePhysics() {{
            physicsEnabled = !physicsEnabled;
            const btn = document.getElementById('btn-physics');
            
            if (physicsEnabled) {{
                btn.innerText = "Fijar Grafo";
                btn.className = "bg-violet-600 hover:bg-violet-500 text-white rounded-lg px-3 py-2 text-xs font-semibold transition-all border border-violet-500";
                network.setOptions({{ physics: {{ enabled: true }} }});
            }} else {{
                btn.innerText = "Rebotar Grafo";
                btn.className = "bg-slate-800 hover:bg-slate-700 text-white rounded-lg px-3 py-2 text-xs font-semibold transition-all border border-slate-700";
                network.setOptions({{ physics: {{ enabled: false }} }});
            }}
        }}

        function showNodeDetails(nodeId) {{
            const noSel = document.getElementById('no-selection-view');
            const sel = document.getElementById('selection-view');
            
            noSel.classList.add('hidden');
            sel.classList.remove('hidden');

            const isPlayerNode = nodeId.startsWith('pnode_');
            
            if (isPlayerNode) {{
                // Parse player info
                const idx = parseInt(nodeId.split('_')[1]);
                const transfer = heteroNodes.find(n => n.id === nodeId);
                const player_name = transfer ? transfer.label : "Jugador";
                const age = transfer ? transfer.age : "N/D";
                const cost = transfer ? transfer.cost_raw : "Desconocido";
                const season = transfer ? transfer.season : "N/D";
                
                document.getElementById('detail-name').innerText = player_name;
                document.getElementById('detail-type').innerText = "Jugador";
                
                document.getElementById('arrivals-list').innerHTML = `
                    <li class="bg-slate-900/60 p-2 rounded border border-slate-800 flex justify-between items-center">
                        <div>
                            <span class="font-semibold text-slate-200">Edad:</span> ${{age}} años<br>
                            <span class="font-semibold text-slate-200">Temporada:</span> ${{season}}<br>
                            <span class="font-semibold text-slate-200">Coste de Fichaje:</span> ${{cost}}
                        </div>
                    </li>
                `;
                document.getElementById('count-arrivals').innerText = "Info";
                
                document.getElementById('departures-list').innerHTML = "";
                document.getElementById('count-departures').innerText = "0";
                return;
            }}

            // Otherwise, it is a Club Node
            const groupInfo = clubNodes.find(n => n.id === nodeId);
            const groupName = groupInfo ? groupInfo.group : "Club";
            
            document.getElementById('detail-name').innerText = nodeId;
            document.getElementById('detail-type').innerText = groupName;
            
            // Get stats from club_stats object
            const stats = clubStats[nodeId];
            if (!stats) {{
                document.getElementById('arrivals-list').innerHTML = "<li class='text-slate-500 italic text-[11px]'>Sin altas registradas</li>";
                document.getElementById('departures-list').innerHTML = "<li class='text-slate-500 italic text-[11px]'>Sin bajas registradas</li>";
                document.getElementById('count-arrivals').innerText = "0";
                document.getElementById('count-departures').innerText = "0";
                return;
            }}

            // Filter arrivals and departures by selectedSeason
            let arrivals = [];
            let departures = [];
            
            if (selectedSeason === 'all') {{
                arrivals = [...stats["2025-2026"].arrivals, ...stats["2026-2027"].arrivals];
                departures = [...stats["2025-2026"].departures, ...stats["2026-2027"].departures];
            }} else {{
                arrivals = stats[selectedSeason].arrivals;
                departures = stats[selectedSeason].departures;
            }}

            // Render arrivals
            document.getElementById('count-arrivals').innerText = arrivals.length;
            if (arrivals.length === 0) {{
                document.getElementById('arrivals-list').innerHTML = "<li class='text-slate-500 italic text-[11px]'>Sin altas en este filtro</li>";
            }} else {{
                document.getElementById('arrivals-list').innerHTML = arrivals.map(a => `
                    <li class="bg-slate-900/60 p-2 rounded border border-slate-800 flex justify-between items-center gap-1">
                        <div>
                            <span class="font-bold text-slate-100">${{a.player}}</span>
                            <p class="text-[10px] text-slate-400">Origen: ${{a.from}} (${{a.age}} años)</p>
                        </div>
                        <span class="text-[10px] text-emerald-400 font-semibold bg-emerald-950/40 border border-emerald-800 px-1 rounded">${{a.cost}}</span>
                    </li>
                `).join('');
            }}

            // Render departures
            document.getElementById('count-departures').innerText = departures.length;
            if (departures.length === 0) {{
                document.getElementById('departures-list').innerHTML = "<li class='text-slate-500 italic text-[11px]'>Sin bajas en este filtro</li>";
            }} else {{
                document.getElementById('departures-list').innerHTML = departures.map(d => `
                    <li class="bg-slate-900/60 p-2 rounded border border-slate-800 flex justify-between items-center gap-1">
                        <div>
                            <span class="font-bold text-slate-100">${{d.player}}</span>
                            <p class="text-[10px] text-slate-400">Destino: ${{d.to}} (${{d.age}} años)</p>
                        </div>
                        <span class="text-[10px] text-red-400 font-semibold bg-red-950/40 border border-red-800 px-1 rounded">${{d.cost}}</span>
                    </li>
                `).join('');
            }}
        }}

        function clearNodeDetails() {{
            document.getElementById('no-selection-view').classList.remove('hidden');
            document.getElementById('selection-view').classList.add('hidden');
        }}

        // Initialize on load
        window.addEventListener('DOMContentLoaded', () => {{
            initNetwork();
        }});
    </script>
</body>
</html>
"""
    
    output_file = "transfer_market_graph.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Interactive Dashboard created successfully at {output_file}!")

if __name__ == "__main__":
    main()
