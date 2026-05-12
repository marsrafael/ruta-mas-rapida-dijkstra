from flask import Flask, render_template, request, session, redirect
import pandas as pd
import networkx as nx
from geopy.distance import geodesic
import json

app = Flask(__name__)
app.secret_key = 'clave123'

# Cargar dataset
df = pd.read_excel("DataSetVersiónFinal.xlsx")
diresas = df['Diresa'].unique()

try:
    users_df = pd.read_excel("usuarios.xlsx")
except:
    # Crear archivo si no existe
    users_df = pd.DataFrame({
        'usuario': ['admin', 'user'],
        'password': ['123', '456'],
        'nombre': ['Administrador', 'Usuario']
    })
    users_df.to_excel("usuarios.xlsx", index=False)

# Cache para grafos ya calculados
_graph_cache = {}

def crear_grafo_completo(nodos_data):
    """Crea un grafo completo con todos los nodos y aristas"""
    G = nx.Graph()
    coords = {}
    
    # Agregar nodos
    for _, row in nodos_data.iterrows():
        nombre = row['Nombre']
        lat, lon = row['Latitud'], row['Longitud']
        G.add_node(nombre, pos=(lon, lat))
        coords[nombre] = (lat, lon)
    
    # Agregar aristas con pesos (distancias)
    nodos = list(G.nodes)
    n = len(nodos)
    
    # Pre-calcular todas las distancias de una vez
    for i in range(n):
        for j in range(i + 1, n):
            dist = geodesic(coords[nodos[i]], coords[nodos[j]]).kilometers
            G.add_edge(nodos[i], nodos[j], weight=round(dist, 2))
    
    return G, coords

@app.route('/ruta')
def index():
    return render_template('index.html', 
                           diresas=diresas,
                           user=session['user']
)

@app.route('/grafo', methods=['POST'])
def grafo():
    opcion_diresa = request.form['diresa']
    num_nodos = int(request.form['num_nodos'])
    tipo_ruta = request.form['tipo_ruta']
    
    print({
        'path': 'grafo',
        'opcion_diresa': opcion_diresa,
        'num_nodos': num_nodos,
        'tipo_ruta': tipo_ruta
    })

    # Generar clave para cache
    cache_key = f"{opcion_diresa}_{num_nodos}"
    
    if cache_key not in _graph_cache:
        resultado_diresa = df[df['Diresa'] == opcion_diresa]
        resul_diresa = resultado_diresa.sample(min(num_nodos, len(resultado_diresa)))
        G, coords = crear_grafo_completo(resul_diresa)
        _graph_cache[cache_key] = (G, coords)
    else:
        G, coords = _graph_cache[cache_key]
    
    nodos = list(G.nodes)
    nodos_info = [{'nombre': nodo, 'lat': coords[nodo][0], 'lon': coords[nodo][1]} 
                  for nodo in nodos]
    
    # Convertir coords a formato para JSON (lista en vez de tupla)
    coords_json = {k: list(v) for k, v in coords.items()}
    
    print({
        'path': 'grafo - resultado',
        'nodos_info': nodos_info,
        'edges': list(G.edges),
        'coords': coords_json,
        'nodos_nombres': nodos,
        'ruta': None,
        'inicio': None,
        'fin': None,
        'tipo_ruta': tipo_ruta
    })

    return render_template('mapa.html',
                        diresa=opcion_diresa,
                        nodos=nodos_info,
                        edges=list(G.edges),
                        coords=json.dumps(coords_json),
                        nodos_nombres=nodos,
                        ruta=None,
                        inicio=None,
                        fin=None,
                        tipo_ruta=tipo_ruta,
                        user=session['user']
    )

@app.route('/ruta', methods=['POST'])
def ruta():
    inicio = request.form['inicio']
    fin = request.form['fin']
    tipo_ruta = request.form['tipo_ruta']
    coords = json.loads(request.form['coords'])
    nodos = json.loads(request.form['nodos'])
    edges = json.loads(request.form['edges'])
    intermedios = request.form.getlist('intermedios')

    # Reconstruir grafo desde edges
    G = nx.Graph()
    
    # Agregar todos los nodos primero
    for nodo in nodos:
        G.add_node(nodo)
    
    # Agregar aristas con pesos pre-calculados
    edge_weights = {}
    for edge in edges:
        n1, n2 = edge[0], edge[1]
        if (n1, n2) not in edge_weights:
            coord1 = coords[n1]
            coord2 = coords[n2]
            dist = geodesic(coord1, coord2).kilometers
            edge_weights[(n1, n2)] = round(dist, 2)
            edge_weights[(n2, n1)] = edge_weights[(n1, n2)]
        
        G.add_edge(n1, n2, weight=edge_weights[(n1, n2)])

    # Calcular ruta según tipo
    if tipo_ruta == "directo":
        ruta = nx.dijkstra_path(G, inicio, fin)

    elif tipo_ruta == "todos":
        # Optimización: usar nearest neighbor heuristic para aproximar TSP
        visitados = {inicio}
        ruta = [inicio]
        actual = inicio
        nodos_restantes = set(nodos) - {inicio, fin}
        
        # Visitar todos los nodos intermedios
        while nodos_restantes:
            # Encontrar el nodo más cercano no visitado
            min_dist = float('inf')
            siguiente = None
            
            for nodo in nodos_restantes:
                if G.has_edge(actual, nodo):
                    dist = G[actual][nodo]['weight']
                    if dist < min_dist:
                        min_dist = dist
                        siguiente = nodo
            
            if siguiente is None:
                # Si no hay conexión directa, usar dijkstra
                min_dist = float('inf')
                for nodo in nodos_restantes:
                    try:
                        path = nx.dijkstra_path(G, actual, nodo)
                        dist = sum(G[path[i]][path[i+1]]['weight'] 
                                 for i in range(len(path)-1))
                        if dist < min_dist:
                            min_dist = dist
                            siguiente = nodo
                    except:
                        continue
            
            if siguiente:
                if not G.has_edge(actual, siguiente):
                    # Agregar camino intermedio
                    path = nx.dijkstra_path(G, actual, siguiente)
                    ruta.extend(path[1:])
                else:
                    ruta.append(siguiente)
                
                nodos_restantes.remove(siguiente)
                visitados.add(siguiente)
                actual = siguiente
        
        # Agregar camino al destino final
        if actual != fin:
            path = nx.dijkstra_path(G, actual, fin)
            ruta.extend(path[1:])

    elif tipo_ruta == "algunos":
        intermedios_filtrados = [n for n in intermedios if n != inicio and n != fin]
        ruta = [inicio]
        
        for i, nodo in enumerate(intermedios_filtrados):
            origen = ruta[-1]
            parcial = nx.dijkstra_path(G, origen, nodo)
            ruta.extend(parcial[1:])
        
        if ruta[-1] != fin:
            parcial = nx.dijkstra_path(G, ruta[-1], fin)
            ruta.extend(parcial[1:])

    nodos_info = [{'nombre': nodo, 'lat': coords[nodo][0], 'lon': coords[nodo][1]} 
                  for nodo in nodos]
    
    print({
        'path': 'ruta - resultado',
        'nodos_info': nodos_info,
        'edges': edges,
        'coords': coords,
        'nodos_nombres': nodos,
        'ruta': ruta,
        'inicio': inicio,
        'fin': fin,
        'tipo_ruta': tipo_ruta
    })

    return render_template('mapa.html',
                         diresa="Ruta calculada",
                         nodos=nodos_info,
                         edges=edges,
                         coords=json.dumps(coords),
                         nodos_nombres=nodos,
                         ruta=ruta,
                         inicio=inicio,
                         fin=fin,
                         tipo_ruta=tipo_ruta,
                         user=session['user']
)

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():

    user = request.form['user'].strip().lower()
    password = request.form['password'].strip()

    users_df['usuario'] = users_df['usuario'].astype(str).str.strip().str.lower()
    users_df['password'] = users_df['password'].astype(str).str.strip()

    usuario_encontrado = users_df[
        (users_df['usuario'] == user) & 
        (users_df['password'] == password)
    ]
    
    if not usuario_encontrado.empty:
        session['user'] = usuario_encontrado.iloc[0]['nombre']
        return redirect('/ruta')
    else:
        return render_template('login.html', error='Usuario o contraseña incorrectos')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, port=5100)