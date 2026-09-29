import streamlit as st
import uuid
import pandas as pd
from sqlalchemy import create_engine, text
import hashlib

# 1. Configuración de página
st.set_page_config(page_title="Chequeo Maquinaria", page_icon="📝", layout="wide")

# 2. Conexión a Base de Datos
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

# 3. Funciones de Seguridad y Estado
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_data' not in st.session_state:
    st.session_state.user_data = None

# --- 4. PANTALLA DE LOGIN ---
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🏭 Sistema de Gestión de Mantenimiento</h1>", unsafe_allow_html=True)
    st.divider()
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.subheader("🔐 Iniciar Sesión")
        with st.form("login_form"):
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submit_login = st.form_submit_button("Entrar", use_container_width=True)
            
            if submit_login:
                if username and password:
                    pwd_hash = make_hash(password)
                    query = f"SELECT id, nombre_completo, rol, planta_origen FROM usuarios WHERE username = '{username}' AND password_hash = '{pwd_hash}' AND activo = TRUE"
                    df_user = run_query(query)
                    
                    if df_user is not None and not df_user.empty:
                        st.session_state.logged_in = True
                        st.session_state.user_data = df_user.iloc[0].to_dict()
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos, o cuenta inactiva.")
                else:
                    st.warning("Por favor ingresa usuario y contraseña.")

# --- 5. APLICACIÓN PRINCIPAL (Solo logueados) ---
else:
    with st.sidebar:
        st.title("📝 Control de Equipos")
        st.write(f"👷 **{st.session_state.user_data['nombre_completo']}**")
        st.caption(f"Rol: {st.session_state.user_data['rol']}")
        st.divider()
        menu = st.radio("Navegación:", ["Realizar Chequeo", "Historial de Chequeos", "Mantenedor Maestros"])
        st.divider()
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_data = None
            st.rerun()

    # --- PESTAÑA: REALIZAR CHEQUEO ---
    if menu == "Realizar Chequeo":
        st.header("📋 Nuevo Chequeo Diario")
        
        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            planta_default = st.session_state.user_data['planta_origen']
            planta_options = ["La Florida", "Quilicura"]
            default_index = planta_options.index(planta_default) if planta_default in planta_options else 0
            planta_seleccionada = st.selectbox("🏭 Seleccione Planta", planta_options, index=default_index)
        
        # OBTENEMOS EL ID DEL EQUIPO DIRECTO DESDE LA BD
        df_equipos = run_query(f"SELECT id, codigo_interno, nombre, categoria FROM equipos WHERE planta = '{planta_seleccionada}' ORDER BY codigo_interno")
        
        if df_equipos is not None and not df_equipos.empty:
            col1, col2 = st.columns(2)
            with col1:
                equipo_display = df_equipos["codigo_interno"] + " - " + df_equipos["nombre"]
                equipo_seleccionado = st.selectbox("Seleccione el Equipo", equipo_display)
                
                cod_seleccionado = equipo_seleccionado.split(" - ")[0]
                equipo_row = df_equipos[df_equipos["codigo_interno"] == cod_seleccionado].iloc[0]
                categoria_seleccionada = equipo_row["categoria"]
                equipo_id_seleccionado = str(equipo_row["id"])
                
            with col2:
                fecha = st.date_input("Fecha de Inspección")
            
            st.divider()
            st.subheader(f"Ítems de Revisión: {categoria_seleccionada}")
            
            df_preguntas = run_query(f"SELECT grupo, orden, descripcion FROM plantilla_items WHERE categoria_equipo = '{categoria_seleccionada}' ORDER BY orden")
            
            if df_preguntas is not None and not df_preguntas.empty:
                with st.form("form_chequeo", clear_on_submit=True):
                    grupos = df_preguntas["grupo"].unique()
                    for grupo in grupos:
                        st.markdown(f"#### {grupo}")
                        items_grupo = df_preguntas[df_preguntas["grupo"] == grupo]
                        
                        for _, row in items_grupo.iterrows():
                            c_item, c_estado, c_obs = st.columns([3, 1, 2])
                            c_item.write(f"{row['orden']}. {row['descripcion']}")
                            c_estado.selectbox("Estado", ["Cumple", "No Cumple", "N/A"], key=f"est_{row['orden']}", label_visibility="collapsed")
                            c_obs.text_input("Observación", key=f"obs_{row['orden']}", label_visibility="collapsed")
                    
                    st.divider()
                    st.text_area("Observaciones Generales", key="obs_generales")
                    
                    if st.form_submit_button("Guardar Chequeo ✅"):
                        try:
                            cabecera_id = str(uuid.uuid4())
                            usuario_id = str(st.session_state.user_data["id"])
                            obs_gen = st.session_state["obs_generales"]
                            
                            # Preparar las consultas
                            query_cabecera = text("""
                                INSERT INTO chequeos_cabecera (id, equipo_id, usuario_id, fecha_registro, observaciones_generales)
                                VALUES (:id, :eq_id, :usr_id, :fecha, :obs_gen)
                            """)
                            
                            query_detalle = text("""
                                INSERT INTO chequeos_detalle (id, chequeo_id, grupo, item_descripcion, estado_item, observacion_item)
                                VALUES (:id, :cab_id, :grp, :desc, :est, :obs)
                            """)
                            
                            with engine.begin() as conn:
                                # 1. Guardar Cabecera
                                conn.execute(query_cabecera, {
                                    "id": cabecera_id,
                                    "eq_id": equipo_id_seleccionado,
                                    "usr_id": usuario_id,
                                    "fecha": fecha,
                                    "obs_gen": obs_gen
                                })
                                
                                # 2. Guardar Detalles (respuestas)
                                for _, row in df_preguntas.iterrows():
                                    orden = row['orden']
                                    conn.execute(query_detalle, {
                                        "id": str(uuid.uuid4()),
                                        "cab_id": cabecera_id,
                                        "grp": row["grupo"],
                                        "desc": row["descripcion"],
                                        "est": st.session_state[f"est_{orden}"],
                                        "obs": st.session_state[f"obs_{orden}"]
                                    })
                            
                            st.success(f"¡Chequeo guardado exitosamente en la base de datos! (ID Registro: {cabecera_id[:8]})")
                        except Exception as e:
                            st.error(f"Error al guardar en la base de datos: {e}")
            else:
                st.warning(f"No hay preguntas configuradas para {categoria_seleccionada}.")
        else:
            st.warning(f"No hay equipos registrados para la planta {planta_seleccionada}.")

    # --- PESTAÑA: HISTORIAL ---
    elif menu == "Historial de Chequeos":
        st.header("📋 Historial de Inspecciones")
        st.info("Módulo en construcción...")

    # --- PESTAÑA: MANTENEDOR (Solo Administradores) ---
    elif menu == "Mantenedor Maestros":
        if st.session_state.user_data['rol'] == 'Administrador':
            st.header("🔧 Mantenedores Maestros")
            
            tab_ver, tab_agregar, tab_usuarios = st.tabs(["📋 Lista de Equipos", "➕ Nuevo Equipo", "👥 Gestión de Usuarios"])
            
            with tab_ver:
                st.subheader("Equipos Registrados en el Sistema")
                df_equipos_ver = run_query("SELECT codigo_interno as Código, nombre as Equipo, categoria as Categoría, planta as Planta, estado as Estado FROM equipos ORDER BY planta, categoria, codigo_interno")
                if df_equipos_ver is not None and not df_equipos_ver.empty:
                    st.dataframe(df_equipos_ver, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay equipos registrados.")
                    
            with tab_agregar:
                st.subheader("Registrar Nuevo Equipo")
                st.info("Al asignar una categoría, la app le asignará automáticamente el checklist correspondiente a ese tipo de máquina.")
                
                with st.form("form_nuevo_equipo"):
                    col1, col2 = st.columns(2)
                    with col1:
                        nuevo_codigo = st.text_input("Código Interno (Ej: AM-06)")
                        nuevo_nombre = st.text_input("Nombre del Equipo")
                    with col2:
                        nueva_categoria = st.selectbox("Categoría de Checklist", 
                                                     ["Amasadoras", "Cortadoras", "Horno Static", "Hornos de Piso", "Cámaras", "Climatización"])
                        nueva_planta = st.selectbox("Planta", ["La Florida", "Quilicura"])
                    
                    submit_equipo = st.form_submit_button("Guardar Equipo 💾")
                    
                    if submit_equipo:
                        if nuevo_codigo.strip() and nuevo_nombre.strip():
                            try:
                                query_insert = text("""
                                INSERT INTO equipos (id, codigo_interno, nombre, categoria, planta)
                                VALUES (:id, :cod, :nom, :cat, :planta)
                                """)
                                with engine.begin() as conn:
                                    conn.execute(query_insert, {
                                        "id": str(uuid.uuid4()),
                                        "cod": nuevo_codigo.strip(),
                                        "nom": nuevo_nombre.strip(),
                                        "cat": nueva_categoria,
                                        "planta": nueva_planta
                                    })
                                st.success(f"Equipo {nuevo_codigo} registrado con éxito para {nueva_planta}.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al guardar. Es probable que el Código Interno ya exista. (Detalle técnico: {e})")
                        else:
                            st.warning("El Código Interno y el Nombre son obligatorios.")
            
            with tab_usuarios:
                st.subheader("Registrar Nuevo Usuario")
                
                with st.form("form_nuevo_usuario"):
                    col1, col2 = st.columns(2)
                    with col1:
                        nuevo_nombre_usr = st.text_input("Nombre Completo (Ej: Juan Pérez)")
                        nuevo_username = st.text_input("Nombre de Usuario (Ej: jperez)")
                        nueva_planta_usr = st.selectbox("Planta Base", ["La Florida", "Quilicura"], key="planta_usr")
                    with col2:
                        nuevo_rol = st.selectbox("Rol", ["Inspector", "Administrador"])
                        nuevo_password = st.text_input("Contraseña", type="password")
                    
                    submit_usuario = st.form_submit_button("Crear Usuario 👤")
                    
                    if submit_usuario:
                        if nuevo_nombre_usr.strip() and nuevo_username.strip() and nuevo_password.strip():
                            pwd_hash = make_hash(nuevo_password)
                            try:
                                query_insert_usr = text("""
                                INSERT INTO usuarios (username, password_hash, nombre_completo, rol, planta_origen)
                                VALUES (:usr, :pwd, :nom, :rol, :planta)
                                """)
                                with engine.begin() as conn:
                                    conn.execute(query_insert_usr, {
                                        "usr": nuevo_username.strip(),
                                        "pwd": pwd_hash,
                                        "nom": nuevo_nombre_usr.strip(),
                                        "rol": nuevo_rol,
                                        "planta": nueva_planta_usr
                                    })
                                st.success(f"Usuario '{nuevo_username}' creado con éxito.")
                            except Exception as e:
                                st.error(f"Error al crear usuario. ¿Quizás el nombre de usuario ya existe? (Detalle: {e})")
                        else:
                            st.warning("Todos los campos de texto son obligatorios.")
        else:
            st.error("No tienes permisos de Administrador para ver esta sección.")
