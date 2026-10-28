import streamlit as st
import pandas as pd
import requests
import io
import time
from clasificador import CATEGORIAS_OFICIALES, categorizar_negocio

st.set_page_config(
    page_title="Directorio Mi Requínoa", 
    page_icon="📍", 
    layout="wide"
)

st.title("📍 Directorio Comercial y de Servicios")
st.markdown("Comunas y sectores: **Requínoa**, **Los Lirios** y **El Abra**.")

# --- CLAVE ÚNICA DE GOOGLE MAPS ---
st.sidebar.header("🔑 Conexión")

maps_key = st.secrets.get("GOOGLE_MAPS_KEY", "") or st.secrets.get("GOOGLE_API_KEY", "")

if not maps_key:
    maps_key = st.sidebar.text_input("Google Maps API Key", type="password")

if maps_key:
    st.sidebar.success("✅ Conectado a Google Maps")
else:
    st.sidebar.warning("⚠️ Ingresa tu clave de Google Maps")

st.sidebar.divider()

# --- BÚSQUEDA ---
st.sidebar.header("🎯 Parámetros")
zona_a_buscar = st.sidebar.selectbox(
    "Sector a escanear", 
    ["Requínoa, Chile", "Los Lirios, Requínoa, Chile", "El Abra, Requínoa, Chile", "Comuna de Requínoa, Chile"]
)

termino_especifico = st.sidebar.text_input(
    "Rubro o negocio (opcional)", 
    placeholder="Ej: peluqueria, taller, cafe, ferreteria..."
)

boton_buscar = st.sidebar.button("🚀 Extraer Comercios", type="primary")

# --- GENERADOR DE DESCRIPCIÓN HUMANA (SIN IA EXTERNA, CERO ERRORES) ---
def generar_descripcion_humana(nombre, rubro, rating, total_reviews, review_texto, zona):
    zona_limpia = zona.replace(", Chile", "")
    
    # 1. Base descriptiva
    partes = []
    
    # Especialidad y ubicación
    if rubro and rubro != "Comercio":
        partes.append(f"{rubro.capitalize()} ubicado en {zona_limpia}")
    else:
        partes.append(f"Local comercial ubicado en {zona_limpia}")
        
    # Calificación si existe
    if rating:
        partes.append(f"(⭐ {rating})")
        
    encabezado = " ".join(partes) + ". "
    
    # 2. Agregar la opinión real de los clientes (lo que le da el toque humano)
    if review_texto and len(review_texto) > 10:
        # Limpiar saltos de línea y comillas
        limpio = review_texto.replace("\n", " ").replace('"', '').strip()
        espacio_restante = 315 - len(encabezado) - 20
        if len(limpio) > espacio_restante:
            limpio = limpio[:espacio_restante] + "..."
        descripcion = f"{encabezado}Opinión destacada: \"{limpio}\""
    else:
        descripcion = f"{encabezado}Atención a la comunidad con servicios y productos en el sector de {nombre}."
        
    # Límite estricto garantizado <= 320 caracteres
    if len(descripcion) > 320:
        descripcion = descripcion[:317] + "..."
        
    return descripcion

# --- CONSULTA OFICIAL A GOOGLE MAPS ---
def consultar_google_maps_new(query, m_key, zona):
    url = "https://places.googleapis.com/v1/places:searchText"
    
    mascara = [
        "places.displayName", "places.formattedAddress", "places.nationalPhoneNumber",
        "places.websiteUri", "places.types", "places.primaryTypeDisplayName",
        "places.rating", "places.userRatingCount", "places.regularOpeningHours", 
        "places.photos", "places.reviews"
    ]
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": m_key,
        "X-Goog-FieldMask": ",".join(mascara)
    }
    
    payload = {"textQuery": query, "languageCode": "es"}
    resp = requests.post(url, headers=headers, json=payload)
    data = resp.json()
    
    if "error" in data:
        st.error(f"Error Google Maps: {data['error'].get('message')}")
        return pd.DataFrame()
        
    lugares = data.get("places", [])
    total = len(lugares)
    if total == 0:
        return pd.DataFrame()

    negocios = []
    progreso = st.progress(0, text="Procesando comercios...")
    
    for i, p in enumerate(lugares):
        nombre = p.get("displayName", {}).get("text", "")
        tipos_raw = ", ".join(p.get("types", []))
        
        rubro_obj = p.get("primaryTypeDisplayName", {})
        rubro_es = rubro_obj.get("text", "Comercio")
        
        direccion = p.get("formattedAddress", "")
        telefono = p.get("nationalPhoneNumber", "")
        sitio_web = p.get("websiteUri", "")
        rating = p.get("rating")
        total_revs = p.get("userRatingCount", 0)
        
        # Horarios
        hours_obj = p.get("regularOpeningHours", {})
        horarios_list = hours_obj.get("weekdayDescriptions", [])
        horarios = " | ".join(horarios_list) if horarios_list else "No informado"
        
        # Foto oficial
        fotos = p.get("photos", [])
        url_foto = f"https://places.googleapis.com/v1/{fotos[0].get('name')}/media?maxWidthPx=400&key={m_key}" if fotos else ""
        
        # Mejor reseña de un cliente
        revs = p.get("reviews", [])
        mejor_review = revs[0].get("text", {}).get("text", "") if revs else ""
        
        # Generar descripción sintética humana (< 320 car.)
        descripcion = generar_descripcion_humana(
            nombre, rubro_es, rating, total_revs, mejor_review, zona
        )
        
        # Clasificar automáticamente en tus 14 categorías
        cat_limpia = categorizar_negocio(nombre, tipos_raw, descripcion)
        
        negocios.append({
            "Foto": url_foto,
            "Nombre": nombre,
            "Categoría": cat_limpia,
            "Descripción": descripcion,
            "Zona": zona.replace(", Chile", ""),
            "Dirección": direccion,
            "Teléfono": telefono,
            "Horarios": horarios,
            "Sitio Web": sitio_web
        })
        
        progreso.progress((i + 1) / total, text=f"Procesando: {nombre}...")
        time.sleep(0.05)
        
    progreso.empty()
    return pd.DataFrame(negocios)

# --- EJECUCIÓN ---
if "datos_extraidos" not in st.session_state:
    st.session_state.datos_extraidos = pd.DataFrame()

if boton_buscar:
    if not maps_key:
        st.warning("⚠️ Ingresa la clave de Google Maps en la barra izquierda.")
    else:
        query = f"{termino_especifico} en {zona_a_buscar}".strip() if termino_especifico else f"comercios en {zona_a_buscar}"
        with st.spinner(f"Consultando Google Maps para: '{query}'..."):
            df_res = consultar_google_maps_new(query, maps_key, zona_a_buscar)
            
            if not df_res.empty:
                st.session_state.datos_extraidos = df_res
                st.success(f"¡Listo! Se encontraron {len(df_res)} comercios.")
            else:
                st.info("No se encontraron resultados para esa búsqueda.")

# --- TABLA Y DESCARGAS ---
df_actual = st.session_state.datos_extraidos

if not df_actual.empty:
    st.subheader(f"Comercios Listos ({len(df_actual)})")
    
    col_csv, col_excel, _ = st.columns([1, 1, 3])
    
    # CSV compatible con Excel en español
    csv_buf = io.StringIO()
    csv_buf.write('\ufeff')
    df_actual.to_csv(csv_buf, index=False, sep=";")
    col_csv.download_button(
        label="📥 Descargar CSV",
        data=csv_buf.getvalue().encode('utf-8-sig'),
        file_name="directorio_requinoa.csv",
        mime="text/csv"
    )
    
    # Excel nativo
    xls_buf = io.BytesIO()
    with pd.ExcelWriter(xls_buf, engine="openpyxl") as wr:
        df_actual.to_excel(wr, index=False, sheet_name="Negocios")
    col_excel.download_button(
        label="📊 Descargar Excel",
        data=xls_buf.getvalue(),
        file_name="directorio_requinoa.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.write("")
    st.dataframe(
        df_actual,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Foto": st.column_config.ImageColumn("Foto"),
            "Descripción": st.column_config.TextColumn("Descripción / Acerca de", width="large"),
            "Sitio Web": st.column_config.LinkColumn("Sitio Web"),
            "Teléfono": st.column_config.TextColumn("Teléfono")
        }
    )
