import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime
import pandas as pd
import os
from PIL import Image

# --- CONFIGURACIÓN CORPORATIVA ---
icono_navegador = "logo_imac_2026.png" if os.path.exists("logo_imac_2026.png") else ("logo_tarc.png" if os.path.exists("logo_tarc.png") else "🏢")
st.set_page_config(page_title="Control de Personal", page_icon=icono_navegador, layout="wide")

# -----------------------------------------
# 🛡️ CANDADO DE SEGURIDAD POR ROLES
# -----------------------------------------
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ Acceso denegado. Inicia sesión en la página principal.")
    st.stop()

ROLES_PERMITIDOS = ["Admin", "RRHH", "Auxiliar", "Operativo"]
if st.session_state.get("role") not in ROLES_PERMITIDOS:
    st.error(f"🚫 ACCESO RESTRINGIDO: Tu perfil de {st.session_state.get('role')} no tiene autorización para este módulo.")
    st.stop()

# 🕵️ FUNCIÓN DE BITÁCORA SILENCIOSA
def registrar_bitacora(doc, modulo, accion):
    try:
        if doc:
            hoja_bitacora = doc.worksheet("Bitacora_Movimientos")
            fecha_hora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            usuario = st.session_state.get("usuario", st.session_state.get("username", "Usuario Sistema"))
            rol = st.session_state.get("role", "Desconocido")
            hoja_bitacora.append_row([fecha_hora, usuario, rol, modulo, accion])
    except Exception:
        pass 

@st.cache_resource
def conectar_sheets():
    try:
        # 🚀 BLINDAJE PARA RENDER
        credenciales_dic = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(credenciales_dic, scopes=scopes)
        cliente = gspread.authorize(creds)
        
        # ⚠️ CONEXIÓN SEGURA
        ID_DEL_EXCEL = os.environ.get("ID_EXCEL") 
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
    st.title("Control de Personal y Asignación de Obra")
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
    
    tab1, tab2, tab3 = st.tabs(["🏗️ Asignación a Obras (Operación)", "🗂️ Base de Datos Maestra (RRHH)", "📊 Tablero Maestro de Ocupación"])

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
                                    ultimo_registro = historial_trabajador[-1]
                                    ultimo_estatus = str(ultimo_registro.get("Estatus IMSS", "")).upper()
                                    ultimo_rp = str(ultimo_registro.get("Registro Patronal", "")).upper()
                                    
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
                                    
                                    # 🚀 INYECCIÓN A LA BITÁCORA
                                    registrar_bitacora(doc, "Control de Trabajadores", f"Asignó a {trabajador_sel} a la obra {folio_seleccionado}. Estatus: {estatus_imss}")
                                    
                                    st.success(f"✅ ¡Éxito! {trabajador_sel} asignado correctamente a la obra {folio_seleccionado}.")
                                    st.rerun()

                # --- MOSTRAR CUADRILLA ACTUAL ---
                st.markdown("---")
                st.subheader(f"📋 Cuadrilla Actual - {folio_seleccionado}")
                
                datos_trabajadores = hoja_trabajadores.get_all_records()
                cuadrilla_obra = [t for t in datos_trabajadores if str(t.get("Folio Obra", "")) == folio_seleccionado]
                
                if not cuadrilla_obra:
                    st.info("Aún no hay trabajadores asignados a este folio.")
                else:
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
                        
                        # 🚀 INYECCIÓN A LA BITÁCORA
                        registrar_bitacora(doc, "Control de Trabajadores", f"Registró al nuevo empleado {nuevo_nombre.upper()} ({nuevo_rol}) en el Catálogo Maestro")
                        
                        st.success(f"✅ ¡Trabajador {nuevo_nombre.upper()} agregado al catálogo general de la empresa!")
                        st.rerun()
            
            st.markdown("---")
            st.write("### Catálogo Histórico de Grupo IMAC")
            if datos_base:
                st.dataframe(pd.DataFrame(datos_base), use_container_width=True, hide_index=True)

    # ==================================================
    # 🚀 PESTAÑA 3: NUEVO TABLERO MAESTRO DE OCUPACIÓN (SÁBANA GLOBAL)
    # ==================================================
    with tab3:
        st.subheader("📊 Estatus de Ocupación General de Plantilla")
        st.write("Control total de asignaciones. Muestra de forma unificada dónde está parado cada elemento del catálogo maestro.")
        
        if not datos_base:
            st.info("No hay personal registrado en el Catálogo Maestro.")
        else:
            # 1. Mapeamos la última asignación cronológica de cada persona
            ultimas_asignaciones = {}
            for reg in datos_trabajadores:
                nombre_t = str(reg.get("Nombre del Trabajador", "")).strip().upper()
                if nombre_t:
                    ultimas_asignaciones[nombre_t] = reg

            # 2. Construimos la Sábana Cruzando el histórico con el estatus
            tabla_global = []
            for emp in datos_base:
                nombre_emp = str(emp.get("Nombre del Trabajador", "")).strip().upper()
                if not nombre_emp:
                    continue
                
                puesto_emp = emp.get("Puesto / Rol", "N/A")
                nss_emp = emp.get("NSS", "N/A")
                rfc_emp = emp.get("RFC", "N/A")

                # Analizamos su situación IMSS / Obra
                registro_asig = ultimas_asignaciones.get(nombre_emp)
                if registro_asig:
                    estatus_imss_act = str(registro_asig.get("Estatus IMSS", "")).upper()
                    if "BAJA" in estatus_imss_act:
                        obra_activa = "🟢 DISPONIBLE (SIN OBRA)"
                        estatus_pantalla = "🔴 BAJA"
                        rp_act = "N/A"
                    else:
                        obra_activa = registro_asig.get("Folio Obra", "N/A")
                        estatus_pantalla = registro_asig.get("Estatus IMSS", "N/A")
                        rp_act = registro_asig.get("Registro Patronal", "N/A")
                else:
                    obra_activa = "🟢 DISPONIBLE (SIN OBRA)"
                    estatus_pantalla = "SIN ASIGNACIONES"
                    rp_act = "N/A"

                tabla_global.append({
                    "Nombre del Trabajador": nombre_emp,
                    "Puesto / Rol": puesto_emp,
                    "NSS": nss_emp,
                    "RFC": rfc_emp,
                    "Obra Asignada": obra_activa,
                    "Estatus IMSS": estatus_pantalla,
                    "RP de Obra": rp_act
                })

            df_master = pd.DataFrame(tabla_global)

            # 🔍 Buscador interactivo integrado
            filtro_texto = st.text_input("🔍 Filtrar Tabla (Escribe nombre, obra o puesto):", placeholder="Ej. Oficial, OBRA04, Juan...")
            
            if filtro_texto:
                # Filtrado inteligente sin importar mayúsculas
                termino = filtro_texto.upper().strip()
                df_master = df_master[df_master.astype(str).apply(lambda x: x.str.contains(termino)).any(axis=1)]

            # Desplegamos la tabla corporativa limpia
            st.dataframe(df_master, use_container_width=True, hide_index=True)
