# Informe de Mejoras, Innovaciones y Comparativa Técnica (Rama: Rivaldo)

**Proyecto:** Análisis de Redes Sociales (SNA) aplicado al Mercado de Fichajes de LaLiga (2025–2027)  
**Institución:** Universidad Politécnica de Yucatán (UPY 2026) — Semana de Ingeniería  
**Autor:** Rivaldo  
**Base del Repositorio:** `RusselKu/UpyTransferMarketProject`

---

## 📌 1. Resumen Ejecutivo del Proyecto

El objetivo de este proyecto es analizar la estructura del mercado de transferencias de fútbol en España (Primera División, Segunda División, Canteras/Filiales y Ligas Internacionales) utilizando la **Teoría de Grafos y el Análisis de Redes Sociales (SNA - Social Network Analysis)**.

A diferencia del repositorio base, la versión desarrollada en la rama **`Rivaldo`** transforma una visualización simple en un **sistema integral de analítica de datos, simulación interactiva y scouting deportivo profesional**, fácil de comprender tanto por un ingeniero de datos como por cualquier jurado o visitante no técnico.

---

## 📊 2. Comparativa: Repositorio Original vs. Versión Rivaldo

| Componente / Dimensión | Repositorio Base (Russel) | Mejoras e Innovaciones (Rama: Rivaldo) |
| :--- | :--- | :--- |
| **Volumen de Datos** | Muestra reducida o estática de fichajes. | **1,034 traspasos oficiales** extraídos en tiempo real desde *Fichajes.com* para las temporadas 2025/2026 y 2026/2027. |
| **Modelación de Grafos** | Grafo simple sin distinguir roles. | **Doble Modelo de Grafo**: <br>1. *Solo Clubes* (Multígrafo Dirigido Ponderado, 56 nodos).<br>2. *Clubes + Jugadores* (Grafo Bipartito/Heterogéneo, 856 nodos). |
| **Métricas SNA Calculadas** | Grado de entrada / salida básico. | **Métricas Avanzadas de Redes Complejas**: <br>• Centralidad de Intermediación (*Betweenness*) para hallar clubes puente.<br>• PageRank y Closeness.<br>• Algoritmo de Comunidades de Modularidad (*Greedy Modularity*).<br>• Coeficiente de Homofilia (*Asortatividad por División = +0.0064*). |
| **Interfaz de Usuario (UI)** | Vista básica tradicional. | **Arquitectura App Shell Profesional (Vercel / Linear Style)** con lienzo HD panorámico libre de tarjetas encimadas. |
| **Buscador de Red** | Filtro manual por texto sin guía. | **Buscador Predictivo con Autocompletado en Tiempo Real**: clasifica entre `⚽ Clubes` y `👤 Jugadores` con cambio automático de modo de vista. |
| **Ficha de Detalles** | Listado estático de datos. | **Ficha Dinámica Contextual & Scouting Card**: <br>• Para clubes: calcula gasto/ventas dinámicos según la temporada seleccionada.<br>• Para jugadores: Ficha de Scouting con Edad, Coste, Vendedor y Comprador (`De ➔ A`). |
| **Hub de Analítica** | Gráficas estándar sin contexto. | **Analytics Hub Didáctico de 4 Gráficas**: incluye **etiquetas explícitas de Eje X y Eje Y**, leyendas detalladas y cajas formales de `📌 Lectura del Gráfico`. |
| **Herramientas Interactivas** | Solo exploración estática. | **6 Herramientas Interactivas de Exploración**: <br>1. 🔄 Restablecimiento Global de Vista.<br>2. 🎞️ Reproductor de Línea del Tiempo Animada (*Play/Pause/Slider*).<br>3. ⚔️ Comparador Cara a Cara entre 2 Clubes.<br>4. 🔍 Buscador de Camino Más Corto (Algoritmo BFS).<br>5. 🧪 Simulador de Fichajes *What-If*.<br>6. 🌓 Selector de 3 Temas Visuales (*OLED Slate, Cyberpunk Glow, Light Mode*). |

---

## 🛠️ 3. Fundamentos Teóricos y Repositorio Base

Para el desarrollo de esta versión, nos basamos en los datos primarios y scripts del repositorio base, extendiéndolos mediante los siguientes pilares de la ciencia de redes:

1. **Estructura del Dataset (`scraper.py` ➔ `transfers_dataset.json`)**:
   * Scrapeo y estructuración JSON conteniendo `source_node` (vendedor), `target_node` (comprador), `player`, `cost`, `age` y `season`.

2. **Cálculos Matemáticos SNA (`generate_graph.py` ➔ `network_analysis.md`)**:
   * Se aplicó NetworkX para demostrar la hipótesis **Scale-Free** (la distribución de grado sigue una Ley de Potencia, indicando que unos pocos clubes dominan las transacciones).
   * Se demostró la **Asortatividad por División (+0.0064)**: al ser cercana a cero, se concluye que no existe homofilia rígida; los clubes realizan traspasos fluidos entre diferentes divisiones y ligas extranjeras sin limitarse a su propio nivel.

3. **Compilación de la Plataforma Web (`generate_web_dashboard.py` ➔ `transfer_market_graph.html`)**:
   * Motor Python que procesa las métricas de NetworkX y genera una aplicación web autónoma en HTML/JS utilizando **Vis.js** para la física de partículas en canvas y **Chart.js** para el tablero de análisis.

---

## 📁 4. Archivos Clave del Repositorio

* [generate_web_dashboard.py](file:///c:/Users/Rivaldo/Documents/semana%20de%20ingenieria/generate_web_dashboard.py): Motor principal que compila el dashboard interactivo.
* [transfer_market_graph.html](file:///c:/Users/Rivaldo/Documents/semana%20de%20ingenieria/transfer_market_graph.html): Plataforma web interactiva resultante.
* [generate_graph.py](file:///c:/Users/Rivaldo/Documents/semana%20de%20ingenieria/generate_graph.py): Script de análisis de red con NetworkX.
* [network_analysis.md](file:///c:/Users/Rivaldo/Documents/semana%20de%20ingenieria/network_analysis.md): Reporte técnico de métricas SNA.
* [transfers_dataset.json](file:///c:/Users/Rivaldo/Documents/semana%20de%20ingenieria/transfers_dataset.json): Base de datos con 1,034 registros de traspasos.
