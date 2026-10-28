import streamlit as st
import pandas as pd
import io
from clasificador import CATEGORIAS_OFICIALES, categorizar_negocio

st.set_page_config(
    page_title="Directorio Comercial Mi Requínoa",
    page_icon="📍",
    layout="wide"
)

@st.cache_data
def load_data():
    try:
        # Detecta automáticamente si el archivo usa ';' o ',' y evita que se caiga
        df = pd.read_csv("data/negocios.csv", sep=None, engine='python', on_bad_lines='skip')
    except Exception:
        df = pd.DataFrame(columns=["Nombre", "Zona", "Tipo de Negocio", "Dirección", "Teléfono", "Email", "Sitio Web", "Descripción"])
    
    df = df.fillna("")
    
    # Asegurar que las columnas requeridas existan
    cols_requeridas = ["Nombre", "Zona", "Tipo de Negocio", "Dirección", "Teléfono", "Email", "Sitio Web", "Descripción"]
    for col in cols_requeridas:
        if col not in df.columns:
            df[col] = ""

    df["Tipo de Negocio"] = df.apply(
        lambda r: categorizar_negocio(str(r["Nombre"]), str(r["Tipo de Negocio"]), str(r["Descripción"])),
        axis=1
    )
    return df

df_original = load_data()

# --- FILTROS (BARRA LATERAL) ---
st.sidebar.title("📍 Filtros de Búsqueda")

zonas = ["Todas", "Requínoa", "Los Lirios", "El Abra"]
zona_sel = st.sidebar.selectbox("Localidad / Sector", zonas)

lista_categorias = ["Todas las Categorías"] + list(CATEGORIAS_OFICIALES.keys())
categoria_sel = st.sidebar.selectbox("Rubro Oficial", lista_categorias)

busqueda = st.sidebar.text_input("Buscar por palabra clave", placeholder="Ej: panadería, repuestos, riego...")

# Aplicar filtros
df_filtrado = df_original.copy()

if zona_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Zona"].str.contains(zona_sel, case=False, na=False)]

if categoria_sel != "Todas las Categorías":
    df_filtrado = df_filtrado[df_filtrado["Tipo de Negocio"] == categoria_sel]

if busqueda:
    mask = (
        df_filtrado["Nombre"].str.contains(busqueda, case=False, na=False) |
        df_filtrado["Descripción"].str.contains(busqueda, case=False, na=False) |
        df_filtrado["Dirección"].str.contains(busqueda, case=False, na=False)
    )
    df_filtrado = df_filtrado[mask]

# --- VISTA PRINCIPAL ---
st.title("📍 Directorio Comercial y Comunitario")
st.markdown("Comercios, servicios y emprendimientos de **Requínoa**, **Los Lirios** y **El Abra**.")

col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("Negocios Encontrados", len(df_filtrado))
col_m2.metric("Con Teléfono", len(df_filtrado[df_filtrado["Teléfono"] != ""]))
col_m3.metric("Con Email", len(df_filtrado[df_filtrado["Email"] != ""]))

st.divider()

# --- DESCARGAS ---
st.subheader("Descargar Resultados")
col_csv, col_excel, _ = st.columns([1, 1, 3])

csv_buffer = io.StringIO()
csv_buffer.write('\ufeff')
df_filtrado.to_csv(csv_buffer, index=False, sep=";")

col_csv.download_button(
    label="📥 Descargar (.CSV)",
    data=csv_buffer.getvalue().encode('utf-8-sig'),
    file_name=f"mirequinoa_{zona_sel.lower()}.csv",
    mime="text/csv"
)

excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
    df_filtrado.to_excel(writer, index=False, sheet_name="Directorio")

col_excel.download_button(
    label="📊 Descargar (.XLSX)",
    data=excel_buffer.getvalue(),
    file_name=f"mirequinoa_{zona_sel.lower()}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.write("")

# --- TABLA DE DATOS ---
st.dataframe(
    df_filtrado[["Nombre", "Tipo de Negocio", "Zona", "Dirección", "Teléfono", "Email", "Sitio Web", "Descripción"]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Sitio Web": st.column_config.LinkColumn("Sitio Web"),
        "Email": st.column_config.LinkColumn("Email"),
        "Tipo de Negocio": st.column_config.TextColumn("Categoría")
    }
)
