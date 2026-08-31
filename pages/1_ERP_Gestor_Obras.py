import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime
import pandas as pd
from fpdf import FPDF
import os
import io
import smtplib
from email.message import EmailMessage
from PIL import Image

# --- CONFIGURACIÓN CORPORATIVA ---
icono_navegador = "logo_imac_2026.png" if os.path.exists("logo_imac_2026.png") else ("logo_tarc.png" if os.path.exists("logo_tarc.png") else "🏢")
st.set_page_config(page_title="ERP - Gestión de Obras", page_icon=icono_navegador, layout="wide")

# 🛡️ CANDADO DE SEGURIDAD GENERAL POR ROLES
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ Acceso denegado. Inicia sesión en la página principal.")
    st.stop()

ROLES_PERMITIDOS = ["Admin", "Operativo", "RRHH"]
if st.session_state.get("role") not in ROLES_PERMITIDOS:
    st.error("🚫 ACCESO RESTRINGIDO: Este módulo es exclusivo para Dirección (Admin).")
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

def limpiar_monto(valor):
    if str(valor).strip() == "" or valor is None: return 0.0
    try: return float(str(valor).replace("$", "").replace(",", "").replace(" ", "").strip())
    except: return 0.0

# 📧 FUNCIÓN: ENVÍO DE PDF (ACTA) A CORREOS CORPORATIVOS
def enviar_cierre_por_correo(pdf_bytes, nombre_archivo, cliente, folio):
    try:
        # 🚀 BLINDAJE PARA RENDER Y ANTI-ESPACIOS INVISIBLES
        remitente = os.environ.get("CORREO_BOT", "").strip()
        password = os.environ.get("PASS_BOT", "").strip()
        
        if not remitente or not password:
            st.error("🚨 ERROR: Faltan las contraseñas del correo (CORREO_BOT o PASS_BOT) en este archivo.")
            return False
        
        correo_destino = "comercial@grupo-imac.com, rh@grupo-imac.com, aco@grupo-imac.com, act@grupo-imac.com" 
        
        msg = EmailMessage()
        msg['Subject'] = f'CIERRE DE OBRA OFICIAL Y ACTA DE ENTREGA: {folio} - {cliente}'
        msg['From'] = remitente
        msg['To'] = correo_destino
        msg.set_content(f"Se ha registrado el cierre definitivo de la obra en el ERP.\n\nFolio: {folio}\nCliente: {cliente}\n\nSe adjunta el Acta de Entrega formal con la evidencia fotográfica del trabajo entregado incrustada.")
        msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=nombre_archivo)
        
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls()
            smtp.login(remitente, password)
            smtp.send_message(msg)
        return True
    except Exception as e: 
        # 🚨 LE QUITAMOS LA MORDAZA AL ERROR PARA QUE NOS AVISE EN PANTALLA QUÉ PASA
        st.error(f"🚨 ERROR TÉCNICO DE CORREO: {e}")
        return False

# --- CLASES PARA LOS 3 PDFs ---
class PDF_Base(FPDF):
    def header(self):
        # 🚀 SOLO LOGO VIEJO PARA LOS PDF OFICIALES (Evita que tape el texto)
        if os.path.exists("logo_tarc.png"): self.image("logo_tarc.png", x=15, y=10, w=50)
        elif os.path.exists("logo_tarc.jpg"): self.image("logo_tarc.jpg", x=15, y=10, w=50)
        
        self.set_font('Arial', 'B', 14)
        self.set_text_color(15, 60, 140)
        self.cell(0, 10, 'TARC S.A. DE C.V.', ln=True, align='R')
        self.set_font('Arial', '', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 4, 'BLVD. MIGUEL ALEMAN No. 306, BOCA DEL RIO, VER.', ln=True, align='R')
        self.cell(0, 4, 'TEL. (229) 935 45 25 / (229) 935 48 40', ln=True, align='R')
        self.set_y(35)
        
    def footer(self):
        # 🚀 NUEVO: PIE DE PÁGINA CON NUMERACIÓN (Página 1 de 2, etc.)
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Página {self.page_no()} de {{nb}}', 0, 0, 'C')

def generar_carta_agradecimiento(cliente, folio, proyecto, fecha_str):
    pdf = PDF_Base()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 5, f"Veracruz, Ver. a {fecha_str}", ln=True, align='R')
    pdf.ln(10)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(15, 60, 140)
    pdf.cell(0, 6, f"ATENCIÓN: {str(cliente).upper()}", ln=True)
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"REF: Cierre de Proyecto - Folio {folio}", ln=True)
    pdf.ln(10)
    
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(0, 0, 0)
    texto = (
        f"Por medio de la presente, el equipo directivo y operativo de TARC S.A. de C.V. (Grupo IMAC) "
        f"le extiende nuestro más sincero agradecimiento por la confianza depositada en nosotros para la "
        f"ejecución de la obra: '{proyecto}'.\n\n"
        f"Hacemos de su conocimiento que los trabajos han sido concluidos satisfactoriamente. "
        f"Nuestro compromiso es brindarle la más alta calidad en materiales y mano de obra.\n\n"
        f"Quedamos a su entera disposición para futuros proyectos y aclaraciones.\n\n"
        f"Sin más por el momento, le enviamos un cordial saludo."
    )
    pdf.multi_cell(0, 6, txt=texto)
    pdf.ln(25)
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(15, 60, 140)
    pdf.cell(0, 5, "Atentamente,", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(0, 5, "___________________________________", ln=True, align='C')
    pdf.cell(0, 5, "Departamento de Operaciones", ln=True, align='C')
    pdf.cell(0, 5, "TARC S.A. DE C.V.", ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1')

def generar_acta_entrega(cliente, folio, ubicacion, sistema, fecha_str, foto_bytes):
    pdf = PDF_Base()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(15, 60, 140)
    pdf.cell(0, 6, "ACTA DE ENTREGA DE OBRA", ln=True, align='C')
    pdf.cell(0, 6, "PROCESO DE ENTREGA DE OBRA", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 5, f"VERACRUZ, VER. A {fecha_str.upper()}", ln=True, align='R')
    pdf.ln(5)
    
    pdf.cell(0, 5, f"DATOS DE LA OBRA: {ubicacion.upper()}", ln=True)
    pdf.cell(0, 5, "CONTRATISTA: TARC, S.A. DE C.V.", ln=True)
    pdf.cell(0, 5, f"CLIENTE: {str(cliente).upper()}", ln=True)
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 10)
    texto_legal = (
        "LA PRESENTE ACTA FORMALIZA LA ENTREGA FINAL DE LA OBRA POR PARTE DEL CONTRATISTA TARC, S. A. DE C. V., "
        "REPRESENTADO EN ESTE ACTO POR EL ING. JOSÉ CARLOS MORALES MORALES. SE HACE LA ENTREGA FÍSICA DE LA OBRA "
        f"CON DOMICILIO EN: {ubicacion.upper()} ESTA FUE EFECTUADA CON MATERIALES DE LA MÁS ALTA CALIDAD, QUE SE RIGEN "
        "CON NORMAS APROBADAS INTERNACIONALMENTE Y CON MANO DE OBRA ESPECIALIZADA, ASÍ COMO BAJO UNA SUPERVISIÓN ADECUADA. "
        "POR PARTE DEL CLIENTE, RECIBO SATISFACTORIAMENTE ESTA ACTA DE ENTREGA DE OBRA, CORROBORANDO FÍSICAMENTE QUE EL INMUEBLE "
        "ME LO ENTREGAN EN PERFECTO ESTADO, SIN NINGÚN PROBLEMA O PERCANCE EN ÉL. ESTOY COMPLETAMENTE CONFORME CON EL TRABAJO "
        "QUE REALIZO EL CONTRATISTA TARC, S. A. DE C. V. EN EL INMUEBLE."
    )
    pdf.multi_cell(0, 5, txt=texto_legal)
    pdf.ln(3)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, f"SISTEMA APLICADO: {sistema.upper()}", ln=True)
    pdf.ln(10)
    
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, txt=f"SIN MÁS POR EL MOMENTO SE EXTIENDE LA PRESENTE ACTA DE ENTREGA DE OBRA EN LA CIUDAD DE VERACRUZ, VER.")
    pdf.ln(25)
    
    # 🚀 LAS FIRMAS SE QUEDAN EN LA HOJA 1
    y_firmas = pdf.get_y()
    pdf.line(20, y_firmas, 90, y_firmas)
    pdf.line(120, y_firmas, 190, y_firmas)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(95, 5, "CLIENTE", align='C')
    pdf.cell(95, 5, "CONTRATISTA", align='C', ln=True)
    
    # 🚀 NUEVO: FOTO GIGANTE EN LA HOJA 2 (ANEXO)
    if foto_bytes:
        try:
            temp_img = "temp_acta.jpg"
            img = Image.open(foto_bytes)
            if img.mode in ('RGBA', 'P'): img = img.convert('RGB')
            img.save(temp_img, format="JPEG")
            
            w_px, h_px = img.size
            # Aumentamos los límites para que se vea mucho más grande (170x150 mm)
            ratio = min(170 / w_px, 150 / h_px)
            w_mm, h_mm = w_px * ratio, h_px * ratio
            x_mm = (210 - w_mm) / 2
            
            # AGREGAMOS LA NUEVA PÁGINA
            pdf.add_page()
            
            pdf.set_font('Arial', 'B', 14)
            pdf.set_text_color(15, 60, 140)
            pdf.cell(0, 10, "ANEXO FOTOGRÁFICO", ln=True, align='C')
            pdf.ln(5)

            y_actual = pdf.get_y()
            pdf.image(temp_img, x=x_mm, y=y_actual, w=w_mm, h=h_mm)
            
            # Ponemos el título solicitado debajo de la imagen
            pdf.set_y(y_actual + h_mm + 10)
            pdf.set_font('Arial', 'B', 12)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 10, "FOTO DEL TRABAJO REALIZADO", ln=True, align='C')
            
            if os.path.exists(temp_img): os.remove(temp_img)
        except Exception:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, "(Error al cargar imagen)", ln=True, align='C')
            
    return pdf.output(dest='S').encode('latin-1')

def generar_poliza_garantia(cliente, ubicacion, sistema, fecha_str):
    pdf = PDF_Base()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(15, 60, 140)
    pdf.cell(0, 6, "POLIZA DE GARANTIA", ln=True, align='C')
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, "PARA TRABAJOS DE IMPERMEABILIZACION.", ln=True, align='C')
    pdf.cell(0, 6, "OTORGA TARC S. A. DE C. V.", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 5, f"VERACRUZ, VER., A {fecha_str.upper()}.", ln=True, align='R')
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, txt=f"ESTA PÓLIZA DE GARANTÍA ES OTORGADA AL CLIENTE: {str(cliente).upper()} POR LOS TRABAJOS DE IMPERMEABILIZACIÓN EN LOSA DE CONCRETO EN: {ubicacion.upper()}.")
    pdf.ln(3)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, f"SISTEMA APLICADO: {sistema.upper()}", ln=True)
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, "C  L  A  U  S  U  L  A  S", ln=True, align='C')
    pdf.ln(3)
    
    pdf.set_font('Arial', '', 9)
    clausulas = [
        "PRIMERA. - LA OBRA FUE EFECTUADA CON MATERIALES DE LA MÁS ALTA CALIDAD, QUE SE RIGEN CON NORMAS APROBADAS INTERNACIONALMENTE Y CON MANO DE OBRA ESPECIALIZADA, ASÍ COMO BAJO UNA SUPERVISIÓN ADECUADA.",
        f"SEGUNDA. - ESTA PÓLIZA DE GARANTÍA AMPARA UN PERIODO DE 5 AÑOS EN {sistema.upper()} CONTRATADOS, A PARTIR DE LA FECHA DE ENTREGA DE LA OBRA, TRANSCURRIDO DICHO PLAZO SE EXTINGUE AUTOMÁTICAMENTE Y EL CLIENTE NO PODRÁ HACER NINGUNA RECLAMACIÓN AL CONTRATISTA.",
        "TERCERA. - EL CONTRATISTA SE COMPROMETE A REPARAR CON SU GESTACIÓN A LAS CLÁUSULAS QUE SIGUEN LAS FALLAS EN LA IMPERMEABILIZACIÓN EFECTUADA, PONIENDO MATERIALES Y MANO DE OBRA SIN CARGO PARA EL CLIENTE.",
        "CUARTA. - EL CONTRATISTA NO ESTÁ OBLIGADO A DAR SERVICIO REQUERIDO POR EL CLIENTE, SI SE COMPRUEBA QUE LOS DAÑOS OCASIONADOS EN EL TRABAJO DE IMPERMEABILIZACIÓN SE DEBEN A CAUSAS AJENAS A LOS PRODUCTOS EMPLEADOS O SU APLICACIÓN, TALES COMO ASENTAMIENTOS O FALLAS ESTRUCTURALES DEL EDIFICIO, INUNDACIONES, INCENDIOS, GRANIZOS, SISMOS, TERREMOTOS O CUALQUIER CASO FORTUITO O DE FUERZA MAYOR. LA PÓLIZA DE GARANTÍA QUEDARA NULA, SI SE OCASIONAN DAÑOS AL ÁREA TRABAJADA, COMO ARRASTRAR O MOVER OBJETOS QUE PERJUDIQUEN LA IMPERMEABILIZACIÓN. (ROMPAN EL SISTEMA)",
        "QUINTA. - EL CONTRATISTA NO SE HACE RESPONSABLE DE LOS DAÑOS Y/O PREJUICIOS QUE OCASIONEN LAS FALLAS DE LA IMPERMEABILIZACIÓN EN EL INTERIOR DEL INMUEBLE.",
        "SEXTA. - EL CLIENTE DEBERÁ DAR AVISO POR ESCRITO AL CONTRATISTA INMEDIATAMENTE DE LAS FALLAS DE LA IMPERMEABILIZACIÓN EFECTUADA.",
        "SEPTIMA. - LA PÓLIZA DE GARANTÍA NO OPERA SI EL CLIENTE NO EFECTÚA SUS PAGOS EN CANTIDAD Y TIEMPO CONVENIDO.",
        "OCTAVA. - POR EL HECHO DE RECIBIR EL CLIENTE ESTA PÓLIZA DE GARANTÍA, ACEPTA EN TODAS SUS PARTES LAS CLÁUSULAS QUE ANTECEDEN."
    ]
    
    for c in clausulas:
        pdf.multi_cell(0, 4.5, txt=c)
        pdf.ln(2)
        
    pdf.ln(15)
    pdf.cell(0, 5, "___________________________________", ln=True, align='C')
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, "C. MARIA ISIDRA ALVARADO ACOSTA", ln=True, align='C')
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, "CONTROL DE CALIDAD.", ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1')

@st.cache_resource
def conectar_sheets():
    try:
        texto_json = os.environ.get("GOOGLE_CREDENTIALS")
        if not texto_json:
            st.error("🚨 ERROR: Render no está detectando la llave GOOGLE_CREDENTIALS en el Environment.")
            return None
            
        credenciales_dic = json.loads(texto_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(credenciales_dic, scopes=scopes)
        cliente = gspread.authorize(creds)
        
        ID_DEL_EXCEL = os.environ.get("ID_EXCEL") 
        if not ID_DEL_EXCEL:
            st.error("🚨 ERROR: Render no está detectando la llave ID_EXCEL en el Environment.")
            return None
            
        return cliente.open_by_key(ID_DEL_EXCEL)
        
    except Exception as e:
        st.error(f"🚨 ERROR TÉCNICO DE CONEXIÓN CON GOOGLE: {e}")
        return None

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
    st.title("Centro de Control de Obras")
st.markdown("---")

doc = conectar_sheets()

if doc:
    try:
        hoja_presupuestos = doc.worksheet("Presupuestos")
        hoja_obras = doc.worksheet("Obras_Activas")
        hoja_convenios = doc.worksheet("Convenios_Adicionales")
        hoja_rp = doc.worksheet("Registros_Patronales") 
        hoja_facturas = doc.worksheet("Facturas_Obras")
    except Exception as e:
        st.error("⚠️ Faltan pestañas en tu Excel. Asegúrate de tener 'Obras_Activas', 'Presupuestos' y 'Facturas_Obras'.")
        st.stop()

    datos_presupuestos = hoja_presupuestos.get_all_records()
    datos_obras = hoja_obras.get_all_records()
    datos_rp = hoja_rp.get_all_records() 
    datos_facturas = hoja_facturas.get_all_records()
    
    llave_folio_pres = next((k for k in (datos_presupuestos[0].keys() if datos_presupuestos else []) if "FOLIO" in str(k).upper()), None)
    folios_disponibles = [str(fila[llave_folio_pres]) for fila in datos_presupuestos if str(fila.get(llave_folio_pres, "")) != ""] if llave_folio_pres else []

    llave_folio_obra = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "FOLIO" in str(k).upper()), None)
    llave_estatus = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "ESTATUS" in str(k).upper()), None)
    obras_activas = [str(fila[llave_folio_obra]) for fila in datos_obras if str(fila.get(llave_estatus, "")).upper() == "EN EJECUCIÓN"] if llave_folio_obra and llave_estatus else []

    lista_rps = [f'{str(r.get("Registro Patronal", ""))} - {str(r.get("Razón Social", ""))}' for r in datos_rp if str(r.get("Registro Patronal", "")) != ""]

    tab1, tab2, tab3, tab4 = st.tabs(["🚀 Apertura de Obra", "📝 Convenios (Trabajos Extra)", "🏁 Cierre de Proyecto", "🏛️ Catálogo Registros Patronales"])

    # ==========================================
    # PESTAÑA 1: APERTURA DE OBRA
    # ==========================================
    with tab1:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Dar de alta nueva obra")
            folio_seleccionado = st.selectbox("Folio Aprobado:", ["Selecciona un folio..."] + folios_disponibles)

        if folio_seleccionado != "Selecciona un folio...":
            datos_obra = next((item for item in datos_presupuestos if str(item.get(llave_folio_pres, "")) == folio_seleccionado), None)
            if datos_obra:
                with col2:
                    with st.form("form_apertura_obra"):
                        llave_cliente = next((k for k in datos_obra.keys() if "CLIENTE" in str(k).upper()), None)
                        cliente_obtenido = datos_obra.get(llave_cliente, "N/A") if llave_cliente else "N/A"

                        llave_proyecto = next((k for k in datos_obra.keys() if any(p in str(k).upper() for p in ["PROYECTO", "UBICACI", "OBRA", "CONCEPTO", "DESCRIPCI"])), None)
                        proyecto_obtenido = datos_obra.get(llave_proyecto, "N/A") if llave_proyecto else "N/A"

                        llave_monto = next((k for k in datos_obra.keys() if any(p in str(k).upper() for p in ["TOTAL", "PRESUPUESTO", "MONTO"])), None)
                        monto_obtenido = datos_obra.get(llave_monto, 0.0) if llave_monto else 0.0

                        st.write(f"**Cliente:** {cliente_obtenido}")
                        st.write(f"**Proyecto:** {proyecto_obtenido}")
                        
                        fecha_inicio = st.date_input("Fecha Oficial de Arranque")
                        residente = st.text_input("Nombre del Residente / Encargado")
                        
                        if not lista_rps:
                            st.warning("⚠️ No hay Registros Patronales dados de alta.")
                            registro_patronal_sel = ""
                        else:
                            registro_patronal_sel = st.selectbox("Registro Patronal IMSS Asignado:", lista_rps)
                        
                        registro_obra = st.text_input("Registro de Obra (SIROC / Número de Contrato)")
                        
                        boton_arranque = st.form_submit_button("🚀 INICIAR PROYECTO")
                        
                        if boton_arranque:
                            if not residente or not registro_patronal_sel or not registro_obra: 
                                st.warning("⚠️ Debes asignar el residente, el Registro Patronal IMSS y el Registro de Obra.")
                            else:
                                rp_final = registro_patronal_sel.split(" - ")[0].strip()
                                hoja_obras.append_row([
                                    folio_seleccionado, cliente_obtenido, proyecto_obtenido,
                                    "EN EJECUCIÓN", monto_obtenido, fecha_inicio.strftime("%d/%m/%Y"), 
                                    residente.upper(), rp_final.upper(), registro_obra.upper()
                                ])
                                registrar_bitacora(doc, "Gestor de Obras", f"Dio de alta la obra {folio_seleccionado}")
                                st.success(f"¡Obra dada de alta con éxito!")

    # ==========================================
    # PESTAÑA 2: CONVENIOS
    # ==========================================
    with tab2:
        colA, colB = st.columns([1, 2])
        with colA:
            st.subheader("Modificación de Presupuesto")
            folio_convenio = st.selectbox("Selecciona la Obra Activa:", ["..."] + obras_activas, key="sel_conv")
            
        if folio_convenio != "...":
            obra_a_modificar = next((item for item in datos_obras if str(item.get(llave_folio_obra, "")) == folio_convenio), None)
            if obra_a_modificar:
                llave_monto = next((k for k in obra_a_modificar.keys() if "PRESUPUESTO" in str(k).upper() or "AUTORIZADO" in str(k).upper() or "MONTO" in str(k).upper()), None)
                presupuesto_actual = limpiar_monto(obra_a_modificar.get(llave_monto, 0)) if llave_monto else 0.0
                
                with colB:
                    st.info(f"📊 **Presupuesto Actual Autorizado:** ${presupuesto_actual:,.2f} MXN")
                    with st.form("form_convenio"):
                        concepto_conv = st.text_input("Concepto del Convenio")
                        monto_conv = st.number_input("Monto Adicional ($ MXN)", min_value=0.0, step=500.0)
                        btn_conv = st.form_submit_button("📝 REGISTRAR CONVENIO")
                        
                        if btn_conv:
                            if not concepto_conv or monto_conv <= 0: st.warning("Escribe un concepto y monto válido.")
                            else:
                                fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
                                hoja_convenios.append_row([fecha_hoy, folio_convenio, concepto_conv.upper(), monto_conv])
                                nuevo_presupuesto = presupuesto_actual + monto_conv
                                fila_excel = next((i + 2 for i, f in enumerate(datos_obras) if str(f.get(llave_folio_obra, "")) == folio_convenio), 0)
                                col_excel = list(datos_obras[0].keys()).index(llave_monto) + 1 if datos_obras and llave_monto in datos_obras[0] else 0
                                
                                if fila_excel > 0 and col_excel > 0:
                                    hoja_obras.update_cell(fila_excel, col_excel, nuevo_presupuesto)
                                    st.success(f"✅ Presupuesto elevado a ${nuevo_presupuesto:,.2f}")
                                    st.rerun()

    # ==========================================
    # 🏁 PESTAÑA 3: CIERRE DE OBRA Y DOCUMENTACIÓN OFICIAL
    # ==========================================
    with tab3:
        st.subheader("🏁 Panel de Cierre y Documentación")
        folio_cierre = st.selectbox("Selecciona la Obra a Cerrar:", ["..."] + obras_activas, key="sel_cierre") if obras_activas else "..."
            
        if folio_cierre != "...":
            st.markdown("---")
            # 1. Recuperar datos combinados (Obras + Presupuestos)
            obra_act = next((item for item in datos_obras if str(item.get(llave_folio_obra, "")) == folio_cierre), {})
            obra_pres = next((item for item in datos_presupuestos if str(item.get(llave_folio_pres, "")) == folio_cierre), {})
            obra_completa = {**obra_act, **obra_pres}
            
            cliente_cierre = next((obra_completa[k] for k in obra_completa.keys() if "CLIENTE" in str(k).upper()), "Cliente General")
            proyecto_cierre = next((obra_completa[k] for k in obra_completa.keys() if any(p in str(k).upper() for p in ["PROYECTO", "OBRA", "CONCEPTO"])), "Proyecto Especificado")
            ubicacion_cierre = next((obra_completa[k] for k in obra_completa.keys() if any(p in str(k).upper() for p in ["UBICACION", "DIRECCION", "LUGAR"])), "Domicilio Conocido")
            sistema_aplicado = next((obra_completa[k] for k in obra_completa.keys() if "SISTEMA" in str(k).upper()), "Sistema Impermeabilizante Autorizado")
            
            # 2. Análisis Financiero en vivo
            llave_monto = next((k for k in obra_completa.keys() if any(p in str(k).upper() for p in ["TOTAL", "PRESUPUESTO", "MONTO"])), None)
            presupuesto_total = limpiar_monto(obra_completa.get(llave_monto, 0))
            
            facturas_obra = [f for f in datos_facturas if str(f.get("Folio Obra", "")) == folio_cierre]
            total_pagado = sum(limpiar_monto(f.get("Monto Facturado", 0)) for f in facturas_obra)
            saldo_pendiente = presupuesto_total - total_pagado
            
            # Fecha para los documentos
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            hoy = datetime.datetime.now()
            fecha_str = f"{hoy.day:02d} de {meses[hoy.month - 1]} de {hoy.year}"

            # Panel de información y candado
            col_info, col_foto = st.columns([1, 1])
            with col_info:
                st.info(f"**Cliente:** {cliente_cierre}\n\n**Dirección:** {ubicacion_cierre}\n\n**Sistema:** {sistema_aplicado}")
                if saldo_pendiente > 0:
                    st.error(f"🔴 **SALDO PENDIENTE DE COBRO:** ${saldo_pendiente:,.2f} MXN. \n\n*La póliza de garantía permanecerá bloqueada hasta que el cliente liquide el total.*")
                else:
                    st.success(f"🟢 **OBRA LIQUIDADA AL 100%.** \n\n*Póliza de garantía desbloqueada y lista para entrega.*")
            
            with col_foto:
                st.write("📷 **Fotografía de Evidencia (Obligatoria para el Acta)**")
                foto_responsiva = st.file_uploader("Sube la imagen del trabajo terminado (JPG/PNG):", type=["jpg", "jpeg", "png"])
                if not foto_responsiva:
                    st.warning("⚠️ Sin la foto, el Acta de Entrega se generará sin evidencia visual.")

            st.markdown("### 📄 Generación de Documentos")
            col_doc1, col_doc2, col_doc3 = st.columns(3)
            
            # BOTÓN 1: Carta
            with col_doc1:
                pdf_carta = generar_carta_agradecimiento(cliente_cierre, folio_cierre, proyecto_cierre, fecha_str)
                st.download_button("1️⃣ DESCARGAR CARTA DE AGRADECIMIENTO", pdf_carta, f"Carta_{folio_cierre}.pdf", "application/pdf")
            
            # BOTÓN 2: Acta
            with col_doc2:
                pdf_acta = generar_acta_entrega(cliente_cierre, folio_cierre, ubicacion_cierre, sistema_aplicado, fecha_str, foto_responsiva)
                st.download_button("2️⃣ DESCARGAR ACTA DE ENTREGA OFICIAL", pdf_acta, f"Acta_Entrega_{folio_cierre}.pdf", "application/pdf")
            
            # BOTÓN 3: Póliza
            with col_doc3:
                if saldo_pendiente > 0:
                    st.button("🔒 PÓLIZA DE GARANTÍA BLOQUEADA", disabled=True, help="El cliente aún presenta saldo deudor.")
                else:
                    pdf_poliza = generar_poliza_garantia(cliente_cierre, ubicacion_cierre, sistema_aplicado, fecha_str)
                    st.download_button("3️⃣ DESCARGAR PÓLIZA DE GARANTÍA", pdf_poliza, f"Poliza_Garantia_{folio_cierre}.pdf", "application/pdf")

            # ACCIÓN FINAL DE CIERRE EN EL SISTEMA
            st.markdown("---")
            if st.button("🚨 CERRAR PROYECTO EN SISTEMA Y ENVIAR ACTA A DIRECCIÓN", type="primary"):
                if not foto_responsiva:
                    st.error("❌ Debes subir la foto de evidencia antes de cerrar la obra en el sistema.")
                else:
                    with st.spinner("Actualizando sistema y enviando el Acta a corporativo..."):
                        # Se envía el acta que contiene la foto
                        envio_exitoso = enviar_cierre_por_correo(pdf_acta, f"Acta_{folio_cierre}.pdf", cliente_cierre, folio_cierre)
                        
                        fila_excel = next((i + 2 for i, f in enumerate(datos_obras) if str(f.get(llave_folio_obra, "")) == folio_cierre), 0)
                        col_estatus = list(datos_obras[0].keys()).index(llave_estatus) + 1 if datos_obras and llave_estatus in datos_obras[0] else 0
                        
                        if fila_excel > 0 and col_estatus > 0:
                            hoja_obras.update_cell(fila_excel, col_estatus, "CERRADA")
                            registrar_bitacora(doc, "Gestor de Obras", f"Cerró obra {folio_cierre}. Acta enviada: {envio_exitoso}")
                            
                            st.success(f"✅ ¡La obra {folio_cierre} ha sido marcada como CERRADA!")
                            if envio_exitoso: st.info("📧 El Acta de Entrega con la foto incrustada fue enviada a los directivos.")

    # ==========================================
    # 🚀 PESTAÑA 4: ALTA DE REGISTROS PATRONALES
    # ==========================================
    with tab4:
        st.subheader("🏛️ Alta de Registros Patronales (IMSS)")
        st.write("Agrega aquí los Registros Patronales (RP) de la empresa o subcontratistas.")
        
        with st.form("form_alta_rp"):
            col1, col2 = st.columns(2)
            with col1: nuevo_rp = st.text_input("Clave del Registro Patronal", placeholder="Ej. Y545678910")
            with col2: razon_social = st.text_input("Razón Social / Empresa Asociada", placeholder="Ej. TARC S.A. DE C.V.")
            notas_rp = st.text_input("Notas o Detalles (Opcional)")
            btn_rp = st.form_submit_button("💾 GUARDAR REGISTRO PATRONAL")
            
            if btn_rp:
                if not nuevo_rp or not razon_social: st.error("⚠️ La Clave del RP y la Razón Social son obligatorias.")
                else:
                    claves_existentes = [str(r.get("Registro Patronal", "")).upper() for r in datos_rp]
                    if nuevo_rp.upper() in claves_existentes: st.error(f"⚠️ El Registro Patronal {nuevo_rp.upper()} ya existe.")
                    else:
                        hoja_rp.append_row([nuevo_rp.upper(), razon_social.upper(), notas_rp])
                        st.success(f"✅ Registro Patronal agregado exitosamente.")
                        st.rerun()
        
        st.markdown("---")
        st.subheader("📋 Catálogo Actual de Registros Patronales")
        if datos_rp: st.dataframe(pd.DataFrame(datos_rp), use_container_width=True, hide_index=True)
