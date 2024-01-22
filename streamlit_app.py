import streamlit as st
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
import data_processing as dp  # Importa el módulo data_processing y lo renombra a dp
import pandas as pd

def main():
    st.title('Sistema de Recomendación')

    cod_cliente = st.number_input('Ingrese Cod_Cliente:', min_value=1, step=1)
    radio_circulo = st.slider('Seleccione el radio del círculo en metros', min_value=1000, max_value=50000, value=30000, step=1000)

    if st.button('Buscar y Recomendar'):
        data = dp.cargar_y_limpiar_datos('Copia - SistemaRecomendacion.xlsx')
        cliente_data = data[data['Cod_Cliente'] == cod_cliente]

        if not cliente_data.empty:
            latitud = cliente_data['LATITUD'].values[0]
            longitud = cliente_data['LONGITUD'].values[0]

            # Mapa con la ubicación del cliente
            m = folium.Map(location=[latitud, longitud], zoom_start=13)
            folium.Marker([latitud, longitud], popup='Cliente Actual', icon=folium.Icon(color='black')).add_to(m)

            # Dibuja un círculo utilizando el radio seleccionado por el usuario
            folium.Circle(radius=radio_circulo, location=[latitud, longitud], color='blue', fill=True).add_to(m)

            # Para encontrar clientes cercanos y recomendar productos
            clientes_cercanos, ubicaciones = dp.encontrar_clientes_cercanos(data, latitud, longitud, radio_circulo)
            grouped_data = dp.agrupar_y_calcular_moda(data)
            recomendaciones = dp.recomendar_productos(data, grouped_data, cod_cliente, clientes_cercanos)
            
            # Añade marcadores para los clientes cercanos
            for cliente_id, (lat, lon) in zip(clientes_cercanos, ubicaciones):
                folium.Marker([lat, lon], popup=f'Cliente {cliente_id}', icon=folium.Icon(color='green')).add_to(m)

            folium_static(m)

            # Mostrar tabla de clientes cercanos y recomendaciones de productos
            if clientes_cercanos:
                st.write("Clientes Cercanos:")
                tabla_clientes_cercanos = data[data['Cod_Cliente'].isin(clientes_cercanos)][['Cod_Cliente', 'LATITUD', 'LONGITUD']]
                st.dataframe(tabla_clientes_cercanos)

            # Recomendaciones de productos
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
            st.error('No se encontraron datos para el cliente proporcionado.')

if __name__ == "__main__":
    main()