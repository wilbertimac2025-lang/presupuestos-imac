import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime
import pandas as pd

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
        # ⚠️ REEMPLAZA CON TU ID DE EXCEL AQUÍ
        ID_DEL_EXCEL = "1-grdT2H5dBlGVPvJbZ5wVYDdtVjQEEmUPGpvEm6C0Gc" 
        return cliente.open_by_key(ID_DEL_EXCEL)
    except Exception: return None

st.title("👷 Control de Personal y Asignación de Obra")
st.markdown("---")

doc = conectar_sheets()

if doc:
    try:
        hoja_obras = doc.worksheet("Obras_Activas")
        hoja_trabajadores = doc.worksheet("Registro_Trabajadores")
        hoja_base = doc.worksheet("Base_Trabajadores")
    except Exception as e:
        st.error("⚠️ Falta crear la pestaña 'Base_Trabajadores' o 'Registro_Trabajadores' en tu Excel.")
        st.stop()

    datos_obras = hoja_obras.get_all_records()
    datos_trabajadores = hoja_trabajadores.get_all_records()
    datos_base = hoja_base.get_all_records()
    
    nombres_base = [str(fila.get("Nombre del Trabajador", "")) for fila in datos_base if str(fila.get("Nombre del Trabajador", "")) != ""]
    
    tab1, tab2, tab3 = st.tabs(["🏗️ Asignación a Obras (Operación)", "🗂️ Base de Datos Maestra (RRHH)", "🔍 Visor de Cuadrillas en Obra"])

    # ==================================================
    # PESTAÑA 1: ASIGNACIÓN A OBRAS (CON CANDADO IMSS)
    # ==================================================
    with tab1:
        llave_folio = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "FOLIO" in str(k).upper()), None)
        llave_estatus = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "ESTATUS" in str(k).upper()), None)
        obras_ejecucion = [str(fila[llave_folio]) for fila in datos_obras if str(fila.get(llave_estatus, "")).upper() == "EN EJECUCIÓN"] if llave_folio and llave_estatus else []

        if not obras_ejecucion:
            st.info("No hay obras en ejecución en este momento.")
        else:
            colA, colB = st.columns([1, 2])
            with colA:
                st.subheader("1. Selecciona la Obra Activa")
                folio_seleccionado = st.selectbox("Folio de Obra:", ["Selecciona un folio..."] + obras_ejecucion)

            if folio_seleccionado != "Selecciona un folio...":
                obra_info = next((f for f in datos_obras if str(f.get(llave_folio, "")) == folio_seleccionado), None)
                llave_rp = next((k for k in (obra_info.keys() if obra_info else []) if "PATRONAL" in str(k).upper() or "REGISTRO" in str(k).upper()), None)
                registro_patronal_obra = str(obra_info.get(llave_rp, "NO ASIGNADO")).upper()
                
                with colB:
                    st.info(f"🏛️ **Registro Patronal (RP) de esta Obra:** {registro_patronal_obra}")
                    
                    st.subheader("2. Asignar Trabajador del Catálogo")
                    if not nombres_base:
                        st.warning("⚠️ Tu catálogo de trabajadores está vacío. Ve a la pestaña 'Base de Datos Maestra' para registrarlos.")
                    else:
                        with st.form("form_asignacion"):
                            trabajador_sel = st.selectbox("Selecciona al Trabajador:", nombres_base)
                            estatus_imss = st.selectbox("Estatus IMSS para esta obra:", ["🟢 ACTIVO (Alta confirmada)", "🟡 EN TRÁMITE", "🔴 BAJA (Desvinculado de la obra)"])
                            
                            btn_asignar = st.form_submit_button("➕ ASIGNAR TRABAJADOR A LA OBRA")
                            
                            if btn_asignar:
                                # LÓGICA DEL CANDADO
                                trabajador_info = next((t for t in datos_base if str(t.get("Nombre del Trabajador", "")) == trabajador_sel), None)
                                historial_trabajador = [t for t in datos_trabajadores if str(t.get("Nombre del Trabajador", "")) == trabajador_sel]
                                
                                candado_activado = False
                                
                                if historial_trabajador:
                                    # Analizamos su última asignación registrada
                                    ultimo_registro = historial_trabajador[-1]
                                    ultimo_estatus = str(ultimo_registro.get("Estatus IMSS", "")).upper()
                                    ultimo_rp = str(ultimo_registro.get("Registro Patronal", "")).upper()
                                    
                                    # Si no está de BAJA y el RP anterior es distinto al de la obra actual = BLOQUEO
                                    if "BAJA" not in ultimo_estatus and ultimo_rp != "NO ASIGNADO" and ultimo_rp != registro_patronal_obra:
                                        candado_activado = True
                                        st.error(f"🔒 **CANDADO IMSS ACTIVADO:** {trabajador_sel} está activo en otra obra con el RP: **{ultimo_rp}**.")
                                        st.error(f"No puedes moverlo a esta obra (RP: **{registro_patronal_obra}**) sin antes registrarle una '🔴 BAJA' en su obra anterior para evitar multas.")

                                if not candado_activado:
                                    fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
                                    hoja_trabajadores.append_row([
                                        folio_seleccionado, 
                                        trabajador_info.get("Nombre del Trabajador", ""), 
                                        trabajador_info.get("Puesto / Rol", ""),
                                        trabajador_info.get("NSS", ""), 
                                        estatus_imss, 
                                        fecha_hoy,
                                        registro_patronal_obra, 
                                        trabajador_info.get("RFC", "")
                                    ])
                                    st.success(f"✅ ¡Éxito! {trabajador_sel} asignado correctamente a la obra {folio_seleccionado}.")
                                    st.rerun()

                # --- MOSTRAR CUADRILLA ACTUAL ---
                st.markdown("---")
                st.subheader(f"📋 Cuadrilla Actual - {folio_seleccionado}")
                
                datos_trabajadores = hoja_trabajadores.get_all_records()
                # Mostramos solo el estatus más reciente de cada trabajador en esta obra
                cuadrilla_obra = [t for t in datos_trabajadores if str(t.get("Folio Obra", "")) == folio_seleccionado]
                
                if not cuadrilla_obra:
                    st.info("Aún no hay trabajadores asignados a este folio.")
                else:
                    # Filtramos para mostrar solo la última actualización de estatus de cada persona en esta obra
                    trabajadores_unicos = {}
                    for t in cuadrilla_obra:
                        trabajadores_unicos[t["Nombre del Trabajador"]] = t
                    
                    for nombre, trabajador in trabajadores_unicos.items():
                        estatus = trabajador.get("Estatus IMSS", "")
                        rp_trabajador = trabajador.get("Registro Patronal", registro_patronal_obra)
                        rfc_trabajador = trabajador.get("RFC", "NO PROPORCIONADO")
                        
                        color_fondo = "#fafafa" if "BAJA" not in estatus.upper() else "#ffebee"
                        
                        st.markdown(f"""
                        <div style='padding: 15px; border-radius: 8px; border: 1px solid #ddd; margin-bottom: 12px; background-color: {color_fondo};'>
                            <strong style='font-size: 16px; color: #0f3c8c;'>{nombre}</strong> - <em>{trabajador.get('Puesto / Rol', 'N/A')}</em><br>
                            <span style='color: #555;'>NSS: {trabajador.get('NSS', 'N/A')} | <strong>RFC: {rfc_trabajador}</strong> | RP Vinculado: {rp_trabajador}</span><br>
                            Estatus Actual: <strong>{estatus}</strong>
                        </div>
                        """, unsafe_allow_html=True)

    # ==================================================
    # PESTAÑA 2: BASE DE DATOS MAESTRA (CATÁLOGO)
    # ==================================================
    with tab2:
        st.subheader("🗂️ Registro de Nuevos Empleados")
        
        if st.session_state.get("role") == "Auxiliar":
            st.warning("⚠️ Tu perfil operativo no tiene permisos para dar de alta nuevos empleados en la base de datos maestra. Solicítalo a RRHH o Dirección.")
        else:
            st.write("Agrega aquí a los trabajadores que ingresan por primera vez a Grupo IMAC. Una vez registrados, aparecerán en el menú desplegable para asignarlos a cualquier obra.")
            with st.form("form_alta_maestra"):
                c1, c2 = st.columns(2)
                with c1:
                    nuevo_nombre = st.text_input("Nombre Completo (Empezando por Apellidos)")
                    nuevo_rol = st.selectbox("Puesto / Rol Oficial", ["Oficial Tablaroquero", "Oficial Impermeabilizador", "Ayudante General", "Residente", "Chofer", "Contratista Externo"])
                with c2:
                    nuevo_nss = st.text_input("Número de Seguridad Social (NSS)", max_chars=11)
                    nuevo_rfc = st.text_input("RFC con Homoclave", max_chars=13, placeholder="Ej. ROMW900101XXX")
                
                btn_maestro = st.form_submit_button("💾 GUARDAR EN BASE DE DATOS")
                
                if btn_maestro:
                    if not nuevo_nombre or not nuevo_nss or not nuevo_rfc:
                        st.error("⚠️ Debes llenar Nombre, NSS y RFC obligatoriamente.")
                    elif nuevo_nombre in nombres_base:
                        st.error(f"⚠️ El trabajador {nuevo_nombre.upper()} ya existe en la base de datos.")
                    else:
                        hoja_base.append_row([nuevo_nombre.upper(), nuevo_rol, nuevo_nss, nuevo_rfc.upper()])
                        st.success(f"✅ ¡Trabajador {nuevo_nombre.upper()} agregado al catálogo general de la empresa!")
                        st.rerun()
            
            st.markdown("---")
            st.write("### Catálogo Histórico de Grupo IMAC")
            if datos_base:
                st.dataframe(pd.DataFrame(datos_base), use_container_width=True, hide_index=True)

    # ==================================================
    # PESTAÑA 3: VISOR GENERAL DE CUADRILLAS
    # ==================================================
    with tab3:
        st.subheader("🔍 Consultar Personal en Obra")
        st.write("Selecciona un proyecto para ver la cuadrilla en forma de tabla.")
        
        if not obras_ejecucion:
            st.info("No hay obras en ejecución.")
        else:
            visor_folio = st.selectbox("Selecciona Obra a Consultar:", ["Selecciona un folio..."] + obras_ejecucion, key="visor_cuadrilla")
            
            if visor_folio != "Selecciona un folio...":
                # Re-cargamos para tener la info más fresca
                datos_frescos = hoja_trabajadores.get_all_records()
                visor_obra = [t for t in datos_frescos if str(t.get("Folio Obra", "")) == visor_folio]
                
                if visor_obra:
                    # Nos quedamos con el último registro de cada persona
                    trabajadores_visor = {}
                    for t in visor_obra:
                        trabajadores_visor[t["Nombre del Trabajador"]] = t
                    
                    # Convertimos el diccionario a una lista plana para pandas
                    lista_final = list(trabajadores_visor.values())
                    df_visor = pd.DataFrame(lista_final)
                    
                    columnas_visor = ["Nombre del Trabajador", "Puesto / Rol", "NSS", "Registro Patronal", "Estatus IMSS", "Fecha de Asignación"]
                    cols_finales = [c for c in columnas_visor if c in df_visor.columns]
                    
                    st.success(f"👷 Hay {len(lista_final)} trabajador(es) registrados en el proyecto **{visor_folio}**:")
                    st.dataframe(df_visor[cols_finales] if cols_finales else df_visor, use_container_width=True, hide_index=True)
                else:
                    st.info(f"No hay registros de trabajadores en el folio {visor_folio}.")
