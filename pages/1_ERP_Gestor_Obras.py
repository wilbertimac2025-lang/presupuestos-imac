import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime
from fpdf import FPDF
import os

st.set_page_config(page_title="ERP - Gestión de Obras", page_icon="🏗️", layout="wide")

# 🛡️ CANDADO DE SEGURIDAD GENERAL POR ROLES
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ Acceso denegado. Inicia sesión en la página principal.")
    st.stop()

ROLES_PERMITIDOS = ["Admin", "Operativo"]
if st.session_state.get("role") not in ROLES_PERMITIDOS:
    st.error(f"🚫 ACCESO RESTRINGIDO: Este módulo es exclusivo para Dirección (Admin).")
    st.stop()

def limpiar_monto(valor):
    if str(valor).strip() == "" or valor is None: return 0.0
    try: return float(str(valor).replace("$", "").replace(",", "").replace(" ", "").strip())
    except: return 0.0

# --- CLASE PARA EL PDF DE LA CARTA ---
class PDF_Carta(FPDF):
    def header(self):
        if os.path.exists("logo_tarc.png"): self.image("logo_tarc.png", x=15, y=10, w=70)
        elif os.path.exists("logo_tarc.jpg"): self.image("logo_tarc.jpg", x=15, y=10, w=70)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(15, 60, 140)
        self.cell(0, 10, 'TARC S.A. DE C.V.', ln=True, align='R')
        self.set_font('Arial', '', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 4, 'BOULEVARD MIGUEL ALEMAN 759, COL. CENTRO', ln=True, align='R')
        self.cell(0, 4, 'VERACRUZ, VER. C.P. 91700', ln=True, align='R')
        self.set_y(45)

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

st.title("🏗️ Centro de Control de Obras")
st.markdown("---")

doc = conectar_sheets()

if doc:
    try:
        hoja_presupuestos = doc.worksheet("Presupuestos")
        hoja_obras = doc.worksheet("Obras_Activas")
        hoja_convenios = doc.worksheet("Convenios_Adicionales") 
    except Exception as e:
        st.error("⚠️ Faltan pestañas en tu Excel.")
        st.stop()

    datos_presupuestos = hoja_presupuestos.get_all_records()
    datos_obras = hoja_obras.get_all_records()
    
    llave_folio_pres = next((k for k in (datos_presupuestos[0].keys() if datos_presupuestos else []) if "FOLIO" in str(k).upper()), None)
    folios_disponibles = [str(fila[llave_folio_pres]) for fila in datos_presupuestos if str(fila.get(llave_folio_pres, "")) != ""] if llave_folio_pres else []

    llave_folio_obra = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "FOLIO" in str(k).upper()), None)
    llave_estatus = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "ESTATUS" in str(k).upper()), None)
    obras_activas = [str(fila[llave_folio_obra]) for fila in datos_obras if str(fila.get(llave_estatus, "")).upper() == "EN EJECUCIÓN"] if llave_folio_obra and llave_estatus else []

    tab1, tab2, tab3 = st.tabs(["🚀 Apertura de Obra", "📝 Convenios (Trabajos Extra)", "🏁 Cierre de Proyecto"])

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
                        registro_patronal = st.text_input("Registro Patronal IMSS (Obligatorio para la obra)")
                        
                        # 📝 NUEVO CAMPO: REGISTRO DE OBRA
                        registro_obra = st.text_input("Registro de Obra (SIROC / Número de Contrato)")
                        
                        boton_arranque = st.form_submit_button("🚀 INICIAR PROYECTO")
                        
                        if boton_arranque:
                            if not residente or not registro_patronal or not registro_obra: 
                                st.warning("⚠️ Debes asignar el residente, el Registro Patronal IMSS y el Registro de Obra.")
                            else:
                                # Se añade el registro de obra al final de la fila
                                hoja_obras.append_row([
                                    folio_seleccionado, cliente_obtenido, proyecto_obtenido,
                                    "EN EJECUCIÓN", monto_obtenido, fecha_inicio.strftime("%d/%m/%Y"), 
                                    residente.upper(), registro_patronal.upper(), registro_obra.upper()
                                ])
                                st.success(f"¡Obra dada de alta con éxito! RP: {registro_patronal.upper()} | Registro Obra: {registro_obra.upper()}")

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
                        concepto_conv = st.text_input("Concepto del Convenio", placeholder="Ej. Trabajos extra")
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
    # PESTAÑA 3: CIERRE DE OBRA Y GENERACIÓN PDF
    # ==========================================
    with tab3:
        colX, colY = st.columns([1, 2])
        with colX:
            st.subheader("Selección de Obra a Cerrar")
            folio_cierre = st.selectbox("Obra a Finalizar:", ["..."] + obras_activas, key="sel_cierre") if obras_activas else "..."

        if folio_cierre != "...":
            obra_a_cerrar = next((item for item in datos_obras if str(item.get(llave_folio_obra, "")) == folio_cierre), None)
            if obra_a_cerrar:
                llave_cliente = next((k for k in obra_a_cerrar.keys() if "CLIENTE" in str(k).upper()), None)
                cliente_cierre = obra_a_cerrar.get(llave_cliente, "Estimado Cliente") if llave_cliente else "Estimado Cliente"

                llave_proyecto = next((k for k in obra_a_cerrar.keys() if any(p in str(k).upper() for p in ["PROYECTO", "UBICACI", "OBRA", "CONCEPTO"])), None)
                proyecto_cierre = obra_a_cerrar.get(llave_proyecto, "Proyecto Especificado") if llave_proyecto else "Proyecto Especificado"
                
                with colY:
                    st.info(f"Vas a cerrar definitivamente la obra de **{cliente_cierre}**.")
                    if st.button("🔒 CERRAR OBRA Y GENERAR CARTA"):
                        with st.spinner("Actualizando base de datos y generando PDF..."):
                            fila_excel = next((i + 2 for i, f in enumerate(datos_obras) if str(f.get(llave_folio_obra, "")) == folio_cierre), 0)
                            col_estatus = list(datos_obras[0].keys()).index(llave_estatus) + 1 if datos_obras and llave_estatus in datos_obras[0] else 4
                            
                            if fila_excel > 0:
                                hoja_obras.update_cell(fila_excel, col_estatus, "CERRADA")
                                
                                pdf = PDF_Carta()
                                pdf.add_page()
                                fecha_hoy = datetime.datetime.now().strftime("%d de %B del %Y")
                                
                                pdf.set_font('Arial', '', 11)
                                pdf.cell(0, 5, f"Veracruz, Ver. a {fecha_hoy}", ln=True, align='R')
                                pdf.ln(15)
                                pdf.set_font('Arial', 'B', 12)
                                pdf.set_text_color(15, 60, 140)
                                pdf.cell(0, 6, f"ATENCIÓN: {str(cliente_cierre).upper()}", ln=True)
                                pdf.set_font('Arial', 'B', 10)
                                pdf.set_text_color(100, 100, 100)
                                pdf.cell(0, 6, f"REF: Cierre de Proyecto - Folio {folio_cierre}", ln=True)
                                pdf.ln(10)
                                
                                pdf.set_font('Arial', '', 11)
                                pdf.set_text_color(50, 50, 50)
                                texto_cuerpo = (
                                    f"Por medio de la presente, el equipo directivo y operativo de TARC S.A. de C.V. (Grupo IMAC) "
                                    f"le extiende nuestro más sincero agradecimiento por la confianza depositada en nosotros para la "
                                    f"ejecución de la obra: '{proyecto_cierre}'.\n\n"
                                    f"Hacemos de su conocimiento que los trabajos han sido concluidos satisfactoriamente. "
                                    f"Nuestro compromiso es brindarle la más alta calidad en materiales y mano de obra, esperando que el resultado final cumpla y supere sus expectativas.\n\n"
                                    f"Quedamos a su entera disposición para futuros proyectos y garantías correspondientes.\n\n"
                                    f"Sin más por el momento, le enviamos un cordial saludo."
                                )
                                pdf.multi_cell(0, 6, txt=texto_cuerpo)
                                pdf.ln(25)
                                pdf.set_font('Arial', 'B', 11)
                                pdf.set_text_color(15, 60, 140)
                                pdf.cell(0, 5, "Atentamente,", ln=True, align='C')
                                pdf.ln(10)
                                pdf.cell(0, 5, "___________________________________", ln=True, align='C')
                                pdf.cell(0, 5, "Departamento de Operaciones", ln=True, align='C')
                                pdf.cell(0, 5, "TARC S.A. DE C.V.", ln=True, align='C')

                                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                                
                                st.success(f"✅ ¡La obra {folio_cierre} ha sido marcada como CERRADA exitosamente!")
                                st.download_button(
                                    label="📥 DESCARGAR CARTA DE AGRADECIMIENTO", 
                                    data=pdf_bytes, 
                                    file_name=f"Carta_Cierre_{folio_cierre}.pdf", 
                                    mime="application/pdf"
                                )
