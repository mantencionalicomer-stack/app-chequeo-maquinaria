import streamlit as st
import uuid
import pandas as pd
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Chequeo Maquinaria", page_icon="📝", layout="wide")

@st.cache_resource
def init_connection():
    return create_engine(st.secrets["SUPABASE_URI"])

try:
    engine = init_connection()
except Exception as e:
    st.error("Error al conectar con la base de datos. Verifica los Secrets.")
    st.stop()

def run_query(query, params=None):
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        conn.commit()
        if query.strip().upper().startswith("SELECT"):
            return pd.DataFrame(result.fetchall(), columns=result.keys())
        return None

if 'inspector_nombre' not in st.session_state:
    st.session_state.inspector_nombre = "Álvaro Cumsille"

with st.sidebar:
    st.title("📝 Control de Equipos")
    st.write(f"👷 **{st.session_state.inspector_nombre}**")
    st.divider()
    menu = st.radio("Navegación:", ["Realizar Chequeo", "Historial de Chequeos"])

if menu == "Realizar Chequeo":
    st.header("📋 Nuevo Chequeo Diario")
    
    # 1. Filtro Principal: Selector de Planta
    col_p1, col_p2 = st.columns([1, 2])
    with col_p1:
        planta_seleccionada = st.selectbox("🏭 Seleccione Planta", ["La Florida", "Quilicura"])
    
    # 2. Consultar equipos filtrados por la planta seleccionada
    df_equipos = run_query(f"SELECT codigo_interno, nombre, categoria FROM equipos WHERE planta = '{planta_seleccionada}' ORDER BY codigo_interno")
    
    if df_equipos is not None and not df_equipos.empty:
        col1, col2 = st.columns(2)
        with col1:
            equipo_display = df_equipos["codigo_interno"] + " - " + df_equipos["nombre"]
            equipo_seleccionado = st.selectbox("Seleccione el Equipo", equipo_display)
            
            cod_seleccionado = equipo_seleccionado.split(" - ")[0]
            categoria_seleccionada = df_equipos[df_equipos["codigo_interno"] == cod_seleccionado].iloc[0]["categoria"]
            
        with col2:
            turno = st.selectbox("Turno", ["Día", "Tarde", "Noche"])
            fecha = st.date_input("Fecha")
        
        st.divider()
        st.subheader(f"Ítems de Revisión: {categoria_seleccionada}")
        
        # 3. Traer preguntas de la BD según la categoría
        df_preguntas = run_query(f"SELECT grupo, orden, descripcion FROM plantilla_items WHERE categoria_equipo = '{categoria_seleccionada}' ORDER BY orden")
        
        if df_preguntas is not None and not df_preguntas.empty:
            with st.form("form_chequeo"):
                grupos = df_preguntas["grupo"].unique()
                for grupo in grupos:
                    st.markdown(f"#### {grupo}")
                    items_grupo = df_preguntas[df_preguntas["grupo"] == grupo]
                    
                    for _, row in items_grupo.iterrows():
                        c_item, c_estado, c_obs = st.columns([3, 1, 2])
                        c_item.write(f"{row['orden']}. {row['descripcion']}")
                        # Requerimiento: Cumple / No Cumple
                        c_estado.selectbox("Estado", ["Cumple", "No Cumple", "N/A"], key=f"est_{row['orden']}", label_visibility="collapsed")
                        c_obs.text_input("Observación", key=f"obs_{row['orden']}", label_visibility="collapsed")
                
                st.divider()
                st.text_area("Observaciones Generales")
                if st.form_submit_button("Guardar Chequeo ✅"):
                    st.success("¡Estructura lista! El siguiente paso será la inserción a la BD del formulario guardado.")
        else:
            st.warning(f"No hay preguntas configuradas para {categoria_seleccionada}.")
    else:
        st.warning(f"No hay equipos registrados para la planta {planta_seleccionada}.")

elif menu == "Historial de Chequeos":
    st.header("📋 Historial de Inspecciones")
    st.info("Módulo en construcción...")
