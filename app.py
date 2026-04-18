import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF
import datetime
import json
import os
import smtplib
from email.message import EmailMessage

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Cotizador Multizona IMAC", page_icon="📝", layout="centered")

# --- TEXTOS PREDEFINIDOS ---
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

class PDF(FPDF):
    def header(self):
        if os.path.exists("logo_tarc.jpg"):
            self.image("logo_tarc.jpg", x=10, y=8, w=65) 
        else:
            self.set_font('Arial', 'B', 14)
            self.set_text_color(15, 60, 140)
            self.cell(0, 6, 'TARC S.A. DE C.V.', ln=True, align='L')
        self.set_y(28)

@st.cache_resource
def conectar_sheets():
    try:
        credenciales_dic = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(credenciales_dic, scopes=scopes)
        cliente = gspread.authorize(creds)
        # ⚠️ 1. REEMPLAZA CON TU ID DE EXCEL
        ID_DEL_EXCEL = "1-grdT2H5dBlGVPvJbZ5wVYDdtVjQEEmUPGpvEm6C0Gc" 
        sheet = cliente.open_by_key(ID_DEL_EXCEL).worksheet("Presupuestos")
        return sheet
    except Exception: return None

def enviar_respaldo_correo(pdf_bytes, nombre_archivo, cliente, asesor):
    try:
        remitente = st.secrets["CORREO_BOT"]
        password = st.secrets["PASS_BOT"]
        # ⚠️ 2. REEMPLAZA CON EL CORREO CENTRAL DE IMAC
        correo_central = "sistematarc@gmail.com" 
        
        msg = EmailMessage()
        msg['Subject'] = f'COTIZACIÓN: {cliente} (Asesor: {asesor})'
        msg['From'] = remitente
        msg['To'] = correo_central
        msg.set_content(f"Nueva cotización generada.\nCliente: {cliente}\nAsesor: {asesor}")
        msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=nombre_archivo)
        
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls()
            smtp.login(remitente, password)
            smtp.send_message(msg)
        return True, "OK"
    except Exception as e: return False, str(e)

st.title("🍊 Presupuestos Multizona")
num_areas = st.number_input("¿Cuántas áreas distintas vas a cotizar?", min_value=1, max_value=10, value=1)

with st.form("form_presupuesto"):
    st.write("### 1. Datos de Contacto y Asignación")
    cliente = st.text_input("Nombre del Cliente")
    compania = st.text_input("Compañía / Empresa")
    telefono = st.text_input("Teléfono de Contacto")
    correo_cliente = st.text_input("Correo Electrónico del Cliente")
    asesor = st.text_input("Nombre del Asesor")
    
    st.write("---")
    st.write("### 2. Información del Proyecto")
    proyecto = st.text_input("Nombre del Proyecto / Obra")
    
    st.write("---")
    st.write("### 3. Desglose de Áreas")
    zonas_data = []
    for i in range(int(num_areas)):
        st.markdown(f"**Área {i+1}**")
        c1, c2 = st.columns(2)
        with c1:
            n = st.text_input(f"Nombre de la zona", key=f"n_{i}")
            s = st.selectbox(f"Sistema", SISTEMAS_CATALOGO, key=f"s_{i}")
        with c2:
            m = st.number_input(f"Metros (m²)", min_value=0.0, key=f"m_{i}")
            p = st.number_input(f"Precio x m²", min_value=0.0, key=f"p_{i}")
        zonas_data.append({"area": n, "sistema": s, "m2": m, "precio": p})

    st.write("---")
    st.write("### 4. Ajustes Finales")
    costo_extra = st.number_input("Costo Extra Adicional (Pesos $)", min_value=0.0)
    desc_extra = st.text_input("Concepto del Costo Extra")
    anotaciones_asesor = st.text_area("Anotaciones Especiales para el Cliente")
    
    boton = st.form_submit_button("GENERAR DOCUMENTO FINAL")

if boton:
    if not cliente or not asesor:
        st.error("⚠️ El nombre del Cliente y el Asesor son obligatorios.")
    else:
        with st.spinner("Generando PDF completo y alineado..."):
            subtotal_obras = sum(z["m2"] * z["precio"] for z in zonas_data)
            
            pdf = PDF()
            pdf.set_auto_page_break(auto=True, margin=20)
            pdf.add_page()
            
            # --- ENCABEZADO DE DATOS ---
            fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
            pdf.set_font('Arial', '', 10)
            pdf.cell(0, 5, f'VERACRUZ, VER. A {fecha_hoy}', ln=True, align='R')
            pdf.ln(5)

            pdf.set_font('Arial', 'B', 11); pdf.set_text_color(15, 60, 140)
            pdf.cell(0, 5, f"CLIENTE: {cliente.upper()}", ln=True)
            if compania: pdf.cell(0, 5, f"COMPAÑÍA: {compania.upper()}", ln=True)
            
            pdf.set_font('Arial', '', 10); pdf.set_text_color(0, 0, 0)
            if telefono: pdf.cell(0, 5, f"TELÉFONO: {telefono}", ln=True)
            if correo_cliente: pdf.cell(0, 5, f"CORREO: {correo_cliente}", ln=True)
            
            pdf.ln(2)
            pdf.set_font('Arial', 'B', 10); pdf.set_text_color(15, 60, 140)
            pdf.cell(0, 5, f"ASESOR COMERCIAL: {asesor.upper()}", ln=True)
            
            pdf.ln(3)
            if proyecto:
                pdf.set_font('Arial', 'B', 11); pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 5, f"PROYECTO: {proyecto.upper()}", ln=True)
            
            pdf.ln(5); pdf.set_font('Arial', '', 10); pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 5, txt="NOS PERMITIMOS PONER A SU AMABLE CONSIDERACION LA SIGUIENTE COTIZACION:")
            pdf.ln(5)

            # --- BUCLE DE ZONAS ---
            for z in zonas_data:
                pdf.set_font('Arial', 'B', 10); pdf.set_text_color(41, 128, 185)
                pdf.multi_cell(0, 6, txt=f"SUMINISTRO Y APLICACION EN {z['area'].upper()}:")
                pdf.set_font('Arial', 'B', 11); pdf.set_text_color(0, 0, 0); pdf.cell(0, 6, z["sistema"], ln=True)
                pdf.set_font('Arial', '', 9); pdf.multi_cell(0, 4, txt=TEXTO_DESCRIPCION)
                
                pdf.ln(3)
                pdf.set_font('Arial', 'B', 9); pdf.set_text_color(15, 60, 140)
                pdf.cell(0, 5, "ESPECIFICACIONES", ln=True)
                pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', '', 9)
                pdf.multi_cell(0, 4, txt=TEXTO_ESPECIFICACIONES)
                pdf.ln(4)
                
                pdf.set_fill_color(235, 245, 255); pdf.set_text_color(15, 60, 140); pdf.set_font('Arial', 'B', 9)
                pdf.cell(60, 6, "AREA (M2)", 1, 0, 'C', True); pdf.cell(60, 6, "PRECIO UNIT.", 1, 0, 'C', True); pdf.cell(70, 6, "SUBTOTAL", 1, 1, 'C', True)
                pdf.set_text_color(0,0,0); pdf.set_font('Arial', '', 9)
                pdf.cell(60, 6, f"{z['m2']:,.2f}", 1, 0, 'C'); pdf.cell(60, 6, f"${z['precio']:,.2f}", 1, 0, 'C'); pdf.cell(70, 6, f"${z['m2']*z['precio']:,.2f}", 1, 1, 'C')
                pdf.ln(8)

            # --- TOTALES Y COSTOS EXTRA ---
            subtotal_final = subtotal_obras + costo_extra
            iva = subtotal_final * 0.16
            total_final = round(subtotal_final + iva)

            if pdf.get_y() > 220: pdf.add_page()
            
            if costo_extra > 0:
                pdf.set_font('Arial', 'B', 10); pdf.set_text_color(15, 60, 140)
                pdf.cell(120, 6, f"COSTO ADICIONAL: {desc_extra.upper() if desc_extra else 'OTROS'}", border=1, align='R')
                pdf.cell(70, 6, f"${costo_extra:,.2f}", border=1, align='R', ln=True)

            pdf.set_font('Arial', 'B', 10); pdf.set_text_color(0,0,0)
            pdf.cell(120, 6, "SUBTOTAL DE PRESUPUESTO", border=1, align='R')
            pdf.cell(70, 6, f"${subtotal_final:,.2f}", border=1, align='R', ln=True)
            pdf.cell(120, 6, "IVA", border=1, align='R')
            pdf.cell(70, 6, f"${iva:,.2f}", border=1, align='R', ln=True)
            
            pdf.set_fill_color(15, 60, 140); pdf.set_text_color(255, 255, 255)
            pdf.cell(120, 8, "TOTAL", border=1, fill=True, align='R')
            pdf.cell(70, 8, f"${total_final:,.2f}", border=1, fill=True, align='R', ln=True)
            
            # --- NOTAS ESTÁNDAR (MODIFICADAS SEGÚN SOLICITUD) ---
            pdf.ln(5)
            pdf.set_text_color(15, 60, 140); pdf.set_font('Arial', 'B', 9)
            pdf.cell(0, 5, "NOTAS:", ln=True)
            pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', '', 8)
            # Aquí está el nuevo texto ajustado:
            pdf.multi_cell(0, 4, txt="- SE DEBERA HACER UN LEVANTAMIENTO FISICO PARA PODER DETERMINAR LOS ALCANCES POR TRABAJO SOLICITADO.\n- NO INCLUYE TRABAJOS NO COTIZADOS")
            pdf.ln(3)
            
            pdf.set_font('Arial', 'B', 9)
            pdf.cell(60, 5, "GARANTIA DEL SISTEMA EN AÑOS:")
            pdf.set_font('Arial', '', 9)
            pdf.cell(0, 5, "8 AÑOS", ln=True)
            
            pdf.set_font('Arial', 'B', 9)
            pdf.cell(60, 5, "CONDICIONES DE PAGO:")
            pdf.set_font('Arial', '', 9)
            pdf.cell(0, 5, "70% DE ANTICIPO, 30% CONTRA ENTREGA", ln=True)
            
            pdf.set_font('Arial', 'B', 9)
            pdf.cell(60, 5, "COTIZACION VALIDA AL:")
            pdf.set_font('Arial', '', 9)
            pdf.cell(0, 5, fecha_validez.strftime("%d/%m/%Y"), ln=True)
            pdf.ln(5)

            # --- ANOTACIONES DEL ASESOR ---
            if anotaciones_asesor:
                pdf.set_text_color(15, 60, 140); pdf.set_font('Arial', 'B', 10)
                pdf.cell(0, 6, "ANOTACIONES ESPECIALES:", ln=True)
                pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', '', 9)
                pdf.multi_cell(0, 5, txt=anotaciones_asesor)
                pdf.ln(5)

            # --- CIERRE CON FIRMA Y LOGO ALINEADOS ---
            if pdf.get_y() > 230: pdf.add_page()
            
            y_base = pdf.get_y() + 10 
            
            if os.path.exists("logo_bbva.jpg"):
                pdf.image("logo_bbva.jpg", x=145, y=y_base, w=55)
            
            pdf.set_y(y_base) 
            pdf.set_font('Arial', 'B', 9); pdf.set_text_color(15, 60, 140)
            pdf.cell(0, 5, 'CORDIALMENTE', ln=True)
            pdf.cell(0, 5, 'TARC S.A. DE C.V.', ln=True)
            
            pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', '', 8)
            pdf.cell(0, 4, 'BOULEVARD MIGUEL ALEMAN 759, COL. CENTRO. VERACRUZ, VER. C.P. 91700', ln=True)
            pdf.cell(0, 4, 'TEL. (229) 935 39 40 | ventas1@grupo-imac.com | www.grupo-imac.com', ln=True)
            
            pdf.set_y(y_base + 40)
            
            if os.path.exists("footer_marcas.jpg"):
                if pdf.get_y() > 250: pdf.add_page()
                pdf.image("footer_marcas.jpg", x=10, y=pdf.get_y(), w=190)

            pdf_output = pdf.output(dest='S').encode('latin-1')
            nombre_file = f"Presupuesto_{cliente.replace(' ', '_')}.pdf"

            hoja = conectar_sheets()
            if hoja:
                resumen = " / ".join([f"{z['area']} ({z['m2']}m2)" for z in zonas_data])
                hoja.append_row([fecha_hoy, asesor, cliente, compania, telefono, correo_cliente, proyecto, resumen, total_final])
            
            enviar_respaldo_correo(pdf_output, nombre_file, cliente, asesor)
            
            st.success(f"✅ Presupuesto generado con éxito.")
            st.download_button("📥 DESCARGAR PDF", data=pdf_output, file_name=nombre_file)
     
