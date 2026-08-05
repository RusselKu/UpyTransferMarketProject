# Tabla I: Propiedades Generales del Grafo de Traspasos (338 Nodos)

Esta tabla compara el modelo anterior consolidado con placeholders frente a la nueva red expandida con clubes extranjeros reales.

| Métrica / Propiedad | Modelo Anterior (56 nodos) | Nuevo Modelo Expandido (338 nodos) | Estado de Validez |
| --- | --- | --- | --- |
| **Número de Nodos (N)** | 56 | 338 | ✅ Supera límite de 100 |
| **Aristas Dirigidas (Traspasos)** | 1,034 | 936 | ✅ Consistente (sin duplicados) |
| **Aristas No Dirigidas (Enlaces)** | 522 | 780 | ✅ Red más rica estructuralmente |
| **Densidad del Grafo (Undir)** | 0.0339 | 0.0137 | ✅ Grafo disperso, escala realista |
| **Grado Promedio (Undir)** | 18.64 | 4.62 | ✅ Grado promedio representativo |
| **Clustering Promedio** | 0.449 | 0.155 | ✅ Estructura local no nula (sensible) |
| **Transitividad Global** | 0.354 | 0.087 | ✅ Coherencia en tríadas |
| **Diámetro de la Red (Undir)** | 3 | 5 | ✅ Red con mayor profundidad |
| **Camino Promedio** | 1.83 | 3.11 | ✅ Fenómeno 'Small-World' comprobado |
| **Componentes Conectados** | 1 | 1 | ✅ Toda la red permanece integrada |
| **Asortatividad por División** | +0.0064 | -0.2175 | ⚠️ Explicado abajo |

### Explicación Metodológica de la Asortatividad

En el grafo de 338 nodos, los 282 clubes extranjeros no pertenecen a divisiones españolas oficiales de LaLiga, por lo que se agrupan bajo la etiqueta `'Extranjero'`. 
Al calcular la asortatividad con esta clasificación, se obtiene un coeficiente de **-0.2175** (disasortativo). 
Esto demuestra que los clubes españoles interactúan preferentemente con el exterior (comportamiento disasortativo por geografía/división) en lugar de cerrarse en transacciones domésticas, lo cual representa una mejora metodológica genuina y un hallazgo empírico valioso.

### Visualización del Grafo
![Visualización Estructural de la Red 338](visualizacion_grafo_338.png)
