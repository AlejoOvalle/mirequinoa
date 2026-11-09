import streamlit as st
import pandas as pd
import requests
import io
import time
from clasificador import CATEGORIAS_OFICIALES, categorizar_negocio

st.set_page_config(
    page_title="Extractor Comunal FindAll - Mi Requínoa", 
    page_icon="📍", 
    layout="wide"
)

st.title("📍 Extractor Comunal Unificado para FindAll (WordPress)")
st.markdown("Escaneo simultáneo en **Requínoa**, **Los Lirios** y **El Abra** con salida lista para **WP All Import**.")

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
st.sidebar.header("🎯 Parámetros de Extracción")
st.sidebar.info("📍 **Sectores incluidos:**\n- Requínoa Centro\n- Los Lirios\n- El Abra")

termino_especifico = st.sidebar.text_input(
    "Rubro o término a buscar", 
    placeholder="Ej: ferreteria, restaurante, almacen, peluqueria..."
)

boton_buscar = st.sidebar.button("🚀 Escanear Toda la Comuna", type="primary")

# --- FUNCIÓN DE CONSULTA POR SECTOR ---
def consultar_sector(query, key, sector_nombre):
    url = "https://places.googleapis.com/v1/places:searchText"
    
    mascara = [
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.nationalPhoneNumber",
        "places.websiteUri",
        "places.types",
        "places.primaryTypeDisplayName",
        "places.regularOpeningHours",
        "places.photos",
        "places.rating",
        "places.userRatingCount"
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
        st.error(f"Error en {sector_nombre}: {data['error'].get('message')}")
        return []
        
    lugares = data.get("places", [])
    resultados = []
    
    for p in lugares:
        title = p.get("displayName", {}).get("text", "")
        tipos_raw = ", ".join(p.get("types", []))
        rubro_es = p.get("primaryTypeDisplayName", {}).get("text", "Comercio")
        address = p.get("formattedAddress", "")
        phone = p.get("nationalPhoneNumber", "")
        website = p.get("websiteUri", "")
        rating = p.get("rating", "")
        votos = p.get("userRatingCount", 0)
        
        # Coordenadas exactas para FindAll
        loc = p.get("location", {})
        lat = loc.get("latitude", "")
        lng = loc.get("longitude", "")
        
        # Horarios
        hours_obj = p.get("regularOpeningHours", {})
        horarios_list = hours_obj.get("weekdayDescriptions", [])
        working_hours = " | ".join(horarios_list) if horarios_list else "No informado"
        
        # Foto oficial
        fotos = p.get("photos", [])
        if fotos:
            f_name = fotos[0].get("name", "")
            featured_image = f"https://places.googleapis.com/v1/{f_name}/media?maxWidthPx=800&key={key}"
        else:
            featured_image = ""
            
        # Categoría oficial limpia
        category = categorizar_negocio(title, tipos_raw, rubro_es)
        
        # Contenido HTML para el cuerpo del Listing en FindAll
        rating_texto = f"<p>⭐ Calificación en Google: <strong>{rating}</strong> ({votos} opiniones)</p>" if rating else ""
        content = f"<p>{rubro_es} ubicado en {sector_nombre}, sector {title}.</p>{rating_texto}"
        
        resultados.append({
            "title": title,
            "category": category,
            "location_tax": sector_nombre,
            "address": address,
            "latitude": lat,
            "longitude": lng,
            "phone": phone,
            "website": website,
            "working_hours": working_hours,
            "featured_image": featured_image,
            "content": content
        })
        
    return resultados

# --- PROCESO UNIFICADO (BARRIDO EN LAS 3 ZONAS) ---
def escanear_toda_la_comuna(termino, key):
    sectores = [
        {"nombre": "Requínoa", "query_extra": "Requínoa, Chile"},
        {"nombre": "Los Lirios", "query_extra": "Los Lirios, Requínoa, Chile"},
        {"nombre": "El Abra", "query_extra": "El Abra, Requínoa, Chile"}
    ]
    
    todos_los_negocios = []
    progreso = st.progress(0, text="Iniciando escaneo comunal...")
    
    for i, sec in enumerate(sectores):
        sector_name = sec["nombre"]
        query = f"{termino} en {sec['query_extra']}".strip() if termino else f"comercios en {sec['query_extra']}"
        
        progreso.progress((i) / len(sectores), text=f"Buscando en {sector_name}...")
        res_sector = consultar_sector(query, key, sector_name)
        todos_los_negocios.extend(res_sector)
        time.sleep(0.3)
        
    progreso.progress(1.0, text="Consolidando y eliminando duplicados...")
    
    if not todos_los_negocios:
        progreso.empty()
        return pd.DataFrame()
        
    df = pd.DataFrame(todos_los_negocios)
    
    # Eliminar duplicados si un negocio salió en más de una zona (por nombre similar o dirección idéntica)
    df = df.drop_duplicates(subset=["title", "address"], keep="first")
    
    progreso.empty()
    return df

# --- EJECUCIÓN ---
if "datos_comunales" not in st.session_state:
    st.session_state.datos_comunales = pd.DataFrame()

if boton_buscar:
    if not maps_key:
        st.warning("⚠️ Ingresa la clave de Google Maps en la barra lateral.")
    else:
        with st.spinner("Escaneando Requínoa, Los Lirios y El Abra simultáneamente..."):
            df_final = escanear_toda_la_comuna(termino_especifico, maps_key)
            
            if not df_final.empty:
                st.session_state.datos_comunales = df_final
                st.success(f"¡Escaneo finalizado con éxito! Se consolidaron {len(df_final)} negocios únicos en toda la comuna.")
            else:
                st.info("No se encontraron resultados para ese rubro en ninguna de las tres zonas.")

# --- RESULTADOS Y DESCARGA PARA WP ALL IMPORT ---
df_actual = st.session_state.datos_comunales

if not df_actual.empty:
    st.subheader(f"Directorio Unificado ({len(df_actual)} comercios)")
    
    # Resumen rápido por zona encontrada
    conteo_zonas = df_actual["location_tax"].value_counts().to_dict()
    resumen_txt = " | ".join([f"**{z}:** {c}" for z, c in conteo_zonas.items()])
    st.markdown(f"Distribución: {resumen_txt}")
    
    col_csv, col_excel, _ = st.columns([1, 1, 3])
    
    # CSV listo para WP All Import
    csv_buf = io.StringIO()
    csv_buf.write('\ufeff')
    df_actual.to_csv(csv_buf, index=False, sep=";")
    
    nombre_archivo = f"import_comuna_{termino_especifico or 'general'}"
    col_csv.download_button(
        label="📥 Descargar CSV Comunal",
        data=csv_buf.getvalue().encode('utf-8-sig'),
        file_name=f"{nombre_archivo}.csv",
        mime="text/csv"
    )
    
    # Excel
    xls_buf = io.BytesIO()
    with pd.ExcelWriter(xls_buf, engine="openpyxl") as wr:
        df_actual.to_excel(wr, index=False, sheet_name="WP_Import_Comunal")
    col_excel.download_button(
        label="📊 Descargar Excel Comunal",
        data=xls_buf.getvalue(),
        file_name=f"{nombre_archivo}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.write("")
    
    # Tabla interactiva
    st.dataframe(
        df_actual,
        use_container_width=True,
        hide_index=True,
        column_config={
            "featured_image": st.column_config.ImageColumn("Foto"),
            "location_tax": st.column_config.TextColumn("Localidad (WP Tax)"),
            "category": st.column_config.TextColumn("Categoría"),
            "website": st.column_config.LinkColumn("Sitio Web"),
            "latitude": st.column_config.NumberColumn("Latitud", format="%.6f"),
            "longitude": st.column_config.NumberColumn("Longitud", format="%.6f")
        }
    )
