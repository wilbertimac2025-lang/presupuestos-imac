import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF
import datetime
import json
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Cotizador TARC / IMAC", page_icon="📝", layout="centered")

# --- TEXTOS TÉCNICOS ---
TEXTO_DESCRIPCION = ("ES UN SISTEMA DE IMPERMEABILIZACION PREFABRICADO, CONSISTE EN UNA MEMBRANA MULTICAPA ELABORADA A BASE DE "
                    "ASFALTOS MODIFICADOS UN REFUERZO CENTRAL DE FIBRA POLIESTER, SON DE LARGA VIDA, RESISTIENDO MUCHO MAS AL "
                    "INTEMPERISMO, SON DE FACIL APLICACION PUES SE ADHIERE POR FUSION TERMICA A CUALQUIER TECHO O SUSTRATO, ES "
                    "FLEXIBLE POR LO QUE SE PUEDE COLOCAR EN CUALQUIER SUPERFICIE LOGRANDOSE TOTAL SEGURIDAD A LO LARGO DE "
                    "TODAS SUS UNIONES Y REMATES PUES QUEDAN PRACTICAMENTE SOLDADAS, OBTENIENDOSE ASI UNA TOTAL IMPERMEABILIDAD.")

TEXTO_ESPECIFICACIONES = ("PREPARACION DE LA SUPERFICIE A IMPERMEABILIZAR.\n"
                         "- LIMPIEZA DEL AREA HASTA QUEDAR LIBRE DE POLVO\n"
                         "- APLICACION DE HIDROFLEX COMO PRIMARIO SELLADOR.\n\n"
                         "COLOCACION DEL IMPERMEABILIZANTE PREFABRICADO\n"
                         "- SELLADO DE ORILLAS Y TRASLAPES POR MEDIO DE FUSION")

SISTEMAS_CATALOGO = [
    "MASTER LASSER 3.0 MM FIBRA POLIESTER LISO ARENADO",
    "MASTER LASSER 3.5 MM FIBRA POLIESTER BLANCO",
    "MASTER LASSER 4.0 MM FIBRA POLIESTER BLANCO",
    "MASTER LASSER 4.5 MM FIBRA POLIESTER ROJO"
]

# --- CLASE PDF CON LOGOS ---
class PDF(FPDF):
    def header(self):
        # Logo de Empresa (Asegúrate de subirlo como logo_tarc.png)
        if os.path.exists("logo_tarc.png"):
            self.image("logo_tarc.png", x=10, y=8, w=40)
        
        self.set_font('Arial', 'B', 14)
        self.set_y(10)
        self.cell(0, 6, 'TARC S.A. DE C.V.', ln=True, align='R')
        self.set_font('Arial', 'B', 11)
        self.cell(0, 6, 'IMAC', ln=True, align='R')
        self.ln(10)

# --- CONEXIÓN SHEETS ---
@st.cache_resource
def conectar_sheets():
    try:
        credenciales_dic = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(credenciales_dic, scopes=scopes)
        cliente = gspread.authorize(creds)
        ID_DEL_EXCEL = "TU_ID_AQUÍ" 
        sheet = cliente.open_by_key(ID_DEL_EXCEL).worksheet("Presupuestos")
        return sheet
    except: return None

# --- INTERFAZ ---
st.title("🍊 Presupuestos TARC / IMAC")
num_areas = st.number_input("Número de áreas a cotizar:", min_value=1, max_value=10, value=1)

with st.form("form_presupuesto"):
    st.write("### Datos Generales")
    fecha_validez = st.date_input("Válida hasta:")
    cliente = st.text_input("Nombre del Cliente / Empresa")
    proyecto = st.text_input("Nombre del Proyecto")
    
    zonas_data = []
    for i in range(int(num_areas)):
        st.markdown(f"--- Area {i+1} ---")
        col1, col2 = st.columns(2)
        with col1:
            n = st.text_input(f"Zona", key=f"n_{i}")
            s = st.selectbox(f"Sistema", SISTEMAS_CATALOGO, key=f"s_{i}")
        with col2:
            m = st.number_input(f"m²", min_value=0.0, key=f"m_{i}")
            p = st.number_input(f"Precio x m²", min_value=0.0, key=f"p_{i}")
        zonas_data.append({"area": n, "sistema": s, "m2": m, "precio": p})
    
    boton = st.form_submit_button("GENERAR PRESUPUESTO")

if boton:
    if not cliente or not zonas_data[0]["area"]:
        st.error("Faltan datos.")
    else:
        with st.spinner("Generando PDF profesional..."):
            subtotal_general = 0
            pdf = PDF()
            pdf.set_auto_page_break(auto=True, margin=50)
            pdf.add_page()
            
            # Encabezado
            pdf.set_font('Arial', '', 10)
            pdf.cell(0, 5, f'VERACRUZ, VER. A {datetime.datetime.now().strftime("%d/%m/%Y")}', ln=True, align='R')
            pdf.ln(5)
            
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 5, cliente.upper(), ln=True)
            if proyecto: pdf.cell(0, 5, proyecto.upper(), ln=True)
            pdf.cell(0, 5, 'PRESENTE', ln=True)
            pdf.ln(5)
            
            pdf.set_font('Arial', '', 10)
            pdf.multi_cell(0, 5, txt="NOS PERMITIMOS PONER A SU CONSIDERACION LA SIGUIENTE COTIZACION:")
            pdf.ln(5)
            
            # Áreas
            for zona in zonas_data:
                sub = zona["m2"] * zona["precio"]
                subtotal_general += sub
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(255, 0, 0)
                pdf.multi_cell(0, 6, txt=f"SUMINISTRO Y APLICACION EN {zona['area'].upper()}:")
                pdf.set_font('Arial', 'B', 11); pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 6, zona["sistema"], ln=True)
                pdf.set_font('Arial', '', 9); pdf.multi_cell(0, 4, txt=TEXTO_DESCRIPCION)
                pdf.ln(2); pdf.set_font('Arial', 'B', 9); pdf.cell(0, 5, "ESPECIFICACIONES", ln=True)
                pdf.set_font('Arial', '', 9); pdf.multi_cell(0, 4, txt=TEXTO_ESPECIFICACIONES)
                
                pdf.set_fill_color(230, 230, 230); pdf.set_font('Arial', 'B', 9)
                pdf.cell(60, 6, "AREA (M2)", 1, 0, 'C', True)
                pdf.cell(60, 6, "PRECIO M2", 1, 0, 'C', True)
                pdf.cell(70, 6, "SUBTOTAL", 1, 1, 'C', True)
                pdf.set_font('Arial', '', 9)
                pdf.cell(60, 6, f"{zona['m2']:,.2f}", 1, 0, 'C')
                pdf.cell(60, 6, f"${zona['precio']:,.2f}", 1, 0, 'C')
                pdf.cell(70, 6, f"${sub:,.2f}", 1, 1, 'C')
                pdf.ln(10)
            
            # Totales
            iva = subtotal_general * 0.16
            total = round(subtotal_general + iva)
            if pdf.get_y() > 220: pdf.add_page()
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(120, 6, "SUBTOTAL", 1, 0, 'R'); pdf.cell(70, 6, f"${subtotal_general:,.2f}", 1, 1, 'R')
            pdf.cell(120, 6, "IVA", 1, 0, 'R'); pdf.cell(70, 6, f"${iva:,.2f}", 1, 1, 'R')
            pdf.set_fill_color(200, 200, 200); pdf.cell(120, 6, "TOTAL", 1, 0, 'R', True)
            pdf.cell(70, 6, f"${total:,.2f}", 1, 1, 'R', True)
            
            # Notas
            pdf.ln(5); pdf.set_font('Arial', 'B', 9); pdf.cell(0, 5, "NOTAS:", ln=True)
            pdf.set_font('Arial', '', 8); pdf.multi_cell(0, 4, txt="- NO INCLUYE ALBAÑILERIA\n- GARANTIA: 8 AÑOS\n- PAGO: 70% ANTICIPO")
            pdf.cell(0, 5, f"COTIZACION VALIDA AL: {fecha_validez.strftime('%d/%m/%Y')}", ln=True)
            
            # Bancos con Logo (logo_bbva.png)
            if pdf.get_y() > 240: pdf.add_page()
            pdf.ln(10)
            if os.path.exists("logo_bbva.png"):
                pdf.image("logo_bbva.png", x=10, y=pdf.get_y(), w=20)
            
            pdf.set_x(35)
            pdf.set_font('Arial', 'B', 9); pdf.cell(0, 5, "BBVA Bancomer", ln=True)
            pdf.set_x(35); pdf.set_font('Arial', '', 9)
            pdf.cell(0, 5, "CUENTA: 450187690 | CLABE: 012905004501876903 | RFC: TAR9803175MA", ln=True)
            
            # Firma
            pdf.ln(10); pdf.set_font('Arial', 'B', 9); pdf.cell(0, 5, 'CORDIALMENTE', ln=True)
            pdf.cell(0, 5, 'TARC S.A. DE C.V.', ln=True); pdf.set_font('Arial', '', 8)
            pdf.cell(0, 4, 'TEL. (229) 935 39 40 | ventas1@grupo-imac.com', ln=True)

            pdf_output = pdf.output(dest='S').encode('latin-1')
            st.download_button("📥 DESCARGAR PRESUPUESTO", data=pdf_output, file_name=f"Presupuesto_{cliente}.pdf")
   
