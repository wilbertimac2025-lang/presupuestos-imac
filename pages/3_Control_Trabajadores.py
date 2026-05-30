import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime

st.set_page_config(page_title="Control de Personal", page_icon="👷", layout="wide")

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
    except Exception:
        return None

st.title("👷 Control de Personal y Estatus IMSS")
st.markdown("---")

doc = conectar_sheets()

if doc:
    try:
        hoja_obras = doc.worksheet("Obras_Activas")
        hoja_trabajadores = doc.worksheet("Registro_Trabajadores")
    except Exception as e:
        st.error("⚠️ Falta crear la pestaña 'Registro_Trabajadores' en tu Excel.")
        st.stop()

    datos_obras = hoja_obras.get_all_records()
    
    # Buscar folios activos
    llave_folio = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "FOLIO" in str(k).upper()), None)
    llave_estatus = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "ESTATUS" in str(k).upper()), None)
    
    obras_ejecucion = []
    if llave_folio and llave_estatus:
        obras_ejecucion = [str(fila[llave_folio]) for fila in datos_obras if str(fila.get(llave_estatus, "")).upper() == "EN EJECUCIÓN"]

    if not obras_ejecucion:
        st.info("No hay obras en ejecución en este momento.")
    else:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("1. Selección de Obra")
            folio_seleccionado = st.selectbox("Obra Activa:", ["Selecciona un folio..."] + obras_ejecucion)

        if folio_seleccionado != "Selecciona un folio...":
            with col2:
                st.subheader("2. Alta de Personal en Obra")
                
                with st.form("form_personal"):
                    c1, c2 = st.columns(2)
                    with c1:
                        nombre = st.text_input("Nombre Completo del Trabajador")
                        rol = st.selectbox("Puesto / Rol", ["Residente de Obra", "Oficial Tablaroquero", "Oficial Impermeabilizador", "Ayudante General", "Chofer", "Contratista Externo"])
                    with c2:
                        nss = st.text_input("Número de Seguridad Social (NSS)")
                        estatus_imss = st.selectbox("Estatus IMSS actual", ["🟢 ACTIVO (Alta confirmada)", "🟡 EN TRÁMITE", "🔴 SIN ALTA (Riesgo)"])
                    
                    btn_guardar = st.form_submit_button("➕ ASIGNAR TRABAJADOR A LA OBRA")
                    
                    if btn_guardar:
                        if not nombre:
                            st.warning("⚠️ El nombre del trabajador es obligatorio.")
                        else:
                            fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
                            hoja_trabajadores.append_row([
                                folio_seleccionado,
                                nombre.upper(),
                                rol,
                                nss if nss else "NO PROPORCIONADO",
                                estatus_imss,
                                fecha_hoy
                            ])
                            st.success(f"✅ {nombre} asignado a la obra {folio_seleccionado}.")

            st.markdown("---")
            st.subheader(f"📋 Cuadrilla Actual - {folio_seleccionado}")
            
            # Mostrar la lista de trabajadores con su semáforo visual
            datos_trabajadores = hoja_trabajadores.get_all_records()
            cuadrilla_obra = [t for t in datos_trabajadores if str(t.get("Folio Obra", "")) == folio_seleccionado]
            
            if not cuadrilla_obra:
                st.info("Aún no hay trabajadores asignados a este folio.")
            else:
                st.write("Personal registrado para ingreso a obra:")
                for trabajador in cuadrilla_obra:
                    estatus = trabajador.get("Estatus IMSS", "")
                    # Diseño de tarjeta para cada trabajador
                    st.markdown(f"""
                    <div style='padding: 10px; border-radius: 5px; border: 1px solid #ddd; margin-bottom: 10px;'>
                        <strong>{trabajador.get('Nombre del Trabajador', 'N/A')}</strong> - <em>{trabajador.get('Puesto / Rol', 'N/A')}</em><br>
                        NSS: {trabajador.get('NSS', 'N/A')} | Estatus: <strong>{estatus}</strong>
                    </div>
                    """, unsafe_allow_html=True)
