# Ruta más rápida entre establecimientos de salud (Dijkstra)

App web que calcula rutas óptimas entre establecimientos de salud del Perú usando grafos y el algoritmo de Dijkstra. Proyecto del curso de Complejidad Algorítmica (UPC).

## Qué hace

- Trabaja con un dataset de **1 500 establecimientos de salud** (puestos y centros de salud) de **29 DIRESA**, con nombre, dirección y coordenadas.
- Arma un grafo por DIRESA donde cada nodo es un establecimiento y el peso de cada arista es la **distancia geodésica en km** entre ellos.
- Calcula tres tipos de ruta:
  - **Directa:** el camino más corto entre un origen y un destino (Dijkstra).
  - **Con paradas:** pasando por establecimientos intermedios que elige el usuario.
  - **Recorrer todos:** una aproximación al problema del viajero con la heurística del vecino más cercano.
- Muestra el grafo y la ruta sobre un mapa interactivo, con inicio de sesión de usuarios.

## Stack

Python · Flask · NetworkX · geopy · pandas · HTML/CSS/JavaScript

## Cómo correrlo

```bash
pip install flask pandas networkx geopy openpyxl
python app.py
```

Abre http://127.0.0.1:5000. El dataset (`DataSetVersiónFinal.xlsx`) no está en el repo; colócalo en la carpeta raíz antes de iniciar.
