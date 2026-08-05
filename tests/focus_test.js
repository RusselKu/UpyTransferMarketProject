/* Arnés mínimo: stubs de DOM + vis para validar el flujo del Modo Enfoque. */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..', 'docs');
const clubs = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/clubs-network.json'), 'utf8'));

// ---- Stub DOM ----
function mkEl(id) {
    const el = {
        id, innerText: '', innerHTML: '', value: '', checked: false, className: '',
        _cls: new Set(id === 'btn-clear-focus' || id === 'focus-badge' || id === 'app-toast' ? ['hidden'] : []),
        offsetWidth: 0, style: {},
    };
    el.classList = {
        add: (...c) => c.forEach(x => el._cls.add(x)),
        remove: (...c) => c.forEach(x => el._cls.delete(x)),
        contains: c => el._cls.has(c),
        toggle: (c, force) => { if (force === undefined) { el._cls.has(c) ? el._cls.delete(c) : el._cls.add(c); } else { force ? el._cls.add(c) : el._cls.delete(c); } return el._cls.has(c); },
    };
    return el;
}
const els = {};
const document = {
    getElementById: id => (els[id] || (els[id] = mkEl(id))),
    createElement: () => ({ set innerHTML(v) { this._h = v; }, get innerHTML() { return this._h; } }),
    addEventListener: () => {},
    querySelectorAll: () => [],
};

// ---- Stub vis ----
class DataSet {
    constructor(items = []) { this.map = new Map(); this.add(items); }
    add(items) { (Array.isArray(items) ? items : [items]).forEach((it, i) => this.map.set(it.id !== undefined ? it.id : `e${this.map.size}_${i}`, it)); }
    clear() { this.map.clear(); }
    get(id) { return id === undefined ? Array.from(this.map.values()) : this.map.get(id); }
    update(items) { (Array.isArray(items) ? items : [items]).forEach(it => this.map.set(it.id, Object.assign({}, this.map.get(it.id), it))); }
    get length() { return this.map.size; }
}
const calls = [];
const handlers = {};
class Network {
    constructor(container, data) { this.data = data; }
    on(ev, cb) { handlers[ev] = cb; }
    fit(o) { calls.push(['fit', o && o.nodes ? o.nodes.length : 'all']); if (o && o.nodes) o.nodes.forEach(id => { if (!this.data.nodes.get(id)) throw new Error('fit: node not in dataset: ' + id); }); }
    moveTo(o) { calls.push(['moveTo', o.scale]); }
    selectNodes(ids) { ids.forEach(id => { if (!this.data.nodes.get(id)) throw new Error('selectNodes: node not in dataset: ' + id); }); calls.push(['select', ids.length]); }
    unselectAll() {}
    setOptions() {}
    getPositions(ids) { const r = {}; ids.forEach(i => r[i] = { x: 0, y: 0 }); return r; }
    getConnectedNodes() { throw new Error('getConnectedNodes must NOT be used'); }
    focus() { calls.push(['focus']); }
}

const ctx = {
    document, window: {}, console,
    vis: { DataSet, Network },
    setTimeout, clearTimeout, setInterval, clearInterval,
    addEventListener: () => {}, innerWidth: 1400,
    fetch: () => Promise.reject(new Error('no fetch')),
};
ctx.window = ctx;
ctx.globalThis = ctx;
vm.createContext(ctx);

for (const f of ['ui.js', 'network.js']) {
    vm.runInContext(fs.readFileSync(path.join(ROOT, 'assets/js', f), 'utf8'), ctx, { filename: f });
}
// Datos globales (main.js los pone vía fetch; aquí los inyectamos)
vm.runInContext(`
clubNodes = ${JSON.stringify(clubs.nodes)};
clubEdges = ${JSON.stringify(clubs.edges)};
heteroNodes = []; heteroEdges = []; clubStats = {}; starTransfers = [];
`, ctx);
vm.runInContext(`
clubStats = {}; window.__META__ = { total_transfers: 999 };
`, ctx);

const run = code => vm.runInContext(code, ctx);
const state = () => run(`({
  nodes: nodesDataset.length, edges: edgesDataset.length,
  isFocused, focusMode, focusedNodeId,
  btnHidden: document.getElementById('btn-clear-focus').classList.contains('hidden'),
  badgeHidden: document.getElementById('focus-badge').classList.contains('hidden'),
  counter: document.getElementById('nodes-count').innerText,
})`);

const assert = (cond, msg) => console.log((cond ? '  OK  ' : ' FAIL ') + msg);

run('initNetwork()');
const base = state();
console.log('Base:', base);
assert(base.btnHidden && base.badgeHidden, 'sin enfoque: botón y badge ocultos');

// 1. Clic en un club con Modo Enfoque OFF -> nada se aísla
run(`currentlySelectedNodeId = 'Real Madrid'; applyNodeEmphasis('Real Madrid');`);
let s = state();
assert(s.nodes === base.nodes && !s.isFocused, 'clic con enfoque OFF no reduce la red (' + s.nodes + ')');
assert(run(`nodesDataset.get().every(n => n.opacity === undefined || n.opacity === 1)`), 'clic con enfoque OFF no atenúa opacidad');

// 2a. Activar el Modo Enfoque NO debe aislar nada por sí solo (solo arma el modo)
run(`setFocusMode(true)`);
s = state();
assert(s.focusMode && !s.isFocused && s.nodes === base.nodes, 'activar el toggle solo ARMA el modo, no aísla (' + s.nodes + ')');

// 2b. Con el modo armado, un CLIC en cualquier nodo aísla (flujo real de vis)
ctx.clickHandler = handlers['click'];
run(`clickHandler({ nodes: ['Real Madrid'], edges: [] })`);
s = state();
console.log('Clic en Real Madrid con el modo armado:', s);
assert(s.isFocused && s.nodes > 1 && s.nodes < base.nodes, 'el clic aísla la vecindad');
assert(!s.btnHidden && !s.badgeHidden, 'botón "Ver todo el grafo" y badge VISIBLES');

// 3. Clic en un vecino visible -> la red NO se encoge a nada
const neighbor = run(`nodesDataset.get().map(n=>n.id).filter(id=>id!=='Real Madrid')[0]`);
run(`currentlySelectedNodeId = ${JSON.stringify(neighbor)}; applyNodeEmphasis(${JSON.stringify(neighbor)});`);
s = state();
console.log(`Enfoque en vecino "${neighbor}":`, s);
assert(s.isFocused && s.nodes > 1, 'navegar a un vecino mantiene una red no vacía (' + s.nodes + ')');
const deg = run(`clubEdges.filter(e => e.from === ${JSON.stringify(neighbor)} || e.to === ${JSON.stringify(neighbor)}).length`);
assert(s.nodes >= 2, `vecindad global del vecino (aristas=${deg}) -> nodos=${s.nodes}`);

// 4. Tres saltos seguidos sin colapsar
for (let i = 0; i < 3; i++) {
    const nxt = run(`nodesDataset.get().map(n=>n.id).filter(id=>id!==focusedNodeId)[0]`);
    if (!nxt) break;
    run(`applyNodeEmphasis(${JSON.stringify(nxt)})`);
    const st = state();
    assert(st.nodes > 1, `salto ${i + 1} -> "${nxt}" con ${st.nodes} nodos`);
}

// 5. Cambiar un filtro conserva el enfoque
run(`setSeason('2025-2026')`);
s = state();
assert(s.isFocused && !s.btnHidden, 'cambiar de temporada conserva el enfoque y su chrome');

// 6. Apagar el Modo Enfoque restaura TODO al 100%
run(`setSeason('all'); setFocusMode(false)`);
s = state();
console.log('Tras apagar enfoque:', s);
assert(!s.isFocused && s.nodes === base.nodes, 'restaura todos los nodos (' + s.nodes + '/' + base.nodes + ')');
assert(s.btnHidden && s.badgeHidden, 'oculta botón y badge');
assert(run(`document.getElementById('toggle-focus-mode').checked === false`), 'checkbox sincronizado en Off');
assert(run(`edgesDataset.get().every(e => !e.color || e.color.color !== '#475569')`), 'aristas sin atenuación residual');
assert(run(`nodesDataset.get().every(n => n.opacity === 1 || n.opacity === undefined)`), 'nodos al 100% de opacidad');

// 7. Nodo aislado sin vecinos presentes -> moveTo, no fit imposible
const isolated = run(`
  (function(){
    const withEdges = new Set(); clubEdges.forEach(e => { withEdges.add(e.from); withEdges.add(e.to); });
    const n = clubNodes.find(n => !withEdges.has(n.id));
    return n ? n.id : null;
  })()`);
console.log('Nodo aislado de prueba:', isolated);
if (isolated) { run(`focusOnNode(${JSON.stringify(isolated)})`); assert(true, 'enfocar un nodo sin vecinos no lanza excepción'); }

// 8. Escape/clearFocus idempotente
run(`clearFocus(); clearFocus();`);
assert(state().nodes === base.nodes, 'clearFocus es idempotente');
console.log('\nLlamadas a la API de vis:', JSON.stringify(calls.slice(0, 12)));
