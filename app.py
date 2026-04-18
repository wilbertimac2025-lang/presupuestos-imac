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
TEXTO_DESCRIPCION = ("SISTEMA DE IMPERMEABILIZACION PREFABRICADO: Membrana multicapa a base de asfaltos modificados y refuerzo central de fibra poliester. "
                    "Resistente al intemperismo, se adhiere por fusion termica. Garantiza seguridad en uniones y remates, logrando total impermeabilidad.")

TEXTO_ESPECIFICACIONES = ("ESPECIFICACIONES TÉCNICAS:\n"
                         "1. Limpieza del area hasta quedar libre de polvo.\n"
                         "2. Aplicacion de hidroflex como primario sellador.\n"
                         "3. Sellado de orillas y traslapes por medio de fusion.")

SISTEMAS_CATALOGO = [
    "MASTER LASSER 3.0 MM FIBRA POLIESTER LISO ARENADO",
    "MASTER LASSER 3.5 MM FIBRA POLIESTER BLANCO",
    "MASTER LASSER 4.0 MM FIBRA POLIESTER BLANCO",
    "MASTER LASSER 4.5 MM FIBRA POLIESTER ROJO"
]

class PDF(FPDF):
    def header(self):
        # LOGO IZQUIERDA
        if os.path.exists("logo_tarc.jpg"):
            self.image("logo_tarc.jpg", x=10, y=8, w=45) 
        else:
            self.set_font('Arial', 'B', 16)
            self.set_text_color(15, 60, 140)
            self.cell(50, 6, 'TARC', ln=False)
        
        # DATOS EMPRESA DERECHA
        self.set_font('Arial', 'B', 9)
        self.set_text_color(15, 60, 140)
        self.cell(0, 4, 'TARC S.A. DE C.V.', ln=True, align='R')
        self.set_font('Arial', '', 8)
        self.set_text_color(50, 50, 50)
        self.cell(0, 4, 'BOULEVARD MIGUEL ALEMAN 759, COL. CENTRO', ln=True, align='R')
        self.cell(0, 4, 'VERACRUZ, VER. C.P. 91700', ln=True, align='R')
        self.cell(0, 4, 'TEL. (229) 935 39 40', ln=True, align='R')
        self.cell(0, 4, 'ventas1@grupo-imac.com | www.grupo-imac.com', ln=True, align='R')
        self.ln(10)

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
    fecha_validez = st.date_input("Cotización válida hasta:") 
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
        with st.spinner("Creando tabla comercial y aplicando estilos..."):
            subtotal_obras = sum(z["m2"] * z["precio"] for z in zonas_data)
            
            pdf = PDF()
            pdf.set_auto_page_break(auto=True, margin=20)
            pdf.add_page()
            
            # --- FECHA ENCABEZADO DERECHO ---
            fecha_hoy = datetime.datetime.now().strftime("%d-%B-%Y").upper()
            pdf.set_font('Arial', 'B', 11)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 5, fecha_hoy, ln=True, align='R')
            pdf.ln(5)

            # --- BLOQUE ATN ---
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 5, f"AT'N. {cliente.upper()}", ln=True)
            if compania: 
                pdf.set_font('Arial', '', 10)
                pdf.cell(0, 5, f"{compania.upper()}", ln=True)
            if proyecto:
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(0, 5, f"PROYECTO: {proyecto.upper()}", ln=True)
            
            pdf.ln(5)
            pdf.set_font('Arial', '', 10)
            pdf.multi_cell(0, 5, txt="POR MEDIO DE LA PRESENTE, LE HACEMOS LLEGAR LA COTIZACION QUE MUY AMABLEMENTE NOS SOLICITO.")
            pdf.ln(8)

            # --- LA TABLA PRINCIPAL COMERCIAL ---
            # Encabezado de la tabla (Azul Marino)
            pdf.set_fill_color(15, 60, 140) 
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Arial', 'B', 9)
            pdf.cell(25, 8, "CANTIDAD", 1, 0, 'C', True)
            pdf.cell(95, 8, "DESCRIPCION (SISTEMA Y AREA)", 1, 0, 'C', True)
            pdf.cell(35, 8, "PRECIO UNIT.", 1, 0, 'C', True)
            pdf.cell(35, 8, "TOTAL", 1, 1, 'C', True)

            # Filas de la tabla
            pdf.set_text_color(0, 0, 0)
            for z in zonas_data:
                x = pdf.get_x()
                y = pdf.get_y()
                
                # Dibujamos las cajas de los bordes
                pdf.rect(x, y, 25, 12)
                pdf.rect(x+25, y, 95, 12)
                pdf.rect(x+120, y, 35, 12)
                pdf.rect(x+155, y, 35, 12)

                # Columna 1: Cantidad
                pdf.set_xy(x, y)
                pdf.set_font('Arial', '', 9)
                pdf.cell(25, 12, f"{z['m2']:,.2f} M2", 0, 0, 'C')
                
                # Columna 2: Descripción (Doble renglón)
                pdf.set_xy(x+25, y+2)
                pdf.set_font('Arial', 'B', 8)
                pdf.set_text_color(15, 60, 140) # Título de área en azul
                pdf.cell(95, 4, f" APLICACION EN: {z['area'].upper()}", 0, 2, 'L')
                pdf.set_font('Arial', '', 8)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(95, 4, f" {z['sistema']}", 0, 0, 'L')

                # Columna 3 y 4: Precios
                pdf.set_xy(x+120, y)
                pdf.set_font('Arial', '', 9)
                pdf.cell(35, 12, f"${z['precio']:,.2f}", 0, 0, 'C')
                pdf.cell(35, 12, f"${z['m2']*z['precio']:,.2f}", 0, 1, 'C')
                
                # Preparamos el salto de línea para la siguiente fila
                pdf.set_y(y + 12)

            # --- BLOQUE DE TOTALES ALINEADOS A LA DERECHA ---
            subtotal_final = subtotal_obras + costo_extra
            iva = subtotal_final * 0.16
            total_final = round(subtotal_final + iva)

            # Usamos un X offset para empujar las celdas a la derecha
            offset_x = 120 + 10  # 190 (ancho total) - 70 (ancho de las dos celdas finales) = 120
            
            if costo_extra > 0:
                pdf.set_x(offset_x)
                pdf.set_font('Arial', 'B', 9); pdf.set_text_color(50, 50, 50)
                pdf.cell(35, 6, "SUBTOTAL OBRA", 1, 0, 'R')
                pdf.cell(35, 6, f"${subtotal_obras:,.2f}", 1, 1, 'C')
                
                pdf.set_x(offset_x)
                pdf.set_text_color(15, 60, 140)
                pdf.cell(35, 6, "CARGO EXTRA", 1, 0, 'R')
                pdf.set_text_color(0, 0, 0)
                pdf.cell(35, 6, f"${costo_extra:,.2f}", 1, 1, 'C')

            pdf.set_x(offset_x)
            pdf.set_font('Arial', 'B', 9); pdf.set_text_color(50, 50, 50)
            pdf.cell(35, 6, "SUBTOTAL", 1, 0, 'R')
            pdf.set_text_color(0, 0, 0)
            pdf.cell(35, 6, f"${subtotal_final:,.2f}", 1, 1, 'C')

            pdf.set_x(offset_x)
            pdf.set_text_color(50, 50, 50)
            pdf.cell(35, 6, "IVA", 1, 0, 'R')
            pdf.set_text_color(0, 0, 0)
            pdf.cell(35, 6, f"${iva:,.2f}", 1, 1, 'C')

            pdf.set_x(offset_x)
            pdf.set_fill_color(15, 60, 140); pdf.set_text_color(255, 255, 255)
            pdf.cell(35, 8, "TOTAL", 1, 0, 'R', True)
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(35, 8, f"${total_final:,.2f}", 1, 1, 'C', True)

            # --- PROTECCIÓN TÉCNICA (TEXTOS DISCRETOS DEBAJO) ---
            pdf.ln(5)
            pdf.set_font('Arial', 'I', 7); pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(0, 3, txt=TEXTO_DESCRIPCION)
            pdf.ln(1)
            pdf.multi_cell(0, 3, txt=TEXTO_ESPECIFICACIONES)
            pdf.ln(5)

            # --- SECCIÓN DE NOTAS TIPO VIÑETAS ---
            pdf.set_font('Arial', 'B', 10); pdf.set_text_color(15, 60, 140)
            pdf.cell(0, 5, "NOTAS:", ln=True)
            pdf.set_font('Arial', '', 9); pdf.set_text_color(0, 0, 0)
            
            # Formato de viñetas clonado de la referencia
            pdf.cell(5, 5, chr(149)) # Punto de viñeta
            pdf.cell(0, 5, "LOS PRECIOS ARRIBA DESCRITOS YA INCLUYEN IVA Y APLICACION.", ln=True)
            
            pdf.cell(5, 5, chr(149))
            pdf.cell(0, 5, "GARANTIA DEL SISTEMA: 8 ANOS CONTRA DEFECTOS DE FABRICACION.", ln=True)
            
            pdf.cell(5, 5, chr(149))
            pdf.cell(0, 5, "PAGO: 70% DE ANTICIPO, 30% CONTRA ENTREGA.", ln=True)
            
            pdf.cell(5, 5, chr(149))
            pdf.cell(0, 5, "NO INCLUYE TRABAJOS NO COTIZADOS NI LEVANTAMIENTO DE ESCOMBRO.", ln=True)
            
            pdf.cell(5, 5, chr(149))
            pdf.cell(0, 5, f"COTIZACION VALIDA HASTA EL: {fecha_validez.strftime('%d/%m/%Y')}", ln=True)
            
            if anotaciones_asesor:
                pdf.set_font('Arial', 'B', 9); pdf.set_text_color(0, 150, 255)
                pdf.cell(5, 5, chr(149))
                pdf.cell(0, 5, f"ESPECIAL: {anotaciones_asesor.upper()}", ln=True)

            pdf.ln(10)

            # --- CIERRE, BANCOS Y FIRMAS ---
            if pdf.get_y() > 230: pdf.add_page()
            
            y_base = pdf.get_y()
            
            # Bloque de Banco a la Derecha
            if os.path.exists("logo_bbva.jpg"):
                pdf.image("logo_bbva.jpg", x=145, y=y_base, w=45)
            else:
                pdf.set_font('Arial', 'B', 10); pdf.set_text_color(15, 60, 140)
                pdf.set_xy(145, y_base)
                pdf.cell(45, 5, "BBVA Bancomer", ln=True, align='C')
            
            pdf.set_xy(145, y_base + 12)
            pdf.set_font('Arial', 'B', 8); pdf.set_text_color(0, 0, 0)
            pdf.cell(45, 4, "CUENTA: 450187690", ln=True, align='C')
            pdf.set_x(145)
            pdf.cell(45, 4, "CLABE: 012905004501876903", ln=True, align='C')
            pdf.set_x(145)
            pdf.cell(45, 4, "RFC: TAR9803175MA", ln=True, align='C')

            # Bloque de Firma a la Izquierda
            pdf.set_xy(10, y_base + 5)
            pdf.set_font('Arial', 'B', 9); pdf.set_text_color(0, 0, 0)
            pdf.cell(100, 5, 'ATENTAMENTE', ln=True)
            pdf.ln(2)
            pdf.set_font('Arial', 'B', 10); pdf.set_text_color(15, 60, 140)
            pdf.cell(100, 5, asesor.upper(), ln=True)
            pdf.set_font('Arial', '', 9); pdf.set_text_color(50, 50, 50)
            pdf.cell(100, 4, 'ASESOR COMERCIAL / DISTRIBUIDOR AUTORIZADO', ln=True)
            pdf.cell(100, 4, 'Especialistas en impermeabilización y recubrimientos', ln=True)
            
            pdf.set_y(y_base + 40)
            if os.path.exists("footer_marcas.jpg"):
                if pdf.get_y() > 250: pdf.add_page()
                pdf.image("footer_marcas.jpg", x=10, y=pdf.get_y(), w=190)

            pdf_output = pdf.output(dest='S').encode('latin-1')
            nombre_file = f"Cotizacion_{cliente.replace(' ', '_')}.pdf"

            hoja = conectar_sheets()
            if hoja:
                resumen = " / ".join([f"{z['area']} ({z['m2']}m2)" for z in zonas_data])
                hoja.append_row([fecha_hoy, asesor, cliente, compania, telefono, correo_cliente, proyecto, resumen, total_final])
            
            enviar_respaldo_correo(pdf_output, nombre_file, cliente, asesor)
            
            st.success(f"✅ ¡Diseño Comercial tipo Tabla generado con éxito!")
            st.download_button("📥 DESCARGAR FORMATO COMERCIAL", data=pdf_output, file_name=nombre_file)
