import streamlit as st
import pandas as pd
import requests
import io
from clasificador import CATEGORIAS_OFICIALES, categorizar_negocio

st.set_page_config(
    page_title="Extractor FindAll WP - Mi Requínoa", 
    page_icon="📍", 
    layout="wide"
)

st.title("📍 Extractor de Negocios para FindAll (WordPress)")
st.markdown("Genera archivos compatibles directamente con **WP All Import** para el tema FindAll.")

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
st.sidebar.header("🎯 Parámetros de Búsqueda")
zona_a_buscar = st.sidebar.selectbox(
    "Localidad / Ubicación (Taxonomía WP)", 
    ["Requínoa", "Los Lirios", "El Abra", "Comuna de Requínoa"]
)

termino_especifico = st.sidebar.text_input(
    "Rubro a buscar (opcional)", 
    placeholder="Ej: ferreteria, restaurante, taller..."
)

boton_buscar = st.sidebar.button("🚀 Extraer Datos para WordPress", type="primary")

# --- CONSULTA A GOOGLE MAPS ---
def consultar_google_maps(query, key, zona_taxonomia):
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
        st.error(f"Error de Google: {data['error'].get('message', 'Desconocido')}")
        return pd.DataFrame()
        
    lugares = data.get("places", [])
    if not lugares:
        return pd.DataFrame()

    negocios = []
    
    for p in lugares:
        title = p.get("displayName", {}).get("text", "")
        tipos_raw = ", ".join(p.get("types", []))
        rubro_es = p.get("primaryTypeDisplayName", {}).get("text", "Comercio")
        address = p.get("formattedAddress", "")
        phone = p.get("nationalPhoneNumber", "")
        website = p.get("websiteUri", "")
        rating = p.get("rating", "")
        votos = p.get("userRatingCount", 0)
        
        # Coordenadas exactas para el Pin del mapa en FindAll
        loc = p.get("location", {})
        lat = loc.get("latitude", "")
        lng = loc.get("longitude", "")
        
        # Horarios
        hours_obj = p.get("regularOpeningHours", {})
        horarios_list = hours_obj.get("weekdayDescriptions", [])
        working_hours = " | ".join(horarios_list) if horarios_list else "No informado"
        
        # Foto oficial (URL compatible con WP All Import Media Downloader)
        fotos = p.get("photos", [])
        if fotos:
            f_name = fotos[0].get("name", "")
            featured_image = f"https://places.googleapis.com/v1/{f_name}/media?maxWidthPx=800&key={key}"
        else:
            featured_image = ""
            
        # Categoría oficial según tu listado
        category = categorizar_negocio(title, tipos_raw, rubro_es)
        
        # Generar contenido base para la ficha (Post Content en FindAll)
        rating_texto = f"<p>⭐ Calificación en Google: <strong>{rating}</strong> ({votos} opiniones)</p>" if rating else ""
        content = f"<p>{rubro_es} ubicado en {zona_taxonomia}, sector {title}.</p>{rating_texto}"
        
        # Estructura adaptada para WP All Import
        negocios.append({
            "title": title,
            "category": category,
            "location_tax": zona_taxonomia,
            "address": address,
            "latitude": lat,
            "longitude": lng,
            "phone": phone,
            "website": website,
            "working_hours": working_hours,
            "featured_image": featured_image,
            "content": content
        })
        
    return pd.DataFrame(negocios)

# --- EJECUCIÓN ---
if "datos_extraidos" not in st.session_state:
    st.session_state.datos_extraidos = pd.DataFrame()

if boton_buscar:
    if not maps_key:
        st.warning("⚠️ Debes configurar la clave de Google Maps en la barra lateral.")
    else:
        query_text = f"{termino_especifico} en {zona_a_buscar}, Chile".strip() if termino_especifico else f"comercios en {zona_a_buscar}, Chile"
        with st.spinner(f"Extrayendo para WordPress: '{query_text}'..."):
            df_res = consultar_google_maps(query_text, maps_key, zona_a_buscar)
            
            if not df_res.empty:
                st.session_state.datos_extraidos = df_res
                st.success(f"¡Éxito! {len(df_res)} comercios listos para importar a FindAll.")
            else:
                st.info("No se encontraron comercios.")

# --- DESCARGA PARA WP ALL IMPORT ---
df_actual = st.session_state.datos_extraidos

if not df_actual.empty:
    st.subheader(f"Comercios para Importar ({len(df_actual)})")
    
    col_csv, col_excel, _ = st.columns([1, 1, 3])
    
    # CSV configurado para WP All Import (UTF-8 con punto y coma)
    csv_buf = io.StringIO()
    csv_buf.write('\ufeff')
    df_actual.to_csv(csv_buf, index=False, sep=";")
    col_csv.download_button(
        label="📥 Descargar CSV para WP All Import",
        data=csv_buf.getvalue().encode('utf-8-sig'),
        file_name=f"import_findall_{zona_a_buscar.lower().replace(' ', '_')}.csv",
        mime="text/csv"
    )
    
    # Excel
    xls_buf = io.BytesIO()
    with pd.ExcelWriter(xls_buf, engine="openpyxl") as wr:
        df_actual.to_excel(wr, index=False, sheet_name="WP_Import")
    col_excel.download_button(
        label="📊 Descargar Excel",
        data=xls_buf.getvalue(),
        file_name=f"import_findall_{zona_a_buscar.lower().replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.write("")
    
    # Vista previa
    st.dataframe(
        df_actual,
        use_container_width=True,
        hide_index=True,
        column_config={
            "featured_image": st.column_config.ImageColumn("Foto"),
            "website": st.column_config.LinkColumn("Sitio Web"),
            "latitude": st.column_config.NumberColumn("Latitud", format="%.6f"),
            "longitude": st.column_config.NumberColumn("Longitud", format="%.6f")
        }
    )
