# Tabla II: Métricas de Centralidad SNA Recalculadas (338 Nodos)

Esta tabla recopila el top 5 de centralidad en la red de 338 nodos (clubes reales) tras retirar los súper-nodos consolidados de ligas extranjeras.

| Rango | Mayor Grado (Total Traspasos) | Mayor Intermediación (Betweenness) | Mayor PageRank (Prestigio) |
| --- | --- | --- | --- |
| 1 | **Elche** (39) | **Real Valladolid** (0.107) | **Mirandés** (0.025) |
| 2 | **Real Valladolid** (39) | **Mirandés** (0.103) | **Elche** (0.025) |
| 3 | **Huesca** (39) | **Elche** (0.102) | **Real Valladolid** (0.024) |
| 4 | **RCD Espanyol** (38) | **RCD Espanyol** (0.099) | **Deportivo Alavés** (0.024) |
| 5 | **Mirandés** (38) | **UD Las Palmas** (0.098) | **UD Las Palmas** (0.024) |

### Análisis de Hallazgos
* **Desaparición del Súper-nodo:** El nodo consolidado "Resto del mundo" (que anteriormente concentraba un grado de 461 y una intermediación de 0.240) ya no existe. Su influencia se distribuye ahora de manera real y fragmentada entre 282 clubes extranjeros individuales.
* **Elche y Real Valladolid como Hubs de Volumen:** Elche y Real Valladolid lideran el grado con 39 transferencias cada uno, reflejando su rol central como distribuidores de jugadores.
* **Mirandés y Real Valladolid como Puentes Clave (Betweenness):** Mirandés (0.103) y Real Valladolid (0.107) tienen la mayor intermediación. Actúan como conectores indispensables entre diferentes comunidades del grafo (especialmente facilitando movimientos entre Primera y Segunda división).
* **PageRank (Prestigio y Centralidad Global):** Mirandés y Elche obtienen el mayor PageRank (0.025), lo que demuestra que no solo tienen muchas conexiones, sino que estas conexiones provienen de otros clubes activos en el mercado.

### Gráfico Comparativo
![Ranking de Centralidad 338](ranking_centralidad_338.png)
