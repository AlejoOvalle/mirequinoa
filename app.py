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
st.markdown("Escaneo con filtro geográfico estricto en **Requínoa**, **Los Lirios** y **El Abra**.")

# --- CONEXIÓN ---
st.sidebar.header("🔑 Conexión")
maps_key = st.secrets.get("GOOGLE_MAPS_KEY", "") or st.secrets.get("GOOGLE_API_KEY", "")

if not maps_key:
    maps_key = st.sidebar.text_input("Google Maps API Key", type="password")

if maps_key:
    st.sidebar.success("✅ Conectado a Google Maps")
else:
    st.sidebar.warning("⚠️ Ingresa tu clave de Google Maps")

st.sidebar.divider()

# --- PARÁMETROS ---
st.sidebar.header("🎯 Parámetros de Extracción")
st.sidebar.info("📍 **Sectores:** Requínoa Centro, Los Lirios, El Abra.")

termino_especifico = st.sidebar.text_input(
    "Rubro o término a buscar", 
    placeholder="Ej: libreria, ferreteria, restaurante, taller..."
)

boton_buscar = st.sidebar.button("🚀 Escanear Toda la Comuna", type="primary")

# --- FUNCIÓN PARA VERIFICAR QUE PERTENEZCA REALMENTE A LA ZONA ---
def es_direccion_local(direccion):
    """
    Descarta cualquier negocio que no pertenezca a la comuna de Requínoa
    o a la Región de O'Higgins circundante inmediata.
    """
    dir_lower = direccion.lower()
    
    # 1. Palabras prohibidas (ciudades lejanas que Google suele meter)
    ciudades_vetadas = [
        "santiago", "viña del mar", "valparaíso", "ñuñoa", "providencia", 
        "las condes", "concepción", "temuco", "antofagasta", "la serena", 
        "macul", "quilicura", "maipú", "la florida", "recoleta"
    ]
    for v in ciudades_vetadas:
        if v in dir_lower:
            return False
            
    # 2. Debe contener alguna referencia a la comuna o región
    terminos_permitidos = ["requínoa", "requinoa", "los lirios", "el abra", "o'higgins", "rancagua"]
    return any(term in dir_lower for term in terminos_permitidos)

# --- CONSULTA A GOOGLE CON RESTRICCIÓN DE COORDENADAS ---
def consultar_sector(query, key, sector_nombre, lat_centro, lng_centro):
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
    
    # Restricción circular estricta (radio de 6 km alrededor de cada localidad)
    payload = {
        "textQuery": query,
        "languageCode": "es",
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": lat_centro,
                    "longitude": lng_centro
                },
                "radius": 6000.0  # 6 kilómetros a la redonda
            }
        }
    }
    
    resp = requests.post(url, headers=headers, json=payload)
    data = resp.json()
    
    if "error" in data:
        st.error(f"Error en {sector_nombre}: {data['error'].get('message')}")
        return []
        
    lugares = data.get("places", [])
    resultados = []
    
    for p in lugares:
        address = p.get("formattedAddress", "")
        
        # FILTRO DE SEGURIDAD: Si no es de la zona, lo descartamos
        if not es_direccion_local(address):
            continue
            
        title = p.get("displayName", {}).get("text", "")
        tipos_raw = ", ".join(p.get("types", []))
        rubro_es = p.get("primaryTypeDisplayName", {}).get("text", "Comercio")
        phone = p.get("nationalPhoneNumber", "")
        website = p.get("websiteUri", "")
        rating = p.get("rating", "")
        votos = p.get("userRatingCount", 0)
        
        loc = p.get("location", {})
        lat = loc.get("latitude", "")
        lng = loc.get("longitude", "")
        
        hours_obj = p.get("regularOpeningHours", {})
        horarios_list = hours_obj.get("weekdayDescriptions", [])
        working_hours = " | ".join(horarios_list) if horarios_list else "No informado"
        
        fotos = p.get("photos", [])
        if fotos:
            f_name = fotos[0].get("name", "")
            featured_image = f"https://places.googleapis.com/v1/{f_name}/media?maxWidthPx=800&key={key}"
        else:
            featured_image = ""
            
        category = categorizar_negocio(title, tipos_raw, rubro_es)
        
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

# --- BARRIDO COMUNAL CON COORDENADAS PRECISAS ---
def escanear_toda_la_comuna(termino, key):
    # Coordenadas exactas para centrar la búsqueda en cada localidad
    sectores = [
        {"nombre": "Requínoa", "query": f"{termino} en Requínoa", "lat": -34.2789, "lng": -70.8131},
        {"nombre": "Los Lirios", "query": f"{termino} en Los Lirios Requínoa", "lat": -34.2372, "lng": -70.7892},
        {"nombre": "El Abra", "query": f"{termino} en El Abra Requínoa", "lat": -34.2985, "lng": -70.8350}
    ]
    
    todos_los_negocios = []
    progreso = st.progress(0, text="Iniciando escaneo con geocercas...")
    
    for i, sec in enumerate(sectores):
        sector_name = sec["nombre"]
        progreso.progress(i / len(sectores), text=f"Buscando en {sector_name}...")
        
        res = consultar_sector(sec["query"], key, sector_name, sec["lat"], sec["lng"])
        todos_los_negocios.extend(res)
        time.sleep(0.3)
        
    progreso.progress(1.0, text="Eliminando duplicados...")
    
    if not todos_los_negocios:
        progreso.empty()
        return pd.DataFrame()
        
    df = pd.DataFrame(todos_los_negocios)
    
    # Eliminar duplicados por nombre y dirección
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
        with st.spinner("Escaneando exclusivamente Requínoa, Los Lirios y El Abra..."):
            df_final = escanear_toda_la_comuna(termino_especifico, maps_key)
            
            if not df_final.empty:
                st.session_state.datos_comunales = df_final
                st.success(f"¡Listo! Se encontraron {len(df_final)} comercios 100% locales.")
            else:
                st.info("No se encontraron comercios de ese rubro en la comuna.")

# --- RESULTADOS Y DESCARGA PARA WP ALL IMPORT ---
df_actual = st.session_state.datos_comunales

if not df_actual.empty:
    st.subheader(f"Directorio Comunal Limpio ({len(df_actual)} comercios)")
    
    conteo_zonas = df_actual["location_tax"].value_counts().to_dict()
    st.markdown("Distribución real: " + " | ".join([f"**{z}:** {c}" for z, c in conteo_zonas.items()]))
    
    col_csv, col_excel, _ = st.columns([1, 1, 3])
    
    csv_buf = io.StringIO()
    csv_buf.write('\ufeff')
    df_actual.to_csv(csv_buf, index=False, sep=";")
    
    col_csv.download_button(
        label="📥 Descargar CSV para WP All Import",
        data=csv_buf.getvalue().encode('utf-8-sig'),
        file_name=f"import_wp_{termino_especifico or 'comuna'}.csv",
        mime="text/csv"
    )
    
    xls_buf = io.BytesIO()
    with pd.ExcelWriter(xls_buf, engine="openpyxl") as wr:
        df_actual.to_excel(wr, index=False, sheet_name="WP_Import")
    col_excel.download_button(
        label="📊 Descargar Excel",
        data=xls_buf.getvalue(),
        file_name=f"import_wp_{termino_especifico or 'comuna'}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.write("")
    st.dataframe(
        df_actual,
        use_container_width=True,
        hide_index=True,
        column_config={
            "featured_image": st.column_config.ImageColumn("Foto"),
            "location_tax": st.column_config.TextColumn("Localidad"),
            "website": st.column_config.LinkColumn("Web"),
            "latitude": st.column_config.NumberColumn("Latitud", format="%.6f"),
            "longitude": st.column_config.NumberColumn("Longitud", format="%.6f")
        }
    )
