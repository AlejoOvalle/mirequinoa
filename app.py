import streamlit as st
import pandas as pd
import requests
import io
import time
from clasificador import CATEGORIAS_OFICIALES, categorizar_negocio

st.set_page_config(page_title="Extractor Google Maps - Mi Requínoa", page_icon="📍", layout="wide")

st.title("📍 Extractor de Negocios desde Google Maps")
st.markdown("Herramienta para consultar Google Maps / Google My Business en **Requínoa**, **Los Lirios** y **El Abra**.")

# --- BARRA LATERAL: CONFIGURACIÓN DE GOOGLE ---
st.sidebar.header("🔑 Conexión con Google Maps")

# Campo para la clave de Google
api_key = st.sidebar.text_input(
    "AIzaSyAX3XL5iu_z0yBLfCcGaS1JEtSXvK9S20g", 
    type="password", 
    help="Clave que obtienes gratis en Google Cloud Console con Places API habilitada."
)

st.sidebar.divider()
st.sidebar.header("🎯 Parámetros de Extracción")

zona_a_buscar = st.sidebar.selectbox(
    "Sector a escanear", 
    ["Requínoa, Chile", "Los Lirios, Requínoa, Chile", "El Abra, Requínoa, Chile", "Toda la comuna (Requínoa completo)"]
)

termino_especifico = st.sidebar.text_input(
    "Rubro o negocio a buscar (opcional)", 
    placeholder="Ej: almacén, ferretería, restaurante... (o vacío para general)"
)

# --- FUNCIÓN PARA EXTRAER DATOS REALES DE GOOGLE MAPS ---
def consultar_google_maps(query, key):
    negocios_extraidos = []
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={requests.utils.quote(query)}&key={key}"
    
    while url:
        resp = requests.get(url).json()
        status = resp.get("status")
        
        if status == "REQUEST_DENIED":
            st.error(f"Error de Google: {resp.get('error_message', 'API Key inválida o sin permisos')}")
            break
            
        resultados = resp.get("results", [])
        
        for lugar in resultados:
            place_id = lugar.get("place_id")
            
            # Pedir detalles extendidos del comercio (teléfono, web, etc.)
            url_detalle = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,formatted_address,formatted_phone_number,website,types,editorial_summary&key={key}"
            detalle = requests.get(url_detalle).json().get("result", {})
            
            nombre = detalle.get("name", lugar.get("name", ""))
            tipos = ", ".join(detalle.get("types", lugar.get("types", [])))
            direccion = detalle.get("formatted_address", lugar.get("formatted_address", ""))
            telefono = detalle.get("formatted_phone_number", "")
            sitio_web = detalle.get("website", "")
            resumen = detalle.get("editorial_summary", {}).get("overview", "")
            
            # Clasificar automáticamente en tus 14 categorías
            categoria_limpia = categorizar_negocio(nombre, tipos, resumen)
            
            negocios_extraidos.append({
                "Nombre": nombre,
                "Categoría Asignada": categoria_limpia,
                "Zona": zona_a_buscar.replace(", Chile", ""),
                "Dirección": direccion,
                "Teléfono": telefono,
                "Email": "", # Google no da correos por privacidad
                "Sitio Web": sitio_web,
                "Descripción": resumen
            })
            time.sleep(0.1) # Pausa preventiva para no saturar la API
            
        # Paginación (Google entrega hasta 60 resultados por búsqueda en bloques de 20)
        next_page_token = resp.get("next_page_token")
        if next_page_token and len(negocios_extraidos) < 60:
            time.sleep(2) # Google exige esperar 2 segundos antes de usar el token de la página siguiente
            url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?pagetoken={next_page_token}&key={key}"
        else:
            url = None

    return pd.DataFrame(negocios_extraidos)

# --- BOTÓN DE DISPARO ---
if "datos_extraidos" not in st.session_state:
    st.session_state.datos_extraidos = pd.DataFrame()

if st.sidebar.button("🚀 Extraer Negocios desde Google Maps"):
    if not api_key:
        st.warning("⚠️ Debes ingresar tu API Key de Google Maps en el panel de la izquierda para extraer en vivo.")
    else:
        with st.spinner(f"Consultando Google Maps para {zona_a_buscar}... Esto puede tomar unos segundos."):
            query = f"{termino_especifico} en {zona_a_buscar}".strip()
            df_resultado = consultar_google_maps(query, api_key)
            
            if not df_resultado.empty:
                st.session_state.datos_extraidos = df_resultado
                st.success(f"¡Extracción completada! Se encontraron {len(df_resultado)} comercios.")
            else:
                st.info("No se encontraron comercios con los criterios especificados.")

# --- RESULTADOS Y DESCARGA ---
df_actual = st.session_state.datos_extraidos

if not df_actual.empty:
    st.subheader(f"Comercios Obtenidos ({len(df_actual)})")
    
    # Botones de descarga directa
    col_csv, col_excel, _ = st.columns([1, 1, 3])
    
    csv_buffer = io.StringIO()
    csv_buffer.write('\ufeff')
    df_actual.to_csv(csv_buffer, index=False, sep=";")
    
    col_csv.download_button(
        label="📥 Descargar Base de Datos (.CSV)",
        data=csv_buffer.getvalue().encode('utf-8-sig'),
        file_name="negocios_google_maps.csv",
        mime="text/csv"
    )
    
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df_actual.to_excel(writer, index=False, sheet_name="Negocios")
        
    col_excel.download_button(
        label="📊 Descargar Base de Datos (.XLSX)",
        data=excel_buffer.getvalue(),
        file_name="negocios_google_maps.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    # Vista previa de la tabla
    st.dataframe(df_actual, use_container_width=True)
else:
    st.info("💡 Ingresa tu clave de Google a la izquierda y presiona **'Extraer Negocios desde Google Maps'** para generar la base de datos.")
