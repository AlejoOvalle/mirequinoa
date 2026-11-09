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
st.markdown("Escaneo garantizado en **Requínoa**, **Los Lirios** y **El Abra** (excluye negocios externos).")

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
st.sidebar.info("📍 **Sectores incluidos:**\n- Requínoa Centro\n- Los Lirios\n- El Abra")

termino_especifico = st.sidebar.text_input(
    "Rubro o término a buscar", 
    placeholder="Ej: libreria, ferreteria, restaurante, taller..."
)

boton_buscar = st.sidebar.button("🚀 Escanear Toda la Comuna", type="primary")

# --- FILTRO GEOGRÁFICO INFALIBLE POR COORDENADAS Y TEXTO ---
def pertenece_a_la_zona(lat, lng, direccion):
    """
    Verifica que el negocio esté físicamente en la zona de Requínoa.
    Requínoa y sus alrededores están entre latitud -34.18 y -34.40.
    Santiago está en -33.4 y Viña del Mar en -33.0 (quedan automáticamente fuera).
    """
    # 1. Filtro estricto por coordenadas GPS
    if lat and lng:
        try:
            lat_f = float(lat)
            lng_f = float(lng)
            # Rango exacto de la comuna de Requínoa y límites inmediatos
            if not (-34.42 <= lat_f <= -34.18 and -70.95 <= lng_f <= -70.65):
                return False
        except ValueError:
            pass

    # 2. Filtro complementario por texto de dirección
    dir_lower = direccion.lower()
    vetadas = ["santiago", "viña", "ñuñoa", "providencia", "las condes", "valparaíso", "concepción", "temuco"]
    if any(v in dir_lower for v in vetadas):
        return False

    return True

# --- CONSULTA A GOOGLE MAPS ---
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
    
    payload = {
        "textQuery": query,
        "languageCode": "es"
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
        loc = p.get("location", {})
        lat = loc.get("latitude", "")
        lng = loc.get("longitude", "")
        
        # FILTRO DE SEGURIDAD: Solo dejamos pasar negocios que estén físicamente en la zona
        if not pertenece_a_la_zona(lat, lng, address):
            continue
            
        title = p.get("displayName", {}).get("text", "")
        tipos_raw = ", ".join(p.get("types", []))
        rubro_es = p.get("primaryTypeDisplayName", {}).get("text", "Comercio")
        phone = p.get("nationalPhoneNumber", "")
        website = p.get("websiteUri", "")
        rating = p.get("rating", "")
        votos = p.get("userRatingCount", 0)
        
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

# --- BARRIDO COMUNAL UNIFICADO ---
def escanear_toda_la_comuna(termino, key):
    # Consultas explícitas con ancla territorial completa para evitar ambigüedades
    sectores = [
        {"nombre": "Requínoa", "query": f"{termino} en Requínoa, O'Higgins, Chile"},
        {"nombre": "Los Lirios", "query": f"{termino} en Los Lirios, Requínoa, O'Higgins, Chile"},
        {"nombre": "El Abra", "query": f"{termino} en El Abra, Requínoa, O'Higgins, Chile"}
    ]
    
    todos_los_negocios = []
    progreso = st.progress(0, text="Iniciando escaneo...")
    
    for i, sec in enumerate(sectores):
        sector_name = sec["nombre"]
        progreso.progress(i / len(sectores), text=f"Buscando en {sector_name}...")
        
        res = consultar_sector(sec["query"], key, sector_name)
        todos_los_negocios.extend(res)
        time.sleep(0.3)
        
    progreso.progress(1.0, text="Finalizando y consolidando...")
    
    if not todos_los_negocios:
        progreso.empty()
        return pd.DataFrame()
        
    df = pd.DataFrame(todos_los_negocios)
    
    # Eliminar duplicados si un negocio apareció en más de una búsqueda
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
                st.success(f"¡Éxito! Se encontraron {len(df_final)} comercios 100% locales.")
            else:
                st.info("No se encontraron comercios de ese rubro registrados en la comuna.")

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
