import streamlit as st
import pandas as pd
import requests
import io
import time
from clasificador import CATEGORIAS_OFICIALES, categorizar_negocio

st.set_page_config(page_title="Mi Requínoa IA", page_icon="📍", layout="wide")

st.title("📍 Directorio Comercial con Redacción IA")
st.markdown("Comunas: **Requínoa**, **Los Lirios** y **El Abra**.")

# --- CLAVES ---
st.sidebar.header("🔑 Claves")

maps_key = st.secrets.get("GOOGLE_MAPS_KEY", "") or st.secrets.get("GOOGLE_API_KEY", "")
gemini_key = st.secrets.get("GEMINI_API_KEY", "")

if not maps_key:
    maps_key = st.sidebar.text_input("Google Maps Key", type="password")
if not gemini_key:
    gemini_key = st.sidebar.text_input("Gemini Key", type="password")

if maps_key and gemini_key:
    st.sidebar.success("✅ Conectado a Maps & Gemini")
else:
    st.sidebar.info("ℹ️ Configura tus claves")

st.sidebar.divider()

# --- PARÁMETROS ---
st.sidebar.header("🎯 Búsqueda")
zona_a_buscar = st.sidebar.selectbox(
    "Sector", 
    ["Requínoa, Chile", "Los Lirios, Requínoa, Chile", "El Abra, Requínoa, Chile", "Comuna de Requínoa, Chile"]
)

termino_especifico = st.sidebar.text_input(
    "Rubro (opcional)", 
    placeholder="Ej: peluqueria, taller..."
)

boton_buscar = st.sidebar.button("🚀 Extraer y Redactar con IA", type="primary")

# --- REDACTAR CON IA (PROMPT HUMANO Y NATURAL) ---
def redactar_descripcion_ia(nombre, rubro, reviews, key):
    if not key:
        return "Servicio comercial local ubicado en la comuna."
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    
    prompt = f"""
    Eres un redactor chileno experto en guías comerciales locales.
    Escribe una descripción humana, atractiva y cercana para este negocio en Requínoa.
    
    REGLAS:
    - Longitud: MÁXIMO 280 CARACTERES.
    - Tono: Cálido, profesional y descriptivo.
    - NUNCA uses frases robot como "Atención al cliente en...", "Este negocio ofrece...", ni repitas el nombre de forma tonta.
    - Menciona especialidades y ambiente.
    
    EJEMPLO DE LO QUE QUIERO:
    "Salón de belleza y peluquería atendido por profesionales. Especialistas en corte unisex, colorimetría y tratamientos capilares en un ambiente acogedor y cómodo."
    
    DATOS DEL NEGOCIO:
    - Nombre: {nombre}
    - Rubro: {rubro}
    - Lo que dice la gente: {reviews}
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 120}
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        
        if "error" in data:
            # Si hay error en la clave, lo mostramos
            return f"[Error Gemini: {data['error'].get('message', 'Clave sin permisos')}]"
            
        texto = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        # Limpiar comillas extras si las pone
        texto = texto.replace('"', '').replace('\n', ' ')
        if len(texto) > 320:
            texto = texto[:317] + "..."
        return texto
    except Exception as e:
        return f"Comercio de {rubro} en {nombre}."

# --- CONSULTAR GOOGLE MAPS ---
def consultar_google_maps_new(query, m_key, g_key, zona):
    url = "https://places.googleapis.com/v1/places:searchText"
    
    mascara = [
        "places.displayName", "places.formattedAddress", "places.nationalPhoneNumber",
        "places.websiteUri", "places.types", "places.primaryTypeDisplayName",
        "places.rating", "places.regularOpeningHours", "places.photos", "places.reviews"
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
    progreso = st.progress(0, text="Procesando con Inteligencia Artificial...")
    
    for i, p in enumerate(lugares):
        nombre = p.get("displayName", {}).get("text", "")
        tipos_raw = ", ".join(p.get("types", []))
        rubro_es = p.get("primaryTypeDisplayName", {}).get("text", "Comercio")
        direccion = p.get("formattedAddress", "")
        telefono = p.get("nationalPhoneNumber", "")
        sitio_web = p.get("websiteUri", "")
        
        # Horarios
        hours_obj = p.get("regularOpeningHours", {})
        horarios_list = hours_obj.get("weekdayDescriptions", [])
        horarios = " | ".join(horarios_list) if horarios_list else "No informado"
        
        # Foto
        fotos = p.get("photos", [])
        url_foto = f"https://places.googleapis.com/v1/{fotos[0].get('name')}/media?maxWidthPx=400&key={m_key}" if fotos else ""
        
        # Reseñas
        revs = p.get("reviews", [])
        opiniones = " ".join([r.get("text", {}).get("text", "") for r in revs[:3]]) if revs else "Buena atención y servicio."
        
        progreso.progress((i + 1) / total, text=f"Redactando con IA: {nombre} ({i+1}/{total})...")
        
        # LLAMADA A GEMINI
        desc_ia = redactar_descripcion_ia(nombre, rubro_es, opiniones, g_key)
        
        # CLASIFICACIÓN
        cat_limpia = categorizar_negocio(nombre, tipos_raw, desc_ia)
        
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
        query = f"{termino_especifico} en {zona_a_buscar}".strip() if termino_especifico else f"comercios en {zona_a_buscar}"
        with st.spinner(f"Buscando y redactando para: '{query}'..."):
            df_res = consultar_google_maps_new(query, maps_key, gemini_key, zona_a_buscar)
            
            if not df_res.empty:
                st.session_state.datos_extraidos = df_res
                st.success(f"¡Se encontraron y redactaron {len(df_res)} comercios con IA!")
            else:
                st.info("No hubo resultados.")

# --- TABLA Y DESCARGAS ---
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
            "Descripción (IA)": st.column_config.TextColumn("Descripción IA", width="large"),
            "Sitio Web": st.column_config.LinkColumn("Sitio Web"),
            "Teléfono": st.column_config.TextColumn("Teléfono")
        }
    )
