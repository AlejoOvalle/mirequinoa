import streamlit as st
import pandas as pd
import requests
import io
import time
from clasificador import CATEGORIAS_OFICIALES, categorizar_negocio

st.set_page_config(page_title="Extractor Google Maps - Mi Requínoa", page_icon="📍", layout="wide")

st.title("📍 Extractor de Negocios desde Google Maps")
st.markdown("Herramienta oficial conectada a Google Places API (New) para **Requínoa**, **Los Lirios** y **El Abra**.")

# --- BARRA LATERAL ---
st.sidebar.header("🔑 Conexión con Google Maps")
api_key = st.sidebar.text_input("Google Places API Key", type="password")

st.sidebar.divider()
st.sidebar.header("🎯 Parámetros de Extracción")
zona_a_buscar = st.sidebar.selectbox(
    "Sector a escanear", 
    ["Requínoa, Chile", "Los Lirios, Requínoa, Chile", "El Abra, Requínoa, Chile", "Comuna de Requínoa, Chile"]
)

termino_especifico = st.sidebar.text_input(
    "Rubro o negocio específico (opcional)", 
    placeholder="Ej: restaurant, taller, panaderia, ferreteria..."
)

# --- FUNCIÓN CON LA NUEVA API DE GOOGLE (PLACES NEW) ---
def consultar_google_maps_new(query, key):
    url = "https://places.googleapis.com/v1/places:searchText"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        # Pedimos los datos necesarios en una sola consulta
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.types,places.editorialSummary"
    }
    
    payload = {
        "textQuery": query,
        "languageCode": "es"
    }
    
    resp = requests.post(url, headers=headers, json=payload)
    data = resp.json()
    
    if "error" in data:
        st.error(f"Error de Google: {data['error'].get('message', 'Error desconocido')}")
        return pd.DataFrame()
        
    lugares = data.get("places", [])
    negocios_extraidos = []
    
    for p in lugares:
        nombre = p.get("displayName", {}).get("text", "")
        tipos = ", ".join(p.get("types", []))
        direccion = p.get("formattedAddress", "")
        telefono = p.get("nationalPhoneNumber", "")
        sitio_web = p.get("websiteUri", "")
        resumen = p.get("editorialSummary", {}).get("text", "")
        
        # Clasificar automáticamente con tu taxonomía
        categoria_limpia = categorizar_negocio(nombre, tipos, resumen)
        
        negocios_extraidos.append({
            "Nombre": nombre,
            "Categoría Asignada": categoria_limpia,
            "Zona": zona_a_buscar.replace(", Chile", ""),
            "Dirección": direccion,
            "Teléfono": telefono,
            "Sitio Web": sitio_web,
            "Descripción": resumen
        })
        
    return pd.DataFrame(negocios_extraidos)

# --- ACCIÓN DE BÚSQUEDA ---
if "datos_extraidos" not in st.session_state:
    st.session_state.datos_extraidos = pd.DataFrame()

if st.sidebar.button("🚀 Extraer Negocios desde Google Maps"):
    if not api_key:
        st.warning("⚠️ Debes ingresar tu clave de Google arriba.")
    else:
        query = f"{termino_especifico} en {zona_a_buscar}".strip() if termino_especifico else f"comercios en {zona_a_buscar}"
        with st.spinner(f"Consultando Google Maps para: '{query}'..."):
            df_resultado = consultar_google_maps_new(query, api_key)
            
            if not df_resultado.empty:
                st.session_state.datos_extraidos = df_resultado
                st.success(f"¡Éxito! Se encontraron {len(df_resultado)} comercios.")
            else:
                st.info("No se encontraron resultados con ese criterio.")

# --- MOSTRAR RESULTADOS Y DESCARGA ---
df_actual = st.session_state.datos_extraidos

if not df_actual.empty:
    st.subheader(f"Negocios Encontrados ({len(df_actual)})")
    
    col_csv, col_excel, _ = st.columns([1, 1, 3])
    
    # Descarga CSV
    csv_buffer = io.StringIO()
    csv_buffer.write('\ufeff')
    df_actual.to_csv(csv_buffer, index=False, sep=";")
    col_csv.download_button(
        label="📥 Descargar (.CSV)",
        data=csv_buffer.getvalue().encode('utf-8-sig'),
        file_name="negocios_requinoa.csv",
        mime="text/csv"
    )
    
    # Descarga Excel
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df_actual.to_excel(writer, index=False, sheet_name="Negocios")
    col_excel.download_button(
        label="📊 Descargar (.XLSX)",
        data=excel_buffer.getvalue(),
        file_name="negocios_requinoa.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.write("")
    st.dataframe(df_actual, use_container_width=True)
