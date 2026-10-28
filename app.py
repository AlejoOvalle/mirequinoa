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
st.markdown("Directorio comercial para **Requínoa**, **Los Lirios** y **El Abra** con datos de Google Maps y descripciones generadas por **Gemini IA**.")

# --- GESTIÓN DE CLAVES (SECRETS O MANUAL) ---
st.sidebar.header("🔑 Conexión y Claves")

# 1. Clave de Google Maps
if "GOOGLE_MAPS_KEY" in st.secrets:
    maps_key = st.secrets["GOOGLE_MAPS_KEY"]
elif "GOOGLE_API_KEY" in st.secrets:
    maps_key = st.secrets["GOOGLE_API_KEY"]
else:
    maps_key = st.sidebar.text_input("Google Maps API Key", type="password")

# 2. Clave de Gemini IA
if "GEMINI_API_KEY" in st.secrets:
    gemini_key = st.secrets["GEMINI_API_KEY"]
else:
    gemini_key = st.sidebar.text_input("Gemini API Key (AI Studio)", type="password")

# Indicador de estado
if maps_key and gemini_key:
    st.sidebar.success("✅ Google Maps & Gemini Conectados")
elif maps_key:
    st.sidebar.info("ℹ️ Google Maps conectado (Falta clave de Gemini)")
else:
    st.sidebar.warning("⚠️ Ingresa las claves para comenzar")

st.sidebar.divider()

# --- PARÁMETROS DE BÚSQUEDA ---
st.sidebar.header("🎯 Parámetros de Extracción")
zona_a_buscar = st.sidebar.selectbox(
    "Sector a escanear", 
    ["Requínoa, Chile", "Los Lirios, Requínoa, Chile", "El Abra, Requínoa, Chile", "Comuna de Requínoa, Chile"]
)

termino_especifico = st.sidebar.text_input(
    "Rubro o negocio específico (opcional)", 
    placeholder="Ej: peluqueria, taller, restaurante..."
)
