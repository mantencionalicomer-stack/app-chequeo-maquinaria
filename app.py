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
    st.error("Error al conectar con la base de datos. Verifica los Secrets en Streamlit.")
    st.stop()

# Función para ejecutar consultas (sin caché para datos en tiempo real)
def run_query(query, params=None):
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        conn.commit()
        if query.strip().upper().startswith("SELECT"):
            return pd.DataFrame(result.fetchall(), columns=result.keys())
        return None

# 3. Estado de sesión
if 'inspector_activo_id' not in st.session_state:
    st.session_state.inspector_activo_id = None
if 'inspector_activo_nombre' not in st.session_state:
    st.session_state.inspector_activo_nombre = "Usuario de Prueba"

# 4. Menú Lateral
with st.sidebar:
    st.title("📝 Control de Equipos")
    st.divider()
    
    st.subheader("Usuario Activo")
    st.write(f"👷 **{st.session_state.inspector_activo_nombre}**")
    
    st.divider()
    st.subheader("Navegación")
    menu = st.radio(
        "Ir a:",
        ["Realizar Chequeo", "Historial de Chequeos", "Mantenedor Maestros"]
    )

# 5. Estructura de Páginas
if menu == "Realizar Chequeo":
    st.header("📋 Nuevo Chequeo Diario")
    st.info("Aquí cargaremos el formulario dinámico basado en tu Excel.")
    
    # Prueba rápida de conexión a la BD
    try:
        df_prueba = run_query("SELECT NOW() as hora_servidor;")
        st.success(f"¡Conexión exitosa a Supabase! Hora del servidor: {df_prueba.iloc[0]['hora_servidor']}")
    except Exception as e:
        st.error(f"Error consultando la base de datos: {e}")

elif menu == "Historial de Chequeos":
    st.header("📋 Historial de Inspecciones")
    st.write("Módulo en construcción...")

elif menu == "Mantenedor Maestros":
    st.header("🔧 Mantenedores Maestros")
    st.write("Módulo en construcción...")
