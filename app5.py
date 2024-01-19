import streamlit as st
import pandas as pd
from scipy import stats
import folium
from streamlit_folium import folium_static
from geopy.distance import great_circle
import matplotlib.pyplot as plt

# Carga de datos
data = pd.read_excel('Copia - SistemaRecomendacion.xlsx')

# Limpieza de data
valores_eliminar = ['BONIFICACION N/C 72', 'BONIFICACION 77']
data = data[~data['Linea'].isin(valores_eliminar)]
data = data[(data['LATITUD'] != 0) & (data['LONGITUD'] != 0)]
data = data[data['ValorVenta'] != 0]

# Columnas relevantes
relevant_columns = ['Id_Producto', 'Producto', 'Cantidad']
filtered_data = data[relevant_columns]

# Agrupar datos y calcular la moda de la cantidad
def moda(group):
    modas = group.mode()
    if len(modas) > 0:
        return modas.iloc[0]
    else:
        # Manejar el caso en que no hay moda o devolver un valor predeterminado
        return None  # O cualquier otro valor que consideres apropiado

grouped_data = filtered_data.groupby(['Id_Producto', 'Producto']).agg(
    CantidadModa=pd.NamedAgg(column='Cantidad', aggfunc=moda)
).reset_index()



# Función para calcular la distancia
def calcular_distancia(lat1, lon1, lat2, lon2):
    return great_circle((lat1, lon1), (lat2, lon2)).meters

# Función para encontrar clientes cercanos
def encontrar_clientes_cercanos(lat_cliente, lon_cliente, radio):
    clientes_cercanos = []
    ubicaciones = []
    for _, row in data.iterrows():
        lat, lon = row['LATITUD'], row['LONGITUD']
        if calcular_distancia(lat_cliente, lon_cliente, lat, lon) <= radio:
            clientes_cercanos.append(row['Cod_Cliente'])
            ubicaciones.append((lat, lon))
    return clientes_cercanos, ubicaciones



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


# Interfaz Streamlit
def main():
    st.title('Sistema de Recomendación')

    cod_cliente = st.number_input('Ingrese Cod_Cliente:', min_value=1, step=1)
    #id_portafolio = st.number_input("Ingrese IDPORTAFOLIO:", min_value=1, step=1)

    # Slider para que el usuario seleccione el radio del círculo
    radio_circulo = st.slider('Seleccione el radio del círculo en metros', min_value=1000, max_value=50000, value=30000, step=1000)

    if st.button('Buscar y Recomendar'):
        cliente_data = data[data['Cod_Cliente'] == cod_cliente]
        if not cliente_data.empty:
            latitud = cliente_data['LATITUD'].values[0]
            longitud = cliente_data['LONGITUD'].values[0]

        # Mapa con la ubicación del cliente
        m = folium.Map(location=[latitud, longitud], zoom_start=13)
        folium.Marker([latitud, longitud], icon=folium.Icon(color='black')).add_to(m)

        # Dibuja un círculo utilizando el radio seleccionado por el usuario
        folium.Circle(radius=radio_circulo, location=[latitud, longitud], color='blue', fill=True).add_to(m)

        # Encuentra y muestra clientes cercanos
        clientes_cercanos, _ = encontrar_clientes_cercanos(latitud, longitud, radio_circulo)
        for cliente_id in clientes_cercanos:
            cliente_info = data[data['Cod_Cliente'] == cliente_id]
            if not cliente_info.empty:
                cliente_loc = cliente_info[['LATITUD', 'LONGITUD']].values[0]
                folium.Marker(cliente_loc, icon=folium.Icon(color='green')).add_to(m)


        folium_static(m)

        # Mostrar tabla de clientes cercanos
        if clientes_cercanos:
            st.write("Clientes Cercanos:")
            tabla_clientes_cercanos = data[data['Cod_Cliente'].isin(clientes_cercanos)][['Cod_Cliente', 'LATITUD', 'LONGITUD']]
            st.dataframe(tabla_clientes_cercanos)
        else:
            st.warning('No se encontraron clientes cercanos.')

        # Recomendaciones de productos
        recomendaciones = recomendar_productos(data, grouped_data, cod_cliente, clientes_cercanos)
        if recomendaciones is not None and not recomendaciones.empty:
            st.write("Recomendaciones de Productos:")
            st.dataframe(recomendaciones)

            # Crear gráfico de barras
            plt.figure(figsize=(10, 6))
            plt.bar(recomendaciones['Producto'], recomendaciones['CantidadModa'])
            plt.xlabel('Producto')
            plt.ylabel('Cantidad Moda')
            plt.xticks(rotation=45)
            plt.title('Gráfico de Barras de Productos Recomendados')
            st.pyplot(plt)

        else:
            st.error('No se encontraron recomendaciones para el código del cliente proporcionado.')


if __name__ == "__main__":
    main()