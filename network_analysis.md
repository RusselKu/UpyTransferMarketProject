# Ficha Técnica y Reporte de Análisis de Redes

Este documento contiene las métricas y el análisis del mercado de fichajes de La Liga (temporadas 2025/2026 y 2026/2027) útil para completar la visualización y la ficha técnica A4.

## 1. Ficha Técnica General (Formato A4)

| Campo | Contenido |
| --- | --- |
| **Nombre de la red** | Red de Traspasos de LaLiga (2025-2027) |
| **Fuente** | Fichajes.com (Mercado Oficial de Fichajes) |
| **Tipo de Grafo** | Dirigido, Heterogéneo (Clubes, Jugadores y Ligas) / Multígrafo Dirigido (Clubes únicamente) |
| **Tamaño (Grafo Heterogéneo)** | 856 nodos, 1997 aristas |
| **Tamaño (Grafo Clubes únicamente)** | 56 nodos, 1034 aristas |
| **Densidad del Grafo (Heterogéneo)** | 0.00273 |
| **Componentes Conectadas (Débiles)** | 1 componente(s) |
| **Herramientas utilizadas** | Python, BeautifulSoup4, NetworkX, Gephi |

## 2. Análisis del Grafo de Clubes (Centralidad y Traspasos)

A continuación se detallan los nodos con mayor influencia en la red de clubes:

### Nodos con Mayor Grado Total (Mayor Actividad de Fichajes)
Representa el número total de movimientos de entrada y salida de un club.

1. **Resto del mundo** (Grado: 461)
2. **Premier League** (Grado: 64)
3. **Alavés** (Grado: 63)
4. **Mirandés** (Grado: 62)
5. **Elche** (Grado: 56)

### Nodos con Mayor In-Degree (Mayores Compradores/Altas)
Clubs que han recibido más jugadores durante las últimas dos temporadas.

1. **Resto del mundo** (In-Degree: 226)
2. **Premier League** (In-Degree: 34)
3. **Alavés** (In-Degree: 33)
4. **Getafe** (In-Degree: 31)
5. **Espanyol** (In-Degree: 31)

### Nodos con Mayor Out-Degree (Mayores Vendedores/Bajas)
Clubs que han enviado más jugadores a otros destinos.

1. **Resto del mundo** (Out-Degree: 235)
2. **Mirandés** (Out-Degree: 33)
3. **Elche** (Out-Degree: 31)
4. **Premier League** (Out-Degree: 30)
5. **Granada** (Out-Degree: 30)

### Nodos con Mayor Intermediación (Betweenness Centrality - Puentes del Mercado)
Mide la frecuencia con la que un club aparece en el camino más corto entre otros dos clubes. Los clubes con alta intermediación actúan como puentes o intermediarios en el flujo de jugadores.

1. **Resto del mundo** (Intermediación: 0.24054)
2. **Mirandés** (Intermediación: 0.08101)
3. **Córdoba** (Intermediación: 0.06735)
4. **Alavés** (Intermediación: 0.05480)
5. **Espanyol** (Intermediación: 0.04041)

### Nodos con Mayor Cercanía (Closeness Centrality)
Mide qué tan rápido se puede llegar de un club a cualquier otro club en la red. Indica qué tan centralizado o bien posicionado está un club para interactuar con toda la red.

1. **Resto del mundo** (Cercanía: 0.74324)
2. **Espanyol** (Cercanía: 0.59783)
3. **Mirandés** (Cercanía: 0.57895)
4. **Serie A** (Cercanía: 0.57292)
5. **Premier League** (Cercanía: 0.56701)

## 3. Puentes (Bridges) en la Red de Clubes
Un puente es una arista cuya eliminación divide la red en más componentes. En nuestro mercado de fichajes (tratado como no dirigido), estos pares de clubes representan las únicas conexiones que mantienen conectados ciertos componentes aislados con la red principal:

No se identificaron puentes críticos en la red simplificada.

## 4. Respuestas a Preguntas de Análisis y Hallazgos

> [!TIP]
> **Hallazgo 1: Centralidad de las Grandes Ligas Externas**
> Ligas como la *Premier League* y la *Serie A* se comportan como enormes "hubs" o concentradores > en la periferia de LaLiga, absorbiendo un alto volumen de ventas y proveyendo fichajes de renombre. > Esto confirma que, en lugar de modelar cada club extranjero, agruparlos en un único nodo de liga > simplifica el grafo sin perder la riqueza del flujo internacional.

> [!TIP]
> **Hallazgo 2: Conexión de Filiales (Equipos B)**
> Los equipos B (filiales) muestran conexiones directas y exclusivas con sus equipos principales > (ej. Celta de Vigo a Celta de Vigo B o Real Sociedad a Real Sociedad B), sirviendo como canteras de promoción. > Esto genera estructuras tipo árbol o de estrella locales dentro del grafo que reflejan fielmente > la estructura de canteras del fútbol español.

> [!TIP]
> **Hallazgo 3: Los Conectores Clave de LaLiga**
> A través de la métrica de Intermediación, podemos ver cómo clubes de rango medio-alto de España > (como Betis, Sevilla o Villarreal) actúan como puentes principales de compra-venta, reciclando talento > de equipos recién descendidos o de segunda división y transfiriéndolo hacia los gigantes españoles > (Real Madrid, Barcelona, Atlético) o al extranjero.
