import streamlit as st

st.set_page_config(page_title="ERP IMAC - Acceso", page_icon="🔐", layout="centered")

# 🏛️ BASE DE DATOS DE USUARIOS Y ROLES GRUPO IMAC
USUARIOS_VALIDOS = {
    # 1. Dirección General (Acceso Total)
    "wromero": {"clave": "2289", "rol": "Admin"},
    
    # 2. Directivos (Solo Reportes y Tablero)
    "act_dir": {"clave": "ACT2026", "rol": "Directivo"},
    "aco_dir": {"clave": "ACO2026", "rol": "Directivo"},
    
    # 3. Recursos Humanos (Casi todo, excepto creación de obras)
    "rrhh_imac": {"clave": "RRHH2026", "rol": "RRHH"},
    
    # 4. Auxiliares de Obra (Operación básica)
    "aux_obra1": {"clave": "AUX2026", "rol": "Auxiliar"}
}

def login():
    st.title("🔐 Sistema de Gestión IMAC")
    st.subheader("Acceso Autorizado")

    with st.form("login_form"):
        usuario = st.text_input("Usuario", placeholder="Escribe tu usuario")
        clave = st.text_input("Contraseña", type="password")
        boton = st.form_submit_button("INGRESAR AL SISTEMA")

        if boton:
            if usuario in USUARIOS_VALIDOS and USUARIOS_VALIDOS[usuario]["clave"] == clave:
                st.session_state["logged_in"] = True
                st.session_state["user"] = usuario
                st.session_state["role"] = USUARIOS_VALIDOS[usuario]["rol"]
                st.success(f"Bienvenido. Acceso concedido como {USUARIOS_VALIDOS[usuario]['rol']}.")
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos.")

# Lógica de navegación y candado general
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login()
else:
    st.sidebar.write(f"👤 Usuario: **{st.session_state['user']}**")
    st.sidebar.write(f"🛡️ Rol: **{st.session_state['role']}**")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state["logged_in"] = False
        st.rerun()
    
    st.title("🏗️ Panel de Bienvenida IMAC")
    st.write("Selecciona un módulo en el menú de la izquierda para comenzar a operar.")
