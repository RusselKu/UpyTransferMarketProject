# Reporte técnico — Modo Enfoque del dashboard de traspasos

**Proyecto:** `UpyTransferMarketProject` · dashboard estático en [docs/](docs/) (GitHub Pages)
**Fecha:** 2026-08-05 · **Estado:** ✅ corregido y verificado con arnés de pruebas
**Archivos tocados:** [docs/assets/js/network.js](docs/assets/js/network.js), [docs/assets/js/ui.js](docs/assets/js/ui.js), [docs/assets/js/main.js](docs/assets/js/main.js), [docs/index.html](docs/index.html), [docs/assets/css/app.css](docs/assets/css/app.css) (rebuild), [generate_web_dashboard.py](generate_web_dashboard.py) (plantilla espejo)

---

## 0. Antes de reportar cualquier bug: purga el caché

Al abrir el dashboard en local (`python -m http.server` o `file://`), Chrome/Edge cachean
`network.js` y `ui.js` de forma agresiva. Se corrige código y el navegador **sigue ejecutando
la versión vieja**, reproduciendo el toggle "invertido" y el grafo encogido.

* **En tu máquina:** `Ctrl + F5` (Windows) / `Cmd + Shift + R` (Mac), o ventana de incógnito.
* **En el código (ya aplicado):** todos los assets llevan sufijo de versión.

```html
<link href="assets/css/app.css?v=20260805" rel="stylesheet">
<script src="assets/js/network.js?v=20260805" defer></script>
```

Además `main.js` hacía `fetch(path, { cache: 'force-cache' })` **sin sufijo de versión**: los
JSON de `docs/data/` quedaban congelados en el navegador para siempre, así que regenerar los
datos no tenía efecto visible. Ahora:

```js
const APP_VERSION = '20260805';                    // docs/assets/js/main.js
fetch(`data/${path}?v=${APP_VERSION}`, { cache: 'default' });
```

> ### 🔴 Convención obligatoria para quien retome esto
> **Cada vez que edites un `.js`/`.css` de `docs/assets/` o regeneres `docs/data/*.json`, sube
> `APP_VERSION` en [main.js](docs/assets/js/main.js) Y los `?v=` de
> [index.html](docs/index.html) al mismo valor** (formato `YYYYMMDD`, agrega `-2`, `-3` si hay
> varios cambios el mismo día). El generador ya lo automatiza: `write_index_html()` lee
> `APP_VERSION` de `main.js` y lo inyecta en la plantilla (`resolve_asset_version()`).

---

## 1. Contexto técnico: por qué este grafo es un caso especial

El layout viene **precalculado** desde Python (`spring_layout`), así que la simulación de
físicas está apagada para que los 338 nodos aparezcan al instante:

```js
// network.js
const hasPrecomputedLayout = nodesDataset.get().every(n => typeof n.x === 'number' && typeof n.y === 'number');
physics: hasPrecomputedLayout ? { enabled: false } : { /* forceAtlas2Based */ }
```

**Consecuencia clave:** con `physics: false`, Vis.js no vuelve a dibujar de forma interactiva.
Un `nodesDataset.update({ id, hidden: true })` **no** repinta el canvas estático. La única forma
fiable de refrescar es **reemplazar el contenido del DataSet**: `clear()` + `add()`. Todo el
Modo Enfoque está construido sobre esa regla.

---

## 2. Los cinco defectos y su corrección

### Bug #1 — El botón «Ver todo el grafo» nunca aparecía (usuario atrapado)

`#btn-clear-focus` nace con la clase `hidden` en el HTML y **nadie se la quitaba**: `focusOnNode()`
no tocaba el botón y el único `classList.add('hidden')` estaba en `updateNetworkData()`. Resultado:
al aislar un club no había ninguna salida visible; solo funcionaba el clic en el vacío, que no es
descubrible.

**Fix:** una única función dueña del chrome flotante, llamada **siempre** que cambia `isFocused`
(`focusOnNode`, `clearFocus`, `updateNetworkData`, `resetFiltersAndVariables`):

```js
// network.js
function updateFocusChrome(nodeCount, edgeCount) {
    const btn = document.getElementById('btn-clear-focus');
    if (btn) btn.classList.toggle('hidden', !isFocused);
    const badge = document.getElementById('focus-badge');
    ...  // 🎯 Real Madrid · 18 vecinos · 45 enlaces
}
```

### Bug #2 — La red se encogía a nada al navegar entre vecinos

Al calcular la vecindad con `network.getConnectedNodes(clubB)` solo se encontraban las conexiones
de `clubB` **que ya estaban en pantalla**, así que cada clic reducía la red hasta vaciarla.

**Fix (invariante del módulo):** la vecindad se calcula **siempre** desde los arreglos globales
estáticos, nunca desde el canvas.

```js
// network.js — la única fuente de verdad de vecindad
function getFullNeighborhood(nodeId) {
    const neighbors = new Set([nodeId]);
    const baseEdges = (viewMode === 'clubs_only') ? clubEdges : heteroEdges;  // ← datos globales
    baseEdges.forEach(e => {
        if (e.from === nodeId) neighbors.add(e.to);
        if (e.to === nodeId) neighbors.add(e.from);
    });
    return neighbors;
}
```

`getConnectedNodes()` ya no se usa en ninguna parte del proyecto — **no lo reintroduzcas**.
`highlightEgoNetwork()` (reflector de los tours guiados) también migró a `getFullNeighborhood()`.

### Bug #3 — `network.fit()` con ids fantasma → zoom disparado / grafo "encogido"

`focusOnNode()` hacía `network.fit({ nodes: Array.from(neighborhood) })`, pero la vecindad se
calcula sobre el grafo **completo**: si un vecino quedaba fuera por los filtros de temporada,
división o costo, se le pedía a Vis.js encuadrar nodos inexistentes → encuadre imposible.

**Fix:** encuadrar solo ids presentes en el DataSet, con tope de zoom, y caso especial de nodo sin vecinos:

```js
const presentIds = filteredNodes.map(n => n.id);
if (presentIds.length > 1) network.fit({ nodes: presentIds, maxZoomLevel: 1.6, animation: anim });
else network.moveTo({ position: pos, scale: 1.1, animation: anim });   // fit() de 1 nodo = zoom al máximo
```

El mismo riesgo existía en `selectSearchResult()`, `focusStarTransfer()`, `playStory()`,
`findAndHighlightPath()` y `simulateWhatIfTransfer()`: `selectNodes`/`focus` sobre un id ausente
lanza excepción y rompe el handler. Se añadieron guardas en [ui.js](docs/assets/js/ui.js):
`nodeIsOnCanvas()`, `safeSelectNodes()`, `safeFocusNode()`. En la búsqueda, si el nodo quedaba
fuera de los filtros, se limpian los filtros y se avisa con un toast en lugar de fallar en silencio.

### Bug #4 — Atenuación "inversa" que parecía un aislamiento a medias

Con el Modo Enfoque **desactivado**, hacer clic en un club bajaba la opacidad del resto a `0.15`.
Se parecía tanto al aislamiento que el toggle se sentía invertido.

**Fix:** con el Modo Enfoque apagado, un clic **no altera ninguna opacidad ni estilo de arista**:
la red se mantiene al 100 %.

```js
function applyNodeEmphasis(nodeId) {
    if (focusMode) focusOnNode(nodeId);
    else resetEgoHighlight();   // devuelve todo a opacidad 1.0; nada más
}
```

El reflector con atenuación queda reservado a los tours guiados (`playStory`), donde el efecto es
intencional y va acompañado de un toast que explica cómo salir.

### Bug #5 — Cambiar un filtro expulsaba al usuario del enfoque

`updateNetworkData()` apagaba `isFocused` en silencio: filtrar por temporada mientras se examinaba
un club te devolvía de golpe a los 338 nodos.

**Fix:** el enfoque se **recompone** con los nuevos filtros si el nodo sigue existiendo:

```js
const refocusId = (preserveFocus && isFocused && focusMode) ? focusedNodeId : null;
/* ...reconstruir datasets... */
if (refocusId && nodesDataset.get(refocusId)) focusOnNode(refocusId);
```

Se añadió la variable de estado `focusedNodeId` (antes solo existía el booleano `isFocused`, que no
permitía recomponer nada).

---

## 3. Mejoras de UX incluidas

| Qué | Dónde |
|---|---|
| Badge de contexto `🎯 Club · N vecinos · M enlaces` sobre el canvas | `#focus-badge` + `updateFocusChrome()` |
| Botón de salida con atajo visible `Esc` y `active:scale-95` | `#btn-clear-focus` |
| Jerarquía visual en el enfoque: nodo raíz con halo cian y borde grueso; aristas incidentes en cian y gruesas; aristas entre vecinos tenues | `focusOnNode()` |
| Toggle del Modo Enfoque como fila-tarjeta con estado explícito **On/Off** | `#toggle-focus-mode`, `#focus-mode-state` |
| Toast no bloqueante (`showToast`), p. ej. al activar el modo sin nodo seleccionado | `#app-toast` + `ui.js` |
| Tecla **Esc** en cascada: modal → drawer → salir del enfoque | listener `keydown` en `ui.js` |
| Checkbox siempre sincronizado con el estado real (Esc, reset global, tours) | `setFocusMode()` |
| Contador de enlaces coherente: total agregado de `meta.json` solo cuando no hay filtros activos | `totalEdgeCountLabel()` |

---

## 4. Cómo verificar (5 minutos)

Sirve el sitio y haz **Hard Reload**:

```bash
cd docs && python -m http.server 8000   # → http://localhost:8000
```

1. Clic en un club **con el Modo Enfoque en Off** → se abre el drawer, la red sigue completa y con
   todo el color. Contador: **338 nodos**.
2. Activa **🎯 Modo Enfoque** (la etiqueta cambia a **On**) → se aísla el club seleccionado, aparecen
   el badge cian y el botón «✕ Ver todo el grafo».
3. Clic en un vecino → se re-enfoca en **su** vecindad completa (puede crecer, nunca colapsar a 1).
   Repítelo 4–5 veces: no debe quedarse vacío.
4. Con el enfoque activo, cambia la temporada → sigues enfocado, con los datos de esa temporada.
5. Botón «✕ Ver todo el grafo» o **Esc** → vuelve el grafo completo, todo al 100 %, badge y botón se ocultan.
6. Apaga el toggle → **Off**, red completa, sin restos de atenuación.

Regresión automatizada (stubs de DOM + Vis, sin navegador ni dependencias):

```bash
node tests/focus_test.js     # última corrida: 17/17 OK
```

Recorre los pasos 1–6 sobre los datos reales de `docs/data/clubs-network.json` y **falla** si
`fit()`/`selectNodes()` reciben un id ausente del DataSet o si `getConnectedNodes()` vuelve a
usarse. El caso "nodo totalmente aislado" está incluido pero se salta: en el dataset actual todos
los 338 clubes tienen al menos una arista.

---

## 5. Notas para quien continúe

* [docs/index.html](docs/index.html) **es un artefacto generado** por
  `write_index_html()` en [generate_web_dashboard.py](generate_web_dashboard.py). Todo cambio de
  HTML va en **los dos** lugares, o el siguiente `python generate_web_dashboard.py` lo borra.
  (Los cambios de este reporte ya están espejados.)
* Clases nuevas de Tailwind exigen rebuild del CSS: `npm run build:css`
  (`tailwind.config.js` escanea `docs/index.html` y `docs/assets/js/**/*.js`).
* [transfer_market_graph.html](transfer_market_graph.html) (versión monolítica de un solo archivo)
  se genera al final del pipeline; **regenérala** con `python generate_web_dashboard.py` para que
  incorpore estos arreglos. Las regex del inliner ya toleran el sufijo `?v=`.
* Invariantes que no hay que romper: (a) vecindad desde `clubEdges`/`heteroEdges`, nunca desde el
  canvas; (b) refresco por `clear()` + `add()`, nunca por `hidden`; (c) `updateFocusChrome()` en
  cada cambio de `isFocused`; (d) `fit`/`selectNodes`/`focus` solo con ids presentes en el DataSet.
