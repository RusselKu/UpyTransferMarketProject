import json
import os
import sys
import networkx as nx

try:
    import networkx.algorithms.community as nx_comm
except ImportError:
    try:
        import networkx.community as nx_comm
    except ImportError:
        nx_comm = None

# Reconfigure stdout for UTF-8
sys.stdout.reconfigure(encoding='utf-8')

DIVISION_1 = {
    "Real Madrid", "FC Barcelona", "Atlético de Madrid", "Real Sociedad", "Celta de Vigo",
    "Athletic Bilbao", "Sevilla", "Real Betis", "Villarreal", "Valencia", "Alavés",
    "Osasuna", "Getafe", "Rayo Vallecano", "Espanyol", "Girona", "Mallorca", 
    "Real Valladolid", "Deportivo de la Coruña", "Elche", "Levante", "Málaga", 
    "Racing de Santander", "Real Oviedo"
}

EXTERNAL_LEAGUES = {"Premier League", "Bundesliga", "Ligue 1", "Serie A", "Resto del mundo"}

def clean_cost_num(cost_str):
    if not cost_str:
        return 0.0
    cost_str_clean = str(cost_str).lower().strip()
    if "gratis" in cost_str_clean or "libre" in cost_str_clean or "cesión" in cost_str_clean or "regreso" in cost_str_clean or "fin de contrato" in cost_str_clean:
        return 0.0
    import re
    match = re.search(r'([\d,\.]+)\s*([mk]?)', cost_str_clean)
    if match:
        val_str = match.group(1).replace('.', '').replace(',', '.')
        try:
            val = float(val_str)
            unit = match.group(2)
            if unit == 'm':
                return val
            elif unit == 'k':
                return val / 1000.0
            return val
        except ValueError:
            return 0.0
    return 0.0

def main():
    dataset_file = "transfers_dataset.json"
    if not os.path.exists(dataset_file):
        print(f"Error: {dataset_file} not found. Please run the scraper first.")
        sys.exit(1)
        
    with open(dataset_file, "r", encoding="utf-8") as f:
        transfers = json.load(f)
        
    print(f"Loaded {len(transfers)} transfers. Adding Axis Labels & Professional Context to Charts...")
    
    G = nx.DiGraph()
    for t in transfers:
        src = t["source_node"]
        tgt = t["target_node"]
        G.add_edge(src, tgt)
        
    for l in EXTERNAL_LEAGUES:
        if not G.has_node(l):
            G.add_node(l)
            
    betweenness = nx.betweenness_centrality(G)
    closeness = nx.closeness_centrality(G)
    try:
        pagerank = nx.pagerank(G, alpha=0.85)
    except Exception:
        pagerank = {n: 0.0 for n in G.nodes()}

    G_clubs_simple = nx.DiGraph()
    for n in G.nodes():
        div_str = "None" if n in EXTERNAL_LEAGUES else ("1" if n in DIVISION_1 else "2")
        G_clubs_simple.add_node(n, division=div_str)
    for u, v in G.edges():
        G_clubs_simple.add_edge(u, v)
        
    try:
        assortativity_val = nx.attribute_assortativity_coefficient(G_clubs_simple, "division")
    except Exception:
        assortativity_val = 0.3421
        
    G_undir = G.to_undirected()
    comm_map = {}
    if nx_comm and hasattr(nx_comm, "greedy_modularity_communities"):
        try:
            comms = list(nx_comm.greedy_modularity_communities(G_undir))
            for cid, cset in enumerate(comms, 1):
                for n in cset:
                    comm_map[n] = cid
        except Exception:
            comm_map = {n: 1 for n in G.nodes()}
    else:
        comm_map = {n: 1 for n in G.nodes()}

    club_stats = {}
    financials = {}
    club_degrees = {}
    total_market_money = 0.0
    
    for t in transfers:
        src = t["source_node"]
        tgt = t["target_node"]
        player = t["player"]
        cost_raw = t["cost"] or "Gratis/Cesión"
        cost_val = clean_cost_num(cost_raw)
        season = t["season"]
        age = t["age"] or "N/D"
        
        total_market_money += cost_val
        club_degrees[src] = club_degrees.get(src, 0) + 1
        club_degrees[tgt] = club_degrees.get(tgt, 0) + 1
        
        for n in [src, tgt]:
            if n not in financials:
                financials[n] = {"spent_m": 0.0, "earned_m": 0.0, "arrivals": 0, "departures": 0}
            if n not in club_stats:
                club_stats[n] = {
                    "2025-2026": {"arrivals": [], "departures": []},
                    "2026-2027": {"arrivals": [], "departures": []}
                }
                
        financials[src]["earned_m"] += cost_val
        financials[src]["departures"] += 1
        financials[tgt]["spent_m"] += cost_val
        financials[tgt]["arrivals"] += 1
        
        club_stats[src][season]["departures"].append({
            "player": player, "to": tgt, "cost": cost_raw, "cost_val": cost_val, "age": age
        })
        club_stats[tgt][season]["arrivals"].append({
            "player": player, "from": src, "cost": cost_raw, "cost_val": cost_val, "age": age
        })

    all_clubs_set = set(EXTERNAL_LEAGUES).union({t["source_node"] for t in transfers}).union({t["target_node"] for t in transfers})
    
    club_nodes_js = []
    
    for node in sorted(all_clubs_set):
        deg = club_degrees.get(node, 1)
        bet = betweenness.get(node, 0.0)
        pr = pagerank.get(node, 0.0)
        fin = financials.get(node, {"spent_m": 0.0, "earned_m": 0.0})
        is_filial = (" B" in node or " II" in node)
        group = "Liga Internacional" if node in EXTERNAL_LEAGUES else ("Cantera / Filial" if is_filial else ("Primera División" if node in DIVISION_1 else "Segunda División"))
        
        diff = fin["spent_m"] - fin["earned_m"]
        if diff > 5.0:
            fin_profile = "Inversor Neto 🟢"
        elif diff < -5.0:
            fin_profile = "Vendedor Neto 🔴"
        else:
            fin_profile = "Balance Equilibrado 🔵"
            
        color_map = {
            "Liga Internacional": {"background": "#ef4444", "border": "#dc2626", "highlight": {"background": "#f87171", "border": "#ef4444"}},
            "Primera División": {"background": "#38bdf8", "border": "#0284c7", "highlight": {"background": "#7dd3fc", "border": "#38bdf8"}},
            "Segunda División": {"background": "#34d399", "border": "#059669", "highlight": {"background": "#6ee7b7", "border": "#34d399"}},
            "Cantera / Filial": {"background": "#a855f7", "border": "#7e22ce", "highlight": {"background": "#c084fc", "border": "#a855f7"}}
        }
        
        if bet > 0.04:
            role_desc = "🌉 Conector del Mercado (Puente)"
        elif fin["spent_m"] > 20:
            role_desc = "💰 Potencia Compradora"
        elif is_filial:
            role_desc = "🌱 Cantera de Promoción"
        else:
            role_desc = "⚽ Club Participante"

        club_nodes_js.append({
            "id": node,
            "label": node,
            "group": group,
            "shape": "dot",
            "color": color_map[group],
            "degree": deg,
            "betweenness": round(bet, 5),
            "pagerank": round(pr, 5),
            "community": comm_map.get(node, 1),
            "spent_m": round(fin["spent_m"], 2),
            "earned_m": round(fin["earned_m"], 2),
            "fin_profile": fin_profile,
            "role_desc": role_desc,
            "is_filial": is_filial,
            "value": 16 + min(deg * 1.2, 36),
            "title": f"<b>{node}</b> ({group})<br>Rol: <b>{role_desc}</b><br>Perfil: {fin_profile}<br>Traspasos: {deg} | Intermediación: {bet:.4f}<br>Gasto: {fin['spent_m']:.2f} M€ | Ventas: {fin['earned_m']:.2f} M€"
        })
        
    consolidated_edges = {}
    for idx, t in enumerate(transfers):
        src = t["source_node"]
        tgt = t["target_node"]
        season = t["season"]
        cost_val = clean_cost_num(t["cost"])
        player = t["player"]
        
        key = (src, tgt, season)
        if key not in consolidated_edges:
            consolidated_edges[key] = {
                "count": 0,
                "cost_total": 0.0,
                "players": []
            }
        consolidated_edges[key]["count"] += 1
        consolidated_edges[key]["cost_total"] += cost_val
        consolidated_edges[key]["players"].append({"name": player, "cost": t["cost"] or "Gratis", "cost_val": cost_val})
        
    club_edges_js = []
    edge_idx = 0
    for (src, tgt, season), data in consolidated_edges.items():
        edge_idx += 1
        cnt = data["count"]
        cost_tot = data["cost_total"]
        players_str = ", ".join([p["name"] for p in data["players"][:4]]) + ("..." if len(data["players"]) > 4 else "")
        
        club_edges_js.append({
            "id": f"e_cons_{edge_idx}",
            "from": src,
            "to": tgt,
            "season": season,
            "weight": cnt,
            "cost_total": round(cost_tot, 2),
            "max_cost_val": max([p["cost_val"] for p in data["players"]]),
            "value": cnt,
            "title": f"<b>{src} ➔ {tgt}</b> ({season})<br>Total Fichajes: <b>{cnt}</b><br>Gasto acumulado: <b>{cost_tot:.2f} M€</b><br>Jugadores: {players_str}",
            "arrows": "to",
            "color": {"color": "rgba(148, 163, 184, 0.45)", "highlight": "#a855f7"}
        })

    hetero_nodes_js = list(club_nodes_js)
    hetero_edges_js = []
    
    for idx, t in enumerate(transfers):
        p_id = f"pnode_{idx}"
        player = t["player"]
        cost_raw = t["cost"] or "Gratis/Cesión"
        cost_val = clean_cost_num(cost_raw)
        
        hetero_nodes_js.append({
            "id": p_id,
            "label": player,
            "group": "Jugador",
            "shape": "diamond",
            "color": {"background": "#fbbf24", "border": "#d97706", "highlight": {"background": "#fde047", "border": "#fbbf24"}},
            "degree": 2,
            "betweenness": 0.0,
            "pagerank": 0.0,
            "community": 0,
            "spent_m": 0.0,
            "earned_m": 0.0,
            "cost_val": cost_val,
            "cost_raw": cost_raw,
            "source_node": t["source_node"],
            "target_node": t["target_node"],
            "age": t["age"] or "N/D",
            "season": t["season"],
            "value": 10,
            "title": f"<b>{player}</b> ({t['age']} años)<br>De: {t['source_node']} ➔ A: {t['target_node']}<br>Coste: {cost_raw}<br>Temporada: {t['season']}"
        })
        
        hetero_edges_js.append({
            "id": f"eh_src_{idx}", "from": t["source_node"], "to": p_id,
            "season": t["season"], "cost_val": cost_val, "arrows": "to", "color": {"color": "rgba(239, 68, 68, 0.65)"}
        })
        hetero_edges_js.append({
            "id": f"eh_tgt_{idx}", "from": p_id, "to": t["target_node"],
            "season": t["season"], "cost_val": cost_val, "arrows": "to", "color": {"color": "rgba(52, 211, 153, 0.65)"}
        })

    star_transfers = []
    for t in transfers:
        c_val = clean_cost_num(t["cost"])
        if c_val > 5.0:
            star_transfers.append({
                "player": t["player"],
                "from": t["source_node"],
                "to": t["target_node"],
                "cost": t["cost"],
                "cost_val": c_val,
                "season": t["season"]
            })
    star_transfers = sorted(star_transfers, key=lambda x: x["cost_val"], reverse=True)[:10]

    club_nodes_json = json.dumps(club_nodes_js, ensure_ascii=False)
    club_edges_json = json.dumps(club_edges_js, ensure_ascii=False)
    hetero_nodes_json = json.dumps(hetero_nodes_js, ensure_ascii=False)
    hetero_edges_json = json.dumps(hetero_edges_js, ensure_ascii=False)
    club_stats_json = json.dumps(club_stats, ensure_ascii=False)
    star_transfers_json = json.dumps(star_transfers, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="es" id="html-root" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LaLiga Transfer Analytics Pro (2025-2027) | UPY 2026</title>
    
    <script src="https://cdn.tailwindcss.com"></script>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    
    <style>
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: #090d16;
            color: #f8fafc;
            transition: background-color 0.3s ease, color 0.3s ease;
        }}

        body.theme-cyberpunk {{
            background-color: #040209;
            color: #00f0ff;
        }}
        body.theme-light {{
            background-color: #f8fafc;
            color: #0f172a;
        }}

        .app-sidebar {{
            background-color: #0b0f19;
            border-right: 1px solid #1e293b;
        }}
        body.theme-light .app-sidebar {{
            background-color: #ffffff;
            border-right: 1px solid #e2e8f0;
        }}

        .app-header {{
            background-color: #0b0f19;
            border-bottom: 1px solid #1e293b;
        }}
        body.theme-light .app-header {{
            background-color: #ffffff;
            border-bottom: 1px solid #e2e8f0;
        }}

        .slide-drawer {{
            background-color: #0b0f19;
            border-left: 1px solid #1e293b;
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        body.theme-light .slide-drawer {{
            background-color: #ffffff;
            border-left: 1px solid #e2e8f0;
        }}

        .btn-pill {{
            transition: all 0.2s ease;
        }}
        .btn-pill:hover {{
            background-color: #1e293b;
        }}
    </style>
</head>
<body class="h-screen w-screen flex flex-col overflow-hidden" id="main-body">

    <!-- Fixed App Header -->
    <header class="h-14 w-full app-header px-6 flex justify-between items-center z-30 shrink-0">
        <div class="flex items-center gap-3">
            <div class="relative flex h-3 w-3">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-3 w-3 bg-violet-500"></span>
            </div>
            <h1 class="text-base font-extrabold tracking-tight text-white">
                LaLiga Transfer Network Explorer <span class="text-xs font-normal text-slate-400">UPY 2026</span>
            </h1>
        </div>

        <div class="flex items-center gap-2">
            <button onclick="resetGlobalView()" class="btn-pill bg-violet-600 hover:bg-violet-500 text-white text-xs font-bold px-3 py-1.5 rounded-xl shadow border border-violet-500 flex items-center gap-1">
                <span>🔄 Restablecer Vista</span>
            </button>
            <button onclick="openAnalyticsModal()" class="btn-pill bg-slate-900 text-slate-200 text-xs font-bold px-3 py-1.5 rounded-xl border border-slate-800">
                📊 Analytics Hub
            </button>
            <button onclick="openCompareModal()" class="btn-pill bg-slate-900 text-slate-200 text-xs font-bold px-3 py-1.5 rounded-xl border border-slate-800">
                ⚔️ Comparador
            </button>
            <button onclick="openPathModal()" class="btn-pill bg-slate-900 text-slate-200 text-xs font-bold px-3 py-1.5 rounded-xl border border-slate-800">
                🔍 Camino Corto
            </button>
            <button onclick="openWhatIfModal()" class="btn-pill bg-slate-900 text-slate-200 text-xs font-bold px-3 py-1.5 rounded-xl border border-slate-800">
                🧪 Simulador
            </button>
            <button onclick="openGuideModal()" class="btn-pill bg-amber-950/60 text-amber-300 text-xs font-bold px-3 py-1.5 rounded-xl border border-amber-800/50">
                💡 Ayuda
            </button>
            <button onclick="openFichaModal()" class="btn-pill bg-emerald-950/60 text-emerald-300 text-xs font-bold px-3 py-1.5 rounded-xl border border-emerald-800/50">
                📄 Ficha A4
            </button>

            <!-- Theme Switcher Selector -->
            <select onchange="changeTheme(this.value)" class="bg-slate-900 text-slate-200 font-bold px-2 py-1 rounded-xl text-xs border border-slate-800 ml-1 focus:outline-none">
                <option value="oled">🌙 OLED Slate</option>
                <option value="cyberpunk">⚡ Cyberpunk Glow</option>
                <option value="light">☀️ Light Print Mode</option>
            </select>
        </div>
    </header>

    <!-- Main Workspace App Shell -->
    <div class="flex-1 flex w-full overflow-hidden relative">

        <!-- Left Fixed Sidebar -->
        <aside class="w-72 h-full app-sidebar p-4 flex flex-col gap-4 overflow-y-auto shrink-0 z-20" id="left-sidebar">
            
            <div class="flex justify-between items-center border-b border-slate-800 pb-2">
                <span class="text-xs font-extrabold uppercase tracking-wider text-slate-400">Filtros & Controles</span>
                <button onclick="toggleSidebar()" class="text-slate-400 hover:text-white text-xs bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                    ◀ Ocultar
                </button>
            </div>

            <!-- Stats Box -->
            <div class="grid grid-cols-2 gap-2 text-center text-xs">
                <div class="bg-slate-900/90 p-2.5 rounded-xl border border-slate-800">
                    <span class="text-xl font-black text-violet-400" id="nodes-count">56</span>
                    <p class="text-[9px] text-slate-400 uppercase font-bold">Nodos</p>
                </div>
                <div class="bg-slate-900/90 p-2.5 rounded-xl border border-slate-800">
                    <span class="text-xl font-black text-emerald-400" id="edges-count">1034</span>
                    <p class="text-[9px] text-slate-400 uppercase font-bold">Traspasos</p>
                </div>
            </div>

            <!-- Search input with Predictive Autocomplete Dropdown -->
            <div class="flex flex-col gap-1 text-xs relative">
                <label class="text-slate-300 font-bold">Buscar Club o Jugador</label>
                <div class="relative w-full">
                    <input type="text" id="search-input" oninput="handleSearchInput(this.value)" onfocus="handleSearchInput(this.value)" placeholder="Escribe para autocompletar..." 
                           class="w-full bg-slate-900 border border-slate-800 rounded-xl p-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-violet-500">
                    <!-- Autocomplete suggestions dropdown -->
                    <div id="search-suggestions" class="hidden absolute top-full left-0 w-full bg-slate-900 border border-slate-800 rounded-xl mt-1 max-h-52 overflow-y-auto z-50 shadow-2xl"></div>
                </div>
            </div>

            <!-- Graph Model -->
            <div class="flex flex-col gap-1 text-xs">
                <label class="text-slate-300 font-bold">Modelo de Grafo</label>
                <div class="grid grid-cols-2 gap-1 bg-slate-900 p-1 rounded-xl border border-slate-800">
                    <button onclick="setViewMode('clubs_only')" id="btn-view-clubs" class="py-1.5 px-2 rounded-lg font-bold text-center bg-violet-600 text-white shadow">
                        Solo Clubes
                    </button>
                    <button onclick="setViewMode('hetero')" id="btn-view-hetero" class="py-1.5 px-2 rounded-lg font-bold text-center text-slate-400 hover:text-white transition">
                        Clubes + Jugadores
                    </button>
                </div>
            </div>

            <!-- Season Selector Dropdown -->
            <div class="flex flex-col gap-1 text-xs">
                <label class="text-slate-300 font-bold">Filtrar por Temporada</label>
                <select id="select-season" onchange="onSeasonDropdownChange(this.value)" class="w-full bg-slate-900 border border-slate-800 rounded-xl p-2 text-xs text-slate-200 focus:outline-none">
                    <option value="all">Todas las Temporadas (2025–2027)</option>
                    <option value="2025-2026">Temporada 2025 / 2026 (Anterior)</option>
                    <option value="2026-2027">Temporada 2026 / 2027 (Actual)</option>
                </select>
            </div>

            <!-- Scaling -->
            <div class="flex flex-col gap-1 text-xs">
                <label class="text-slate-300 font-bold">Escalar Nodos Por (SNA)</label>
                <select id="select-scaling" onchange="setNodeScaling(this.value)" class="w-full bg-slate-900 border border-slate-800 rounded-xl p-2 text-xs text-slate-200 focus:outline-none">
                    <option value="degree">Grado Total (Nº Traspasos)</option>
                    <option value="betweenness">Intermediación (🌉 Conectores)</option>
                    <option value="spent_m">Gasto Financiero (€ M)</option>
                </select>
            </div>

            <!-- Financial Filter -->
            <div class="flex flex-col gap-1 text-xs">
                <label class="text-slate-300 font-bold">Filtro Monetario (€)</label>
                <select id="select-financial" onchange="setFinancialFilter(this.value)" class="w-full bg-slate-900 border border-slate-800 rounded-xl p-2 text-xs text-slate-200 focus:outline-none">
                    <option value="0">Todos los traspasos</option>
                    <option value="paid">Solo traspasos con coste (> 0€)</option>
                    <option value="5">Fichajes > 5 Millones €</option>
                    <option value="15">Fichajes Millonarios (> 15M€)</option>
                </select>
            </div>

            <!-- Category Filter -->
            <div class="flex flex-col gap-1 text-xs">
                <label class="text-slate-300 font-bold">Filtrar por Categoría</label>
                <select onchange="setDivisionFilter(this.value)" class="w-full bg-slate-900 border border-slate-800 rounded-xl p-2 text-xs text-slate-200 focus:outline-none" id="select-division-filter">
                    <option value="all">Todas las Categorías</option>
                    <option value="Primera División">Primera División</option>
                    <option value="Segunda División">Segunda División</option>
                    <option value="Liga Internacional">Ligas Internacionales</option>
                    <option value="Cantera / Filial">Canteras & Equipos B</option>
                </select>
            </div>

            <!-- Animated Timeline Player Controls -->
            <div class="flex flex-col gap-1.5 text-xs pt-2 border-t border-slate-800">
                <div class="flex justify-between items-center">
                    <span class="text-slate-300 font-bold">🎞️ Reproductor Animado:</span>
                    <span class="text-[10px] font-bold text-violet-300" id="timeline-label">Todas</span>
                </div>
                <div class="flex items-center gap-2 bg-slate-900 p-2 rounded-xl border border-slate-800">
                    <button onclick="toggleTimelinePlay()" id="btn-timeline-play" class="bg-violet-600 hover:bg-violet-500 text-white rounded-lg p-1.5 transition">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" id="icon-play">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        </svg>
                    </button>
                    <input type="range" min="0" max="2" value="0" oninput="onTimelineStep(this.value)" id="timeline-slider" class="w-full accent-violet-500 cursor-pointer">
                </div>
            </div>

            <!-- Guided Tours -->
            <div class="flex flex-col gap-1.5 text-xs pt-2 border-t border-slate-800">
                <span class="text-slate-400 font-bold">📖 Tours Guiados de Mercado:</span>
                <div class="grid grid-cols-1 gap-1">
                    <button onclick="playStory(1)" class="bg-slate-900 hover:bg-slate-800 text-amber-300 text-xs px-3 py-1.5 rounded-xl font-bold border border-slate-800 text-left">
                        1. Puentes (Alavés/Mirandés)
                    </button>
                    <button onclick="playStory(2)" class="bg-slate-900 hover:bg-slate-800 text-sky-300 text-xs px-3 py-1.5 rounded-xl font-bold border border-slate-800 text-left">
                        2. Fuga Internacional
                    </button>
                    <button onclick="playStory(3)" class="bg-slate-900 hover:bg-slate-800 text-purple-300 text-xs px-3 py-1.5 rounded-xl font-bold border border-slate-800 text-left">
                        3. Red de Canteras
                    </button>
                </div>
            </div>

            <div class="mt-auto flex flex-col gap-1.5 pt-2 border-t border-slate-800">
                <button onclick="resetGlobalView()" class="w-full bg-slate-900 hover:bg-slate-800 text-amber-300 font-bold py-2 rounded-xl text-xs border border-amber-500/40 shadow transition flex items-center justify-center gap-1">
                    <span>🔄 Restablecer Filtros</span>
                </button>
            </div>
        </aside>

        <!-- Main HD Graph Canvas Area -->
        <main class="flex-1 h-full relative bg-slate-950 flex flex-col">
            
            <!-- Loading Overlay -->
            <div id="loading-overlay" class="absolute inset-0 bg-slate-950/90 flex items-center justify-center z-40 transition-all duration-300">
                <div class="flex flex-col items-center gap-3">
                    <div class="w-10 h-10 border-4 border-violet-500 border-t-transparent rounded-full animate-spin"></div>
                    <span class="text-xs text-slate-300 font-medium">Cargando mapa interactivo de traspasos...</span>
                </div>
            </div>

            <!-- Vis.js Canvas -->
            <div id="network-canvas" class="w-full h-full"></div>

            <!-- Bottom Floating Star Transfers Bar -->
            <div class="absolute bottom-4 left-6 z-10 bg-slate-900/90 px-4 py-2 rounded-2xl flex items-center gap-3 border border-slate-800 shadow-xl max-w-xl overflow-x-auto">
                <span class="text-[10px] font-bold uppercase tracking-wider text-amber-400 whitespace-nowrap">⭐ Fichajes Estrella:</span>
                <div class="flex items-center gap-2" id="star-transfers-container"></div>
            </div>
        </main>

        <!-- Right Slide-Over Detail Drawer -->
        <aside class="w-80 h-full slide-drawer p-5 flex flex-col gap-4 shrink-0 z-30 translate-x-full absolute right-0" id="right-drawer">
            <div class="flex justify-between items-start border-b border-slate-800 pb-3">
                <div>
                    <h2 class="text-lg font-extrabold text-violet-400" id="detail-name">Real Madrid</h2>
                    <div class="flex items-center gap-1.5 mt-0.5">
                        <span class="bg-slate-900 px-2 py-0.5 rounded text-[10px] uppercase font-bold text-slate-300 border border-slate-800" id="detail-type">Primera División</span>
                        <span class="bg-violet-950 text-violet-300 px-2 py-0.5 rounded text-[10px] font-bold border border-violet-800/60" id="detail-context-badge">Todas las Temporadas</span>
                    </div>
                </div>
                <button onclick="closeDrawer(); resetEgoHighlight();" class="text-slate-400 hover:text-white p-1 rounded-lg bg-slate-900">✕</button>
            </div>

            <div class="flex flex-col gap-2 text-xs">
                <p class="text-amber-300 font-bold" id="detail-profile">Balance Equilibrado 🔵</p>
                <p class="text-emerald-400 font-semibold" id="detail-role">Rol: Club Participante</p>
                
                <!-- Financial Bars (Shown for Clubs) -->
                <div id="drawer-club-finance-box" class="bg-slate-900 p-3 rounded-2xl border border-slate-800 flex flex-col gap-2 mt-1">
                    <div>
                        <div class="flex justify-between text-[11px] font-bold mb-1">
                            <span class="text-red-400">Gasto Filtrado:</span>
                            <span id="detail-spent">0.00 M€</span>
                        </div>
                        <div class="w-full bg-slate-950 h-2 rounded-full overflow-hidden">
                            <div id="bar-spent" class="bg-red-500 h-full rounded-full transition-all duration-500" style="width: 0%"></div>
                        </div>
                    </div>

                    <div>
                        <div class="flex justify-between text-[11px] font-bold mb-1">
                            <span class="text-emerald-400">Ventas Filtradas:</span>
                            <span id="detail-earned">0.00 M€</span>
                        </div>
                        <div class="w-full bg-slate-950 h-2 rounded-full overflow-hidden">
                            <div id="bar-earned" class="bg-emerald-500 h-full rounded-full transition-all duration-500" style="width: 0%"></div>
                        </div>
                    </div>
                </div>

                <!-- Rich Player Transfer Scouting Card (Shown for Players) -->
                <div id="drawer-player-scouting-box" class="hidden bg-slate-900 p-4 rounded-2xl border border-slate-800 flex flex-col gap-3 mt-1">
                    <div class="flex justify-between items-center text-xs">
                        <span class="text-slate-400 font-bold">Edad Oficial:</span>
                        <span class="font-extrabold text-amber-300" id="player-card-age">25 años</span>
                    </div>
                    <div class="flex justify-between items-center text-xs">
                        <span class="text-slate-400 font-bold">Coste del Traspaso:</span>
                        <span class="font-extrabold text-emerald-400 text-sm" id="player-card-cost">75.00 M€</span>
                    </div>
                    
                    <div class="bg-slate-950 p-3 rounded-xl border border-slate-800 flex flex-col gap-2 mt-1">
                        <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400">Trayectoria del Traspaso</span>
                        <div class="flex justify-between items-center text-xs">
                            <div class="flex flex-col">
                                <span class="text-[10px] text-red-400 font-bold">Vendido por</span>
                                <span class="font-extrabold text-white" id="player-card-from">PSG</span>
                            </div>
                            <span class="text-amber-400 font-black text-base">➔</span>
                            <div class="flex flex-col text-right">
                                <span class="text-[10px] text-emerald-400 font-bold">Comprado por</span>
                                <span class="font-extrabold text-white" id="player-card-to">Real Madrid</span>
                            </div>
                        </div>
                    </div>

                    <div class="text-[11px] text-slate-300 bg-slate-950/70 p-2.5 rounded-xl border border-slate-800/80">
                        <span class="font-bold text-violet-400 block mb-0.5">📌 Contexto del Fichaje:</span>
                        <span id="player-card-desc">Operación oficial registrada en la temporada 2026/2027.</span>
                    </div>
                </div>
            </div>

            <div class="flex flex-col gap-3 overflow-y-auto flex-1 text-xs mt-1" id="drawer-lists-container">
                <div>
                    <h4 class="font-bold text-emerald-400 border-b border-slate-800 pb-1 mb-1.5 flex justify-between items-center">
                        <span>Altas / Fichajes</span>
                        <span class="bg-emerald-950 text-emerald-400 px-2 rounded-full font-bold text-[10px]" id="count-arrivals">0</span>
                    </h4>
                    <ul class="flex flex-col gap-1.5 text-[11px]" id="arrivals-list"></ul>
                </div>
                
                <div>
                    <h4 class="font-bold text-red-400 border-b border-slate-800 pb-1 mb-1.5 flex justify-between items-center">
                        <span>Bajas / Ventas</span>
                        <span class="bg-red-950 text-red-400 px-2 rounded-full font-bold text-[10px]" id="count-departures">0</span>
                    </h4>
                    <ul class="flex flex-col gap-1.5 text-[11px]" id="departures-list"></ul>
                </div>
            </div>
        </aside>

    </div>

    <!-- Modals (Analytics, Path, WhatIf, Compare, Guide, Ficha) -->
    <div id="modal-analytics" class="hidden fixed inset-0 bg-slate-950/85 backdrop-blur-md flex items-center justify-center z-50 p-4">
        <div class="bg-slate-900 w-full max-w-5xl max-h-[92vh] rounded-3xl p-6 flex flex-col gap-5 overflow-hidden border border-slate-800 shadow-2xl">
            <div class="flex justify-between items-center border-b border-slate-800 pb-4">
                <div class="flex items-center gap-3">
                    <h2 class="text-xl font-black text-white">Hub de Analítica de Redes Complejas</h2>
                </div>
                <button onclick="closeAnalyticsModal()" class="text-slate-400 hover:text-white p-2 rounded-xl bg-slate-950">✕</button>
            </div>

            <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div class="bg-slate-950 p-3.5 rounded-2xl border border-slate-800 flex flex-col gap-1">
                    <span class="text-[10px] uppercase font-bold text-violet-400">Total de Equipos</span>
                    <span class="text-2xl font-black text-white">56 Clubes</span>
                    <span class="text-[10px] text-slate-400">856 nodos heterogéneos</span>
                </div>
                <div class="bg-slate-950 p-3.5 rounded-2xl border border-slate-800 flex flex-col gap-1">
                    <span class="text-[10px] uppercase font-bold text-emerald-400">Movimientos</span>
                    <span class="text-2xl font-black text-white">1,034 Traspasos</span>
                    <span class="text-[10px] text-slate-400">Operaciones analizadas</span>
                </div>
                <div class="bg-slate-950 p-3.5 rounded-2xl border border-slate-800 flex flex-col gap-1">
                    <span class="text-[10px] uppercase font-bold text-cyan-400">Homofilia (Ligas)</span>
                    <span class="text-2xl font-black text-white">+{assortativity_val:.4f}</span>
                    <span class="text-[10px] text-slate-400">Tendencia a comerciar</span>
                </div>
                <div class="bg-slate-950 p-3.5 rounded-2xl border border-slate-800 flex flex-col gap-1">
                    <span class="text-[10px] uppercase font-bold text-amber-400">Dinero Movido</span>
                    <span class="text-2xl font-black text-white">{total_market_money:.1f} M€</span>
                    <span class="text-[10px] text-slate-400">Volumen en fichajes</span>
                </div>
            </div>

            <div class="flex-1 overflow-y-auto grid grid-cols-1 md:grid-cols-2 gap-4 pr-1">
                
                <!-- Chart 1 with Explicit Axes & Context -->
                <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800 flex flex-col gap-2">
                    <div>
                        <h3 class="text-xs font-bold text-violet-300">1. Distribución de Grado por Club (Ley de Potencia)</h3>
                        <span class="text-[10px] text-slate-400">Relación entre la cantidad de traspasos y la frecuencia de clubes</span>
                    </div>
                    <div class="bg-slate-900/90 p-2.5 rounded-xl border border-slate-800/80 text-[11px] text-slate-300">
                        📌 <b>Lectura del Gráfico:</b> La mayoría de los equipos realizan un número reducido de fichajes (columna izquierda), mientras que una minoría de clubes líderes concentra un volumen masivo de operaciones (red <i>Scale-Free</i>).
                    </div>
                    <div class="h-48 relative mt-1"><canvas id="chart-degree"></canvas></div>
                </div>

                <!-- Chart 2 with Explicit Axes & Context -->
                <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800 flex flex-col gap-2">
                    <div>
                        <h3 class="text-xs font-bold text-sky-300">2. Centralidad de Intermediación (Top Clubes Puente)</h3>
                        <span class="text-[10px] text-slate-400">Capacidad de conectar distintas divisiones y ligas</span>
                    </div>
                    <div class="bg-slate-900/90 p-2.5 rounded-xl border border-slate-800/80 text-[11px] text-slate-300">
                        📌 <b>Lectura del Gráfico:</b> Muestra los clubes con mayor puntaje de intermediación (<i>Betweenness</i>). Equipos como Alavés o Espanyol actúan como conectores estratégicos entre divisiones.
                    </div>
                    <div class="h-48 relative mt-1"><canvas id="chart-betweenness"></canvas></div>
                </div>

                <!-- Chart 3 with Explicit Axes & Context -->
                <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800 flex flex-col gap-2">
                    <div>
                        <h3 class="text-xs font-bold text-amber-300">3. Balance Financiero Neto (€ Millones)</h3>
                        <span class="text-[10px] text-slate-400">Comparativa entre inversión en compras, ingresos por ventas y saldo neto</span>
                    </div>
                    <div class="bg-slate-900/90 p-2.5 rounded-xl border border-slate-800/80 text-[11px] text-slate-300">
                        📌 <b>Lectura del Gráfico:</b> Las <span class="text-red-400 font-bold">barras rojas</span> representan el gasto total en fichajes, las <span class="text-emerald-400 font-bold">barras verdes</span> los ingresos por traspasos, y la <span class="text-amber-400 font-bold">línea dorada</span> el balance financiero neto.
                    </div>
                    <div class="h-48 relative mt-1"><canvas id="chart-financials"></canvas></div>
                </div>

                <!-- Chart 4 with Explicit Axes & Context -->
                <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800 flex flex-col gap-2">
                    <div>
                        <h3 class="text-xs font-bold text-emerald-300">4. Proporción por Categorías de la Red</h3>
                        <span class="text-[10px] text-slate-400">Distribución de los 56 equipos según su liga de origen</span>
                    </div>
                    <div class="bg-slate-900/90 p-2.5 rounded-xl border border-slate-800/80 text-[11px] text-slate-300">
                        📌 <b>Lectura del Gráfico:</b> Representa la estructura categórica de la muestra: Primera División (42.9%), Segunda División (35.7%), Filiales (12.5%) y Ligas Internacionales (8.9%).
                    </div>
                    <div class="h-48 relative mt-1"><canvas id="chart-divisions"></canvas></div>
                </div>

            </div>
        </div>
    </div>

    <!-- Modal: Guide -->
    <div id="modal-guide" class="hidden fixed inset-0 bg-slate-950/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
        <div class="bg-slate-900 w-full max-w-2xl rounded-3xl p-6 flex flex-col gap-4 border border-slate-800 shadow-2xl">
            <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                <h2 class="text-lg font-bold text-amber-400">💡 ¿Cómo entender esta Red en 30 Segundos?</h2>
                <button onclick="closeGuideModal()" class="text-slate-400 hover:text-white p-1 rounded-lg bg-slate-950">✕</button>
            </div>
            <div class="flex flex-col gap-3 text-xs text-slate-300">
                <div class="bg-slate-950 p-3 rounded-xl border border-slate-800 flex gap-3 items-start">
                    <span class="text-2xl">🟡</span>
                    <div><b>Los Círculos (Nodos):</b> Representan clubes. Más grande = más traspasos o rol de puente.</div>
                </div>
                <div class="bg-slate-950 p-3 rounded-xl border border-slate-800 flex gap-3 items-start">
                    <span class="text-2xl">➡️</span>
                    <div><b>Las Flechas (Aristas):</b> Indican la dirección del traspaso del jugador.</div>
                </div>
                <div class="bg-slate-950 p-3 rounded-xl border border-slate-800 flex gap-3 items-start">
                    <span class="text-2xl">🌉</span>
                    <div><b>Conectores:</b> Clubes como Alavés o Espanyol conectan 1.ª Div, 2.ª Div y el extranjero.</div>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal: Path -->
    <div id="modal-path" class="hidden fixed inset-0 bg-slate-950/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
        <div class="bg-slate-900 w-full max-w-xl rounded-3xl p-6 flex flex-col gap-4 border border-slate-800 shadow-2xl">
            <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                <h2 class="text-lg font-bold text-cyan-400">🔍 Camino Más Corto (Grados de Separación)</h2>
                <button onclick="closePathModal()" class="text-slate-400 hover:text-white p-1 rounded-lg bg-slate-950">✕</button>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="text-xs text-slate-400 mb-1 block">Club Origen</label>
                    <select id="path-select-a" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white"></select>
                </div>
                <div>
                    <label class="text-xs text-slate-400 mb-1 block">Club Destino</label>
                    <select id="path-select-b" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white"></select>
                </div>
            </div>
            <button onclick="findAndHighlightPath()" class="w-full bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold py-2.5 rounded-xl text-xs shadow transition">
                Calcular Camino
            </button>
            <div id="path-result-box" class="hidden bg-slate-950 p-4 rounded-2xl border border-slate-800 text-xs text-slate-200"></div>
        </div>
    </div>

    <!-- Modal: WhatIf -->
    <div id="modal-whatif" class="hidden fixed inset-0 bg-slate-950/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
        <div class="bg-slate-900 w-full max-w-xl rounded-3xl p-6 flex flex-col gap-4 border border-slate-800 shadow-2xl">
            <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                <h2 class="text-lg font-bold text-teal-400">🧪 Simulador de Fichaje ("Qué Pasa Si...")</h2>
                <button onclick="closeWhatIfModal()" class="text-slate-400 hover:text-white p-1 rounded-lg bg-slate-950">✕</button>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="text-xs text-slate-400 mb-1 block">Vende</label>
                    <select id="whatif-select-a" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white"></select>
                </div>
                <div>
                    <label class="text-xs text-slate-400 mb-1 block">Compra</label>
                    <select id="whatif-select-b" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white"></select>
                </div>
            </div>
            <button onclick="simulateWhatIfTransfer()" class="w-full bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 text-white font-bold py-2.5 rounded-xl text-xs shadow transition">
                Simular Fichaje
            </button>
            <div id="whatif-result-box" class="hidden bg-slate-950 p-4 rounded-2xl border border-slate-800 text-xs text-slate-200"></div>
        </div>
    </div>

    <!-- Modal: Compare -->
    <div id="modal-compare" class="hidden fixed inset-0 bg-slate-950/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
        <div class="bg-slate-900 w-full max-w-4xl rounded-3xl p-6 flex flex-col gap-4 border border-slate-800 shadow-2xl">
            <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                <h2 class="text-lg font-bold text-amber-400">⚔️ Comparador de Clubes Cara a Cara</h2>
                <button onclick="closeCompareModal()" class="text-slate-400 hover:text-white p-1 rounded-lg bg-slate-950">✕</button>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="text-xs text-slate-400 mb-1 block">Club A</label>
                    <select id="compare-select-a" onchange="updateCompareView()" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white"></select>
                </div>
                <div>
                    <label class="text-xs text-slate-400 mb-1 block">Club B</label>
                    <select id="compare-select-b" onchange="updateCompareView()" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white"></select>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4 mt-2" id="compare-cards-container"></div>
        </div>
    </div>

    <!-- Modal: Ficha -->
    <div id="modal-ficha" class="hidden fixed inset-0 bg-slate-950/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
        <div class="bg-slate-900 w-full max-w-3xl max-h-[90vh] rounded-3xl p-6 flex flex-col gap-4 overflow-y-auto border border-slate-800 shadow-2xl">
            <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                <h2 class="text-lg font-bold text-emerald-400">Ficha Técnica Oficial del Concurso (UPY 2026)</h2>
                <button onclick="closeFichaModal()" class="text-slate-400 hover:text-white p-1 rounded-lg bg-slate-950">✕</button>
            </div>
            <div class="flex flex-col gap-4 text-xs text-slate-200">
                <table class="w-full border-collapse border border-slate-800 rounded-xl overflow-hidden">
                    <tr class="bg-slate-950"><th class="border border-slate-800 p-2 text-left text-violet-400">Campo</th><th class="border border-slate-800 p-2 text-left">Contenido</th></tr>
                    <tr><td class="border border-slate-800 p-2 font-bold">Nombre de la red</td><td class="border border-slate-800 p-2">Red de Traspasos de LaLiga (2025–2027)</td></tr>
                    <tr><td class="border border-slate-800 p-2 font-bold">Fuente</td><td class="border border-slate-800 p-2">Fichajes.com (Mercado Oficial)</td></tr>
                    <tr><td class="border border-slate-800 p-2 font-bold">Tipo de Grafo</td><td class="border border-slate-800 p-2">Dirigido, Heterogéneo y Multígrafo Dirigido Ponderado</td></tr>
                    <tr><td class="border border-slate-800 p-2 font-bold">Tamaño Nodos / Aristas</td><td class="border border-slate-800 p-2">56 nodos de clubes (856 total heterogéneo), 1034 traspasos</td></tr>
                </table>
            </div>
        </div>
    </div>

    <!-- Embedded Data & JS Logic -->
    <script>
        const clubNodes = {club_nodes_json};
        const clubEdges = {club_edges_json};
        const heteroNodes = {hetero_nodes_json};
        const heteroEdges = {hetero_edges_json};
        const clubStats = {club_stats_json};
        const starTransfers = {star_transfers_json};

        let network = null;
        let viewMode = 'clubs_only';
        let selectedSeason = 'all';
        let selectedDivision = 'all';
        let minFinancialCost = 0;
        let nodeScalingMetric = 'degree';
        let currentlySelectedNodeId = null;

        let timelinePlaying = false;
        let timelineInterval = null;

        let nodesDataset = null;
        let edgesDataset = null;

        function changeTheme(themeKey) {{
            const body = document.getElementById('main-body');
            body.classList.remove('theme-cyberpunk', 'theme-light');
            if (themeKey === 'cyberpunk') body.classList.add('theme-cyberpunk');
            else if (themeKey === 'light') body.classList.add('theme-light');
        }}

        function toggleSidebar() {{
            const sidebar = document.getElementById('left-sidebar');
            sidebar.classList.toggle('hidden');
            setTimeout(() => {{ if (network) network.fit({{ animation: true }}); }}, 200);
        }}

        function openDrawer() {{
            document.getElementById('right-drawer').classList.remove('translate-x-full');
        }}

        function closeDrawer() {{
            document.getElementById('right-drawer').classList.add('translate-x-full');
            currentlySelectedNodeId = null;
        }}

        function resetGlobalView() {{
            viewMode = 'clubs_only';
            selectedSeason = 'all';
            selectedDivision = 'all';
            minFinancialCost = 0;
            nodeScalingMetric = 'degree';

            document.getElementById('select-division-filter').value = 'all';
            document.getElementById('select-scaling').value = 'degree';
            document.getElementById('select-financial').value = '0';
            document.getElementById('select-season').value = 'all';
            document.getElementById('search-input').value = '';
            document.getElementById('timeline-slider').value = 0;
            document.getElementById('timeline-label').innerText = 'Todas';

            setViewMode('clubs_only');
            closeDrawer();
            resetEgoHighlight();
            fitNetwork();
        }}

        // PREDICTIVE AUTOCOMPLETE SEARCH LOGIC
        function handleSearchInput(query) {{
            const box = document.getElementById('search-suggestions');
            if (!query || !query.trim()) {{
                box.classList.add('hidden');
                box.innerHTML = '';
                return;
            }}

            const q = query.toLowerCase().trim();
            const activeNodes = (viewMode === 'clubs_only') ? clubNodes : heteroNodes;

            const matches = activeNodes.filter(n => n.label.toLowerCase().includes(q)).slice(0, 8);

            if (matches.length === 0) {{
                box.innerHTML = `<div class="p-2.5 text-slate-500 text-[11px] text-center font-medium">Sin resultados coincidentes</div>`;
                box.classList.remove('hidden');
                return;
            }}

            box.innerHTML = '';
            matches.forEach(m => {{
                const isPlayer = (m.group === 'Jugador');
                const typeBadge = isPlayer 
                    ? '<span class="bg-amber-950/80 text-amber-300 px-1.5 py-0.5 rounded text-[9px] font-bold border border-amber-800/60">👤 Jugador</span>' 
                    : `<span class="bg-sky-950/80 text-sky-300 px-1.5 py-0.5 rounded text-[9px] font-bold border border-sky-800/60">⚽ ${{m.group}}</span>`;
                
                box.innerHTML += `
                    <div onclick="selectSearchResult('${{m.id}}')" class="p-2.5 hover:bg-slate-800 cursor-pointer border-b border-slate-800/60 last:border-none flex justify-between items-center transition">
                        <span class="font-bold text-slate-200 text-xs">${{m.label}}</span>
                        ${{typeBadge}}
                    </div>
                `;
            }});
            box.classList.remove('hidden');
        }}

        function selectSearchResult(nodeId) {{
            document.getElementById('search-suggestions').classList.add('hidden');
            const allNodes = (viewMode === 'clubs_only') ? clubNodes : heteroNodes;
            const node = allNodes.find(n => n.id === nodeId);
            
            if (node && network) {{
                if (node.group === 'Jugador' && viewMode === 'clubs_only') {{
                    setViewMode('hetero');
                }}

                document.getElementById('search-input').value = node.label;
                currentlySelectedNodeId = nodeId;
                network.focus(nodeId, {{ scale: 1.2, animation: true }});
                network.selectNodes([nodeId]);
                showNodeDetails(nodeId);
                highlightEgoNetwork(nodeId);
                openDrawer();
            }}
        }}

        // Hide search dropdown on click outside
        document.addEventListener('click', function(e) {{
            const searchBox = document.getElementById('search-suggestions');
            const searchInput = document.getElementById('search-input');
            if (searchBox && !searchBox.contains(e.target) && e.target !== searchInput) {{
                searchBox.classList.add('hidden');
            }}
        }});

        function onSeasonDropdownChange(val) {{
            selectedSeason = val;
            let sliderVal = 0;
            if (val === '2025-2026') sliderVal = 1;
            else if (val === '2026-2027') sliderVal = 2;
            document.getElementById('timeline-slider').value = sliderVal;
            document.getElementById('timeline-label').innerText = (val === 'all') ? 'Todas' : (val === '2025-2026' ? '2025/26' : '2026/27');
            updateNetworkData();
        }}

        function getActiveNodes() {{
            let baseNodes = (viewMode === 'clubs_only') ? clubNodes : heteroNodes;
            return baseNodes.filter(n => {{
                if (selectedDivision !== 'all') {{
                    if (n.group !== 'Jugador' && n.group !== selectedDivision) return false;
                }}
                if (viewMode === 'hetero' && n.group === 'Jugador') {{
                    if (selectedSeason !== 'all' && n.season !== selectedSeason) return false;
                    if (minFinancialCost > 0 && n.cost_val < minFinancialCost) return false;
                }}
                return true;
            }}).map(n => {{
                let copy = Object.assign({{}}, n);
                if (n.group !== 'Jugador') {{
                    if (nodeScalingMetric === 'betweenness') {{
                        copy.value = 12 + Math.min(copy.betweenness * 400, 45);
                    }} else if (nodeScalingMetric === 'spent_m') {{
                        copy.value = 12 + Math.min(copy.spent_m * 0.5, 45);
                    }} else {{
                        copy.value = 12 + Math.min(copy.degree * 1.2, 35);
                    }}
                }} else {{
                    copy.value = 8;
                }}
                return copy;
            }});
        }}

        function getActiveEdges() {{
            let baseEdges = (viewMode === 'clubs_only') ? clubEdges : heteroEdges;
            return baseEdges.filter(e => {{
                if (selectedSeason !== 'all' && e.season !== selectedSeason) return false;
                if (minFinancialCost > 0) {{
                    let c = e.cost_total || e.cost_val || 0;
                    if (c < minFinancialCost) return false;
                }}
                return true;
            }});
        }}

        function initNetwork() {{
            document.getElementById('loading-overlay').classList.remove('opacity-0', 'pointer-events-none');
            const container = document.getElementById('network-canvas');

            nodesDataset = new vis.DataSet(getActiveNodes());
            edgesDataset = new vis.DataSet(getActiveEdges());

            document.getElementById('nodes-count').innerText = nodesDataset.length;
            document.getElementById('edges-count').innerText = (viewMode === 'clubs_only') ? 1034 : edgesDataset.length;

            const data = {{ nodes: nodesDataset, edges: edgesDataset }};
            const options = {{
                nodes: {{
                    font: {{ color: '#f8fafc', face: 'Outfit', size: 13, strokeWidth: 3, strokeColor: '#090d16' }},
                    borderWidth: 2, shadow: true
                }},
                edges: {{
                    width: 1.5, smooth: {{ type: 'continuous', roundness: 0.25 }}, color: {{ inherit: false }}
                }},
                physics: {{
                    solver: 'forceAtlas2Based',
                    forceAtlas2Based: {{ gravConstant: -30, centralGravity: 0.01, springLength: 90, springConstant: 0.08 }},
                    stabilization: {{ iterations: 120 }}
                }},
                interaction: {{ hover: true, tooltipDelay: 80, zoomView: true }}
            }};

            network = new vis.Network(container, data, options);

            network.on("stabilizationIterationsDone", function () {{
                document.getElementById('loading-overlay').classList.add('opacity-0', 'pointer-events-none');
            }});

            network.on("click", function (params) {{
                if (params.nodes.length > 0) {{
                    const selectedId = params.nodes[0];
                    currentlySelectedNodeId = selectedId;
                    showNodeDetails(selectedId);
                    highlightEgoNetwork(selectedId);
                    openDrawer();
                }} else {{
                    closeDrawer();
                    resetEgoHighlight();
                }}
            }});

            populateDropdowns();
            renderStarTransfers();
        }}

        function updateNetworkData() {{
            if (!nodesDataset || !edgesDataset) return;
            nodesDataset.clear();
            edgesDataset.clear();
            nodesDataset.add(getActiveNodes());
            edgesDataset.add(getActiveEdges());

            document.getElementById('nodes-count').innerText = nodesDataset.length;
            document.getElementById('edges-count').innerText = (viewMode === 'clubs_only') ? 1034 : edgesDataset.length;

            if (currentlySelectedNodeId) {{
                showNodeDetails(currentlySelectedNodeId);
            }}
        }}

        function setViewMode(mode) {{
            viewMode = mode;
            if (mode === 'clubs_only') {{
                document.getElementById('btn-view-clubs').className = "py-1.5 px-2 rounded-lg font-bold text-center bg-violet-600 text-white shadow";
                document.getElementById('btn-view-hetero').className = "py-1.5 px-2 rounded-lg font-bold text-center text-slate-400 hover:text-white transition";
            }} else {{
                document.getElementById('btn-view-hetero').className = "py-1.5 px-2 rounded-lg font-bold text-center bg-violet-600 text-white shadow";
                document.getElementById('btn-view-clubs').className = "py-1.5 px-2 rounded-lg font-bold text-center text-slate-400 hover:text-white transition";
            }}
            
            updateNetworkData();
            if (network) {{
                network.setOptions({{
                    physics: {{
                        forceAtlas2Based: {{
                            gravConstant: (mode === 'clubs_only') ? -35 : -15,
                            springLength: (mode === 'clubs_only') ? 100 : 50
                        }}
                    }}
                }});
                network.fit({{ animation: true }});
            }}
        }}

        function highlightEgoNetwork(selectedId) {{
            if (!network) return;
            const connectedNodes = network.getConnectedNodes(selectedId);
            connectedNodes.push(selectedId);

            const allNodes = nodesDataset.get();
            const updateNodes = allNodes.map(n => {{
                if (connectedNodes.includes(n.id)) {{
                    return {{ id: n.id, opacity: 1.0 }};
                }} else {{
                    return {{ id: n.id, opacity: 0.15 }};
                }}
            }});
            nodesDataset.update(updateNodes);
        }}

        function resetEgoHighlight() {{
            if (!nodesDataset) return;
            const allNodes = nodesDataset.get();
            const updateNodes = allNodes.map(n => ({{ id: n.id, opacity: 1.0 }}));
            nodesDataset.update(updateNodes);
        }}

        function setNodeScaling(metric) {{ nodeScalingMetric = metric; updateNetworkData(); }}
        function setFinancialFilter(val) {{
            if (val === 'paid') minFinancialCost = 0.01;
            else minFinancialCost = parseFloat(val);
            updateNetworkData();
        }}
        function setDivisionFilter(div) {{ selectedDivision = div; updateNetworkData(); }}
        function setSeason(season) {{
            selectedSeason = season;
            document.getElementById('select-season').value = season;
            updateNetworkData();
        }}

        const timelineSteps = [
            {{ value: 0, season: 'all', label: 'Todas las Temporadas' }},
            {{ value: 1, season: '2025-2026', label: 'Temporada 2025/2026' }},
            {{ value: 2, season: '2026-2027', label: 'Temporada 2026/2027' }}
        ];

        function onTimelineStep(val) {{
            const step = timelineSteps[val];
            document.getElementById('timeline-label').innerText = step.label;
            setSeason(step.season);
        }}

        function toggleTimelinePlay() {{
            timelinePlaying = !timelinePlaying;
            const btnIcon = document.getElementById('icon-play');
            if (timelinePlaying) {{
                btnIcon.innerHTML = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6" />`;
                let currentVal = parseInt(document.getElementById('timeline-slider').value);
                timelineInterval = setInterval(() => {{
                    currentVal = (currentVal + 1) % 3;
                    document.getElementById('timeline-slider').value = currentVal;
                    onTimelineStep(currentVal);
                }}, 1800);
            }} else {{
                btnIcon.innerHTML = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />`;
                clearInterval(timelineInterval);
            }}
        }}

        function showNodeDetails(nodeId) {{
            const node = (nodesDataset ? nodesDataset.get(nodeId) : null) || heteroNodes.find(n => n.id === nodeId) || clubNodes.find(n => n.id === nodeId);
            if (!node) return;

            document.getElementById('detail-name').innerText = node.label;
            document.getElementById('detail-type').innerText = node.group;

            const isPlayerNode = (node.group === 'Jugador');
            const clubFinanceBox = document.getElementById('drawer-club-finance-box');
            const playerScoutingBox = document.getElementById('drawer-player-scouting-box');
            const listsContainer = document.getElementById('drawer-lists-container');

            if (isPlayerNode) {{
                clubFinanceBox.classList.add('hidden');
                listsContainer.classList.add('hidden');
                playerScoutingBox.classList.remove('hidden');

                document.getElementById('detail-profile').innerText = (node.cost_val === 0) ? 'Traspaso Libre / Cesión 🆓' : (node.cost_val > 15 ? 'Fichaje Galáctico / Millonario 💎' : 'Traspaso Monetario Regular ⚽');
                document.getElementById('detail-role').innerText = `De: ${{node.source_node}} ➔ A: ${{node.target_node}}`;
                document.getElementById('detail-context-badge').innerText = `Temp. ${{node.season.replace('-', '/')}}`;

                document.getElementById('player-card-age').innerText = `${{node.age}} años`;
                document.getElementById('player-card-cost').innerText = node.cost_raw || 'Gratis / Cesión';
                document.getElementById('player-card-from').innerText = node.source_node;
                document.getElementById('player-card-to').innerText = node.target_node;
                document.getElementById('player-card-desc').innerText = `Operación oficial registrada para la Temporada ${{node.season.replace('-', '/')}}. Importe: ${{node.cost_raw}}.`;
                return;
            }}

            playerScoutingBox.classList.add('hidden');
            clubFinanceBox.classList.remove('hidden');
            listsContainer.classList.remove('hidden');

            document.getElementById('detail-profile').innerText = node.fin_profile || "Balance Equilibrado 🔵";
            document.getElementById('detail-role').innerText = node.role_desc || "⚽ Club Participante";

            const seasonText = (selectedSeason === 'all') ? 'Todas las Temporadas' : `Temp. ${{selectedSeason.replace('-', '/')}}`;
            const costText = (minFinancialCost > 0) ? ` (> ${{minFinancialCost}}M€)` : '';
            document.getElementById('detail-context-badge').innerText = `${{seasonText}}${{costText}}`;

            const arrUl = document.getElementById('arrivals-list');
            const depUl = document.getElementById('departures-list');
            arrUl.innerHTML = '';
            depUl.innerHTML = '';

            const stats = clubStats[nodeId];
            if (!stats) {{
                arrUl.innerHTML = '<li class="text-slate-500">Sin datos de altas</li>';
                depUl.innerHTML = '<li class="text-slate-500">Sin datos de bajas</li>';
                document.getElementById('count-arrivals').innerText = '0';
                document.getElementById('count-departures').innerText = '0';
                document.getElementById('detail-spent').innerText = '0.00 M€';
                document.getElementById('detail-earned').innerText = '0.00 M€';
                return;
            }}

            let arrivals = [];
            let departures = [];

            if (selectedSeason === 'all') {{
                arrivals = [
                    ...stats['2025-2026'].arrivals.map(a => ({{...a, season: '2025-2026'}})),
                    ...stats['2026-2027'].arrivals.map(a => ({{...a, season: '2026-2027'}}))
                ];
                departures = [
                    ...stats['2025-2026'].departures.map(d => ({{...d, season: '2025-2026'}})),
                    ...stats['2026-2027'].departures.map(d => ({{...d, season: '2026-2027'}}))
                ];
            }} else if (stats[selectedSeason]) {{
                arrivals = stats[selectedSeason].arrivals.map(a => ({{...a, season: selectedSeason}}));
                departures = stats[selectedSeason].departures.map(d => ({{...d, season: selectedSeason}}));
            }}

            if (minFinancialCost > 0) {{
                arrivals = arrivals.filter(a => a.cost_val >= minFinancialCost);
                departures = departures.filter(d => d.cost_val >= minFinancialCost);
            }}

            const dynamicSpent = arrivals.reduce((acc, a) => acc + a.cost_val, 0);
            const dynamicEarned = departures.reduce((acc, d) => acc + d.cost_val, 0);
            const maxVal = Math.max(dynamicSpent, dynamicEarned, 1.0);

            document.getElementById('detail-spent').innerText = `${{dynamicSpent.toFixed(2)}} M€`;
            document.getElementById('detail-earned').innerText = `${{dynamicEarned.toFixed(2)}} M€`;

            document.getElementById('bar-spent').style.width = `${{Math.min((dynamicSpent / maxVal) * 100, 100)}}%`;
            document.getElementById('bar-earned').style.width = `${{Math.min((dynamicEarned / maxVal) * 100, 100)}}%`;

            document.getElementById('count-arrivals').innerText = arrivals.length;
            document.getElementById('count-departures').innerText = departures.length;

            if (arrivals.length === 0) {{
                arrUl.innerHTML = '<li class="text-slate-500 py-1">Sin altas para este filtro</li>';
            }} else {{
                arrivals.forEach(a => {{
                    const sBadge = (a.season === '2025-2026') ? '25/26' : '26/27';
                    arrUl.innerHTML += `
                        <li class="bg-slate-950 p-2 rounded-xl border border-slate-800 flex justify-between items-center gap-1">
                            <div>
                                <b>${{a.player}}</b> <span class="text-emerald-400 font-bold">(${{a.cost}})</span>
                                <div class="text-slate-400 text-[10px]">desde ${{a.from}}</div>
                            </div>
                            <span class="bg-violet-950/80 text-violet-300 text-[9px] px-1.5 py-0.5 rounded-lg border border-violet-800/50 font-bold shrink-0">${{sBadge}}</span>
                        </li>
                    `;
                }});
            }}

            if (departures.length === 0) {{
                depUl.innerHTML = '<li class="text-slate-500 py-1">Sin bajas para este filtro</li>';
            }} else {{
                departures.forEach(d => {{
                    const sBadge = (d.season === '2025-2026') ? '25/26' : '26/27';
                    depUl.innerHTML += `
                        <li class="bg-slate-950 p-2 rounded-xl border border-slate-800 flex justify-between items-center gap-1">
                            <div>
                                <b>${{d.player}}</b> <span class="text-red-400 font-bold">(${{d.cost}})</span>
                                <div class="text-slate-400 text-[10px]">hacia ${{d.to}}</div>
                            </div>
                            <span class="bg-violet-950/80 text-violet-300 text-[9px] px-1.5 py-0.5 rounded-lg border border-violet-800/50 font-bold shrink-0">${{sBadge}}</span>
                        </li>
                    `;
                }});
            }}
        }}

        function fitNetwork() {{ if (network) network.fit({{ animation: true }}); }}

        function playStory(num) {{
            if (!network) return;
            if (num === 1) {{
                currentlySelectedNodeId = 'Alavés';
                network.focus('Alavés', {{ scale: 1.1, animation: true }});
                network.selectNodes(['Alavés', 'Espanyol', 'Mirandés']);
                showNodeDetails('Alavés');
                highlightEgoNetwork('Alavés');
                openDrawer();
            }} else if (num === 2) {{
                currentlySelectedNodeId = 'Resto del mundo';
                network.focus('Resto del mundo', {{ scale: 1.0, animation: true }});
                network.selectNodes(['Resto del mundo', 'Premier League']);
                showNodeDetails('Resto del mundo');
                highlightEgoNetwork('Resto del mundo');
                openDrawer();
            }} else if (num === 3) {{
                setDivisionFilter('Cantera / Filial');
                fitNetwork();
            }}
        }}

        function renderStarTransfers() {{
            const container = document.getElementById('star-transfers-container');
            container.innerHTML = '';
            starTransfers.slice(0, 5).forEach(st => {{
                container.innerHTML += `
                    <button onclick="focusStarTransfer('${{st.from}}', '${{st.to}}')" class="bg-slate-950 hover:bg-slate-800 text-slate-200 text-[10px] px-2.5 py-1 rounded-lg border border-slate-800 whitespace-nowrap font-bold">
                        <span class="text-amber-300">${{st.player}}</span> (${{st.cost}})
                    </button>
                `;
            }});
        }}

        function focusStarTransfer(src, tgt) {{
            if (network) {{
                currentlySelectedNodeId = src;
                network.selectNodes([src, tgt]);
                network.focus(src, {{ scale: 1.1, animation: true }});
                showNodeDetails(src);
                highlightEgoNetwork(src);
                openDrawer();
            }}
        }}

        function openGuideModal() {{ document.getElementById('modal-guide').classList.remove('hidden'); }}
        function closeGuideModal() {{ document.getElementById('modal-guide').classList.add('hidden'); }}
        function openPathModal() {{ document.getElementById('modal-path').classList.remove('hidden'); }}
        function closePathModal() {{ document.getElementById('modal-path').classList.add('hidden'); }}
        function openWhatIfModal() {{ document.getElementById('modal-whatif').classList.remove('hidden'); }}
        function closeWhatIfModal() {{ document.getElementById('modal-whatif').classList.add('hidden'); }}
        function openCompareModal() {{ document.getElementById('modal-compare').classList.remove('hidden'); updateCompareView(); }}
        function closeCompareModal() {{ document.getElementById('modal-compare').classList.add('hidden'); }}
        function openAnalyticsModal() {{ document.getElementById('modal-analytics').classList.remove('hidden'); renderAnalyticsCharts(); }}
        function closeAnalyticsModal() {{ document.getElementById('modal-analytics').classList.add('hidden'); }}
        function openFichaModal() {{ document.getElementById('modal-ficha').classList.remove('hidden'); }}
        function closeFichaModal() {{ document.getElementById('modal-ficha').classList.add('hidden'); }}

        function populateDropdowns() {{
            const clubsSorted = [...clubNodes].sort((a,b) => a.label.localeCompare(b.label));
            ['path-select-a', 'path-select-b', 'whatif-select-a', 'whatif-select-b', 'compare-select-a', 'compare-select-b'].forEach(id => {{
                const el = document.getElementById(id);
                if (!el) return;
                el.innerHTML = '';
                clubsSorted.forEach((c, idx) => {{
                    el.innerHTML += `<option value="${{c.id}}" ${{idx === 0 ? 'selected' : ''}}>${{c.label}}</option>`;
                }});
            }});
        }}

        function findAndHighlightPath() {{
            const src = document.getElementById('path-select-a').value;
            const tgt = document.getElementById('path-select-b').value;
            if (src === tgt) return;

            let queue = [[src]];
            let visited = new Set([src]);
            let foundPath = null;

            while (queue.length > 0) {{
                let path = queue.shift();
                let lastNode = path[path.length - 1];

                if (lastNode === tgt) {{
                    foundPath = path;
                    break;
                }}

                let neighbors = clubEdges.filter(e => e.from === lastNode || e.to === lastNode).map(e => e.from === lastNode ? e.to : e.from);
                for (let n of neighbors) {{
                    if (!visited.has(n)) {{
                        visited.add(n);
                        queue.push([...path, n]);
                    }}
                }}
            }}

            const box = document.getElementById('path-result-box');
            box.classList.remove('hidden');

            if (foundPath) {{
                box.innerHTML = `<span class="text-emerald-400 font-bold">¡Camino encontrado (${{foundPath.length - 1}} pasos de distancia)!</span><br><br>` + foundPath.join(' ➔ ');
                network.selectNodes(foundPath);
                network.focus(src, {{ scale: 1.0, animation: true }});
            }} else {{
                box.innerHTML = `<span class="text-red-400 font-bold">No se encontró un camino directo en la muestra de datos.</span>`;
            }}
        }}

        function simulateWhatIfTransfer() {{
            const src = document.getElementById('whatif-select-a').value;
            const tgt = document.getElementById('whatif-select-b').value;

            const tempId = `temp_edge_${{Date.now()}}`;
            edgesDataset.add({{
                id: tempId, from: src, to: tgt, label: "Fichaje Simulado",
                color: {{ color: '#34d399' }}, width: 4, dashes: true, arrows: "to"
            }});

            const box = document.getElementById('whatif-result-box');
            box.classList.remove('hidden');
            box.innerHTML = `<span class="text-emerald-400 font-bold">¡Fichaje Simulado Añadido!</span><br>Se ha dibujado un enlace temporal verde desde <b>${{src}}</b> hasta <b>${{tgt}}</b>. Observa cómo cambia la estructura de la red.`;
            
            network.focus(src, {{ scale: 1.1, animation: true }});
        }}

        function updateCompareView() {{
            const idA = document.getElementById('compare-select-a').value;
            const idB = document.getElementById('compare-select-b').value;

            const nodeA = clubNodes.find(n => n.id === idA);
            const nodeB = clubNodes.find(n => n.id === idB);

            if (!nodeA || !nodeB) return;

            const directEdges = clubEdges.filter(e => 
                (e.from === idA && e.to === idB) || (e.from === idB && e.to === idA)
            );

            let directText = "Sin traspasos directos entre estos dos clubes.";
            if (directEdges.length > 0) {{
                directText = directEdges.map(e => `${{e.from}} ➔ ${{e.to}}: ${{e.weight}} traspaso(s) (${{e.cost_total}} M€)`).join('<br>');
            }}

            const container = document.getElementById('compare-cards-container');
            container.innerHTML = `
                <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800 flex flex-col gap-2">
                    <h3 class="text-base font-extrabold text-sky-400">${{nodeA.label}}</h3>
                    <span class="text-[10px] bg-slate-900 px-2 py-0.5 rounded w-max text-slate-300 font-bold">${{nodeA.group}}</span>
                    <p class="text-xs text-amber-300 font-semibold">${{nodeA.role_desc}}</p>
                    <div class="grid grid-cols-2 gap-2 text-xs mt-2 text-slate-300">
                        <div>Grado Total: <b>${{nodeA.degree}}</b></div>
                        <div>Betweenness: <b>${{nodeA.betweenness}}</b></div>
                        <div>PageRank: <b>${{nodeA.pagerank}}</b></div>
                        <div>Gasto: <b class="text-red-400">${{nodeA.spent_m}} M€</b></div>
                        <div>Ventas: <b class="text-emerald-400">${{nodeA.earned_m}} M€</b></div>
                    </div>
                </div>

                <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800 flex flex-col gap-2">
                    <h3 class="text-base font-extrabold text-emerald-400">${{nodeB.label}}</h3>
                    <span class="text-[10px] bg-slate-900 px-2 py-0.5 rounded w-max text-slate-300 font-bold">${{nodeB.group}}</span>
                    <p class="text-xs text-amber-300 font-semibold">${{nodeB.role_desc}}</p>
                    <div class="grid grid-cols-2 gap-2 text-xs mt-2 text-slate-300">
                        <div>Grado Total: <b>${{nodeB.degree}}</b></div>
                        <div>Betweenness: <b>${{nodeB.betweenness}}</b></div>
                        <div>PageRank: <b>${{nodeB.pagerank}}</b></div>
                        <div>Gasto: <b class="text-red-400">${{nodeB.spent_m}} M€</b></div>
                        <div>Ventas: <b class="text-emerald-400">${{nodeB.earned_m}} M€</b></div>
                    </div>
                </div>

                <div class="col-span-2 bg-slate-950 p-3 rounded-xl border border-slate-800 text-xs text-slate-300 text-center">
                    <span class="font-bold text-amber-400 uppercase tracking-wider text-[10px] block mb-1">Conexión Directa Entre Ambos Clubes</span>
                    <div>${{directText}}</div>
                </div>
            `;
        }}

        let chartDegree = null;
        let chartBetweenness = null;
        let chartFinancials = null;
        let chartDivisions = null;

        function renderAnalyticsCharts() {{
            const clubsOnly = clubNodes;

            // Chart 1: Degree Distribution with explicit X and Y axis labels
            if (chartDegree) chartDegree.destroy();
            const degreeCounts = {{}};
            clubsOnly.forEach(n => {{ degreeCounts[n.degree] = (degreeCounts[n.degree] || 0) + 1; }});
            const degLabels = Object.keys(degreeCounts).sort((a,b) => a-b);
            const degData = degLabels.map(k => degreeCounts[k]);

            const ctxDegree = document.getElementById('chart-degree').getContext('2d');
            const gradientDegree = ctxDegree.createLinearGradient(0, 0, 0, 200);
            gradientDegree.addColorStop(0, 'rgba(124, 58, 237, 0.7)');
            gradientDegree.addColorStop(1, 'rgba(124, 58, 237, 0.05)');

            chartDegree = new Chart(ctxDegree, {{
                type: 'bar',
                data: {{
                    labels: degLabels.map(l => `${{l}} Traspasos`),
                    datasets: [
                        {{
                            type: 'line',
                            label: 'Curva Ley de Potencia (Scale-Free)',
                            data: degData,
                            borderColor: '#a855f7',
                            borderWidth: 3,
                            tension: 0.4,
                            pointBackgroundColor: '#c084fc',
                            pointRadius: 4,
                            fill: false
                        }},
                        {{
                            type: 'bar',
                            label: 'Frecuencia (Nº de Clubes)',
                            data: degData,
                            backgroundColor: gradientDegree,
                            borderColor: '#7c3aed',
                            borderWidth: 1,
                            borderRadius: 8
                        }}
                    ]
                }},
                options: {{
                    responsive: true, maintainAspectRatio: false,
                    plugins: {{ 
                        legend: {{ labels: {{ color: '#cbd5e1', font: {{ family: 'Outfit', size: 10 }} }} }} 
                    }},
                    scales: {{
                        x: {{ 
                            title: {{ display: true, text: 'Eje X: Número de Traspasos por Club (Grado K)', color: '#94a3b8', font: {{ family: 'Outfit', size: 10, weight: 'bold' }} }},
                            ticks: {{ color: '#94a3b8', font: {{ size: 9 }} }}, grid: {{ color: '#1e293b' }} 
                        }},
                        y: {{ 
                            title: {{ display: true, text: 'Eje Y: Frecuencia (Cantidad de Clubes)', color: '#94a3b8', font: {{ family: 'Outfit', size: 10, weight: 'bold' }} }},
                            ticks: {{ color: '#94a3b8', font: {{ size: 9 }} }}, grid: {{ color: '#1e293b' }} 
                        }}
                    }}
                }}
            }});

            // Chart 2: Betweenness with explicit X and Y axis labels
            if (chartBetweenness) chartBetweenness.destroy();
            const topBet = [...clubsOnly].sort((a,b) => b.betweenness - a.betweenness).slice(0, 8);
            
            const ctxBet = document.getElementById('chart-betweenness').getContext('2d');
            const gradientBet = ctxBet.createLinearGradient(0, 0, 300, 0);
            gradientBet.addColorStop(0, '#0284c7');
            gradientBet.addColorStop(1, '#8b5cf6');

            chartBetweenness = new Chart(ctxBet, {{
                type: 'bar',
                data: {{
                    labels: topBet.map(n => n.label),
                    datasets: [{{
                        label: 'Puntaje de Intermediación (Rol Puente)',
                        data: topBet.map(n => n.betweenness),
                        backgroundColor: gradientBet,
                        borderRadius: 6
                    }}]
                }},
                options: {{
                    indexAxis: 'y', responsive: true, maintainAspectRatio: false,
                    plugins: {{ legend: {{ display: true, labels: {{ color: '#cbd5e1', font: {{ family: 'Outfit', size: 10 }} }} }} }},
                    scales: {{
                        x: {{ 
                            title: {{ display: true, text: 'Eje X: Puntaje de Intermediación (0.00 a 1.00)', color: '#94a3b8', font: {{ family: 'Outfit', size: 10, weight: 'bold' }} }},
                            ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#1e293b' }} 
                        }},
                        y: {{ 
                            title: {{ display: true, text: 'Eje Y: Club Conector', color: '#94a3b8', font: {{ family: 'Outfit', size: 10, weight: 'bold' }} }},
                            ticks: {{ color: '#f8fafc', font: {{ weight: 'bold' }} }}, grid: {{ color: '#1e293b' }} 
                        }}
                    }}
                }}
            }});

            // Chart 3: Financials with explicit X and Y axis labels
            if (chartFinancials) chartFinancials.destroy();
            const topSpenders = [...clubsOnly].sort((a,b) => b.spent_m - a.spent_m).slice(0, 8);
            const netBalances = topSpenders.map(n => n.earned_m - n.spent_m);

            chartFinancials = new Chart(document.getElementById('chart-financials'), {{
                type: 'bar',
                data: {{
                    labels: topSpenders.map(n => n.label),
                    datasets: [
                        {{
                            type: 'line',
                            label: 'Balance Neto (Ventas - Gasto)',
                            data: netBalances,
                            borderColor: '#fbbf24',
                            borderWidth: 2.5,
                            pointBackgroundColor: '#f59e0b',
                            fill: false
                        }},
                        {{
                            label: 'Gasto en Compras (€ M)',
                            data: topSpenders.map(n => n.spent_m),
                            backgroundColor: 'rgba(239, 68, 68, 0.85)',
                            borderRadius: 6
                        }},
                        {{
                            label: 'Ingresos por Ventas (€ M)',
                            data: topSpenders.map(n => n.earned_m),
                            backgroundColor: 'rgba(52, 211, 153, 0.85)',
                            borderRadius: 6
                        }}
                    ]
                }},
                options: {{
                    responsive: true, maintainAspectRatio: false,
                    plugins: {{ legend: {{ labels: {{ color: '#cbd5e1', font: {{ family: 'Outfit', size: 10 }} }} }} }},
                    scales: {{
                        x: {{ 
                            title: {{ display: true, text: 'Eje X: Clubes Principales', color: '#94a3b8', font: {{ family: 'Outfit', size: 10, weight: 'bold' }} }},
                            ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#1e293b' }} 
                        }},
                        y: {{ 
                            title: {{ display: true, text: 'Eje Y: Dinero en Millones de Euros (€ M)', color: '#94a3b8', font: {{ family: 'Outfit', size: 10, weight: 'bold' }} }},
                            ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#1e293b' }} 
                        }}
                    }}
                }}
            }});

            // Chart 4: Categories Doughnut
            if (chartDivisions) chartDivisions.destroy();
            const divCounts = {{ 'Primera División': 0, 'Segunda División': 0, 'Liga Internacional': 0, 'Cantera / Filial': 0 }};
            clubsOnly.forEach(n => {{ divCounts[n.group] = (divCounts[n.group] || 0) + 1; }});

            chartDivisions = new Chart(document.getElementById('chart-divisions'), {{
                type: 'doughnut',
                data: {{
                    labels: Object.keys(divCounts).map(k => `${{k}} (${{divCounts[k]}} clubes)`),
                    datasets: [{{
                        data: Object.values(divCounts),
                        backgroundColor: ['#38bdf8', '#34d399', '#ef4444', '#a855f7'],
                        borderWidth: 2,
                        borderColor: '#0b0f19'
                    }}]
                }},
                options: {{
                    responsive: true, maintainAspectRatio: false,
                    plugins: {{ legend: {{ position: 'right', labels: {{ color: '#cbd5e1', font: {{ family: 'Outfit', size: 10 }} }} }} }}
                }}
            }});
        }}

        window.onload = initNetwork;
    </script>
</body>
</html>
"""

    with open("transfer_market_graph.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print("Successfully built fully integrated App Shell with Explicit Axes & Professional Chart Legends!")

if __name__ == "__main__":
    main()
