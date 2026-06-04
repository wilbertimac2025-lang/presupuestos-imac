import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime
from fpdf import FPDF
import os

st.set_page_config(page_title="ERP - Gestión de Obras", page_icon="🏗️", layout="wide")

def limpiar_monto(valor):
    """Limpia los textos de Excel para poder hacer operaciones matemáticas"""
    if str(valor).strip() == "" or valor is None: return 0.0
    try: return float(str(valor).replace("$", "").replace(",", "").replace(" ", "").strip())
    except: return 0.0

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
        doc = cliente.open_by_key(ID_DEL_EXCEL)
        return doc
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

st.title("🏗️ Centro de Control de Obras")
st.markdown("---")

doc = conectar_sheets()

if doc:
    try:
        hoja_presupuestos = doc.worksheet("Presupuestos")
        hoja_obras = doc.worksheet("Obras_Activas")
        hoja_convenios = doc.worksheet("Convenios_Adicionales") # Nueva pestaña conectada
    except Exception as e:
        st.error("⚠️ Falta crear la pestaña 'Convenios_Adicionales' en tu Excel.")
        st.stop()

    datos_presupuestos = hoja_presupuestos.get_all_records()
    datos_obras = hoja_obras.get_all_records()
    
    llave_folio_pres = None
    if datos_presupuestos:
        for llave in datos_presupuestos[0].keys():
            if str(llave).strip().upper() == "FOLIO":
                llave_folio_pres = llave
                break
                
    folios_disponibles = [str(fila[llave_folio_pres]) for fila in datos_presupuestos if str(fila.get(llave_folio_pres, "")) != ""] if llave_folio_pres else []

    llave_folio_obra = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "FOLIO" in str(k).upper()), None)
    llave_estatus = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "ESTATUS" in str(k).upper()), None)
    obras_activas = [str(fila[llave_folio_obra]) for fila in datos_obras if str(fila.get(llave_estatus, "")).upper() == "EN EJECUCIÓN"] if llave_folio_obra and llave_estatus else []

    # --- PESTAÑAS DEL MÓDULO ---
    tab1, tab2, tab3 = st.tabs(["🚀 Apertura de Obra", "📝 Convenios (Trabajos Extra)", "🏁 Cierre de Proyecto"])

    # =======================================================
    # PESTAÑA 1: APERTURA DE OBRA
    # =======================================================
    with tab1:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Dar de alta nueva obra")
            if not folios_disponibles: st.warning("⚠️ No se detectaron Folios en tus presupuestos.")
            folio_seleccionado = st.selectbox("Folio Aprobado:", ["Selecciona un folio..."] + folios_disponibles)

        if folio_seleccionado != "Selecciona un folio...":
            datos_obra = next((item for item in datos_presupuestos if str(item.get(llave_folio_pres, "")) == folio_seleccionado), None)
            if datos_obra:
                with col2:
                    with st.form("form_apertura_obra"):
                        cliente_obtenido = "N/A"
                        proyecto_obtenido = "N/A"
                        monto_obtenido = "N/A"
                        
                        for llave, valor in datos_obra.items():
                            llave_upper = str(llave).strip().upper()
                            if "CLIENTE" in llave_upper: cliente_obtenido = valor
                            elif "PROYECTO" in llave_upper or "UBICACIÓN" in llave_upper or "UBICACION" in llave_upper: proyecto_obtenido = valor
                            elif "TOTAL" in llave_upper or "PRESUPUESTO" in llave_upper: monto_obtenido = valor

                        st.write(f"**Cliente:** {cliente_obtenido}")
                        st.write(f"**Proyecto/Ubicación:** {proyecto_obtenido}")
                        fecha_inicio = st.date_input("Fecha Oficial de Arranque")
                        residente = st.text_input("Nombre del Residente / Encargado")
                        
                        boton_arranque = st.form_submit_button("🚀 INICIAR PROYECTO")
                        
                        if boton_arranque:
                            if not residente: st.warning("⚠️ Debes asignar un residente.")
                            else:
                                hoja_obras.append_row([
                                    folio_seleccionado, cliente_obtenido, proyecto_obtenido,
                                    "EN EJECUCIÓN", monto_obtenido, fecha_inicio.strftime("%d/%m/%Y"), residente.upper()
                                ])
                                st.success(f"¡Obra {folio_seleccionado} dada de alta!")

    # =======================================================
    # PESTAÑA 2: CONVENIOS Y TRABAJOS ADICIONALES (LA NUEVA MAGIA)
    # =======================================================
    with tab2:
        colA, colB = st.columns([1, 2])
        with colA:
            st.subheader("Modificación de Presupuesto")
            folio_convenio = st.selectbox("Selecciona la Obra Activa:", ["..."] + obras_activas, key="sel_conv")
            
        if folio_convenio != "...":
            obra_a_modificar = next((item for item in datos_obras if str(item.get(llave_folio_obra, "")) == folio_convenio), None)
            if obra_a_modificar:
                # Buscar en qué columna está el presupuesto y cuánto es actualmente
                llave_monto = next((k for k in obra_a_modificar.keys() if "PRESUPUESTO" in str(k).upper() or "AUTORIZADO" in str(k).upper() or "MONTO" in str(k).upper()), None)
                presupuesto_actual = limpiar_monto(obra_a_modificar.get(llave_monto, 0)) if llave_monto else 0.0
                
                with colB:
                    st.info(f"📊 **Presupuesto Actual Autorizado:** ${presupuesto_actual:,.2f} MXN")
                    
                    with st.form("form_convenio"):
                        concepto_conv = st.text_input("Concepto del Convenio / Trabajo Extra", placeholder="Ej. Modificación en diseño de plafón y pintura extra")
                        monto_conv = st.number_input("Monto Adicional Autorizado ($ MXN)", min_value=0.0, step=500.0)
                        
                        btn_conv = st.form_submit_button("📝 REGISTRAR CONVENIO Y AUMENTAR PRESUPUESTO")
                        
                        if btn_conv:
                            if not concepto_conv or monto_conv <= 0:
                                st.warning("⚠️ Escribe un concepto válido y un monto mayor a cero.")
                            else:
                                # 1. Guardar en el historial de convenios
                                fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
                                hoja_convenios.append_row([fecha_hoy, folio_convenio, concepto_conv.upper(), monto_conv])
                                
                                # 2. Matemáticas: Sumar el nuevo dinero al presupuesto original
                                nuevo_presupuesto = presupuesto_actual + monto_conv
                                
                                # 3. Buscar la fila y columna exactas en Excel para reescribir la celda
                                fila_excel = 0
                                for indice, fila in enumerate(datos_obras):
                                    if str(fila.get(llave_folio_obra, "")) == folio_convenio:
                                        fila_excel = indice + 2 
                                        break
                                
                                titulos_obras = list(datos_obras[0].keys()) if datos_obras else []
                                col_excel = titulos_obras.index(llave_monto) + 1 if llave_monto in titulos_obras else 0
                                
                                if fila_excel > 0 and col_excel > 0:
                                    hoja_obras.update_cell(fila_excel, col_excel, nuevo_presupuesto)
                                    st.success(f"✅ ¡Éxito! El convenio se guardó y el presupuesto de la obra subió a ${nuevo_presupuesto:,.2f} MXN.")
                                    st.rerun()

    # =======================================================
    # PESTAÑA 3: CIERRE DE OBRA
    # =======================================================
    with tab3:
        colX, colY = st.columns([1, 2])
        with colX:
            st.subheader("Selección de Obra a Cerrar")
            if not obras_activas: st.info("No hay obras en ejecución.")
            else: folio_cierre = st.selectbox("Obra a Finalizar:", ["..."] + obras_activas, key="sel_cierre")

        if 'folio_cierre' in locals() and folio_cierre != "...":
            obra_a_cerrar = next((item for item in datos_obras if str(item.get(llave_folio_obra, "")) == folio_cierre), None)
            if obra_a_cerrar:
                cliente_cierre = obra_a_cerrar.get("Cliente", "Estimado Cliente")
                proyecto_cierre = obra_a_cerrar.get("Proyecto", "Proyecto Especificado")
                
                with colY:
                    st.info(f"Vas a cerrar definitivamente la obra de **{cliente_cierre}**.")
                    if st.button("🔒 CERRAR OBRA Y GENERAR CARTA"):
                        with st.spinner("Actualizando sistema y generando documento..."):
                            fila_excel = 0
                            for indice, fila in enumerate(datos_obras):
                                if str(fila.get(llave_folio_obra, "")) == folio_cierre:
                                    fila_excel = indice + 2 
                                    break
                            
                            titulos_obras = list(datos_obras[0].keys()) if datos_obras else []
                            col_estatus = titulos_obras.index(llave_estatus) + 1 if llave_estatus in titulos_obras else 4
                            
                            if fila_excel > 0:
                                hoja_obras.update_cell(fila_excel, col_estatus, "CERRADA")
                                
                            pdf = PDF_Carta()
                            pdf.add_page()
                            fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
                            
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
                                f"Quedamos a su entera disposición para futuros proyectos.\n\n"
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
                            st.download_button(label="📥 DESCARGAR CARTA DE AGRADECIMIENTO", data=pdf_bytes, file_name=f"Carta_Cierre_{folio_cierre}.pdf", mime="application/pdf")
