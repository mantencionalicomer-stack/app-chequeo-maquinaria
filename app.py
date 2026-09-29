elif menu == "Mantenedor Maestros":
    st.header("🔧 Mantenedor de Equipos")
    
    tab_ver, tab_agregar = st.tabs(["📋 Lista de Equipos", "➕ Nuevo Equipo"])
    
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
                # Las categorías deben coincidir con las que tenemos en plantilla_items
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
                        st.rerun() # Recarga la app para actualizar la tabla
                    except Exception as e:
                        st.error(f"Error al guardar. Es probable que el Código Interno ya exista. (Detalle técnico: {e})")
                else:
                    st.warning("El Código Interno y el Nombre son obligatorios.")
