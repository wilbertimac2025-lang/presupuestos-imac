import streamlit as st

st.set_page_config(page_title="ERP IMAC - Acceso", page_icon="🔐", layout="centered")

# 🏛️ BASE DE DATOS DE USUARIOS CON PERMISOS GEOGRÁFICOS
# 🏛️ BASE DE DATOS DE USUARIOS CON PERMISOS GEOGRÁFICOS
USUARIOS_VALIDOS = {
    # Dirección y Directivos (Acceso Global a todo el sistema)
    "wromero": {"clave": "2289", "rol": "Admin", "zona": "Todas"},
    "act_dir": {"clave": "ACT2026", "rol": "Directivo", "zona": "Todas"},
    "aco_dir": {"clave": "ACO2026", "rol": "Directivo", "zona": "Todas"},
    
    # Recursos Humanos (Restringido exclusivamente a zona Local)
    "rrhh_imac": {"clave": "RRHH2026", "rol": "RRHH", "zona": "Local"},
    
    # Auxiliares y Operativos segmentados por territorio
    "aux_local": {"clave": "LOCAL2026", "rol": "Auxiliar", "zona": "Local"},
    "aux_foraneo": {"clave": "FORANEO2026", "rol": "Auxiliar", "zona": "Foránea"},
    
    # 🚀 NUEVO: Usuario Operativo (Exclusivo para zona Foránea)
    "operativo": {"clave": "OPE2026", "rol": "Auxiliar", "zona": "Foránea"}
}

def login():
    st.title("🔐 Sistema de Gestión IMAC")
    st.subheader("Acceso Geográfico Autorizado")

    with st.form("login_form"):
        usuario = st.text_input("Usuario", placeholder="Escribe tu usuario")
        clave = st.text_input("Contraseña", type="password")
        boton = st.form_submit_button("INGRESAR AL SISTEMA")

        if boton:
            if usuario in USUARIOS_VALIDOS and USUARIOS_VALIDOS[usuario]["clave"] == clave:
                st.session_state["logged_in"] = True
                st.session_state["user"] = usuario
                st.session_state["role"] = USUARIOS_VALIDOS[usuario]["rol"]
                # 🚀 AQUÍ GUARDAMOS EL TERRITORIO DEL USUARIO
                st.session_state["zona"] = USUARIOS_VALIDOS[usuario]["zona"]
                st.success(f"Acceso concedido como {st.session_state['role']} - Zona: {st.session_state['zona']}.")
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos.")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login()
else:
    st.sidebar.write(f"👤 Usuario: **{st.session_state['user']}**")
    st.sidebar.write(f"🛡️ Rol: **{st.session_state['role']}**")
    st.sidebar.write(f"📍 Territorio: **{st.session_state['zona']}**")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state["logged_in"] = False
        st.rerun()
    
    st.title("🏗️ Panel de Bienvenida IMAC")
    st.write("Selecciona un módulo en el menú de la izquierda para operar tu zona correspondiente.")
