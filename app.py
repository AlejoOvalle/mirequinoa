import streamlit as st
import pandas as pd
import requests
import io
import time
from clasificador import CATEGORIAS_OFICIALES, categorizar_negocio

st.set_page_config(page_title="Extractor & IA - Mi Requínoa", page_icon="📍", layout="wide")

st.title("📍 Directorio Comercial con Redacción IA")
st.markdown("Extractor de comercios para **Requínoa**, **Los Lirios** y **El Abra** con descripciones generadas por **Google Gemini**.")

# --- BARRA LATERAL ---
st.sidebar.header("🔑 Conexión")

if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
    st.sidebar.success("✅ Conectado a Google Maps & Gemini")
else:
    api_key = st.sidebar.text_input("Google API Key", type="password")

st.sidebar.divider()
st.sidebar.header("🎯 Parámetros de Extracción")
zona_a_buscar = st.sidebar.selectbox(
    "Sector a escanear", 
    ["Requínoa, Chile", "Los Lirios, Requínoa, Chile", "El Abra, Requínoa, Chile", "Comuna de Requínoa, Chile"]
)

termino_especifico = st.sidebar.text_input(
    "Rubro o negocio específico (opcional)", 
    placeholder="Ej: peluqueria, restaurant, ferreteria..."
)

# --- FUNCIÓN: REDACTAR DESCRIPCIÓN CON GEMINI IA (MAX 320 CARACTERES) ---
def redactar_descripcion_ia(nombre, rubro, reviews_texto, key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    
    prompt = f"""
    Actúa como un redactor de guías locales y comerciales de Chile.
    Escribe una descripción atractiva, fluida y en tercera persona sobre este negocio.
    Sintetiza qué ofrece y qué destaca la clientela en un tono natural.
    
    REGLAS ESTRICTAS:
    - Longitud: MÁXIMO 320 CARACTERES.
    - No uses saludos, ni comillas, ni introducciones tipo "Este negocio ofrece...".
    - Comienza directamente describiendo el lugar o su especialidad.

    Datos del local:
    - Nombre: {nombre}
    - Rubro: {rubro}
    - Reseñas / Comentarios de clientes: {reviews_texto}
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 100}
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=8)
        data = resp.json()
        texto = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # Asegurar límite estricto de 320 caracteres
        if len(texto) > 320:
            texto = texto[:317] + "..."
        return texto
    except Exception:
        # Fallback elegante si falla la IA
        return f"{rubro}. Comercio y atención al público ubicado en el sector de {nombre}."

# --- FUNCIÓN DE EXTRACCIÓN GOOGLE MAPS ---
def consultar_google_maps_new(query, key):
    url = "https://places.googleapis.com/v1/places:searchText"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": (
            "places.displayName,places.formattedAddress,places.nationalPhoneNumber,"
            "places.websiteUri,places.types,places.primaryTypeDisplayName,places.rating,"
            "places.regularOpeningHours,places.photos,places.reviews"
        )
    }
    
    payload = {"textQuery": query, "languageCode": "es"}
    resp = requests.post(url, headers=headers, json=payload)
    data = resp.json()
    
    if "error" in data:
        st.error(f"Error de Google: {data['error'].get('message', 'Error desconocido')}")
        return pd.DataFrame()
        
    lugares = data.get("places", [])
    negocios_extraidos = []
    
    # Barra de progreso visual
    progreso = st.progress(0, text="Extrayendo y redactando con IA...")
    total = len(lugares)
    
    for i, p in enumerate(lugares):
        nombre = p.get("displayName", {}).get("text", "")
        tipos_raw = ", ".join(p.get("types", []))
        rubro_es = p.get("primaryTypeDisplayName", {}).get("text", "Comercio")
        direccion = p.get("formattedAddress", "")
        telefono = p.get("nationalPhoneNumber", "")
        sitio_web = p.get("websiteUri", "")
        
        # Horarios
        horarios_lista = p.get("regularOpeningHours", {}).get("weekdayDescriptions", [])
        horarios_texto = " | ".join(horarios_lista) if horarios_lista else "No informado"
        
        # Foto
        fotos = p.get("photos", [])
        url_foto = f"https://places.googleapis.com/v1/{fotos[0].get('name')}/media?maxWidthPx=400&key={key}" if fotos else ""
        
        # Juntar reseñas para darle contexto a la IA
        reviews = p.get("reviews", [])
        opiniones = " ".join([r.get("text", {}).get("text", "") for r in reviews[:3]]) if reviews else "Excelente atención."
        
        # Llamar a Gemini para redactar la descripción
        descripcion_ia = redactar_descripcion_ia(nombre, rubro_es, opiniones, key)
        
        categoria_limpia = categorizar_negocio(nombre, tipos_raw, descripcion_ia)
        
        negocios_extraidos.append({
            "Foto": url_foto,
            "Nombre": nombre,
            "Categoría Asignada": categoria_limpia,
            "Descripción (IA)": descripcion_ia,
            "Zona": zona_a_buscar.replace(", Chile", ""),
            "Dirección": direccion,
            "Teléfono": telefono,
            "Horarios de Atención": horarios_texto,
            "Sitio Web": sitio_web
        })
        
        progreso.progress((i + 1) / total, text=f"Redactando con IA para {nombre} ({i+1}/{total})...")
        time.sleep(0.1)
        
    progreso.empty()
    return pd.DataFrame(negocios_extraidos)

# --- ACCIÓN DE BÚSQUEDA ---
if "datos_extraidos" not in st.session_state:
    st.session_state.datos_extraidos = pd.DataFrame()

if st.sidebar.button("🚀 Extraer y Redactar con IA"):
    if not api_key:
        st.warning("⚠️ No se encontró la clave de API.")
    else:
        query = f"{termino_especifico} en {zona_a_buscar}".strip() if termino_especifico else f"comercios en {zona_a_buscar}"
        with st.spinner(f"Consultando Google Maps para: '{query}'..."):
            df_resultado = consultar_google_maps_new(query, api_key)
            
            if not df_resultado.empty:
                st.session_state.datos_extraidos = df_resultado
                st.success(f"¡Éxito! Se procesaron {len(df_resultado)} comercios con descripciones personalizadas.")
            else:
                st.info("No se encontraron resultados.")

# --- RESULTADOS Y DESCARGAS ---
df_actual = st.session_state.datos_extraidos

if not df_actual.empty:
    st.subheader(f"Comercios Listos ({len(df_actual)})")
    
    col_csv, col_excel, _ = st.columns([1, 1, 3])
    
    # CSV
    csv_buffer = io.StringIO()
    csv_buffer.write('\ufeff')
    df_actual.to_csv(csv_buffer, index=False, sep=";")
    col_csv.download_button(
        label="📥 Descargar (.CSV)",
        data=csv_buffer.getvalue().encode('utf-8-sig'),
        file_name="directorio_requinoa_ia.csv",
        mime="text/csv"
    )
    
    # Excel
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df_actual.to_excel(writer, index=False, sheet_name="Negocios")
    col_excel.download_button(
        label="📊 Descargar (.XLSX)",
        data=excel_buffer.getvalue(),
        file_name="directorio_requinoa_ia.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.write("")
    
    # Tabla con previsualización
    st.dataframe(
        df_actual,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Foto": st.column_config.ImageColumn("Foto", help="Foto de portada"),
            "Descripción (IA)": st.column_config.TextColumn("Descripción redactada por IA", width="large"),
            "Sitio Web": st.column_config.LinkColumn("Sitio Web"),
            "Teléfono": st.column_config.TextColumn("Teléfono")
        }
    )
