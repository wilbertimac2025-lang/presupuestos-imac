import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import math
from fpdf import FPDF
import datetime
import json
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Presupuestos IMAC", page_icon="📝", layout="centered")

# --- CLASE PARA EL PDF ---
class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Grupo IMAC | Presupuesto de Obra | Pagina {self.page_no()}', 0, 0, 'C')

# --- CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def conectar_sheets():
    try:
        credenciales_dic = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(credenciales_dic, scopes=scopes)
        cliente = gspread.authorize(creds)
        # ⚠️ PON AQUÍ TU ID REAL DE GOOGLE SHEETS
        sheet = cliente.open_by_key("1-grdT2H5dBlGVPvJbZ5wVYDdtVjQEEmUPGpvEm6C0Gc").worksheet("Presupuestos")
        return sheet
    except Exception as e:
        st.error("Error de conexión a la base de datos.")
        return None

# --- ESTILO ---
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #FF6600; color: white; height: 3em; width: 100%; border-radius: 10px; font-size: 20px; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INTERFAZ ---
st.title("🍊 Generador de Presupuestos IMAC")
st.subheader("Suministro y Aplicación de Impermeabilizante")

with st.form("presupuesto_form"):
    st.write("### 1. Información General")
    vendedor = st.text_input("Asesor Comercial")
    cliente_nom = st.text_input("Nombre del Cliente")
    obra_loc = st.text_input("Ubicación de la Obra")
    
    st.write("---")
    st.write("### 2. Detalles del Trabajo")
    col1, col2 = st.columns(2)
    with col1:
        sistema = st.selectbox("Sistema a Presupuestar:", [
            "Master Lasser 3.5mm Fibra Poliester",
            "Master Lasser 4.0mm Fibra Poliester",
            "Master Lasser 4.5mm APP",
            "Sistema Especial (Especificar en notas)"
        ])
        m2_obra = st.number_input("Metros Cuadrados (m²):", min_value=0.0, step=10.0)
    
    with col2:
        precio_m2 = st.number_input("Precio Unitario (Mat + M.O.) por m²:", min_value=0.0, step=5.0)
        garantia = st.selectbox("Garantía ofrecida:", ["3 años", "5 años", "8 años", "10 años"])

    notas = st.text_area("Descripción detallada de los trabajos (Ej: Limpieza, sellado de grietas, etc.)")

    submit = st.form_submit_button("GENERAR PRESUPUESTO FORMAL")

if submit:
    if not cliente_nom or m2_obra <= 0 or precio_m2 <= 0:
        st.warning("⚠️ Completa los datos del cliente, m² y precio para continuar.")
    else:
        with st.spinner("Creando propuesta técnica-económica..."):
            
            subtotal = m2_obra * precio_m2
            iva = subtotal * 0.16
            total_presupuesto = subtotal + iva

            hoja = conectar_sheets()
            if hoja:
                fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                fila = [fecha_hoy, vendedor, cliente_nom, obra_loc, sistema, m2_obra, precio_m2, total_presupuesto]
                hoja.append_row(fila)
                st.success("✅ Registro guardado en la nube.")

                pdf = PDF()
                pdf.add_page()
                
                try:
                    if os.path.exists("logo.jpg"): pdf.image("logo.jpg", x=10, y=8, w=50)
                    elif os.path.exists("logo.png"): pdf.image("logo.png", x=10, y=8, w=50)
                except: pass

                pdf.set_font("Arial", 'B', 14)
                pdf.set_text_color(255, 102, 0)
                pdf.cell(0, 8, txt="GRUPO IMAC", ln=True, align='R')
                pdf.set_font("Arial", size=9)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 4, txt="Presupuesto de Obra Profesional", ln=True, align='R')
                pdf.ln(15)

                pdf.set_fill_color(245, 245, 245)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(0, 8, txt=f"  DIRIGIDO A: {cliente_nom}", ln=True, fill=True)
                pdf.set_font("Arial", size=10)
                pdf.cell(100, 6, txt=f"  Ubicacion: {obra_loc}")
                pdf.cell(90, 6, txt=f"Fecha: {datetime.datetime.now().strftime('%d/%m/%Y')}", ln=True, align='R')
                pdf.ln(5)

                pdf.set_fill_color(255, 102, 0)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, txt="  PROPUESTA TECNICA Y ECONOMICA", ln=True, fill=True)
                pdf.ln(3)

                pdf.set_text_color(50, 50, 50)
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(0, 6, txt="DESCRIPCION DE LOS TRABAJOS:", ln=True)
                pdf.set_font("Arial", size=10)
                pdf.multi_cell(0, 5, txt=notas if notas else "Suministro e instalacion de sistema impermeabilizante.")
                pdf.ln(5)

                pdf.set_font("Courier", 'B', 11)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(120, 8, txt=f"CONCEPTO: {sistema}", border=1)
                pdf.cell(70, 8, txt=f"AREA: {m2_obra} m2", border=1, ln=True, align='C')
                
                pdf.set_font("Courier", size=11)
                pdf.cell(120, 8, txt="PRECIO UNITARIO (SUMINISTRO + MANO DE OBRA)", border=1)
                pdf.cell(70, 8, txt=f"${precio_m2:,.2f} MXN", border=1, ln=True, align='R')

                pdf.ln(5)
                pdf.set_font("Courier", 'B', 12)
                pdf.cell(120, 8, txt="")
                pdf.cell(70, 8, txt=f"SUBTOTAL: ${subtotal:,.2f}", ln=True, align='R')
                pdf.cell(120, 8, txt="")
                pdf.cell(70, 8, txt=f"I.V.A. 16%: ${iva:,.2f}", ln=True, align='R')
                pdf.set_text_color(255, 102, 0)
                pdf.cell(120, 10, txt="")
                pdf.cell(70, 10, txt=f"TOTAL: ${total_presupuesto:,.2f}", ln=True, align='R')

                pdf.ln(5)
                pdf.set_font("Arial", 'B', 10)
                pdf.set_text_color(0, 102, 0)
                pdf.cell(0, 6, txt=f"GARANTIA POR ESCRITO: {garantia} CONTRA DEFECTOS DE INSTALACION O MATERIAL.", ln=True)
                
                pdf.ln(10)
                pdf.set_font("Arial", 'B', 10)
                pdf.set_text_color(255, 102, 0)
                pdf.cell(0, 6, txt="DATOS PARA PAGO:", ln=True)
                pdf.set_font("Courier", size=9)
                pdf.set_text_color(50, 50, 50)
                pdf.multi_cell(0, 4, txt="Banco: BBVA\nCuenta: 0134508394\nCLABE: 012905001345083942\nRFC: IVE840928BS5")

                archivo_pdf = pdf.output(dest='S').encode('latin-1')
                st.download_button(label="📥 Descargar Presupuesto Formal", data=archivo_pdf, file_name=f"Presupuesto_{cliente_nom}.pdf", mime="application/pdf")
