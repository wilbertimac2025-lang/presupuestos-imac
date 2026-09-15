import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime
import pandas as pd
import os
import smtplib
from email.message import EmailMessage
from PIL import Image
from fpdf import FPDF

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

# --- CLASE PARA EL PDF CORPORATIVO DE TRABAJADORES ---
class PDF_Trabajadores(FPDF):
    def header(self):
        if os.path.exists("logo_tarc.png"): self.image("logo_tarc.png", x=10, y=8, w=40)
        elif os.path.exists("logo_imac_2026.png"): self.image("logo_imac_2026.png", x=10, y=8, w=40)
        
        self.set_font('Arial', 'B', 14)
        self.set_text_color(15, 60, 140)
        self.cell(0, 10, 'GRUPO IMAC - REPORTE DE PERSONAL EN OBRA', ln=True, align='R')
        self.set_font('Arial', 'I', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f'Fecha de Emision: {datetime.datetime.now().strftime("%d/%m/%Y")}', ln=True, align='R')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()} de {{nb}}', 0, 0, 'C')
        
    def draw_table_header(self, tipo):
        self.set_fill_color(15, 60, 140) if tipo == "ACTIVOS" else self.set_fill_color(100, 100, 100)
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 9)
        if tipo == "ACTIVOS":
            self.cell(70, 7, "NOMBRE DEL TRABAJADOR", border=1, fill=True)
            self.cell(45, 7, "OBRA ASIGNADA", border=1, fill=True)
            self.cell(25, 7, "VIG. IMSS", border=1, align='C', fill=True)
            self.cell(50, 7, "ESTATUS / ALERTA", border=1, align='C', fill=True, ln=True)
        else:
            self.cell(100, 7, "NOMBRE DEL TRABAJADOR", border=1, fill=True)
            self.cell(90, 7, "ULTIMA OBRA REGISTRADA", border=1, fill=True, ln=True)

# 📧 FUNCIÓN: REPORTE DE VIGENCIAS (AHORA CON PDF)
def enviar_reporte_imss_manual(datos_trabajadores, datos_base):
    try:
        remitente = os.environ.get("CORREO_BOT", "").strip()
        password = os.environ.get("PASS_BOT", "").strip()
        
        if not remitente or not password:
            return False, "Faltan las contraseñas del correo en el servidor."

        hoy = datetime.datetime.now().date()
        
        ultimas_asignaciones = {}
        for reg in datos_trabajadores:
            nombre = str(reg.get("Nombre del Trabajador", "")).strip().upper()
            if nombre: ultimas_asignaciones[nombre] = reg
        
        lista_activos = []
        lista_inactivos = []
        
        for emp in datos_base:
            nombre = str(emp.get("Nombre del Trabajador", "")).strip().upper()
            if not nombre: continue
            
            asig = ultimas_asignaciones.get(nombre)
            if asig:
                estatus = str(asig.get("Estatus IMSS", "")).upper()
                obra = str(asig.get("Folio Obra", "N/A"))
                vigencia = str(asig.get("Vigencia IMSS", "N/A"))
                
                if "BAJA" in estatus:
                    lista_inactivos.append({"nombre": nombre, "obra": obra})
                else:
                    estado_vigencia = ""
                    if vigencia and vigencia != "N/A":
                        try:
                            fecha_v = datetime.datetime.strptime(vigencia, "%d/%m/%Y").date()
                            dias = (fecha_v - hoy).days
                            if dias < 0: estado_vigencia = "¡VENCIDO!"
                            elif dias <= 7: estado_vigencia = f"¡ALERTA! Vence en {dias} dias"
                            else: estado_vigencia = f"Vigente ({dias} d. restantes)"
                        except Exception:
                            estado_vigencia = "Error de fecha"
                    lista_activos.append({"nombre": nombre, "obra": obra, "vigencia": vigencia, "estado": estado_vigencia})
            else:
                lista_inactivos.append({"nombre": nombre, "obra": "SIN ASIGNACIONES HISTORICAS"})

        # --- CREACIÓN DEL PDF ---
        pdf = PDF_Trabajadores()
        pdf.alias_nb_pages()
        pdf.add_page()
        
        # TABLA DE ACTIVOS
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(15, 60, 140)
        pdf.cell(0, 8, "TRABAJADORES ACTIVOS EN OBRA", ln=True)
        pdf.draw_table_header("ACTIVOS")
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', '', 8)
        
        for act in lista_activos:
            if pdf.get_y() > 260: 
                pdf.add_page()
                pdf.draw_table_header("ACTIVOS")
                pdf.set_font('Arial', '', 8)
            
            # ✂️ Tijera anti-descuadre para nombres larguísimos
            nom_str = act['nombre'][:35]
            obra_str = act['obra'][:23]
            vig_str = act['vigencia']
            est_str = act['estado'][:25]
            
            pdf.set_text_color(0, 0, 0)
            pdf.cell(70, 6, nom_str, border=1)
            pdf.cell(45, 6, obra_str, border=1)
            pdf.cell(25, 6, vig_str, border=1, align='C')
            
            # Semáforo de colores para Recursos Humanos
            if "VENCIDO" in est_str: 
                pdf.set_text_color(200, 0, 0); pdf.set_font('Arial', 'B', 8)
            elif "ALERTA" in est_str: 
                pdf.set_text_color(200, 120, 0); pdf.set_font('Arial', 'B', 8)
            else: 
                pdf.set_text_color(0, 100, 0); pdf.set_font('Arial', '', 8)
                
            pdf.cell(50, 6, est_str, border=1, ln=True, align='C')
            pdf.set_font('Arial', '', 8)

        # TABLA DE INACTIVOS
        pdf.ln(10)
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, "TRABAJADORES SIN OBRA (O DADOS DE BAJA)", ln=True)
        pdf.draw_table_header("INACTIVOS")
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', '', 8)
        
        for ina in lista_inactivos:
            if pdf.get_y() > 260: 
                pdf.add_page()
                pdf.draw_table_header("INACTIVOS")
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Arial', '', 8)
            
            nom_str = ina['nombre'][:50]
            obra_str = ina['obra'][:45]
            pdf.cell(100, 6, nom_str, border=1)
            pdf.cell(90, 6, obra_str, border=1, ln=True)

        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        
        # --- ENVÍO DEL CORREO ---
        msg = EmailMessage()
        msg['Subject'] = f'REPORTE IMSS: Estatus de Plantilla al {hoy.strftime("%d/%m/%Y")}'
        msg['From'] = remitente
        msg['To'] = 'rh@grupo-imac.com, comercial@grupo-imac.com'
        msg.set_content("Se adjunta a este correo el PDF con el Reporte Oficial de Trabajadores, Asignaciones de Obra y Vigencias IMSS actualizado.\n\nFavor de revisar las alertas de vencimiento en las casillas correspondientes.\n\nAtentamente,\nERP Grupo IMAC")
        
        nombre_archivo = f"Reporte_IMSS_{hoy.strftime('%d%m%Y')}.pdf"
        msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=nombre_archivo)
        
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls()
            smtp.login(remitente, password)
            smtp.send_message(msg)
            
        return True, "El PDF fue generado y enviado exitosamente a Recursos Humanos."
    except Exception as e:
        return False, f"Ocurrió un error al enviar el correo: {e}"

@st.cache_resource
def conectar_sheets():
    try:
        credenciales_dic = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(credenciales_dic, scopes=scopes)
        cliente = gspread.authorize(creds)
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
                            
                            st.markdown("---")
                            st.markdown("**Vigencia del Seguro:**")
                            vigencia_imss = st.date_input("Selecciona la fecha límite de vigencia (IMSS):", min_value=datetime.date.today())
                            
                            btn_asignar = st.form_submit_button("➕ ASIGNAR TRABAJADOR A LA OBRA")
                            
                            if btn_asignar:
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
                                        st.error(f"No puedes moverlo a esta obra (RP: **{registro_patronal_obra}**) sin antes registrarle una '🔴 BAJA' en su obra anterior.")

                                if vigencia_imss < datetime.date.today() and "BAJA" not in estatus_imss:
                                    candado_activado = True
                                    st.error("⚠️ **CANDADO DE VIGENCIA:** No puedes dar de alta a un trabajador con una fecha del IMSS que ya está vencida en el pasado.")

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
                                        trabajador_info.get("RFC", ""),
                                        vigencia_imss.strftime("%d/%m/%Y") 
                                    ])
                                    
                                    registrar_bitacora(doc, "Control de Trabajadores", f"Asignó a {trabajador_sel} a la obra {folio_seleccionado}. Vence: {vigencia_imss.strftime('%d/%m/%Y')}")
                                    st.success(f"✅ ¡Éxito! {trabajador_sel} asignado correctamente a la obra {folio_seleccionado}.")
                                    st.rerun()

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
                        vigencia_txt = trabajador.get("Vigencia IMSS", "No registrada") 
                        
                        color_fondo = "#fafafa" if "BAJA" not in estatus.upper() else "#ffebee"
                        
                        st.markdown(f"""
                        <div style='padding: 15px; border-radius: 8px; border: 1px solid #ddd; margin-bottom: 12px; background-color: {color_fondo};'>
                            <strong style='font-size: 16px; color: #0f3c8c;'>{nombre}</strong> - <em>{trabajador.get('Puesto / Rol', 'N/A')}</em><br>
                            <span style='color: #555;'>NSS: {trabajador.get('NSS', 'N/A')} | <strong>RFC: {rfc_trabajador}</strong> | RP Vinculado: {rp_trabajador}</span><br>
                            Estatus Actual: <strong>{estatus}</strong> | 📅 <strong>Vigencia: {vigencia_txt}</strong>
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
        # 🚀 BOTÓN MANUAL PARA ENVIAR REPORTE PDF A RRHH
        col_tit_tablero, col_btn_reporte = st.columns([2, 1])
        with col_tit_tablero:
            st.subheader("📊 Estatus de Ocupación General de Plantilla")
            st.write("Control total de asignaciones. Muestra de forma unificada dónde está parado cada elemento del catálogo maestro.")
        with col_btn_reporte:
            st.write("") # Espaciador
            # 🚀 EL BOTÓN AHORA INDICA QUE GENERA PDF
            if st.button("📄 GENERAR Y ENVIAR PDF A RRHH", type="primary", use_container_width=True):
                with st.spinner("Ensamblando PDF corporativo y enviando a Recursos Humanos..."):
                    exito, mensaje = enviar_reporte_imss_manual(datos_trabajadores, datos_base)
                    if exito:
                        st.success(mensaje)
                        registrar_bitacora(doc, "Control de Trabajadores", "Envió reporte PDF manual de vigencias IMSS")
                    else:
                        st.error(mensaje)
        
        st.markdown("---")
        
        if not datos_base:
            st.info("No hay personal registrado en el Catálogo Maestro.")
        else:
            ultimas_asignaciones = {}
            for reg in datos_trabajadores:
                nombre_t = str(reg.get("Nombre del Trabajador", "")).strip().upper()
                if nombre_t:
                    ultimas_asignaciones[nombre_t] = reg

            tabla_global = []
            for emp in datos_base:
                nombre_emp = str(emp.get("Nombre del Trabajador", "")).strip().upper()
                if not nombre_emp: continue
                
                puesto_emp = emp.get("Puesto / Rol", "N/A")
                nss_emp = emp.get("NSS", "N/A")
                rfc_emp = emp.get("RFC", "N/A")

                registro_asig = ultimas_asignaciones.get(nombre_emp)
                if registro_asig:
                    estatus_imss_act = str(registro_asig.get("Estatus IMSS", "")).upper()
                    if "BAJA" in estatus_imss_act:
                        obra_activa = "🟢 DISPONIBLE (SIN OBRA)"
                        estatus_pantalla = "🔴 BAJA"
                        rp_act = "N/A"
                        vigencia_pantalla = "N/A"
                    else:
                        obra_activa = registro_asig.get("Folio Obra", "N/A")
                        estatus_pantalla = registro_asig.get("Estatus IMSS", "N/A")
                        rp_act = registro_asig.get("Registro Patronal", "N/A")
                        vigencia_pantalla = registro_asig.get("Vigencia IMSS", "N/A")
                else:
                    obra_activa = "🟢 DISPONIBLE (SIN OBRA)"
                    estatus_pantalla = "SIN ASIGNACIONES"
                    rp_act = "N/A"
                    vigencia_pantalla = "N/A"

                tabla_global.append({
                    "Nombre del Trabajador": nombre_emp,
                    "Puesto / Rol": puesto_emp,
                    "NSS": nss_emp,
                    "RFC": rfc_emp,
                    "Obra Asignada": obra_activa,
                    "Estatus IMSS": estatus_pantalla,
                    "RP de Obra": rp_act,
                    "Vigencia": vigencia_pantalla
                })

            df_master = pd.DataFrame(tabla_global)
            filtro_texto = st.text_input("🔍 Filtrar Tabla (Escribe nombre, obra o puesto):", placeholder="Ej. Oficial, OBRA04, Juan...")
            
            if filtro_texto:
                termino = filtro_texto.upper().strip()
                df_master = df_master[df_master.astype(str).apply(lambda x: x.str.contains(termino)).any(axis=1)]

            st.dataframe(df_master, use_container_width=True, hide_index=True)
