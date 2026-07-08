import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime

st.set_page_config(page_title="Control de Personal", page_icon="👷", layout="wide")

# -----------------------------------------
# 🛡️ CANDADO DE SEGURIDAD POR ROLES
# -----------------------------------------
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ Acceso denegado. Inicia sesión en la página principal.")
    st.stop()

ROLES_PERMITIDOS = ["Admin", "RRHH", "Auxiliar"]
if st.session_state.get("role") not in ROLES_PERMITIDOS:
    st.error(f"🚫 ACCESO RESTRINGIDO: Tu perfil de {st.session_state.get('role')} no tiene autorización para este módulo.")
    st.stop()

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
    datos_trabajadores = hoja_trabajadores.get_all_records()
    
    llave_folio = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "FOLIO" in str(k).upper()), None)
    llave_estatus = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "ESTATUS" in str(k).upper()), None)
    obras_ejecucion = [str(fila[llave_folio]) for fila in datos_obras if str(fila.get(llave_estatus, "")).upper() == "EN EJECUCIÓN"] if llave_folio and llave_estatus else []

    if not obras_ejecucion:
        st.info("No hay obras en ejecución en este momento.")
    else:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("1. Selección de Obra")
            folio_seleccionado = st.selectbox("Obra Activa:", ["Selecciona un folio..."] + obras_ejecucion)

        if folio_seleccionado != "Selecciona un folio...":
            
            obra_info = next((f for f in datos_obras if str(f.get(llave_folio, "")) == folio_seleccionado), None)
            llave_rp = next((k for k in (obra_info.keys() if obra_info else []) if "PATRONAL" in str(k).upper() or "REGISTRO" in str(k).upper()), None)
            registro_patronal = obra_info.get(llave_rp, "NO ASIGNADO") if llave_rp else "NO ASIGNADO"
            
            with col2:
                st.info(f"🏛️ **Registro Patronal IMSS vinculado a la Obra:** {registro_patronal}")
                
                tab1, tab2 = st.tabs(["➕ Alta de Personal", "🔄 Actualizar Estatus IMSS"])
                
                with tab1:
                    with st.form("form_personal"):
                        c1, c2 = st.columns(2)
                        with c1:
                            nombre = st.text_input("Nombre Completo del Trabajador")
                            rol = st.selectbox("Puesto / Rol", ["Residente", "Oficial Tablaroquero", "Oficial Impermeabilizador", "Ayudante General", "Chofer", "Contratista Externo"])
                            nss = st.text_input("Número de Seguridad Social (NSS)")
                        with c2:
                            # 📝 NUEVO CAMPO: RFC DEL TRABAJADOR
                            rfc = st.text_input("RFC del Trabajador", max_chars=13, placeholder="Ej. ROMW900101XXX")
                            estatus_imss = st.selectbox("Estatus IMSS actual", ["🟢 ACTIVO (Alta confirmada)", "🟡 EN TRÁMITE", "🔴 SIN ALTA (Riesgo)"])
                        
                        btn_guardar = st.form_submit_button("➕ ASIGNAR A LA OBRA")
                        
                        if btn_guardar:
                            if not nombre:
                                st.warning("⚠️ El nombre es obligatorio.")
                            else:
                                fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
                                # Guardamos el RFC al final para mantener el orden del Excel
                                hoja_trabajadores.append_row([
                                    folio_seleccionado, nombre.upper(), rol,
                                    nss if nss else "NO PROPORCIONADO", estatus_imss, fecha_hoy,
                                    registro_patronal, rfc.upper() if rfc else "NO PROPORCIONADO"
                                ])
                                st.success(f"✅ {nombre} asignado con éxito. RFC: {rfc.upper() if rfc else 'N/P'}")
                                datos_trabajadores = hoja_trabajadores.get_all_records()

                with tab2:
                    st.write("Selecciona a un trabajador para modificar su estatus IMSS.")
                    cuadrilla_actual_nombres = [t.get("Nombre del Trabajador", "") for t in datos_trabajadores if str(t.get("Folio Obra", "")) == folio_seleccionado]
                    
                    if not cuadrilla_actual_nombres:
                        st.info("Primero debes dar de alta personal en esta obra.")
                    else:
                        with st.form("form_actualizar_imss"):
                            trabajador_sel = st.selectbox("Trabajador:", cuadrilla_actual_nombres)
                            nuevo_estatus = st.selectbox("Nuevo Estatus:", ["🟢 ACTIVO (Alta confirmada)", "🟡 EN TRÁMITE", "🔴 SIN ALTA (Riesgo)"])
                            btn_actualizar = st.form_submit_button("🔄 GUARDAR CAMBIOS")
                            
                            if btn_actualizar:
                                fila_excel = next((i + 2 for i, f in enumerate(datos_trabajadores) if str(f.get("Folio Obra", "")) == folio_seleccionado and str(f.get("Nombre del Trabajador", "")) == trabajador_sel), 0)
                                if fila_excel > 0:
                                    # Mantiene el estatus en la columna 5
                                    hoja_trabajadores.update_cell(fila_excel, 5, nuevo_estatus)
                                    st.success(f"✅ Estatus de {trabajador_sel} actualizado.")
                                    st.rerun()

            st.markdown("---")
            st.subheader(f"📋 Cuadrilla Actual - {folio_seleccionado}")
            
            datos_trabajadores = hoja_trabajadores.get_all_records()
            cuadrilla_obra = [t for t in datos_trabajadores if str(t.get("Folio Obra", "")) == folio_seleccionado]
            
            if not cuadrilla_obra:
                st.info("Aún no hay trabajadores asignados a este folio.")
            else:
                for trabajador in cuadrilla_obra:
                    estatus = trabajador.get("Estatus IMSS", "")
                    rp_trabajador = trabajador.get("Registro Patronal", registro_patronal)
                    rfc_trabajador = trabajador.get("RFC", "NO PROPORCIONADO")
                    
                    st.markdown(f"""
                    <div style='padding: 15px; border-radius: 8px; border: 1px solid #ddd; margin-bottom: 12px; background-color: #fafafa;'>
                        <strong style='font-size: 16px; color: #0f3c8c;'>{trabajador.get('Nombre del Trabajador', 'N/A')}</strong> - <em>{trabajador.get('Puesto / Rol', 'N/A')}</em><br>
                        <span style='color: #555;'>NSS: {trabajador.get('NSS', 'N/A')} | <strong>RFC: {rfc_trabajador}</strong> | RP Obra: {rp_trabajador}</span><br>
                        Estatus IMSS: <strong>{estatus}</strong>
                    </div>
                    """, unsafe_allow_html=True)
