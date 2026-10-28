import streamlit as st
import pandas as pd
import requests
import io
import time
from clasificador import (
    CATEGORIAS_OFICIALES, 
    categorizar_negocio
)

st.set_page_config(
    page_title="Mi Requínoa IA", 
    page_icon="📍", 
    layout="wide"
)

st.title("📍 Directorio Comercial con Redacción IA")
st.markdown("Comunas: **Requínoa**, **Los Lirios** y **El Abra**.")

# --- CLAVES ---
st.sidebar.header("🔑 Claves")

if "GOOGLE_MAPS_KEY" in st.secrets:
    maps_key = st.secrets["GOOGLE_MAPS_KEY"]
elif "GOOGLE_API_KEY" in st.secrets:
    maps_key = st.secrets["GOOGLE_API_KEY"]
else:
    maps_key = st.sidebar.text_input(
        "Google Maps Key", 
        type="password"
    )

if "GEMINI_API_KEY" in st.secrets:
    gemini_key = st.secrets["GEMINI_API_KEY"]
else:
    gemini_key = st.sidebar.text_input(
        "Gemini Key", 
        type="password"
    )

if maps_key and gemini_key:
    st.sidebar.success("✅ Conectado a Maps & Gemini")
else:
    st.sidebar.info("ℹ️ Configura tus claves")

st.sidebar.divider()

# --- PARÁMETROS ---
st.sidebar.header("🎯 Búsqueda")

sectores = [
    "Requínoa, Chile", 
    "Los Lirios, Requínoa, Chile", 
    "El Abra, Requínoa, Chile", 
    "Comuna de Requínoa, Chile"
]

zona_a_buscar = st.sidebar.selectbox(
    "Sector", 
    sectores
)

termino_especifico = st.sidebar.text_input(
    "Rubro (opcional)", 
    placeholder="Ej: peluqueria, taller..."
)

# BOTÓN
boton_buscar = st.sidebar.button(
    "🚀 Extraer y Redactar con IA", 
    type="primary"
)

# --- REDACTAR CON IA ---
def redactar_descripcion_ia(nombre, rubro, reviews, key):
    if not key:
        return f"{rubro} en {nombre}."
        
    url = "https://generativelanguage.googleapis.com"
    url += f"/v1beta/models/gemini-1.5-flash:generateContent"
    url += f"?key={key}"
    
    prompt = f"""
    Redacta una guía comercial en Chile.
    Descripción atractiva de MÁXIMO 320 CARACTERES.
    Sin saludos ni comillas. Directo al grano.
    Local: {nombre} | Rubro: {rubro} | Opiniones: {reviews}
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4, 
            "maxOutputTokens": 100
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=8)
        data = resp.json()
        cand = data["candidates"][0]["content"]["parts"][0]
        texto = cand["text"].strip()
        if len(texto) > 320:
            texto = texto[:317] + "..."
        return texto
    except Exception:
        return f"{rubro}. Atención al cliente en {nombre}."

# --- CONSULTAR GOOGLE MAPS ---
def consultar_google_maps_new(query, m_key, g_key, zona):
    url = "https://places.googleapis.com/v1/places:searchText"
    
    mascara = [
        "places.displayName",
        "places.formattedAddress",
        "places.nationalPhoneNumber",
        "places.websiteUri",
        "places.types",
        "places.primaryTypeDisplayName",
        "places.rating",
        "places.regularOpeningHours",
        "places.photos",
        "places.reviews"
    ]
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": m_key,
        "X-Goog-FieldMask": ",".join(mascara)
    }
    
    payload = {
        "textQuery": query, 
        "languageCode": "es"
    }
    
    resp = requests.post(url, headers=headers, json=payload)
    data = resp.json()
    
    if "error" in data:
        st.error(data['error'].get('message', 'Error'))
        return pd.DataFrame()
        
    lugares = data.get("places", [])
    total = len(lugares)
    if total == 0:
        return pd.DataFrame()

    negocios = []
    progreso = st.progress(0, text="Procesando...")
    
    for i, p in enumerate(lugares):
        nombre = p.get("displayName", {}).get("text", "")
        tipos_raw = ", ".join(p.get("types", []))
        
        rubro_obj = p.get("primaryTypeDisplayName", {})
        rubro_es = rubro_obj.get("text", "Comercio")
        
        direccion = p.get("formattedAddress", "")
        telefono = p.get("nationalPhoneNumber", "")
        sitio_web = p.get("websiteUri", "")
        
        # Horarios
        hours_obj = p.get("regularOpeningHours", {})
        horarios_list = hours_obj.get("weekdayDescriptions", [])
        if horarios_list:
            horarios = " | ".join(horarios_list)
        else:
            horarios = "No informado"
        
        # Foto (construida en líneas cortas)
        fotos = p.get("photos", [])
        if fotos:
            f_name = fotos[0].get("name", "")
            url_foto = "https://places.googleapis.com/v1/"
            url_foto += f"{f_name}/media?maxWidthPx=400"
            url_foto += f"&key={m_key}"
        else:
            url_foto = ""
        
        # Reviews
        revs = p.get("reviews", [])
        opiniones = " ".join(
            [r.get("text", {}).get("text", "") for r in revs[:3]]
        ) if revs else "Buena atención."
        
        progreso.progress(
            (i + 1) / total, 
            text=f"Redactando: {nombre}..."
        )
        
        desc_ia = redactar_descripcion_ia(
            nombre, rubro_es, opiniones, g_key
        )
        
        cat_limpia = categorizar_negocio(
            nombre, tipos_raw, desc_ia
        )
        
        negocios.append({
            "Foto": url_foto,
            "Nombre": nombre,
            "Categoría": cat_limpia,
            "Descripción (IA)": desc_ia,
            "Zona": zona.replace(", Chile", ""),
            "Dirección": direccion,
            "Teléfono": telefono,
            "Horarios": horarios,
            "Sitio Web": sitio_web
        })
        time.sleep(0.1)
        
    progreso.empty()
    return pd.DataFrame(negocios)

# --- EJECUCIÓN ---
if "datos_extraidos" not in st.session_state:
    st.session_state.datos_extraidos = pd.DataFrame()

if boton_buscar:
    if not maps_key:
        st.warning("⚠️ Falta la clave de Google Maps.")
    else:
        if termino_especifico:
            query = f"{termino_especifico} en {zona_a_buscar}"
        else:
            query = f"comercios en {zona_a_buscar}"
            
        with st.spinner(f"Buscando: '{query}'..."):
            df_res = consultar_google_maps_new(
                query, maps_key, gemini_key, zona_a_buscar
            )
            
            if not df_res.empty:
                st.session_state.datos_extraidos = df_res
                st.success(f"¡Se encontraron {len(df_res)} comercios!")
            else:
                st.info("No hubo resultados.")

# --- DESCARGAS Y TABLA ---
df_actual = st.session_state.datos_extraidos

if not df_actual.empty:
    st.subheader(f"Comercios Listos ({len(df_actual)})")
    
    col_csv, col_excel, _ = st.columns([1, 1, 3])
    
    # CSV
    csv_buf = io.StringIO()
    csv_buf.write('\ufeff')
    df_actual.to_csv(csv_buf, index=False, sep=";")
    col_csv.download_button(
        label="📥 Descargar CSV",
        data=csv_buf.getvalue().encode('utf-8-sig'),
        file_name="directorio_requinoa.csv",
        mime="text/csv"
    )
    
    # Excel
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
            "Descripción (IA)": st.column_config.TextColumn(
                "Descripción IA", 
                width="large"
            ),
            "Sitio Web": st.column_config.LinkColumn("Sitio Web"),
            "Teléfono": st.column_config.TextColumn("Teléfono")
        }
    )
