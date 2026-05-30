import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json

st.set_page_config(page_title="ERP - Gestión de Obras", page_icon="🏗️", layout="wide")

@st.cache_resource
def conectar_sheets():
    try:
        credenciales_dic = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(credenciales_dic, scopes=scopes)
        cliente = gspread.authorize(creds)
        
        # ⚠️ REEMPLAZA CON TU ID DE EXCEL
        ID_DEL_EXCEL = "1-grdT2H5dBlGVPvJbZ5wVYDdtVjQEEmUPGpvEm6C0Gc" 
        doc = cliente.open_by_key(ID_DEL_EXCEL)
        return doc
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

st.title("🏗️ Centro de Control de Obras")
st.markdown("---")

doc = conectar_sheets()

if doc:
    hoja_presupuestos = doc.worksheet("Presupuestos")
    hoja_obras = doc.worksheet("Obras_Activas")

    datos_presupuestos = hoja_presupuestos.get_all_records()
    
    # 🛠️ CORRECCIÓN: Código blindado. Solo lee la columna si existe realmente.
    folios_disponibles = [str(fila["Folio"]) for fila in datos_presupuestos if "Folio" in fila and str(fila.get("Folio", "")) != ""]

    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("1. Apertura de Obra")
        st.write("Selecciona una cotización aprobada para darla de alta.")
        
        # Si la lista está vacía, te avisa amigablemente en lugar de tronar
        if not folios_disponibles:
            st.warning("⚠️ No se detectaron Folios. Por favor, verifica en tu Excel que la celda A1 de la pestaña 'Presupuestos' diga exactamente 'Folio' (sin espacios).")
        
        folio_seleccionado = st.selectbox("Folio Aprobado:", ["Selecciona un folio..."] + folios_disponibles)

    if folio_seleccionado != "Selecciona un folio...":
        datos_obra = next((item for item in datos_presupuestos if str(item.get("Folio", "")) == folio_seleccionado), None)

        if datos_obra:
            with col2:
                st.success("✅ Cotización encontrada en la base de datos.")
                
                with st.form("form_apertura_obra"):
                    st.write(f"**Cliente:** {datos_obra.get('Cliente', 'N/A')}")
                    st.write(f"**Proyecto:** {datos_obra.get('Proyecto / Obra', 'N/A')}")
                    st.write(f"**Monto Autorizado:** {datos_obra.get('Total del Presupuesto', 'N/A')}")
                    
                    st.markdown("---")
                    st.write("**Datos de Operación**")
                    fecha_inicio = st.date_input("Fecha Oficial de Arranque")
                    residente = st.text_input("Nombre del Residente / Encargado de Cuadrilla")
                    
                    boton_arranque = st.form_submit_button("🚀 INICIAR PROYECTO")
                    
                    if boton_arranque:
                        if not residente: 
                            st.warning("⚠️ Debes asignar un residente para la obra.")
                        else:
                            hoja_obras.append_row([
                                folio_seleccionado,
                                datos_obra.get('Cliente', ''),
                                datos_obra.get('Proyecto / Obra', ''),
                                "EN EJECUCIÓN",
                                datos_obra.get('Total del Presupuesto', ''),
                                fecha_inicio.strftime("%d/%m/%Y"),
                                residente.upper()
                            ])
                            st.balloons()
                            st.success(f"¡Obra {folio_seleccionado} dada de alta! Ya puedes comenzar a gestionar salidas.")
