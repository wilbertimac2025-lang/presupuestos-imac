import streamlit as st
import os
from PIL import Image

# --- CONFIGURACIÓN CORPORATIVA ---
icono_navegador = "logo_imac_2026.png" if os.path.exists("logo_imac_2026.png") else ("logo_tarc.png" if os.path.exists("logo_tarc.png") else "🏢")
st.set_page_config(page_title="ERP IMAC - Acceso", page_icon=icono_navegador, layout="centered")

# 🚀 BLINDAJE EXTREMO: Los usuarios y contraseñas ya no viven en el código.
# Ahora se extraen directamente de la bóveda de seguridad (Secrets).
try:
    USUARIOS_VALIDOS = st.secrets["usuarios"]
except Exception as e:
    st.error("⚠️ Error de seguridad: No se encontraron los usuarios en la bóveda secreta.")
    st.info(f"🔍 Detalle técnico del error: {e}")
    
    # Esto nos dirá si Streamlit está logrando leer algo o si el archivo está vacío
    try:
        llaves_detectadas = list(st.secrets.keys())
        st.warning(f"Llaves que el sistema SÍ está leyendo: {llaves_detectadas}")
    except Exception as e_keys:
        st.error(f"El servidor ni siquiera puede leer los secrets: {e_keys}")
        
    st.stop()

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
    
    mostrar_logo("Panel de Bienvenida IMAC")
    st.write("Selecciona un módulo en el menú de la izquierda para operar tu zona correspondiente.")
    
