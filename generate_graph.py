import json
import os
import sys
import subprocess
import re

# Self-install dependencies if missing
for lib in ["networkx", "matplotlib"]:
    try:
        __import__(lib)
    except ImportError:
        print(f"Installing {lib}...")
        subprocess.run([sys.executable, "-m", "pip", "install", lib], check=True)

import networkx as nx

try:
    import networkx.algorithms.community as nx_comm
except ImportError:
    try:
        import networkx.community as nx_comm
    except ImportError:
        nx_comm = None

import matplotlib.pyplot as plt

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

def clean_cost(cost_str):
    if not cost_str:
        return 0.0
    cost_str_clean = cost_str.lower().strip()
    if "gratis" in cost_str_clean or "libre" in cost_str_clean or "cesión" in cost_str_clean or "regreso" in cost_str_clean or "fin de contrato" in cost_str_clean:
        return 0.0
    
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
        
    print(f"Loaded {len(transfers)} transfers from dataset.")
    
    G_clubs = nx.MultiDiGraph()
    G_clubs_weighted = nx.DiGraph()
    financials = {}
    cantera_transfers = []
    
    for league in EXTERNAL_LEAGUES:
        G_clubs.add_node(league, type="external_league", division="None", label=league)
        G_clubs_weighted.add_node(league, type="external_league", division="None", label=league)
        financials[league] = {"spent_m": 0.0, "earned_m": 0.0, "arrivals": 0, "departures": 0}
        
    for t in transfers:
        source = t["source_node"]
        target = t["target_node"]
        player = t["player"]
        cost_val = clean_cost(t["cost"])
        
        # Check if cantera / filial transfer
        if " b" in source.lower() or " b" in target.lower() or "ii" in source.lower() or "ii" in target.lower():
            cantera_transfers.append(t)
            
        for node in [source, target]:
            if node not in financials:
                financials[node] = {"spent_m": 0.0, "earned_m": 0.0, "arrivals": 0, "departures": 0}
        
        financials[source]["earned_m"] += cost_val
        financials[source]["departures"] += 1
        financials[target]["spent_m"] += cost_val
        financials[target]["arrivals"] += 1
        
        for node in [source, target]:
            div_str = "None" if node in EXTERNAL_LEAGUES else ("1" if node in DIVISION_1 else "2")
            node_type = "external_league" if node in EXTERNAL_LEAGUES else ("filial" if " B" in node or " II" in node else "club")
            
            if not G_clubs.has_node(node):
                G_clubs.add_node(node, type=node_type, division=div_str, label=node)
            if not G_clubs_weighted.has_node(node):
                G_clubs_weighted.add_node(node, type=node_type, division=div_str, label=node)
                
        G_clubs.add_edge(
            source, target,
            player=player,
            age=t["age"] or 0,
            cost_raw=t["cost"],
            cost_millions=cost_val,
            season=t["season"]
        )
        
        if G_clubs_weighted.has_edge(source, target):
            G_clubs_weighted[source][target]["weight"] += 1
            G_clubs_weighted[source][target]["cost_millions"] += cost_val
            G_clubs_weighted[source][target]["players"].append(player)
        else:
            G_clubs_weighted.add_edge(
                source, target,
                weight=1,
                cost_millions=cost_val,
                players=[player]
            )

    # Heterogeneous Graph
    G_hetero = nx.DiGraph()
    for league in EXTERNAL_LEAGUES:
        G_hetero.add_node(league, type="external_league", division="None", label=league)
        
    for t in transfers:
        source = t["source_node"]
        target = t["target_node"]
        player = t["player"]
        cost_val = clean_cost(t["cost"])
        
        for node in [source, target]:
            if not G_hetero.has_node(node):
                div_str = "None" if node in EXTERNAL_LEAGUES else ("1" if node in DIVISION_1 else "2")
                node_type = "external_league" if node in EXTERNAL_LEAGUES else ("filial" if " B" in node or " II" in node else "club")
                G_hetero.add_node(node, type=node_type, division=div_str, label=node)
                
        player_node_id = f"Player: {player}"
        G_hetero.add_node(
            player_node_id,
            type="player",
            division="None",
            label=player,
            age=t["age"] or 0,
            cost_raw=t["cost"],
            cost_millions=cost_val,
            season=t["season"]
        )
        G_hetero.add_edge(source, player_node_id, type="departure", season=t["season"], cost_millions=cost_val)
        G_hetero.add_edge(player_node_id, target, type="arrival", season=t["season"], cost_millions=cost_val)

    # Calculate Network Analysis Metrics
    G_clubs_simple = nx.DiGraph(G_clubs)
    
    in_degrees = dict(G_clubs.in_degree())
    out_degrees = dict(G_clubs.out_degree())
    total_degrees = dict(G_clubs.degree())
    
    betweenness = nx.betweenness_centrality(G_clubs_simple)
    closeness = nx.closeness_centrality(G_clubs_simple)
    
    try:
        pagerank = nx.pagerank(G_clubs_simple, alpha=0.85)
    except Exception:
        pagerank = {node: 0.0 for node in G_clubs_simple.nodes()}
        
    # Assortativity by division
    try:
        assortativity = nx.attribute_assortativity_coefficient(G_clubs_simple, "division")
    except Exception:
        assortativity = 0.0
        
    G_undirected = G_clubs_simple.to_undirected()
    communities_tuple = []
    if nx_comm and hasattr(nx_comm, "greedy_modularity_communities"):
        try:
            communities_tuple = list(nx_comm.greedy_modularity_communities(G_undirected))
        except Exception:
            communities_tuple = [set(G_undirected.nodes())]
    else:
        communities_tuple = [set(G_undirected.nodes())]
        
    community_map = {}
    for comm_id, comm_nodes in enumerate(communities_tuple, 1):
        for node in comm_nodes:
            community_map[node] = comm_id

    for node in G_clubs.nodes():
        G_clubs.nodes[node]["betweenness"] = betweenness.get(node, 0.0)
        G_clubs.nodes[node]["closeness"] = closeness.get(node, 0.0)
        G_clubs.nodes[node]["pagerank"] = pagerank.get(node, 0.0)
        G_clubs.nodes[node]["community"] = community_map.get(node, 1)
        G_clubs.nodes[node]["spent_m"] = financials.get(node, {}).get("spent_m", 0.0)
        G_clubs.nodes[node]["earned_m"] = financials.get(node, {}).get("earned_m", 0.0)

    for node in G_hetero.nodes():
        G_hetero.nodes[node]["community"] = community_map.get(node, 1) if node in community_map else 0

    nx.write_gexf(G_clubs, "la_liga_transfers_clubs_only.gexf")
    nx.write_gexf(G_hetero, "la_liga_transfers_heterogeneous.gexf")
    print("Exported enhanced GEXF graph files successfully.")

    top_in_degrees = sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)[:5]
    top_out_degrees = sorted(out_degrees.items(), key=lambda x: x[1], reverse=True)[:5]
    top_total_degrees = sorted(total_degrees.items(), key=lambda x: x[1], reverse=True)[:5]
    top_betweenness = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:5]
    top_closeness = sorted(closeness.items(), key=lambda x: x[1], reverse=True)[:5]
    top_pagerank = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[:5]
    top_spenders = sorted(financials.items(), key=lambda x: x[1]["spent_m"], reverse=True)[:5]
    top_earners = sorted(financials.items(), key=lambda x: x[1]["earned_m"], reverse=True)[:5]

    analysis_file = "network_analysis.md"
    with open(analysis_file, "w", encoding="utf-8") as f:
        f.write("# Ficha Técnica y Reporte de Análisis de Redes\n\n")
        f.write("Este documento contiene las métricas avanzadas y el análisis del mercado de fichajes de LaLiga (2025-2027) útil para completar la visualización y la ficha técnica A4.\n\n")
        
        f.write("## 1. Ficha Técnica General (Formato A4)\n\n")
        f.write("| Campo | Contenido |\n")
        f.write("| --- | --- |\n")
        f.write("| **Nombre de la red** | Red de Traspasos de LaLiga (2025-2027) |\n")
        f.write("| **Fuente** | Fichajes.com (Mercado Oficial de Fichajes) |\n")
        f.write(f"| **Tipo de Grafo** | Dirigido, Heterogéneo / Multígrafo Dirigido Ponderado |\n")
        f.write(f"| **Tamaño (Grafo Heterogéneo)** | {G_hetero.number_of_nodes()} nodos, {G_hetero.number_of_edges()} aristas |\n")
        f.write(f"| **Tamaño (Grafo Clubes)** | {G_clubs.number_of_nodes()} nodos, {G_clubs.number_of_edges()} traspasos ({G_clubs_weighted.number_of_edges()} enlaces únicos) |\n")
        f.write(f"| **Coeficiente de Homofilia (División)** | {assortativity:.4f} |\n")
        f.write(f"| **Número de Comunidades (Louvain/Greedy)** | {len(communities_tuple)} comunidades detectadas |\n")
        f.write(f"| **Traspasos de Cantera (Equipos B)** | {len(cantera_transfers)} movimientos detectados |\n")
        f.write("| **Herramientas utilizadas** | Python, BeautifulSoup4, NetworkX, Gephi, Vis.js, Chart.js |\n\n")
        
        f.write("## 2. Métricas de Centralidad SNA\n\n")
        f.write("### Nodos con Mayor Grado Total\n")
        for rank, (club, deg) in enumerate(top_total_degrees, 1):
            f.write(f"{rank}. **{club}** (Grado: {deg})\n")
            
        f.write("\n### Nodos con Mayor Intermediación (Betweenness Centrality - Puentes)\n")
        for rank, (club, bet) in enumerate(top_betweenness, 1):
            f.write(f"{rank}. **{club}** (Intermediación: {bet:.5f})\n")

        f.write("\n### Nodos con Mayor PageRank\n")
        for rank, (club, pr) in enumerate(top_pagerank, 1):
            f.write(f"{rank}. **{club}** (PageRank: {pr:.5f})\n")

        f.write("\n## 3. Análisis Financiero (€ M)\n\n")
        f.write("### Mayor Gasto en Fichajes\n")
        for rank, (club, fin) in enumerate(top_spenders, 1):
            f.write(f"{rank}. **{club}**: {fin['spent_m']:.2f} M€ ({fin['arrivals']} fichajes)\n")

        f.write("\n### Mayor Ingreso por Ventas\n")
        for rank, (club, fin) in enumerate(top_earners, 1):
            f.write(f"{rank}. **{club}**: {fin['earned_m']:.2f} M€ ({fin['departures']} ventas)\n")

    print(f"Generated network analysis report in {analysis_file}")

    # Generate Static PNG
    fig, ax = plt.subplots(figsize=(16, 16), facecolor="#0f172a")
    ax.set_facecolor("#0f172a")
    pos = nx.spring_layout(G_clubs_weighted, k=1.4, iterations=120, seed=42)
    
    max_bet = max(betweenness.values()) if max(betweenness.values()) > 0 else 1.0
    node_sizes = [300 + (betweenness.get(n, 0.0) / max_bet) * 1200 for n in G_clubs_weighted.nodes()]
    
    node_colors = []
    for n in G_clubs_weighted.nodes():
        if n in EXTERNAL_LEAGUES:
            node_colors.append("#ef4444")
        elif n in DIVISION_1:
            node_colors.append("#38bdf8")
        else:
            node_colors.append("#34d399")
            
    weights = [G_clubs_weighted[u][v]["weight"] for u, v in G_clubs_weighted.edges()]
    max_w = max(weights) if weights else 1
    edge_widths = [0.5 + (w / max_w) * 3.5 for w in weights]
    
    nx.draw_networkx_edges(
        G_clubs_weighted, pos, ax=ax,
        width=edge_widths, alpha=0.35, edge_color="#94a3b8",
        arrows=True, arrowsize=10, min_source_margin=12, min_target_margin=12
    )
    nx.draw_networkx_nodes(
        G_clubs_weighted, pos, ax=ax,
        node_size=node_sizes, node_color=node_colors, alpha=0.9,
        linewidths=1.5, edgecolors="#ffffff"
    )
    
    for node, (x, y) in pos.items():
        bet_val = betweenness.get(node, 0.0)
        font_weight = "bold" if bet_val > 0.03 or node in EXTERNAL_LEAGUES else "normal"
        font_size = 9 if font_weight == "bold" else 7.5
        
        ax.text(
            x, y + 0.025, node,
            fontsize=font_size, fontweight=font_weight, color="#f8fafc",
            ha="center", va="bottom",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#1e293b", edgecolor="#475569", alpha=0.85, lw=0.5)
        )
        
    ax.set_title("Red de Traspasos de LaLiga (2025-2027) - Grafo Consolidado de Clubes", color="#f8fafc", fontsize=16, fontweight="bold", pad=20)
    
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='Ligas Internacionales', markerfacecolor='#ef4444', markersize=10),
        Line2D([0], [0], marker='o', color='w', label='Primera División', markerfacecolor='#38bdf8', markersize=10),
        Line2D([0], [0], marker='o', color='w', label='Segunda División', markerfacecolor='#34d399', markersize=10),
        Line2D([0], [0], color='#94a3b8', lw=2, label='Grosor arista = Nº Traspasos')
    ]
    ax.legend(handles=legend_elements, loc='lower left', facecolor='#1e293b', edgecolor='#475569', labelcolor='#f8fafc', fontsize=10)
    
    plt.axis("off")
    plt.tight_layout()
    plt.savefig("la_liga_transfers_layout.png", dpi=300, facecolor="#0f172a")
    plt.close()
    print("Saved enhanced preview visualization to la_liga_transfers_layout.png")

if __name__ == "__main__":
    main()
