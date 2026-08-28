import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import pandas as pd
import os
from PIL import Image

# --- CONFIGURACIÓN CORPORATIVA ---
icono_navegador = "logo_imac_2026.png" if os.path.exists("logo_imac_2026.png") else ("logo_tarc.png" if os.path.exists("logo_tarc.png") else "🏢")
st.set_page_config(page_title="Tablero General", page_icon=icono_navegador, layout="wide")

# -----------------------------------------
# 🛡️ CANDADO DE SEGURIDAD POR ROLES
# -----------------------------------------
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ Acceso denegado. Inicia sesión en la página principal.")
    st.stop()

# Nota: Si el Tablero General no lo debe ver RRHH, quita "RRHH" de esta lista en ese archivo.
ROLES_PERMITIDOS = ["Admin", "Directivo"]
if st.session_state.get("role") not in ROLES_PERMITIDOS:
    st.error(f"🚫 ACCESO RESTRINGIDO: Tu perfil de {st.session_state.get('role')} no tiene autorización para este módulo.")
    st.stop()
# -----------------------------------------

# 🔐 CONTRASEÑA MAESTRA PARA VER EL TABLERO GLOBAL
CLAVE_ADMIN = "2289"

def limpiar_monto(valor):
    if str(valor).strip() == "" or valor is None: return 0.0
    try: return float(str(valor).replace("$", "").replace(",", "").replace(" ", "").strip())
    except: return 0.0

@st.cache_resource
def conectar_sheets():
    try:
        credenciales_dic = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(credenciales_dic, scopes=scopes)
        cliente = gspread.authorize(creds)
        
        # ⚠️ REEMPLAZA CON TU ID DE EXCEL
        ID_DEL_EXCEL = "1-grdT2H5dBlGVPvJbZ5wVYDdtVjQEEmUPGpvEm6C0Gc" 
        return cliente.open_by_key(ID_DEL_EXCEL)
    except Exception: return None

# --- ENCABEZADO OFICIAL BLINDADO ---
col_logo, col_tit = st.columns([1, 5])
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
    st.title("Tablero de Control Global")
st.markdown("---")

clave_ingresada = st.text_input("🔑 Ingresa la clave de Administrador para acceder al resumen financiero:", type="password")

if clave_ingresada == CLAVE_ADMIN:
    st.success("🔓 Acceso de Administrador Concedido")
    
    doc = conectar_sheets()

    if doc:
        try:
            hoja_obras = doc.worksheet("Obras_Activas")
            hoja_gastos = doc.worksheet("Gastos_Financieros")
        except Exception as e:
            st.error("⚠️ Faltan pestañas en tu Excel (Obras_Activas o Gastos_Financieros).")
            st.stop()

        datos_obras = hoja_obras.get_all_records()
        datos_gastos = hoja_gastos.get_all_records()

        if not datos_obras:
            st.info("No hay obras registradas en el sistema para generar un reporte.")
        else:
            resumen_obras = []
            for obra in datos_obras:
                llave_folio = next((k for k in obra.keys() if "FOLIO" in str(k).upper()), None)
                folio = str(obra.get(llave_folio, "")) if llave_folio else ""
                
                if not folio: continue 
                
                estatus = str(obra.get("Estatus", "N/A"))
                cliente = obra.get("Cliente", "N/A")
                proyecto = obra.get("Proyecto", "N/A")
                
                llave_monto = next((k for k in obra.keys() if "PRESUPUESTO" in str(k).upper() or "AUTORIZADO" in str(k).upper() or "MONTO" in str(k).upper()), None)
                presupuesto = limpiar_monto(obra.get(llave_monto, 0)) if llave_monto else 0.0

                # AQUÍ SUMA ABSOLUTAMENTE TODO (Material + Nómina + FSR + Extras)
                gastos_obra = [limpiar_monto(g.get("Monto ($)", 0)) for g in datos_gastos if str(g.get("Folio Obra", "")) == folio]
                total_gastado = sum(gastos_obra)
                utilidad = presupuesto - total_gastado
                
                avance_financiero = (total_gastado / presupuesto * 100) if presupuesto > 0 else 0

                resumen_obras.append({
                    "Folio": folio,
                    "Cliente": cliente,
                    "Proyecto": proyecto,
                    "Estatus": estatus,
                    "Presupuesto Cobrado": presupuesto, 
                    "Egresos Totales": total_gastado, 
                    "Saldo Disponible": utilidad,
                    "Avance Gasto": avance_financiero
                })

            df = pd.DataFrame(resumen_obras)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.subheader("Filtros de Búsqueda")
                filtro_estatus = st.radio("Filtrar la vista de obras:", ["Todas las Obras", "Solo Obras EN EJECUCIÓN"])
                
                if filtro_estatus == "Solo Obras EN EJECUCIÓN":
                    df = df[df["Estatus"] == "EN EJECUCIÓN"]

            st.markdown("---")
            st.subheader("📊 Indicadores Globales TARC S.A. DE C.V. (Obras Filtradas)")
            
            c1, c2, c3 = st.columns(3)
            
            total_presupuestos = df["Presupuesto Cobrado"].sum()
            total_gastos = df["Egresos Totales"].sum() 
            total_utilidad = df["Saldo Disponible"].sum()
            
            c1.metric("Obras en Pantalla", len(df))
            c2.metric("Suma Total de Presupuestos", f"${total_presupuestos:,.2f} MXN")
            c3.metric("Fondo / Utilidad Global Libre", f"${total_utilidad:,.2f} MXN")

            st.markdown("---")
            st.subheader("📋 Resumen Desglosado")
            
            df_mostrar = df.copy()
            df_mostrar["Presupuesto Cobrado"] = df_mostrar["Presupuesto Cobrado"].apply(lambda x: f"${x:,.2f}")
            df_mostrar["Egresos Totales"] = df_mostrar["Egresos Totales"].apply(lambda x: f"${x:,.2f}")
            df_mostrar["Saldo Disponible"] = df_mostrar["Saldo Disponible"].apply(lambda x: f"${x:,.2f}")
            df_mostrar["Avance Gasto"] = df_mostrar["Avance Gasto"].apply(lambda x: f"{x:.1f}%")
            
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

elif clave_ingresada != "":
    st.error("❌ Contraseña incorrecta. Acceso denegado a la información financiera global.")
