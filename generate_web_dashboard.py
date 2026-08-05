import datetime
import json
import os
import random
import sys
import re
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

# Import SLUG_TO_NAME and LEAGUE_KEYWORDS from scraper
from scraper import SLUG_TO_NAME, LEAGUE_KEYWORDS

SPANISH_CLUBS = set(SLUG_TO_NAME.values())

# Define DIVISION_2 clubs based on Spanish list but not Primera/Cantera
DIVISION_2 = {
    "Albacete", "Almería", "Burgos", "Cádiz", "Castellón", "Eldense",
    "CD Leganés", "Tenerife", "Sabadell", "Córdoba", "FC Andorra",
    "Granada", "Sporting de Gijón", "Eibar", "Las Palmas", "Ceuta",
    "Cultural Leonesa", "Huesca", "Mirandés", "Real Zaragoza"
}

def clean_cost_num(cost_str):
    if not cost_str:
        return 0.0
    cost_str_clean = str(cost_str).lower().strip()
    if "gratis" in cost_str_clean or "libre" in cost_str_clean or "cesión" in cost_str_clean or "regreso" in cost_str_clean or "fin de contrato" in cost_str_clean or "cesion" in cost_str_clean:
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

def is_filial_club(name):
    name_lower = name.lower()
    return any(p in name_lower for p in [" b", " ii", "castilla", "promesas", "mestalla", "atlètic", "filial"])

def get_club_group(node):
    node_clean = node.strip()
    node_lower = node_clean.lower()
    
    # 1. Check if filial
    if is_filial_club(node_clean):
        return "Cantera / Filial"
        
    # 2. Check if Primera División
    for c in DIVISION_1:
        if node_lower == c.lower():
            return "Primera División"
            
    # 3. Check if Segunda División
    for c in DIVISION_2:
        if node_lower == c.lower():
            return "Segunda División"
            
    # 4. Check if other Spanish club name
    is_spanish = False
    for c in SPANISH_CLUBS:
        if node_lower == c.lower() or c.lower() in node_lower:
            is_spanish = True
            break
    if is_spanish:
        return "Segunda División"
        
    # 5. Check external leagues
    for league, keywords in LEAGUE_KEYWORDS.items():
        for kw in keywords:
            if kw in node_lower:
                return league
                
    # 6. Default to Resto del mundo
    return "Resto del mundo"

def main():
    dataset_file = "transfers_dataset.json"
    if not os.path.exists(dataset_file):
        print(f"Error: {dataset_file} not found. Please run the scraper first.")
        sys.exit(1)
        
    with open(dataset_file, "r", encoding="utf-8") as f:
        transfers = json.load(f)
        
    print(f"Loaded {len(transfers)} transfers. Building 338-node network for Web Explorer...")
    
    # Build 338-node homogeneous graph
    G = nx.DiGraph()
    for t in transfers:
        src = t["from_club_raw"].strip()
        tgt = t["to_club_raw"].strip()
        G.add_edge(src, tgt)
        
    betweenness = nx.betweenness_centrality(G)
    closeness = nx.closeness_centrality(G)
    try:
        pagerank = nx.pagerank(G, alpha=0.85)
    except Exception:
        pagerank = {n: 0.0 for n in G.nodes()}

    G_clubs_simple = nx.DiGraph()
    for n in G.nodes():
        grp = get_club_group(n)
        G_clubs_simple.add_node(n, division=grp)
    for u, v in G.edges():
        G_clubs_simple.add_edge(u, v)
        
    try:
        assortativity_val = nx.attribute_assortativity_coefficient(G_clubs_simple.to_undirected(), "division")
    except Exception:
        assortativity_val = 0.0
        
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

    # Spring layout positions for 338 nodes
    layout_pos = nx.spring_layout(G_clubs_simple, seed=42, k=2.5, iterations=250, scale=1400)

    club_stats = {}
    financials = {}
    club_degrees = {}
    total_market_money = 0.0
    
    for t in transfers:
        src = t["from_club_raw"].strip()
        tgt = t["to_club_raw"].strip()
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

    all_clubs_set = set(G.nodes())
    
    club_nodes_js = []
    
    color_map = {
        "Primera División": {"background": "#38bdf8", "border": "#0284c7", "highlight": {"background": "#7dd3fc", "border": "#38bdf8"}},
        "Segunda División": {"background": "#34d399", "border": "#059669", "highlight": {"background": "#6ee7b7", "border": "#34d399"}},
        "Cantera / Filial": {"background": "#a855f7", "border": "#7e22ce", "highlight": {"background": "#c084fc", "border": "#a855f7"}},
        "Premier League": {"background": "#ef4444", "border": "#dc2626", "highlight": {"background": "#f87171", "border": "#ef4444"}},
        "Bundesliga": {"background": "#eab308", "border": "#ca8a04", "highlight": {"background": "#fde047", "border": "#eab308"}},
        "Ligue 1": {"background": "#84cc16", "border": "#65a30d", "highlight": {"background": "#a3e635", "border": "#84cc16"}},
        "Serie A": {"background": "#06b6d4", "border": "#0891b2", "highlight": {"background": "#22d3ee", "border": "#06b6d4"}},
        "Resto del mundo": {"background": "#f43f5e", "border": "#e11d48", "highlight": {"background": "#fb7185", "border": "#f43f5e"}}
    }
    
    for node in sorted(all_clubs_set):
        deg = club_degrees.get(node, 1)
        bet = betweenness.get(node, 0.0)
        pr = pagerank.get(node, 0.0)
        fin = financials.get(node, {"spent_m": 0.0, "earned_m": 0.0})
        is_filial = is_filial_club(node)
        group = get_club_group(node)
        
        diff = fin["spent_m"] - fin["earned_m"]
        if diff > 5.0:
            fin_profile = "Inversor Neto 🟢"
        elif diff < -5.0:
            fin_profile = "Vendedor Neto 🔴"
        else:
            fin_profile = "Balance Equilibrado 🔵"
            
        if bet > 0.04:
            role_desc = "🌉 Conector del Mercado (Puente)"
        elif fin["spent_m"] > 20:
            role_desc = "💰 Potencia Compradora"
        elif is_filial:
            role_desc = "🌱 Cantera de Promoción"
        else:
            role_desc = "⚽ Club Participante"

        pos = layout_pos.get(node, (0.0, 0.0))
        club_nodes_js.append({
            "id": node,
            "label": node,
            "group": group,
            "shape": "dot",
            "color": color_map[group],
            "x": round(float(pos[0]), 2),
            "y": round(float(pos[1]), 2),
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
        src = t["from_club_raw"].strip()
        tgt = t["to_club_raw"].strip()
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
        src = t["from_club_raw"].strip()
        tgt = t["to_club_raw"].strip()
        
        import math
        src_pos = layout_pos.get(src, (0.0, 0.0))
        rng = random.Random(idx)
        angle = rng.uniform(0.0, 2.0 * math.pi)
        radius = rng.uniform(35.0, 120.0)
        jitter_x = radius * math.cos(angle)
        jitter_y = radius * math.sin(angle)

        hetero_nodes_js.append({
            "id": p_id,
            "label": player,
            "group": "Jugador",
            "shape": "diamond",
            "color": {"background": "#fbbf24", "border": "#d97706", "highlight": {"background": "#fde047", "border": "#fbbf24"}},
            "x": round(float(src_pos[0] + jitter_x), 2),
            "y": round(float(src_pos[1] + jitter_y), 2),
            "degree": 2,
            "betweenness": 0.0,
            "pagerank": 0.0,
            "community": 0,
            "spent_m": 0.0,
            "earned_m": 0.0,
            "cost_val": cost_val,
            "cost_raw": cost_raw,
            "source_node": src,
            "target_node": tgt,
            "age": t["age"] or "N/D",
            "season": t["season"],
            "value": 10,
            "title": f"<b>{player}</b> ({t['age']} años)<br>De: {src} ➔ A: {tgt}<br>Coste: {cost_raw}<br>Temporada: {t['season']}"
        })
        
        hetero_edges_js.append({
            "id": f"eh_src_{idx}", "from": src, "to": p_id,
            "season": t["season"], "cost_val": cost_val, "arrows": "to", "color": {"color": "rgba(239, 68, 68, 0.65)"}
        })
        hetero_edges_js.append({
            "id": f"eh_tgt_{idx}", "from": p_id, "to": tgt,
            "season": t["season"], "cost_val": cost_val, "arrows": "to", "color": {"color": "rgba(52, 211, 153, 0.65)"}
        })

    star_transfers = []
    for t in transfers:
        c_val = clean_cost_num(t["cost"])
        src = t["from_club_raw"].strip()
        tgt = t["to_club_raw"].strip()
        if c_val > 5.0:
            star_transfers.append({
                "player": t["player"],
                "from": src,
                "to": tgt,
                "cost": t["cost"],
                "cost_val": c_val,
                "season": t["season"]
            })
    star_transfers = sorted(star_transfers, key=lambda x: x["cost_val"], reverse=True)[:10]

    docs_dir = "docs"
    data_dir = os.path.join(docs_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    meta = {
        "assortativity": round(float(assortativity_val), 4),
        "total_market_money": round(float(total_market_money), 1),
        "total_clubs": len(club_nodes_js),
        "total_hetero_nodes": len(hetero_nodes_js),
        "total_transfers": len(transfers),
        "timeline_steps": [
            {"value": 0, "season": "all", "label": "Todas las Temporadas"},
            {"value": 1, "season": "2025-2026", "label": "Temporada 2025/2026"},
            {"value": 2, "season": "2026-2027", "label": "Temporada 2026/2027"}
        ]
    }

    data_files = {
        "clubs-network.json": {"nodes": club_nodes_js, "edges": club_edges_js},
        "hetero-network.json": {"nodes": hetero_nodes_js, "edges": hetero_edges_js},
        "club-stats.json": club_stats,
        "star-transfers.json": star_transfers,
        "meta.json": meta,
    }

    for filename, payload in data_files.items():
        out_path = os.path.join(data_dir, filename)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=None, separators=(",", ":"))

    write_index_html(docs_dir)
    
    # Generate the monolithic self-contained dashboard
    write_monolithic_html(docs_dir, club_nodes_js, club_edges_js, hetero_nodes_js, hetero_edges_js, club_stats, star_transfers, meta)

    print(f"Datos escritos en {data_dir}/ (clubs-network.json, hetero-network.json, club-stats.json, star-transfers.json, meta.json)")
    print(f"Shell HTML escrito en {docs_dir}/index.html")
    print("Successfully built the modular App Shell (docs/) with precomputed layout and lazy-loaded hetero data / Chart.js!")


def write_index_html(docs_dir):
    """Escribe docs/index.html: un shell HTML delgado sin datos ni JS embebido."""
    html_content = """<!DOCTYPE html>
<html lang="es" id="html-root" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LaLiga Transfer Analytics Pro (2025-2027) | UPY 2026</title>

    <!-- Cache-busting: el sufijo ?v= debe subirse en CADA cambio de CSS/JS
         (y coincidir con APP_VERSION en main.js). Sin él, Chrome/Edge sirven la
         versión vieja de los scripts en local y parece que los arreglos
         "no funcionan". -->
    <link href="assets/css/app.css?v=__ASSET_VERSION__" rel="stylesheet">
    <link href="assets/css/custom.css?v=__ASSET_VERSION__" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">

    <script type="text/javascript" src="assets/js/vendor/vis-network.min.js" defer></script>
</head>
<body class="h-screen w-screen flex flex-col overflow-hidden" id="main-body">

    <!-- Fixed App Header -->
    <header class="h-auto md:h-14 w-full app-header px-4 md:px-6 flex flex-col md:flex-row justify-between items-center z-30 shrink-0 py-2.5 md:py-0 gap-2.5 md:gap-0">
        <div class="flex items-center gap-3 w-full md:w-auto">
            <div class="relative flex h-3 w-3">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-3 w-3 bg-violet-500"></span>
            </div>
            <h1 class="text-base font-extrabold tracking-tight text-white whitespace-nowrap">
                LaLiga Transfer Network Explorer <span class="text-xs font-normal text-slate-400">UPY 2026</span>
            </h1>
        </div>

        <div class="flex items-center gap-2 overflow-x-auto w-full md:w-auto pb-1.5 md:pb-0 scrollbar-none whitespace-nowrap">
            <button onclick="resetGlobalView()" class="btn-pill bg-violet-600 hover:bg-violet-500 text-white text-xs font-bold px-3 py-1.5 rounded-xl shadow border border-violet-500 flex items-center gap-1 shrink-0">
                <span>🔄 Restablecer Vista</span>
            </button>
            <button onclick="openAnalyticsModal()" class="btn-pill bg-slate-900 text-slate-200 text-xs font-bold px-3 py-1.5 rounded-xl border border-slate-800 shrink-0">
                📊 Analytics Hub
            </button>
            <button onclick="openCompareModal()" class="btn-pill bg-slate-900 text-slate-200 text-xs font-bold px-3 py-1.5 rounded-xl border border-slate-800 shrink-0">
                ⚔️ Comparador
            </button>
            <button onclick="openPathModal()" class="btn-pill bg-slate-900 text-slate-200 text-xs font-bold px-3 py-1.5 rounded-xl border border-slate-800 shrink-0">
                🔍 Camino Corto
            </button>
            <button onclick="openWhatIfModal()" class="btn-pill bg-slate-900 text-slate-200 text-xs font-bold px-3 py-1.5 rounded-xl border border-slate-800 shrink-0">
                🧪 Simulador
            </button>
            <button onclick="openGuideModal()" class="btn-pill bg-amber-950/60 text-amber-300 text-xs font-bold px-3 py-1.5 rounded-xl border border-amber-800/50 shrink-0">
                💡 Ayuda
            </button>
            <button onclick="openFichaModal()" class="btn-pill bg-emerald-950/60 text-emerald-300 text-xs font-bold px-3 py-1.5 rounded-xl border border-emerald-800/50 shrink-0">
                📄 Ficha A4
            </button>

            <!-- Theme Switcher Selector -->
            <select onchange="changeTheme(this.value)" class="bg-slate-900 text-slate-200 font-bold px-2 py-1 rounded-xl text-xs border border-slate-800 ml-1 focus:outline-none shrink-0">
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
                <label class="flex items-center gap-2 mt-1.5 cursor-pointer select-none text-[11px] text-slate-400">
                    <input type="checkbox" id="toggle-player-labels" onchange="setPlayerLabels(this.checked)" class="accent-violet-500 w-3.5 h-3.5">
                    Mostrar nombres de jugadores
                    <span class="text-[9px] text-slate-500">(pasa el cursor para ver)</span>
                </label>
                <label class="flex items-center justify-between gap-2 mt-1.5 cursor-pointer select-none text-[11px] text-slate-200 font-semibold bg-slate-900/60 border border-slate-800 hover:border-cyan-600/60 rounded-xl px-2.5 py-2 transition">
                    <span>🎯 Modo Enfoque</span>
                    <span class="flex items-center gap-2">
                        <span id="focus-mode-state" class="text-[9px] font-extrabold uppercase tracking-wider text-slate-500">Off</span>
                        <input type="checkbox" id="toggle-focus-mode" onchange="setFocusMode(this.checked)" class="accent-cyan-500 w-3.5 h-3.5">
                    </span>
                </label>
                <span id="focus-mode-hint" class="hidden text-[9px] text-cyan-300/80 leading-tight">
                    Haz clic en un club, jugador o liga para aislar solo su ruta de traspasos. Clic en el vacío o <b>Esc</b> para volver.
                </span>
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
                <label class="text-slate-300 font-bold">Filtrar por Categoría / Liga</label>
                <select onchange="setDivisionFilter(this.value)" class="w-full bg-slate-900 border border-slate-800 rounded-xl p-2 text-xs text-slate-200 focus:outline-none" id="select-division-filter">
                    <option value="all">Todas las Categorías / Ligas</option>
                    <option value="Primera División">Primera División (España)</option>
                    <option value="Segunda División">Segunda División (España)</option>
                    <option value="Cantera / Filial">Canteras & Equipos B (España)</option>
                    <option value="Premier League">Premier League (Inglaterra)</option>
                    <option value="Bundesliga">Bundesliga (Alemania)</option>
                    <option value="Ligue 1">Ligue 1 (Francia)</option>
                    <option value="Serie A">Serie A (Italia)</option>
                    <option value="Resto del mundo">Resto del mundo (Otras Ligas)</option>
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

            <!-- Floating "show filters" button (visible when sidebar is hidden) -->
            <button id="btn-show-sidebar" onclick="toggleSidebar()" class="absolute top-4 left-4 z-20 bg-slate-900/90 text-slate-200 hover:text-white hover:bg-slate-800 text-xs font-bold px-3 py-2 rounded-xl shadow-lg border border-slate-850 flex items-center gap-1.5 transition">
                <span>⚡ Mostrar Filtros</span>
            </button>

            <!-- Loading Overlay -->
            <div id="loading-overlay" class="absolute inset-0 bg-slate-950/90 flex items-center justify-center z-40 transition-all duration-300">
                <div class="flex flex-col items-center gap-3">
                    <div class="w-10 h-10 border-4 border-violet-500 border-t-transparent rounded-full animate-spin"></div>
                    <span class="text-xs text-slate-300 font-medium">Cargando mapa interactivo de traspasos...</span>
                </div>
            </div>

            <!-- Vis.js Canvas -->
            <div id="network-canvas" class="w-full h-full"></div>

            <!-- Chrome flotante del Modo Enfoque: badge de contexto + salida.
                 Ambos los muestra/oculta updateFocusChrome() en network.js. -->
            <div class="absolute top-4 right-4 z-20 flex flex-col items-end gap-2 pointer-events-none">
                <div id="focus-badge" class="hidden pointer-events-auto bg-cyan-950/90 backdrop-blur text-cyan-100 text-[11px] font-semibold px-3 py-1.5 rounded-xl border border-cyan-500/50 shadow-lg max-w-[70vw] truncate"></div>
                <button id="btn-clear-focus" onclick="clearFocus()" title="Salir del enfoque (Esc)"
                        class="hidden pointer-events-auto bg-cyan-600 hover:bg-cyan-500 active:scale-95 text-white text-xs font-bold px-4 py-2 rounded-xl shadow-lg border border-cyan-400 flex items-center gap-2 transition">
                    <span>✕ Ver todo el grafo</span>
                    <kbd class="hidden md:inline bg-cyan-800/80 border border-cyan-400/60 rounded px-1.5 py-0.5 text-[9px] font-bold">Esc</kbd>
                </button>
            </div>

            <!-- Toast global de feedback -->
            <div id="app-toast" role="status" aria-live="polite"
                 class="hidden opacity-0 translate-y-2 absolute top-4 left-1/2 -translate-x-1/2 z-40 bg-slate-900/95 backdrop-blur text-slate-100 text-[11px] font-semibold px-4 py-2.5 rounded-xl border border-violet-500/50 shadow-2xl max-w-[85%] text-center transition-all duration-300"></div>

            <!-- Bottom Floating Star Transfers Bar -->
            <div class="absolute bottom-4 left-4 right-4 md:left-6 md:right-auto z-10 bg-slate-900/90 px-4 py-2 rounded-2xl flex items-center gap-3 border border-slate-800 shadow-xl max-w-full md:max-w-xl overflow-x-auto">
                <span class="text-[10px] font-bold uppercase tracking-wider text-amber-400 whitespace-nowrap">⭐ Fichajes Estrella:</span>
                <div class="flex items-center gap-2" id="star-transfers-container"></div>
            </div>
        </main>

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
                    <div class="flex flex-col gap-1 mt-1 border-t border-slate-800 pt-2 text-[11px]">
                        <span class="text-slate-400">Club Vendedor:</span>
                        <span class="font-bold text-slate-200" id="player-card-seller">Chelsea</span>
                        <span class="text-slate-400 mt-1.5">Club Comprador:</span>
                        <span class="font-bold text-slate-200" id="player-card-buyer">Real Madrid</span>
                    </div>
                </div>

                <!-- Transfers Lists (Shown for Clubs) -->
                <div id="drawer-transfers-container" class="flex flex-col gap-3 flex-1 overflow-y-auto max-h-[45vh] pr-1">
                    <div>
                        <span class="text-[10px] font-extrabold uppercase tracking-wider text-emerald-400 mb-1.5 block">Altas:</span>
                        <div class="flex flex-col gap-1.5" id="detail-arrivals-list"></div>
                    </div>
                    <div>
                        <span class="text-[10px] font-extrabold uppercase tracking-wider text-red-400 mb-1.5 block">Bajas:</span>
                        <div class="flex flex-col gap-1.5" id="detail-departures-list"></div>
                    </div>
                </div>
            </div>
        </aside>
    </div>

    <!-- Modal: Analytics -->
    <div id="modal-analytics" class="hidden fixed inset-0 bg-slate-950/80 backdrop-blur-md flex items-center justify-center z-50 p-3 md:p-4">
        <div class="bg-slate-900 w-full max-w-6xl max-h-[94vh] overflow-y-auto rounded-3xl p-5 md:p-6 flex flex-col gap-5 border border-slate-800 shadow-2xl">
            <div class="flex justify-between items-start gap-3 border-b border-slate-800 pb-3">
                <div class="flex flex-col gap-1">
                    <h2 class="text-lg font-bold text-violet-400 flex items-center gap-2 flex-wrap">
                        <span>&#128202; Analytics &amp; SNA Hub</span>
                        <span class="text-[10px] bg-violet-950 border border-violet-800/80 text-violet-300 font-bold px-2 py-0.5 rounded-full uppercase">Project 3 &middot; Social Network Analysis</span>
                    </h2>
                    <span class="text-[10px] text-slate-500">Todas las medidas se calculan en vivo sobre la red cargada (simplificaci&oacute;n no dirigida <i>U</i>), igual que en NetworkX.</span>
                </div>
                <button onclick="closeAnalyticsModal()" class="text-slate-400 hover:text-white p-1 rounded-lg bg-slate-950 shrink-0">&#10005;</button>
            </div>

            <!-- KPIs -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-2.5">
                <div class="bg-slate-950 p-3 rounded-2xl border border-slate-800 text-center">
                    <span class="block text-2xl font-black text-violet-300" id="stat-avg-path">3.11</span>
                    <span class="text-[9px] uppercase font-bold tracking-wider text-slate-400">Camino promedio</span>
                </div>
                <div class="bg-slate-950 p-3 rounded-2xl border border-slate-800 text-center">
                    <span class="block text-2xl font-black text-cyan-300" id="stat-diameter">5</span>
                    <span class="text-[9px] uppercase font-bold tracking-wider text-slate-400">Di&aacute;metro</span>
                </div>
                <div class="bg-slate-950 p-3 rounded-2xl border border-slate-800 text-center">
                    <span class="block text-2xl font-black text-emerald-300" id="stat-transitivity">0.087</span>
                    <span class="text-[9px] uppercase font-bold tracking-wider text-slate-400">Transitividad global</span>
                </div>
                <div class="bg-slate-950 p-3 rounded-2xl border border-slate-800 text-center">
                    <span class="block text-2xl font-black text-amber-300" id="stat-auc">0.725</span>
                    <span class="text-[9px] uppercase font-bold tracking-wider text-slate-400">AUC predicci&oacute;n</span>
                </div>
            </div>

            <!-- 1. Caracteristicas basicas -->
            <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800 flex flex-col gap-3">
                <div class="flex items-center justify-between gap-2 flex-wrap">
                    <span class="text-xs font-bold text-slate-200">1. Caracter&iacute;sticas b&aacute;sicas de la red</span>
                    <span class="text-[9px] bg-slate-900 border border-slate-800 text-slate-400 font-bold px-2 py-0.5 rounded-full uppercase">Basic Measures</span>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-[11px] border-collapse">
                        <thead>
                            <tr class="text-[9px] uppercase tracking-wider text-slate-500 border-b border-slate-800">
                                <th class="text-left pb-1.5 font-bold">M&eacute;trica</th>
                                <th class="text-right pb-1.5 font-bold">Valor</th>
                                <th class="text-left pb-1.5 font-bold hidden sm:table-cell">Interpretaci&oacute;n</th>
                            </tr>
                        </thead>
                        <tbody id="tbl-basic-measures"></tbody>
                    </table>
                </div>
                <div class="bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/50 text-[10px] leading-relaxed text-slate-400" id="basic-measures-insight"></div>
            </div>

            <!-- 2 y 3. Distribucion de grados -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800 flex flex-col gap-2">
                    <span class="text-xs font-bold text-slate-200">2. Distribuci&oacute;n de grados P(k)</span>
                    <div class="h-48 w-full"><canvas id="chart-degree"></canvas></div>
                    <div class="bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/50 text-[10px] leading-relaxed text-slate-400">
                        <span class="text-violet-400 font-bold block mb-0.5">&#128204; Lectura:</span>
                        Distribuci&oacute;n sesgada a la derecha: la mayor&iacute;a de clubes tiene pocos socios comerciales y unos cuantos hubs concentran el volumen. <b>Esper&aacute;bamos</b> dominio de hubs y se confirma.
                    </div>
                </div>
                <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800 flex flex-col gap-2">
                    <span class="text-xs font-bold text-slate-200">3. Misma distribuci&oacute;n en escala log&ndash;log</span>
                    <div class="h-48 w-full"><canvas id="chart-degree-loglog"></canvas></div>
                    <div class="bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/50 text-[10px] leading-relaxed text-slate-400">
                        <span class="text-violet-400 font-bold block mb-0.5">&#128204; Lectura:</span>
                        En log&ndash;log una ley de potencias ser&iacute;a una recta. Aqu&iacute; la tendencia es de <b>cola pesada pero no una power-law limpia</b>: es m&aacute;s honesto reportarlo as&iacute; que forzar el ajuste.
                    </div>
                </div>
            </div>

            <!-- 4. Centralidad -->
            <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800 flex flex-col gap-3">
                <div class="flex items-center justify-between gap-2 flex-wrap">
                    <span class="text-xs font-bold text-slate-200">4. Centralidad: qui&eacute;n mueve m&aacute;s y qui&eacute;n conecta</span>
                    <span class="text-[9px] bg-slate-900 border border-slate-800 text-slate-400 font-bold px-2 py-0.5 rounded-full uppercase">Grado &middot; Betweenness &middot; PageRank</span>
                </div>
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div class="h-52 w-full"><canvas id="chart-betweenness"></canvas></div>
                    <div class="overflow-x-auto">
                        <table class="w-full text-[10.5px] border-collapse">
                            <thead>
                                <tr class="text-[9px] uppercase tracking-wider text-slate-500 border-b border-slate-800">
                                    <th class="text-left pb-1.5 font-bold">#</th>
                                    <th class="text-left pb-1.5 font-bold">Mayor grado</th>
                                    <th class="text-left pb-1.5 font-bold">Mayor intermediaci&oacute;n</th>
                                    <th class="text-left pb-1.5 font-bold">Mayor PageRank</th>
                                </tr>
                            </thead>
                            <tbody id="tbl-centrality"></tbody>
                        </table>
                    </div>
                </div>
                <div class="bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/50 text-[10px] leading-relaxed text-slate-400" id="centrality-insight"></div>
            </div>

            <!-- 5 y 6. Composicion + financiero -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800 flex flex-col gap-2">
                    <span class="text-xs font-bold text-slate-200">5. Composici&oacute;n por divisi&oacute;n y homofilia</span>
                    <div class="h-44 w-full"><canvas id="chart-divisions"></canvas></div>
                    <div class="flex items-baseline gap-2 justify-center">
                        <span class="text-2xl font-black text-emerald-400" id="stat-assortativity">-0.1123</span>
                        <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Asortatividad por divisi&oacute;n</span>
                    </div>
                    <div class="bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/50 text-[10px] leading-relaxed text-slate-400" id="assortativity-insight"></div>
                </div>
                <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800 flex flex-col gap-2">
                    <span class="text-xs font-bold text-slate-200">6. Volumen financiero por club (M&euro;)</span>
                    <div class="h-52 w-full"><canvas id="chart-financials"></canvas></div>
                    <div class="bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/50 text-[10px] leading-relaxed text-slate-400" id="financial-insight"></div>
                </div>
            </div>

            <!-- 7. Prediccion de enlaces -->
            <div class="bg-slate-950 p-4 rounded-2xl border border-violet-900/60 flex flex-col gap-3">
                <div class="flex items-center justify-between gap-2 flex-wrap">
                    <span class="text-xs font-bold text-violet-200">7. Predicci&oacute;n de enlaces &mdash; &iquest;qu&eacute; traspaso falta por ocurrir?</span>
                    <span class="text-[9px] bg-violet-950 border border-violet-800/80 text-violet-300 font-bold px-2 py-0.5 rounded-full uppercase">Link Prediction</span>
                </div>
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div class="h-56 w-full"><canvas id="chart-linkpred"></canvas></div>
                    <div class="flex flex-col gap-3">
                        <div class="overflow-x-auto">
                            <table class="w-full text-[10.5px] border-collapse">
                                <thead>
                                    <tr class="text-[9px] uppercase tracking-wider text-slate-500 border-b border-slate-800">
                                        <th class="text-left pb-1.5 font-bold">Medida</th>
                                        <th class="text-left pb-1.5 font-bold">Par predicho (sin traspaso previo)</th>
                                        <th class="text-right pb-1.5 font-bold">Score</th>
                                    </tr>
                                </thead>
                                <tbody id="tbl-linkpred"></tbody>
                            </table>
                        </div>
                        <div class="grid grid-cols-2 gap-2.5">
                            <div class="bg-slate-900/80 p-2.5 rounded-xl border border-slate-800 text-center">
                                <span class="block text-xl font-black text-violet-300" id="stat-precision50">14.0%</span>
                                <span class="text-[9px] uppercase font-bold tracking-wider text-slate-400">Precision@50</span>
                            </div>
                            <div class="bg-slate-900/80 p-2.5 rounded-xl border border-slate-800 text-center">
                                <span class="block text-sm font-black text-amber-300 leading-tight pt-1.5" id="stat-lp-hidden">156 aristas ocultas (20%)</span>
                                <span class="text-[9px] uppercase font-bold tracking-wider text-slate-400">Validaci&oacute;n hold-out</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/50 text-[10px] leading-relaxed text-slate-400" id="linkpred-insight"></div>
            </div>
        </div>
    </div>

    <!-- Modal: Shortest Path -->
    <div id="modal-path" class="hidden fixed inset-0 bg-slate-950/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
        <div class="bg-slate-900 w-full max-w-2xl rounded-3xl p-6 flex flex-col gap-4 border border-slate-800 shadow-2xl">
            <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                <h2 class="text-lg font-bold text-violet-400">🔍 Buscador de Camino Más Corto (Algoritmo BFS)</h2>
                <button onclick="closePathModal()" class="text-slate-400 hover:text-white p-1 rounded-lg bg-slate-950">✕</button>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="text-xs text-slate-400 mb-1 block">Club Origen</label>
                    <select id="path-select-from" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white"></select>
                </div>
                <div>
                    <label class="text-xs text-slate-400 mb-1 block">Club Destino</label>
                    <select id="path-select-to" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white"></select>
                </div>
            </div>
            <button onclick="calculateShortestPath()" class="w-full bg-violet-600 hover:bg-violet-500 text-white font-bold py-2.5 rounded-xl text-xs shadow transition">
                Calcular Ruta Óptima de Traspaso
            </button>
            <div id="path-result-box" class="hidden bg-slate-950 p-4 rounded-2xl border border-slate-800 text-xs text-slate-200"></div>
        </div>
    </div>

    <!-- Modal: Guide/Help -->
    <div id="modal-guide" class="hidden fixed inset-0 bg-slate-950/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
        <div class="bg-slate-900 w-full max-w-2xl rounded-3xl p-6 flex flex-col gap-4 border border-slate-800 shadow-2xl max-h-[85vh] overflow-y-auto">
            <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                <h2 class="text-lg font-bold text-amber-400">💡 Guía Rápida & Conceptos de Redes</h2>
                <button onclick="closeGuideModal()" class="text-slate-400 hover:text-white p-1 rounded-lg bg-slate-950">✕</button>
            </div>
            <div class="text-xs text-slate-300 flex flex-col gap-3 leading-relaxed">
                <div>
                    <span class="text-violet-400 font-bold text-sm block">1. ¿Qué representa la red?</span>
                    Es el mercado de fichajes de fútbol de España (Primera, Segunda, canteras) e internacional (Inglaterra, Italia, Alemania, Francia, etc.) entre 2025 y 2027. Los nodos son los clubes y las aristas son las transferencias de los jugadores.
                </div>
                <div>
                    <span class="text-violet-400 font-bold text-sm block">2. Conceptos de Centralidad (SNA)</span>
                    <ul class="list-disc pl-4 flex flex-col gap-1 mt-1">
                        <li><b>Grado (Degree):</b> Suma de entradas y salidas de jugadores. Destaca a los clubes más activos transaccionalmente.</li>
                        <li><b>Intermediación (Betweenness):</b> Mide cuántas veces un club está en la ruta más corta entre otros dos clubes. Un alto valor indica que el club funciona como un "puente" o intermediario estratégico.</li>
                        <li><b>PageRank:</b> Mide el prestigio o relevancia del club basándose en la calidad de sus conexiones dirigidas.</li>
                    </ul>
                </div>
                <div>
                    <span class="text-violet-400 font-bold text-sm block">3. Modos de Vista</span>
                    <ul class="list-disc pl-4 flex flex-col gap-1 mt-1">
                        <li><b>Solo Clubes:</b> Vista macro ponderada. Cada línea representa el flujo de jugadores entre clubes.</li>
                        <li><b>Clubes + Jugadores:</b> Vista micro. Los jugadores se muestran como diamantes amarillos conectados individualmente a su club de origen y club de destino.</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal: What-If Simulator -->
    <div id="modal-whatif" class="hidden fixed inset-0 bg-slate-950/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
        <div class="bg-slate-900 w-full max-w-2xl rounded-3xl p-6 flex flex-col gap-4 border border-slate-800 shadow-2xl">
            <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                <h2 class="text-lg font-bold text-cyan-400">🧪 Simulador de Fichajes "What-If"</h2>
                <button onclick="closeWhatIfModal()" class="text-slate-400 hover:text-white p-1 rounded-lg bg-slate-950">✕</button>
            </div>
            <div class="text-xs text-slate-300 leading-relaxed -mt-1">
                Simula el impacto de un fichaje hipotético en el mercado actual para ver cómo se conectan y re-ordenan las centralidades de red de forma predictiva.
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="text-xs text-slate-400 mb-1 block">Club Vendedor</label>
                    <select id="whatif-select-from" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white"></select>
                </div>
                <div>
                    <label class="text-xs text-slate-400 mb-1 block">Club Comprador</label>
                    <select id="whatif-select-to" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white"></select>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="text-xs text-slate-400 mb-1 block">Nombre del Jugador</label>
                    <input type="text" id="whatif-player-name" placeholder="Ej. Kylian Mbappé" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-white focus:outline-none">
                </div>
                <div>
                    <label class="text-xs text-slate-400 mb-1 block">Coste Hipotético (€ Millones)</label>
                    <input type="number" id="whatif-player-cost" placeholder="Ej. 120" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-white focus:outline-none">
                </div>
            </div>
            <button onclick="simulateWhatIfTransfer()" class="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-bold py-2.5 rounded-xl text-xs shadow transition">
                Insertar Simulación y Recalcular Centralidad
            </button>
            <div id="whatif-result-box" class="hidden bg-slate-950 p-4 rounded-2xl border border-slate-800 text-xs text-slate-200"></div>
        </div>
    </div>

    <!-- Modal: Compare -->
    <div id="modal-compare" class="hidden fixed inset-0 bg-slate-950/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
        <div class="bg-slate-900 w-full max-w-4xl max-h-[92vh] overflow-y-auto rounded-3xl p-6 flex flex-col gap-4 border border-slate-800 shadow-2xl">
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
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2" id="compare-cards-container"></div>
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
                    <tr><td class="border border-slate-800 p-2 font-bold">Tamaño Nodos / Aristas</td><td class="border border-slate-800 p-2" id="ficha-node-edge-summary">338 nodos de clubes (1138 total heterogéneo), 936 traspasos</td></tr>
                </table>
            </div>
        </div>
    </div>

    <!-- Scripts: ui.js y network.js definen funciones globales; main.js hace el fetch y arranca la app -->
    <script src="assets/js/ui.js?v=__ASSET_VERSION__" defer></script>
    <script src="assets/js/network.js?v=__ASSET_VERSION__" defer></script>
    <script src="assets/js/main.js?v=__ASSET_VERSION__" defer></script>
</body>
</html>
"""

    # Sella la versión de los assets: se toma de APP_VERSION en main.js si existe
    # (así HTML y fetch de datos comparten el mismo sufijo) y si no, de la fecha.
    html_content = html_content.replace("__ASSET_VERSION__", resolve_asset_version(docs_dir))

    index_path = os.path.join(docs_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)


def resolve_asset_version(docs_dir):
    """Devuelve el sufijo de cache-busting: APP_VERSION de main.js o la fecha de hoy."""
    main_js = os.path.join(docs_dir, "assets", "js", "main.js")
    if os.path.exists(main_js):
        with open(main_js, "r", encoding="utf-8") as f:
            m = re.search(r"const\s+APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", f.read())
            if m:
                return m.group(1)
    return datetime.date.today().strftime("%Y%m%d")


def write_monolithic_html(docs_dir, club_nodes, club_edges, hetero_nodes, hetero_edges, club_stats, star_transfers, meta):
    """Genera transfer_market_graph.html: la versión autónoma monolítica sin dependencias locales de archivos."""
    index_path = os.path.join(docs_dir, "index.html")
    if not os.path.exists(index_path):
        return

    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Read CSS contents
    css_app_path = os.path.join(docs_dir, "assets", "css", "app.css")
    css_custom_path = os.path.join(docs_dir, "assets", "css", "custom.css")
    
    css_app_content = ""
    if os.path.exists(css_app_path):
        with open(css_app_path, "r", encoding="utf-8") as f:
            css_app_content = f.read()
            
    css_custom_content = ""
    if os.path.exists(css_custom_path):
        with open(css_custom_path, "r", encoding="utf-8") as f:
            css_custom_content = f.read()

    # Replace CSS file links with inline <style> tags
    style_app = f"<style>\n{css_app_content}\n</style>"
    style_custom = f"<style>\n{css_custom_content}\n</style>"
    
    # El (?:\?[^"]*)? tolera el sufijo de cache-busting ?v=...
    html = re.sub(r'<link\s+href="assets/css/app\.css(?:\?[^"]*)?"\s+rel="stylesheet">', lambda _: style_app, html)
    html = re.sub(r'<link\s+href="assets/css/custom\.css(?:\?[^"]*)?"\s+rel="stylesheet">', lambda _: style_custom, html)

    # Inject CDN Chart.js since it will be inlined in the document
    chart_js_script = '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'
    html = html.replace('</head>', f'{chart_js_script}\n</head>')

    # Use unpkg CDN for vis-network in monolithic mode to make it fully standalone and CORS-free.
    # Remove defer so it loads synchronously before the inline scripts execute.
    html = html.replace('<script type="text/javascript" src="assets/js/vendor/vis-network.min.js" defer></script>',
                        '<script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>')

    # Read JS contents
    js_ui_path = os.path.join(docs_dir, "assets", "js", "ui.js")
    js_network_path = os.path.join(docs_dir, "assets", "js", "network.js")
    js_main_path = os.path.join(docs_dir, "assets", "js", "main.js")
    js_charts_path = os.path.join(docs_dir, "assets", "js", "charts.js")

    js_ui = ""
    if os.path.exists(js_ui_path):
        with open(js_ui_path, "r", encoding="utf-8") as f:
            js_ui = f.read()
            
    js_network = ""
    if os.path.exists(js_network_path):
        with open(js_network_path, "r", encoding="utf-8") as f:
            js_network = f.read()
            
    js_main = ""
    if os.path.exists(js_main_path):
        with open(js_main_path, "r", encoding="utf-8") as f:
            js_main = f.read()
            
    js_charts = ""
    if os.path.exists(js_charts_path):
        with open(js_charts_path, "r", encoding="utf-8") as f:
            js_charts = f.read()

    # Create the inline dataset scripts, avoiding variable name redeclaration errors in main.js
    data_block = f"""
    <script>
        // Monolithic Inline Datasets
        const _INLINE_CLUB_NODES = {json.dumps(club_nodes, ensure_ascii=False)};
        const _INLINE_CLUB_EDGES = {json.dumps(club_edges, ensure_ascii=False)};
        const _INLINE_HETERO_NODES = {json.dumps(hetero_nodes, ensure_ascii=False)};
        const _INLINE_HETERO_EDGES = {json.dumps(hetero_edges, ensure_ascii=False)};
        const _INLINE_CLUB_STATS = {json.dumps(club_stats, ensure_ascii=False)};
        const _INLINE_STAR_TRANSFERS = {json.dumps(star_transfers, ensure_ascii=False)};
        const _INLINE_META = {json.dumps(meta, ensure_ascii=False)};

        // Override fetchJSON to resolve directly with monolithic inlined data (CORS free!)
        async function fetchJSON(path) {{
            if (path.includes('clubs-network.json')) return {{ nodes: _INLINE_CLUB_NODES, edges: _INLINE_CLUB_EDGES }};
            if (path.includes('hetero-network.json')) return {{ nodes: _INLINE_HETERO_NODES, edges: _INLINE_HETERO_EDGES }};
            if (path.includes('club-stats.json')) return _INLINE_CLUB_STATS;
            if (path.includes('star-transfers.json')) return _INLINE_STAR_TRANSFERS;
            if (path.includes('meta.json')) return _INLINE_META;
            throw new Error('Unknown JSON request in standalone mode: ' + path);
        }}
        window.fetchJSON = fetchJSON;

        // Force loaded state immediately in standalone mode
        window.ensureHeteroDataLoaded = async function() {{
            window.heteroNodes = _INLINE_HETERO_NODES;
            window.heteroEdges = _INLINE_HETERO_EDGES;
            window.heteroDataLoaded = true;
            return Promise.resolve();
        }};
        window.loadChartsModuleAndRender = async function() {{
            window.chartsModuleLoaded = true;
            if (typeof renderAnalyticsCharts === 'function') renderAnalyticsCharts();
            return Promise.resolve();
        }};
    </script>
    """

    # Remove script links to local assets
    script_pattern = r'<script\s+src="assets/js/(ui|network|main)\.js(?:\?[^"]*)?"\s+defer></script>'
    html = re.sub(script_pattern, '', html)

    # Clean js_main to prevent shadowing/overwriting of mocked functions
    js_main_clean = js_main
    js_main_clean = re.sub(r'async\s+function\s+fetchJSON\b', 'async function _original_fetchJSON', js_main_clean)
    js_main_clean = re.sub(r'async\s+function\s+ensureHeteroDataLoaded\b', 'async function _original_ensureHeteroDataLoaded', js_main_clean)
    js_main_clean = re.sub(r'async\s+function\s+loadChartsModuleAndRender\b', 'async function _original_loadChartsModuleAndRender', js_main_clean)

    # Inline all scripts in dependency order
    inlined_js = f"""
    {data_block}
    <script>
    // --- ui.js ---
    {js_ui}
    
    // --- network.js ---
    {js_network}
    
    // --- charts.js ---
    {js_charts}
    
    // --- main.js ---
    {js_main_clean}
    </script>
    """
    
    html = html.replace('</body>', f'{inlined_js}\n</body>')

    monolithic_path = "transfer_market_graph.html"
    with open(monolithic_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Stand-alone monolithic dashboard generated at {monolithic_path}!")


if __name__ == "__main__":
    main()
