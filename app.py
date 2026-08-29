import streamlit as st
import os
from PIL import Image

# --- CONFIGURACIÓN CORPORATIVA ---
icono_navegador = "logo_imac_2026.png" if os.path.exists("logo_imac_2026.png") else ("logo_tarc.png" if os.path.exists("logo_tarc.png") else "🏢")
st.set_page_config(page_title="ERP IMAC - Acceso", page_icon=icono_navegador, layout="centered")

# 🏛️ BASE DE DATOS DE USUARIOS CON PERMISOS GEOGRÁFICOS
USUARIOS_VALIDOS = {
    # Dirección y Directivos (Acceso Global a todo el sistema)
    "wromero": {"clave": "2289", "rol": "Admin", "zona": "Todas"},
    "act_dir": {"clave": "ACT2026", "rol": "Directivo", "zona": "Todas"},
    "aco_dir": {"clave": "ACO2026", "rol": "Directivo", "zona": "Todas"},
    
    # Recursos Humanos (Restringido exclusivamente a zona Local)
    "vane": {"clave": "1234", "rol": "RRHH", "zona": "Local"},
    
    # Auxiliares y Operativos segmentados por territorio
    "jose": {"clave": "local26", "rol": "Auxiliar", "zona": "Local"},
    "aux_foraneo": {"clave": "FORANEO2026", "rol": "Auxiliar", "zona": "Foránea"},
    
    # 🚀 NUEVO: Usuario Operativo (Exclusivo para zona Foránea)
    "operativo": {"clave": "OPE2026", "rol": "Operativo", "zona": "Foránea"}
}

# 🚀 FUNCIÓN PARA EL ENCABEZADO OFICIAL BLINDADO
def mostrar_logo(titulo):
    col_logo, col_tit = st.columns([1, 4])
    with col_logo:
        try:
            if os.path.exists("logo_imac_2026.png"):
                img_logo = Image.open("logo_imac_2026.png")
                st.image(img_logo, use_container_width=True)
            elif os.path.exists("logo_tarc.png"):
                img_logo = Image.open("logo_tarc.png")
                st.image(img_logo, use_container_width=True)
            elif os.path.exists("logo_tarc.jpg"):
                img_logo = Image.open("logo_tarc.jpg")
                st.image(img_logo, use_container_width=True)
        except Exception:
            st.write("🏢 GRUPO IMAC")
    with col_tit:
        st.title(titulo)
    st.markdown("---")

def login():
    # Mandamos llamar al encabezado corporativo
    mostrar_logo("Sistema de Gestión IMAC")
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
    
    # Encabezado corporativo también en la pantalla de bienvenida
    mostrar_logo("Panel de Bienvenida IMAC")
    st.write("Selecciona un módulo en el menú de la izquierda para operar tu zona correspondiente.")
