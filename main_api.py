from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import data_processing as dp

app = FastAPI()

class RecomendacionRequest(BaseModel):
    cod_cliente: int
    radio_circulo: float

@app.post("/recomendaciones/")
async def obtener_recomendaciones(request: RecomendacionRequest):
    # Aquí cargarías tus datos. Puede que necesites ajustar la ruta del archivo o manejarla como una variable de entorno o parámetro.
    data = dp.cargar_y_limpiar_datos('Copia - SistemaRecomendacion.xlsx')
    cliente_data = data[data['Cod_Cliente'] == request.cod_cliente]

    if cliente_data.empty:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    latitud = cliente_data['LATITUD'].values[0]
    longitud = cliente_data['LONGITUD'].values[0]

    # Encuentra clientes cercanos
    clientes_cercanos, _ = dp.encontrar_clientes_cercanos(data, latitud, longitud, request.radio_circulo)
    if not clientes_cercanos:
        return {"message": "No hay clientes cercanos."}

    # Obtiene recomendaciones de productos
    grouped_data = dp.agrupar_y_calcular_moda(data)
    recomendaciones = dp.recomendar_productos(data, grouped_data, request.cod_cliente, clientes_cercanos)
    
    return recomendaciones.to_dict(orient='records')

# Uvicorn es un servidor ASGI. Esto iniciará tu aplicación FastAPI de forma que puedas conectarte a ella.
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)