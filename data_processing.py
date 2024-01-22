import pandas as pd
from scipy import stats
from geopy.distance import great_circle

# Carga y limpieza de datos
def cargar_y_limpiar_datos(ruta_archivo):
    data = pd.read_excel('Copia - SistemaRecomendacion.xlsx')
    valores_eliminar = ['BONIFICACION N/C 72', 'BONIFICACION 77']
    data = data[~data['Linea'].isin(valores_eliminar)]
    data = data[(data['LATITUD'] != 0) & (data['LONGITUD'] != 0)]
    data = data[data['ValorVenta'] != 0]
    return data

# Agrupación de datos y cálculo de la moda
def agrupar_y_calcular_moda(data):
    relevant_columns = ['Id_Producto', 'Producto', 'Cantidad']
    filtered_data = data[relevant_columns]

    def moda(group):
        modas = group.mode()
        if len(modas) > 0:
            return modas.iloc[0]
        else:
            return None

    grouped_data = filtered_data.groupby(['Id_Producto', 'Producto']).agg(
        CantidadModa=pd.NamedAgg(column='Cantidad', aggfunc=moda)
    ).reset_index()

    return grouped_data

# Cálculo de distancia y búsqueda de clientes cercanos
def calcular_distancia(lat1, lon1, lat2, lon2):
    return great_circle((lat1, lon1), (lat2, lon2)).meters

def encontrar_clientes_cercanos(data, lat_cliente, lon_cliente, radio):
    clientes_cercanos = []
    ubicaciones = []
    for _, row in data.iterrows():
        lat, lon = row['LATITUD'], row['LONGITUD']
        if calcular_distancia(lat_cliente, lon_cliente, lat, lon) <= radio:
            clientes_cercanos.append(row['Cod_Cliente'])
            ubicaciones.append((lat, lon))
    return clientes_cercanos, ubicaciones

# Recomendación de productos
def recomendar_productos(data_original, data_agrupada, cod_cliente, clientes_cercanos, top_n=5):
    if not clientes_cercanos:
        recomendaciones_cliente = data_agrupada[data_agrupada['Id_Producto'].isin(
            data_original[data_original['Cod_Cliente'] == cod_cliente]['Id_Producto'])]
        return recomendaciones_cliente.sort_values(by='CantidadModa', ascending=False).head(top_n)[['Id_Producto', 'Producto', 'CantidadModa']]

    # Productos comprados por el cliente
    productos_cliente = set(data_original[data_original['Cod_Cliente'] == cod_cliente]['Id_Producto'])

    # Productos comprados por clientes cercanos
    productos_cercanos = set(data_original[data_original['Cod_Cliente'].isin(clientes_cercanos)]['Id_Producto'])

    # Filtrar productos que el cliente no ha comprado pero clientes cercanos sí
    productos_recomendar = productos_cercanos - productos_cliente

    # Filtrar en 'data_agrupada' para obtener solo los productos recomendables
    recomendaciones = data_agrupada[data_agrupada['Id_Producto'].isin(productos_recomendar)]

    # Asegúrate de que 'ValorVenta' esté presente en 'data_original'
    if 'ValorVenta' in data_original.columns:
        # Calcular los ingresos totales de cada producto recomendable
        ingresos_producto = data_original.groupby('Id_Producto')['ValorVenta'].sum()

        # Asignar los ingresos a las recomendaciones
        recomendaciones = recomendaciones.assign(ValorVenta=recomendaciones['Id_Producto'].map(ingresos_producto))

        # Ordenar por moda y luego por ingresos
        recomendaciones = recomendaciones.sort_values(by=['CantidadModa', 'ValorVenta'], ascending=[False, False])

        return recomendaciones.head(top_n)[['Id_Producto', 'Producto', 'CantidadModa', 'ValorVenta']]
    else:
        # Si 'ValorVenta' no está presente, devolver las recomendaciones basadas solo en la moda
        return recomendaciones.sort_values(by='CantidadModa', ascending=False).head(top_n)[['Id_Producto', 'Producto', 'CantidadModa']]
