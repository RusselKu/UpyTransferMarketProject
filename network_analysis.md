# Ficha Técnica y Reporte de Análisis de Redes

Este documento contiene las métricas avanzadas y el análisis del mercado de fichajes de LaLiga (2025-2027) útil para completar la visualización y la ficha técnica A4.

## 1. Ficha Técnica General (Formato A4)

| Campo | Contenido |
| --- | --- |
| **Nombre de la red** | Red de Traspasos de LaLiga (2025-2027) |
| **Fuente** | Fichajes.com (Mercado Oficial de Fichajes) |
| **Tipo de Grafo** | Dirigido, Heterogéneo / Multígrafo Dirigido Ponderado |
| **Tamaño (Grafo Heterogéneo)** | 856 nodos, 1997 aristas |
| **Tamaño (Grafo Clubes)** | 56 nodos, 1034 traspasos (522 enlaces únicos) |
| **Coeficiente de Homofilia (División)** | -0.0239 |
| **Número de Comunidades (Louvain/Greedy)** | 4 comunidades detectadas |
| **Traspasos de Cantera (Equipos B)** | 144 movimientos detectados |
| **Herramientas utilizadas** | Python, BeautifulSoup4, NetworkX, Gephi, Vis.js, Chart.js |

## 2. Métricas de Centralidad SNA

### Nodos con Mayor Grado Total
1. **Resto del mundo** (Grado: 461)
2. **Premier League** (Grado: 64)
3. **Alavés** (Grado: 63)
4. **Mirandés** (Grado: 62)
5. **Elche** (Grado: 56)

### Nodos con Mayor Intermediación (Betweenness Centrality - Puentes)
1. **Resto del mundo** (Intermediación: 0.24054)
2. **Mirandés** (Intermediación: 0.08101)
3. **Córdoba** (Intermediación: 0.06735)
4. **Alavés** (Intermediación: 0.05480)
5. **Espanyol** (Intermediación: 0.04041)

### Nodos con Mayor PageRank
1. **Resto del mundo** (PageRank: 0.06022)
2. **Espanyol** (PageRank: 0.03355)
3. **Mirandés** (PageRank: 0.03276)
4. **Serie A** (PageRank: 0.03263)
5. **Premier League** (PageRank: 0.03147)

## 3. Análisis Financiero (€ M)

### Mayor Gasto en Fichajes
1. **Atlético de Madrid**: 309.00 M€ (22 fichajes)
2. **Premier League**: 276.00 M€ (34 fichajes)
3. **Real Madrid**: 242.50 M€ (13 fichajes)
4. **Resto del mundo**: 176.95 M€ (226 fichajes)
5. **FC Barcelona**: 107.50 M€ (10 fichajes)

### Mayor Ingreso por Ventas
1. **Resto del mundo**: 286.56 M€ (235 ventas)
2. **Premier League**: 269.50 M€ (30 ventas)
3. **Atlético de Madrid**: 145.88 M€ (21 ventas)
4. **Villarreal**: 106.50 M€ (18 ventas)
5. **Serie A**: 99.65 M€ (25 ventas)
