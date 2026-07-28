# Proyecto: Visualización de Grafo de Traspasos de LaLiga (2025-2027)

Este proyecto realiza un web scraping respetuoso y eficiente de **Fichajes.com** para extraer las transferencias de fútbol de la Primera y Segunda División de España de las temporadas **2025/2026** y **2026/2027** (mercado actual). Con estos datos, construye un grafo de red y genera las métricas necesarias para la ficha técnica del Concurso de Visualización de Redes.

## Estructura del Proyecto

1. **`scraper.py`**: El script en Python que recopila los datos. Consulta la lista de clubes de Primera y Segunda División y extrae sus altas y bajas utilizando la API parcial (`?partial=1`) para cada club. Categoriza los filiales y agrupa los clubes extranjeros en nodos de ligas representativas (*Premier League*, *Bundesliga*, *Ligue 1*, *Serie A* y *Resto del mundo*).
2. **`generate_graph.py`**: Lee `transfers_dataset.json` y construye dos representaciones del grafo con la librería `NetworkX` (Solo Clubes y Heterogéneo), calcula métricas de centralidad y exporta los archivos `.gexf`.
3. **`generate_web_dashboard.py`**: Compila el dataset y genera un dashboard HTML interactivo completo (`transfer_market_graph.html`) usando **vis.js** y estilos premium en modo oscuro.
4. **`transfer_market_graph.html`**: El dashboard interactivo autoejecutable. No requiere servidor local: solo debes hacer doble clic en el archivo y se abrirá en tu navegador (Chrome, Edge, Firefox, etc.) para que puedas explorar la red, buscar clubes y filtrar las temporadas y vistas interactivamente.
5. **`transfers_dataset.json`**: El dataset crudo de 1,034 traspasos únicos extraídos.
6. **`la_liga_transfers_clubs_only.gexf`**: Archivo de grafo para Gephi (modelo de solo clubes).
7. **`la_liga_transfers_heterogeneous.gexf`**: Archivo de grafo para Gephi (modelo de clubes y jugadores).
8. **`network_analysis.md`**: Reporte técnico detallado con las métricas calculadas listo para rellenar la ficha técnica A4.
9. **`la_liga_transfers_layout.png`**: Una vista previa visual rápida del grafo generado.

## Instrucciones de Ejecución

Si deseas volver a recopilar los datos, recalcular las métricas o reconstruir el dashboard, ejecuta los siguientes comandos en tu terminal:

### 1. Ejecutar el Scraper
```bash
python scraper.py
```

### 2. Generar el Grafo y Análisis
```bash
python generate_graph.py
```

### 3. Generar el Dashboard Interactivo HTML
```bash
python generate_web_dashboard.py
```


## Visualización Recomendada (en Gephi)

Para lograr un diseño "premium" en tu lámina A4 utilizando los archivos `.gexf` en Gephi:
1. **Distribución (Layout)**: Utiliza el algoritmo **ForceAtlas 2** o **Yifan Hu** para separar las comunidades.
2. **Color de Nodos (Partition)**: Colorea los nodos según su `type` (distinguiendo clubes de jugadores y ligas externas) o por su `division` (Primera en un color, Segunda en otro).
3. **Tamaño de Nodos (Ranking)**: Escala el tamaño de los clubes según su **Grado** o su centralidad de **Intermediación (Betweenness)** para destacar los clubes con mayor actividad.
4. **Exportación**: Exporta como PDF/SVG en la pestaña "Preview" para mantener la máxima calidad vectorial en tu lámina A4.