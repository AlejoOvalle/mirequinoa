import streamlit as st
import pandas as pd
import requests
import io
import time
from clasificador import CATEGORIAS_OFICIALES, categorizar_negocio

st.set_page_config(
    page_title="Directorio Comercial - Mi Requínoa", 
    page_icon="📍", 
    layout="wide"
)

st.title("📍 Directorio Comercial y Emprendimientos")
st.markdown("Comunas y sectores: **Requínoa**, **Los Lirios** y **El Abra** con datos de Google Maps.")

# --- CONEXIÓN DE CLAVE ---
st.sidebar.header("🔑 Conexión")

maps_key = st.secrets.get("GOOGLE_MAPS_KEY", "") or st.secrets.get("GOOGLE_API_KEY", "")

if not maps_key:
    maps_key = st.sidebar.text_input("Google Maps API Key", type="password")

if maps_key:
    st.sidebar.success("✅ Conectado a Google Maps")
else:
    st.sidebar.warning("⚠️ Ingresa tu clave de Google Maps")

st.sidebar.divider()

# --- PARÁMETROS DE BÚSQUEDA ---
st.sidebar.header("🎯 Parámetros")
zona_a_buscar = st.sidebar.selectbox(
    "Sector a escanear", 
    ["Requínoa, Chile", "Los Lirios, Requínoa, Chile", "El Abra, Requínoa, Chile", "Comuna de Requínoa, Chile"]
)

termino_especifico = st.sidebar.text_input(
    "Rubro o negocio (opcional)", 
    placeholder="Ej: peluqueria, taller, cafe, ferreteria..."
)

boton_buscar = st.sidebar.button("🚀 Extraer Negocios", type="primary")

# --- CONSULTA A GOOGLE MAPS CON COORDENADAS ---
def consultar_google_maps(query, key, zona_nombre):
    url = "https://places.googleapis.com/v1/places:searchText"
    
    # Se agrega 'places.location' para obtener latitud y longitud exactas
    mascara = [
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.nationalPhoneNumber",
        "places.websiteUri",
        "places.types",
        "places.primaryTypeDisplayName",
        "places.regularOpeningHours",
        "places.photos"
    ]
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": ",".join(mascara)
    }
    
    payload = {"textQuery": query, "languageCode": "es"}
    resp = requests.post(url, headers=headers, json=payload)
    data = resp.json()
    
    if "error" in data:
        st.error(f"Error de Google Maps: {data['error'].get('message', 'Desconocido')}")
        return pd.DataFrame()
        
    lugares = data.get("places", [])
    if not lugares:
        return pd.DataFrame()

    negocios = []
    
    for p in lugares:
        nombre = p.get("displayName", {}).get("text", "")
        tipos_raw = ", ".join(p.get("types", []))
        rubro_es = p.get("primaryTypeDisplayName", {}).get("text", "Comercio")
        direccion = p.get("formattedAddress", "")
        telefono = p.get("nationalPhoneNumber", "")
        sitio_web = p.get("websiteUri", "")
        
        # 1. Coordenadas exactas para mapa / picker
        loc = p.get("location", {})
        lat = loc.get("latitude", None)
        lng = loc.get("longitude", None)
        
        # 2. Horarios de atención
        hours_obj = p.get("regularOpeningHours", {})
        horarios_list = hours_obj.get("weekdayDescriptions", [])
        horarios = " | ".join(horarios_list) if horarios_list else "No informado"
        
        # 3. Foto oficial
        fotos = p.get("photos", [])
        if fotos:
            f_name = fotos[0].get("name", "")
            url_foto = f"https://places.googleapis.com/v1/{f_name}/media?maxWidthPx=400&key={key}"
        else:
            url_foto = ""
            
        # 4. Clasificación limpia en tus 14 categorías
        cat_limpia = categorizar_negocio(nombre, tipos_raw, rubro_es)
        
        negocios.append({
            "Foto": url_foto,
            "Nombre": nombre,
            "Categoría": cat_limpia,
            "Rubro Google": rubro_es,
            "Zona": zona_nombre.replace(", Chile", ""),
            "Dirección": direccion,
            "Latitud": lat,
            "Longitud": lng,
            "Teléfono": telefono,
            "Horarios": horarios,
            "Sitio Web": sitio_web
        })
        
    return pd.DataFrame(negocios)

# --- EJECUCIÓN ---
if "datos_extraidos" not in st.session_state:
    st.session_state.datos_extraidos = pd.DataFrame()

if boton_buscar:
    if not maps_key:
        st.warning("⚠️ Debes configurar la clave de Google Maps en la barra lateral.")
    else:
        query = f"{termino_especifico} en {zona_a_buscar}".strip() if termino_especifico else f"comercios en {zona_a_buscar}"
        with st.spinner(f"Consultando Google Maps para: '{query}'..."):
            df_res = consultar_google_maps(query, maps_key, zona_a_buscar)
            
            if not df_res.empty:
                st.session_state.datos_extraidos = df_res
                st.success(f"¡Éxito! Se encontraron {len(df_res)} comercios.")
            else:
                st.info("No se encontraron comercios con ese criterio de búsqueda.")

# --- RESULTADOS Y DESCARGA ---
df_actual = st.session_state.datos_extraidos

if not df_actual.empty:
    st.subheader(f"Comercios Listos ({len(df_actual)})")
    
    col_csv, col_excel, _ = st.columns([1, 1, 3])
    
    # 1. Descargar CSV
    csv_buf = io.StringIO()
    csv_buf.write('\ufeff')
    df_actual.to_csv(csv_buf, index=False, sep=";")
    col_csv.download_button(
        label="📥 Descargar (.CSV)",
        data=csv_buf.getvalue().encode('utf-8-sig'),
        file_name="negocios_requinoa.csv",
        mime="text/csv"
    )
    
    # 2. Descargar Excel
    xls_buf = io.BytesIO()
    with pd.ExcelWriter(xls_buf, engine="openpyxl") as wr:
        df_actual.to_excel(wr, index=False, sheet_name="Negocios")
    col_excel.download_button(
        label="📊 Descargar (.XLSX)",
        data=xls_buf.getvalue(),
        file_name="negocios_requinoa.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.write("")
    
    # Visualización en tabla interactiva
    st.dataframe(
        df_actual,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Foto": st.column_config.ImageColumn("Foto"),
            "Sitio Web": st.column_config.LinkColumn("Sitio Web"),
            "Teléfono": st.column_config.TextColumn("Teléfono"),
            "Latitud": st.column_config.NumberColumn("Latitud", format="%.6f"),
            "Longitud": st.column_config.NumberColumn("Longitud", format="%.6f")
        }
    )
