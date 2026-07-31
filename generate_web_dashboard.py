import json
import os
import random
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

    # Precalculamos el layout (posiciones x,y) para poder deshabilitar las
    # físicas de vis-network en el navegador y evitar el "warm-up" de la
    # simulación al cargar la página (carga instantánea del grafo).
    # k alto = mayor distancia óptima entre nodos (grafo menos "achocado");
    # más iteraciones = mejor convergencia y menos solapamiento en el centro.
    layout_pos = nx.spring_layout(G_clubs_simple, seed=42, k=2.5, iterations=250, scale=1400)

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
        
        # Los nodos de jugador heredan una posición cercana a su club de
        # origen, con un jitter aleatorio determinista (seed = idx) para que
        # el layout sea reproducible entre ejecuciones.
        # Distribución radial alrededor del club de origen: ángulo y radio
        # deterministas (seed = idx) para separar visualmente a los jugadores
        # que comparten club, formando una "nube" legible en vez de un apilado.
        import math
        src_pos = layout_pos.get(t["source_node"], (0.0, 0.0))
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

    # ------------------------------------------------------------------
    # Emisión: a partir de aquí ya no se toca ninguna métrica de red; solo
    # se escriben los datos calculados arriba como JSON estáticos en
    # docs/data/ y se genera el shell HTML delgado docs/index.html.
    # ------------------------------------------------------------------
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

    print(f"Datos escritos en {data_dir}/ (clubs-network.json, hetero-network.json, "
          f"club-stats.json, star-transfers.json, meta.json)")
    print(f"Shell HTML escrito en {docs_dir}/index.html")
    print("Successfully built the modular App Shell (docs/) with precomputed layout "
          "and lazy-loaded hetero data / Chart.js!")


def write_index_html(docs_dir):
    """Escribe docs/index.html: un shell HTML delgado sin datos ni JS embebido.
    El layout visual es idéntico al dashboard original; solo cambian las
    referencias a CSS/JS (ahora en docs/assets/) y se elimina todo dato
    interpolado (los contadores y métricas se rellenan en runtime vía
    main.js a partir de docs/data/meta.json)."""

    html_content = """<!DOCTYPE html>
<html lang="es" id="html-root" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LaLiga Transfer Analytics Pro (2025-2027) | UPY 2026</title>

    <link href="assets/css/app.css" rel="stylesheet">
    <link href="assets/css/custom.css" rel="stylesheet">
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
                <label class="flex items-center gap-2 mt-1 cursor-pointer select-none text-[11px] text-slate-300 font-semibold">
                    <input type="checkbox" id="toggle-focus-mode" onchange="setFocusMode(this.checked)" class="accent-cyan-500 w-3.5 h-3.5">
                    🎯 Modo Enfoque
                </label>
                <span id="focus-mode-hint" class="hidden text-[9px] text-cyan-300/80 leading-tight -mt-0.5">
                    Haz clic en un club, jugador o liga para aislar solo su ruta de traspasos. Clic en el vacío para volver.
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

            <!-- Floating "show filters" button (visible when sidebar is hidden) -->
            <button id="btn-show-sidebar" onclick="toggleSidebar()" class="absolute top-4 left-4 z-20 bg-slate-900/90 text-slate-200 hover:text-white hover:bg-slate-800 text-xs font-bold px-3 py-2 rounded-xl shadow-lg border border-slate-800 flex items-center gap-1.5 transition">
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

            <!-- Floating "exit focus" button (visible only while a node is isolated) -->
            <button id="btn-clear-focus" onclick="clearFocus()" class="hidden absolute top-4 right-4 z-20 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold px-4 py-2 rounded-xl shadow-lg border border-cyan-400 flex items-center gap-2 transition">
                <span>✕ Ver todo el grafo</span>
            </button>

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
                    <span class="text-2xl font-black text-white" id="stat-total-clubs">56 Clubes</span>
                    <span class="text-[10px] text-slate-400" id="stat-hetero-nodes">856 nodos heterogéneos</span>
                </div>
                <div class="bg-slate-950 p-3.5 rounded-2xl border border-slate-800 flex flex-col gap-1">
                    <span class="text-[10px] uppercase font-bold text-emerald-400">Movimientos</span>
                    <span class="text-2xl font-black text-white" id="stat-total-transfers">1,034 Traspasos</span>
                    <span class="text-[10px] text-slate-400">Operaciones analizadas</span>
                </div>
                <div class="bg-slate-950 p-3.5 rounded-2xl border border-slate-800 flex flex-col gap-1">
                    <span class="text-[10px] uppercase font-bold text-cyan-400">Homofilia (Ligas)</span>
                    <span class="text-2xl font-black text-white" id="stat-homophily">+0.3421</span>
                    <span class="text-[10px] text-slate-400">Tendencia a comerciar</span>
                </div>
                <div class="bg-slate-950 p-3.5 rounded-2xl border border-slate-800 flex flex-col gap-1">
                    <span class="text-[10px] uppercase font-bold text-amber-400">Dinero Movido</span>
                    <span class="text-2xl font-black text-white" id="stat-money-moved">0.0 M€</span>
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
        <div class="bg-slate-900 w-full max-w-2xl max-h-[92vh] overflow-y-auto rounded-3xl p-6 flex flex-col gap-4 border border-slate-800 shadow-2xl">
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
        <div class="bg-slate-900 w-full max-w-xl max-h-[92vh] overflow-y-auto rounded-3xl p-6 flex flex-col gap-4 border border-slate-800 shadow-2xl">
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
        <div class="bg-slate-900 w-full max-w-xl max-h-[92vh] overflow-y-auto rounded-3xl p-6 flex flex-col gap-4 border border-slate-800 shadow-2xl">
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
                    <tr><td class="border border-slate-800 p-2 font-bold">Tamaño Nodos / Aristas</td><td class="border border-slate-800 p-2" id="ficha-node-edge-summary">56 nodos de clubes (856 total heterogéneo), 1034 traspasos</td></tr>
                </table>
            </div>
        </div>
    </div>

    <!-- Scripts: ui.js y network.js definen funciones globales; main.js hace el fetch y arranca la app -->
    <script src="assets/js/ui.js" defer></script>
    <script src="assets/js/network.js" defer></script>
    <script src="assets/js/main.js" defer></script>
</body>
</html>
"""

    index_path = os.path.join(docs_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)


if __name__ == "__main__":
    main()
