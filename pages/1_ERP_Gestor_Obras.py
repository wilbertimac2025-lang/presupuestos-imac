import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime
from fpdf import FPDF
import os

st.set_page_config(page_title="ERP - Gestión de Obras", page_icon="🏗️", layout="wide")

# --- CLASE PARA EL PDF DE LA CARTA ---
class PDF_Carta(FPDF):
    def header(self):
        if os.path.exists("logo_tarc.png"):
            self.image("logo_tarc.png", x=15, y=10, w=70)
        elif os.path.exists("logo_tarc.jpg"):
            self.image("logo_tarc.jpg", x=15, y=10, w=70)
        
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
    hoja_presupuestos = doc.worksheet("Presupuestos")
    hoja_obras = doc.worksheet("Obras_Activas")

    datos_presupuestos = hoja_presupuestos.get_all_records()
    datos_obras = hoja_obras.get_all_records()
    
    # Llaves inteligentes
    llave_folio_pres = None
    if datos_presupuestos:
        for llave in datos_presupuestos[0].keys():
            if str(llave).strip().upper() == "FOLIO":
                llave_folio_pres = llave
                break
                
    folios_disponibles = []
    if llave_folio_pres:
        folios_disponibles = [str(fila[llave_folio_pres]) for fila in datos_presupuestos if str(fila.get(llave_folio_pres, "")) != ""]

    # --- PESTAÑAS DEL MÓDULO ---
    tab1, tab2 = st.tabs(["🚀 Apertura de Obra", "🏁 Cierre de Proyecto (Carta al Cliente)"])

    # =======================================================
    # PESTAÑA 1: APERTURA DE OBRA (Tu código que ya funcionaba)
    # =======================================================
    with tab1:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Dar de alta nueva obra")
            if not folios_disponibles:
                st.warning("⚠️ No se detectaron Folios en tus presupuestos.")
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
                        residente = st.text_input("Nombre del Residente / Encargado de Cuadrilla")
                        
                        boton_arranque = st.form_submit_button("🚀 INICIAR PROYECTO")
                        
                        if boton_arranque:
                            if not residente: 
                                st.warning("⚠️ Debes asignar un residente para la obra.")
                            else:
                                hoja_obras.append_row([
                                    folio_seleccionado, cliente_obtenido, proyecto_obtenido,
                                    "EN EJECUCIÓN", monto_obtenido, fecha_inicio.strftime("%d/%m/%Y"), residente.upper()
                                ])
                                st.balloons()
                                st.success(f"¡Obra {folio_seleccionado} dada de alta!")

    # =======================================================
    # PESTAÑA 2: CIERRE Y CARTA DE AGRADECIMIENTO
    # =======================================================
    with tab2:
        # Filtrar solo obras que están "EN EJECUCIÓN"
        llave_folio_obra = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "FOLIO" in str(k).upper()), None)
        llave_estatus = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "ESTATUS" in str(k).upper()), None)
        
        obras_activas = []
        if llave_folio_obra and llave_estatus:
            obras_activas = [str(fila[llave_folio_obra]) for fila in datos_obras if str(fila.get(llave_estatus, "")).upper() == "EN EJECUCIÓN"]

        colA, colB = st.columns([1, 2])
        
        with colA:
            st.subheader("Selección de Obra a Cerrar")
            if not obras_activas:
                st.info("No hay obras en ejecución en este momento.")
            else:
                folio_cierre = st.selectbox("Obra a Finalizar:", ["..."] + obras_activas)

        if 'folio_cierre' in locals() and folio_cierre != "...":
            obra_a_cerrar = next((item for item in datos_obras if str(item.get(llave_folio_obra, "")) == folio_cierre), None)
            
            if obra_a_cerrar:
                cliente_cierre = obra_a_cerrar.get("Cliente", "Estimado Cliente")
                proyecto_cierre = obra_a_cerrar.get("Proyecto", "Proyecto Especificado")
                
                with colB:
                    st.info(f"Vas a cerrar definitivamente la obra de **{cliente_cierre}**. Esta acción la removerá de las listas de gastos y almacén.")
                    
                    if st.button("🔒 CERRAR OBRA Y GENERAR CARTA"):
                        with st.spinner("Actualizando sistema y generando documento..."):
                            # 1. ACTUALIZAR EXCEL A "CERRADA"
                            fila_excel = 0
                            for indice, fila in enumerate(datos_obras):
                                if str(fila.get(llave_folio_obra, "")) == folio_cierre:
                                    fila_excel = indice + 2 
                                    break
                            
                            if fila_excel > 0:
                                # Suponiendo que el Estatus está en la columna 4 (D)
                                hoja_obras.update_cell(fila_excel, 4, "CERRADA")
                                
                            # 2. GENERAR CARTA PDF
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
                                f"Hacemos de su conocimiento que los trabajos han sido concluidos satisfactoriamente. Nuestro compromiso "
                                f"es brindarle la más alta calidad en materiales y mano de obra, esperando que el resultado final "
                                f"cumpla y supere sus expectativas.\n\n"
                                f"Quedamos a su entera disposición para futuros proyectos y para hacer válida cualquier garantía correspondiente "
                                f"a los sistemas instalados.\n\n"
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
                                label="📥 DESCARGAR CARTA DE AGRADECIMIENTO (PDF)",
                                data=pdf_bytes,
                                file_name=f"Carta_Cierre_{folio_cierre}.pdf",
                                mime="application/pdf"
                            )
