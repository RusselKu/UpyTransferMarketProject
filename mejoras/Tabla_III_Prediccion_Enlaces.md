# Tabla III: Predicción de Enlaces (Validación con Adamic-Adar)

Este documento analiza el rendimiento de la predicción de enlaces en la red utilizando un 20% de aristas ocultas para validación (test set).

| Métrica | Valor (338 nodos) | Valor anterior (56 nodos) | Implicación Metodológica |
| --- | --- | --- | --- |
| **Precision@50** | **12.0%** | 22.0% | Desciende debido a la gran dispersión del grafo expandido (red más grande y difícil de adivinar). |
| **AUC Estimado** | **0.72** | 0.71 | Se mantiene robusto; confirma que hay una señal estructural real para predecir fichajes futuros. |

### Interpretación de Resultados
* **Resiliencia de la AUC:** Que el área bajo la curva (AUC) aumente levemente de 0.71 a 0.72 en una red mucho mayor (338 nodos vs 56 nodos) es una señal matemática muy fuerte. Indica que las características locales de los nodos (vecinos comunes, estructura de tríadas) siguen siendo un predictor fiable y no son un artefacto del tamaño reducido del grafo anterior.
* **Precision@50:** La reducción de la precisión era esperada. En una red con 338 nodos hay más de 56,000 conexiones posibles sin explotar, por lo que el espacio de búsqueda es mucho más amplio y disperso que en el grafo consolidado de 56 nodos.

### Gráfico Comparativo de Predicción
![Validación de Predicción de Enlaces 338](prediccion_enlaces_338.png)
