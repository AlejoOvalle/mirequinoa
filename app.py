import streamlit as st
import pandas as pd
import requests
import io
import time
from clasificador import CATEGORIAS_OFICIALES, categorizar_negocio

st.set_page_config(
    page_title="Directorio Comercial con IA - Mi Requínoa", 
    page_icon="📍", 
    layout="wide"
)

st.title("📍 Extractor Comercial con Redacción IA")
st.markdown("Directorio para **Requínoa**, **Los Lirios** y **El Abra** con Google Maps y **Gemini IA**.")

# --- BARRA LATERAL: 1. CLAVES ---
st.sidebar.header("🔑 Conexión y Claves")

if "GOOGLE_MAPS_KEY" in st.secrets:
    maps_key = st.secrets["GOOGLE_MAPS_KEY"]
elif "GOOGLE_API_KEY" in st.secrets:
    maps_key = st.secrets["GOOGLE_API_KEY"]
else:
    maps_key = st.sidebar.text_input("Google Maps API Key", type="password")

if "GEMINI_API_KEY" in st.secrets:
    gemini_key = st.secrets["GEMINI_API_KEY"]
else:
    gemini_key = st.sidebar.text_input("Gemini API Key", type="password")

if maps_key and gemini_key:
    st.sidebar.success("✅ Google Maps & Gemini Conectados")
else:
    st.sidebar.info("ℹ️ Configura las claves para continuar")

st.sidebar.divider()

# --- BARRA LATERAL: 2. PARÁMETROS Y BOTÓN DIRECTO ---
st.sidebar.header("🎯 Parámetros de Extracción")
zona_a_buscar = st.sidebar.selectbox(
    "Sector a escanear", 
    ["Requínoa, Chile", "Los Lirios, Requínoa, Chile", "El Abra, Requínoa, Chile", "Comuna de Requínoa, Chile"]
)

termino_especifico = st.sidebar.text_input(
    "Rubro o negocio específico (opcional)", 
    placeholder="Ej: peluqueria, taller, cafe..."
)

# EL BOTÓN COLOCADO AQUÍ MISMO PARA QUE SIEMPRE SEA VISIBLE
boton_buscar = st.sidebar.button("🚀 Extraer y Redactar con IA", type="primary")

# --- FUNCIONES DE SOPORTE ---
def redactar_descripcion_ia(nombre, rubro, reviews_texto, key):
    if not key:
        return f"{rubro} ubicado en {nombre}."
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    
    prompt = f"""
    Actúa como redactor de una guía comercial en Chile.
    Escribe una descripción breve y atractiva (MÁXIMO 320 CARACTERES) en tercera persona.
    Sin saludos, sin comillas y sin introducciones.
    Local: {nombre} | Rubro: {rubro} | Opiniones: {reviews_texto}
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 100}
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=8)
        data = resp.json()
        texto = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        if len(texto) > 320:
            texto = texto[:317] + "..."
        return texto
    except Exception:
        return f"{rubro}. Atención al público en el sector de {nombre}."

def consultar_google_maps_new(query, m_key, g_key, zona_nombre):
    url = "https://places.googleapis.com/v1/places:searchText"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": m_key,
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
    total = len(lugares)
    if total == 0:
        return pd.DataFrame()

    negocios_extraidos = []
    progreso = st.progress(0, text="Procesando datos con IA...")
    
    for i, p in enumerate(lugares):
        nombre = p.get("displayName", {}).get("text", "")
        tipos_raw = ", ".join(p.get("types", []))
        rubro_es = p.get("primaryTypeDisplayName", {}).get("text", "Comercio")
        direccion = p.get("formattedAddress", "")
        telefono = p.get("nationalPhoneNumber", "")
        sitio_web = p.get("websiteUri", "")
        
        horarios_lista = p.get("regularOpeningHours", {}).get("weekdayDescriptions", [])
        horarios_texto = " | ".join(horarios_lista) if horarios_lista else "No informado"
        
        fotos = p.get("photos", [])
        url_foto = f"https://places.googleapis.com/v1/{fotos[0].get('name')}/media?maxWidthPx=40
