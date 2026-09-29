import streamlit as st
import uuid
import pandas as pd
from sqlalchemy import create_engine, text

# 1. Configuración de página
st.set_page_config(page_title="Chequeo Maquinaria", page_icon="📝", layout="wide")

# 2. Conexión segura a Supabase
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

# 3. Estado de sesión
if 'inspector_id' not in st.session_state:
    st.session_state.inspector_id = None
if 'inspector_nombre' not in st.session_state:
    st.session_state.inspector_nombre = "Álvaro Cumsille" # Tu usuario por defecto

# 4. Menú Lateral
with st.sidebar:
    st.title("📝 Control de Equipos")
    st.write(f"👷 **{st.session_state.inspector_nombre}**")
    st.divider()
    menu = st.radio("Navegación:", ["Realizar Chequeo", "Historial de Chequeos"])

# 5. Estructura de Páginas
if menu == "Realizar Chequeo":
    st.header("📋 Nuevo Chequeo Diario")
    
    # Verificación de conexión con HORA CHILENA
    try:
        df_hora = run_query("SELECT NOW() AT TIME ZONE 'America/Santiago' as hora_cl;")
        st.success(f"¡Conectado a Supabase! Hora Chile: {df_hora.iloc[0]['hora_cl'].strftime('%Y-%m-%d %H:%M:%S')}")
    except:
        pass

    # Traer equipos de la BD
    df_equipos = run_query("SELECT codigo_interno, nombre, categoria FROM equipos ORDER BY codigo_interno")
    
    if df_equipos is not None and not df_equipos.empty:
        col1, col2 = st.columns(2)
        with col1:
            equipo_display = df_equipos["codigo_interno"] + " - " + df_equipos["nombre"]
            equipo_seleccionado = st.selectbox("Seleccione el Equipo", equipo_display)
            # Extraer la categoría del equipo seleccionado
            cod_seleccionado = equipo_seleccionado.split(" - ")[0]
            categoria_seleccionada = df_equipos[df_equipos["codigo_interno"] == cod_seleccionado].iloc[0]["categoria"]
            
        with col2:
            turno = st.selectbox("Turno", ["Día", "Tarde", "Noche"])
            fecha = st.date_input("Fecha")
        
        st.divider()
        st.subheader(f"Ítems de Revisión: {categoria_seleccionada}")
        
        # Traer preguntas de la BD según la categoría
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
                        c_estado.selectbox("Estado", ["OK", "NOK", "N/A"], key=f"est_{row['orden']}", label_visibility="collapsed")
                        c_obs.text_input("Observación", key=f"obs_{row['orden']}", label_visibility="collapsed")
                
                st.divider()
                st.text_area("Observaciones Generales")
                if st.form_submit_button("Guardar Chequeo ✅"):
                    st.success("El código de guardado lo haremos en el siguiente paso.")
        else:
            st.warning("No hay preguntas configuradas para esta máquina en la base de datos.")
    else:
        st.warning("No hay equipos registrados en la base de datos.")

elif menu == "Historial de Chequeos":
    st.header("📋 Historial de Inspecciones")
    st.info("Módulo en construcción...")
