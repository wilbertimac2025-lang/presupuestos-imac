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
TEXTO_DESCRIPCION = ("Es un sistema de impermeabilizacion prefabricado, consiste en una membrana multicapa elaborada a base de "
                    "asfaltos modificados un refuerzo central de fibra poliester, son de larga vida, resistiendo mucho mas al "
                    "intemperismo, son de facil aplicacion pues se adhiere por fusion termica a cualquier techo o sustrato, es "
                    "flexible por lo que se puede colocar en cualquier superficie lograndose total seguridad a lo largo de "
                    "todas sus uniones y remates pues quedan practicamente soldadas, obteniendose asi una total impermeabilidad.")

TEXTO_ESPECIFICACIONES = ("PREPARACION DE LA SUPERFICIE A IMPERMEABILIZAR.\n"
                         "- Limpieza del area hasta quedar libre de polvo.\n"
                         "- Aplicacion de hidroflex como primario sellador.\n"
                         "COLOCACION DEL IMPERMEABILIZANTE PREFABRICADO\n"
                         "- Sellado de orillas y traslapes por medio de fusion.")

SISTEMAS_CATALOGO = [
    "MASTER LASSER 3.0 MM FIBRA POLIESTER LISO ARENADO",
    "MASTER LASSER 3.5 MM FIBRA POLIESTER BLANCO",
    "MASTER LASSER 4.0 MM FIBRA POLIESTER BLANCO",
    "MASTER LASSER 4.5 MM FIBRA POLIESTER ROJO"
]

class PDF(FPDF):
    def header(self):
        # 1. MARCA DE AGUA ENCAPSULADA
        if os.path.exists("marca_agua.jpg"):
            self.image("marca_agua.jpg", x=5, y=5, w=200, h=287)

        # 2. MARCO / BORDE DE LA HOJA
        self.set_draw_color(15, 60, 140) 
        self.set_line_width(0.7) 
        self.rect(5, 5, 200, 287) 
        self.set_line_width(0.2) 

        # 3. LOGO PRINCIPAL (Transparente)
        if os.path.exists("logo_tarc.png"):
            self.image("logo_tarc.png", x=10, y=8, w=85) 
        elif os.path.exists("logo_tarc.jpg"): 
            self.image("logo_tarc.jpg", x=10, y=8, w=85)
        else:
            self.set_font('Arial', 'B', 14)
            self.set_text_color(15, 60, 140)
            self.cell(0, 6, 'TARC S.A. DE C.V.', ln=True, align='L')
            
        self.set_y(38)

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

def obtener_nuevo_folio(hoja):
    """Genera el folio dinámico estilo OBRA01-26, OBRA150-26"""
    try:
        anio_corto = datetime.datetime.now().strftime("%y") 
        if hoja:
            filas = hoja.get_all_values()
            numero_obra = len(filas) if len(filas) > 0 else 1
            return f"OBRA{numero_obra:02d}-{anio_corto}"
    except Exception:
        pass
    anio_corto = datetime.datetime.now().strftime("%y")
    return f"OBRA-TEMP-{datetime.datetime.now().strftime('%H%M')}-{anio_corto}"

def enviar_respaldo_correo(pdf_bytes, nombre_archivo, cliente, asesor, folio):
    try:
        remitente = st.secrets["CORREO_BOT"]
        password = st.secrets["PASS_BOT"]
        # ⚠️ 2. REEMPLAZA CON EL CORREO CENTRAL DE IMAC
        correo_central = "sistematarc@gmail.com" 
        
        msg = EmailMessage()
        msg['Subject'] = f'NUEVO FOLIO {folio}: Presupuesto {cliente} (Asesor: {asesor})'
        msg['From'] = remitente
        msg['To'] = correo_central
        msg.set_content(f"Se ha registrado un nuevo presupuesto en el sistema.\n\nFolio Asignado: {folio}\nCliente: {cliente}\nAsesor: {asesor}\n\nSe adjunta el PDF oficial.")
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
    fecha_validez = st.date_input("Presupuesto válido hasta:") 
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
        col1, col2 = st.columns(2)
        with col1:
            n = st.text_input(f"Nombre de la zona", key=f"n_{i}")
            s = st.selectbox(f"Sistema", SISTEMAS_CATALOGO, key=f"s_{i}")
        with col2:
            m = st.number_input(f"Metros (m²)", min_value=0.0, key=f"m_{i}")
            p = st.number_input(f"Precio x m²", min_value=0.0, key=f"p_{i}")
        zonas_data.append({"area": n, "sistema": s, "m2": m, "precio": p})

    st.write("---")
    st.write("### 4. Ajustes Finales y Anexos")
    costo_extra = st.number_input("Costo Extra Adicional (Pesos $)", min_value=0.0)
    desc_extra = st.text_input("Concepto del Costo Extra")
    anotaciones_asesor = st.text_area("Anotaciones Especiales para el Cliente")
    
    # 📸 NUEVO MÓDULO FOTOGRÁFICO
    fotos_subidas = st.file_uploader("📸 Subir Evidencia Fotográfica del Área (Opcional)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    
    boton = st.form_submit_button("GENERAR DOCUMENTO Y FOLIO")

if boton:
    if not cliente or not asesor:
        st.error("⚠️ El nombre del Cliente y el Asesor son obligatorios.")
    else:
        with st.spinner("Procesando imágenes, conectando a la base de datos y asignando Folio Oficial..."):
            
            # 1. GUARDAR TEMPORALMENTE LAS FOTOS
            temp_paths = []
            if fotos_subidas:
                for idx, foto in enumerate(fotos_subidas):
                    ext = foto.name.split('.')[-1]
                    temp_path = f"temp_img_{idx}.{ext}"
                    with open(temp_path, "wb") as f:
                        f.write(foto.getbuffer())
                    temp_paths.append(temp_path)

            hoja = conectar_sheets()
            folio_actual = obtener_nuevo_folio(hoja)

            subtotal_obras = sum(z["m2"] * z["precio"] for z in zonas_data)
            
            pdf = PDF()
            pdf.set_auto_page_break(auto=True, margin=20)
            pdf.add_page()
            
            pdf.set_font('Arial', 'B', 12)
            pdf.set_text_color(200, 30, 30) 
            pdf.cell(0, 5, f"FOLIO: {folio_actual}", ln=True, align='R')

            fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
            pdf.set_font('Arial', 'I', 10) 
            pdf.set_text_color(100, 100, 100) 
            pdf.cell(0, 5, f'Veracruz, Ver. a {fecha_hoy}', ln=True, align='R')
            pdf.ln(5)

            pdf.set_font('Arial', 'B', 12); pdf.set_text_color(15, 60, 140) 
            pdf.cell(0, 5, f"CLIENTE: {cliente.upper()}", ln=True)
            if compania: 
                pdf.set_font('Arial', 'B', 10); pdf.set_text_color(0, 150, 255) 
                pdf.cell(0, 5, f"{compania.upper()}", ln=True)
            
            pdf.set_font('Arial', '', 10); pdf.set_text_color(50, 50, 50)
            if telefono: pdf.cell(0, 5, f"Tel: {telefono}", ln=True)
            if correo_cliente: pdf.cell(0, 5, f"Email: {correo_cliente}", ln=True)
            
            pdf.ln(2)
            pdf.set_font('Arial', 'B', 10); pdf.set_text_color(15, 60, 140)
            pdf.cell(0, 5, f"ASESOR COMERCIAL: {asesor.upper()}", ln=True)
            
            pdf.ln(3)
            if proyecto:
                pdf.set_font('Arial', 'B', 11); pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 5, f"PROYECTO: {proyecto.upper()}", ln=True)
            
            pdf.ln(5); pdf.set_font('Arial', 'I', 10); pdf.set_text_color(80, 80, 80) 
            pdf.multi_cell(0, 5, txt="Nos permitimos poner a su amable consideración el siguiente presupuesto:")
            pdf.ln(5)

            for z in zonas_data:
                pdf.set_font('Arial', 'B', 11); pdf.set_text_color(0, 150, 255)
                pdf.multi_cell(0, 6, txt=f"SUMINISTRO Y APLICACIÓN EN {z['area'].upper()}:")
                
                pdf.set_font('Arial', 'B', 11); pdf.set_text_color(15, 60, 140); pdf.cell(0, 6, z["sistema"], ln=True)
                
                pdf.set_font('Arial', 'I', 9); pdf.set_text_color(80, 80, 80)
                pdf.multi_cell(0, 4, txt=TEXTO_DESCRIPCION)
                
                pdf.ln(3)
                pdf.set_font('Arial', 'B', 9); pdf.set_text_color(0, 150, 255)
                pdf.cell(0, 5, "Especificaciones Técnicas:", ln=True)
                pdf.set_text_color(50, 50, 50); pdf.set_font('Arial', '', 9)
                pdf.multi_cell(0, 4, txt=TEXTO_ESPECIFICACIONES)
                pdf.ln(4)
                
                pdf.set_fill_color(240, 248, 255); pdf.set_text_color(15, 60, 140); pdf.set_font('Arial', 'B', 9)
                pdf.set_draw_color(200, 200, 200) 
                pdf.cell(60, 6, "AREA (M2)", 'B', 0, 'C', True); pdf.cell(60, 6, "PRECIO UNIT.", 'B', 0, 'C', True); pdf.cell(70, 6, "SUBTOTAL", 'B', 1, 'C', True)
                pdf.set_text_color(0,0,0); pdf.set_font('Arial', '', 9)
                pdf.cell(60, 6, f"{z['m2']:,.2f}", 'B', 0, 'C'); pdf.cell(60, 6, f"${z['precio']:,.2f}", 'B', 0, 'C'); pdf.cell(70, 6, f"${z['m2']*z['precio']:,.2f}", 'B', 1, 'C')
                pdf.ln(8)

            subtotal_final = subtotal_obras + costo_extra
            iva = subtotal_final * 0.16
            total_final = round(subtotal_final + iva)

            if pdf.get_y() > 210: pdf.add_page()
            
            if costo_extra > 0:
                pdf.set_font('Arial', 'B', 10); pdf.set_text_color(15, 60, 140)
                pdf.cell(120, 6, f"COSTO ADICIONAL: {desc_extra.upper() if desc_extra else 'OTROS'}", border=0, align='R')
                pdf.cell(70, 6, f"${costo_extra:,.2f}", border=0, align='R', ln=True)

            pdf.set_font('Arial', 'B', 10); pdf.set_text_color(50, 50, 50)
            pdf.cell(120, 6, "SUBTOTAL:", border=0, align='R')
            pdf.cell(70, 6, f"${subtotal_final:,.2f}", border=0, align='R', ln=True)
            pdf.cell(120, 6, "IVA (16%):", border=0, align='R')
            pdf.cell(70, 6, f"${iva:,.2f}", border=0, align='R', ln=True)
            pdf.ln(2)

            x_inicial = pdf.get_x()
            y_inicial = pdf.get_y()
            
            pdf.set_fill_color(200, 200, 200)
            pdf.rect(x_inicial + 60 + 1.5, y_inicial + 1.5, 130, 9, 'F')
            
            pdf.set_fill_color(15, 60, 140); pdf.set_text_color(255, 255, 255); pdf.set_font('Arial', 'B', 11)
            pdf.set_xy(x_inicial + 60, y_inicial) 
            pdf.cell(60, 9, "INVERSIÓN TOTAL", border=0, fill=True, align='R')
            pdf.set_fill_color(0, 150, 255) 
            pdf.cell(70, 9, f"${total_final:,.2f} MXN", border=0, fill=True, align='C', ln=True)
            
            pdf.ln(8)
            pdf.set_text_color(15, 60, 140); pdf.set_font('Arial', 'B', 9)
            pdf.cell(0, 5, "Consideraciones Importantes:", ln=True)
            pdf.set_text_color(80, 80, 80); pdf.set_font('Arial', 'I', 8)
            pdf.multi_cell(0, 4, txt="- Se deberá hacer un levantamiento físico para determinar los alcances exactos.\n- No incluye trabajos no cotizados.")
            pdf.ln(3)
            
            pdf.set_font('Arial', 'B', 9); pdf.set_text_color(50, 50, 50)
            pdf.cell(60, 5, "Garantía del Sistema:")
            pdf.set_font('Arial', '', 9); pdf.set_text_color(15, 60, 140)
            pdf.cell(0, 5, "8 AÑOS CONTRA DEFECTOS DE FABRICACIÓN", ln=True)
            
            pdf.set_font('Arial', 'B', 9); pdf.set_text_color(50, 50, 50)
            pdf.cell(60, 5, "Condiciones de Pago:")
            pdf.set_font('Arial', '', 9); pdf.set_text_color(15, 60, 140)
            pdf.cell(0, 5, "70% DE ANTICIPO, 30% CONTRA ENTREGA", ln=True)
            
            pdf.set_font('Arial', 'B', 9); pdf.set_text_color(50, 50, 50)
            pdf.cell(60, 5, "Presupuesto válido hasta:")
            pdf.set_font('Arial', '', 9); pdf.set_text_color(15, 60, 140)
            pdf.cell(0, 5, fecha_validez.strftime("%d/%m/%Y"), ln=True)
            pdf.ln(5)

            if anotaciones_asesor:
                pdf.set_text_color(0, 150, 255); pdf.set_font('Arial', 'B', 10)
                pdf.cell(0, 6, "Anotaciones Especiales:", ln=True)
                pdf.set_text_color(80, 80, 80); pdf.set_font('Arial', 'I', 9)
                pdf.multi_cell(0, 5, txt=anotaciones_asesor)
                pdf.ln(5)

            if pdf.get_y() > 230: pdf.add_page()
            
            y_base = pdf.get_y() + 10 
            
            if os.path.exists("logo_bbva.png"):
                pdf.image("logo_bbva.png", x=145, y=y_base, w=55)
            elif os.path.exists("logo_bbva.jpg"):
                pdf.image("logo_bbva.jpg", x=145, y=y_base, w=55)
            
            pdf.set_y(y_base) 
            pdf.set_font('Arial', 'B', 10); pdf.set_text_color(15, 60, 140)
            pdf.cell(0, 5, 'Atentamente,', ln=True)
            pdf.set_font('Arial', 'B', 12); pdf.set_text_color(0, 150, 255)
            pdf.cell(0, 5, 'TARC S.A. DE C.V.', ln=True)
            
            pdf.set_text_color(100, 100, 100); pdf.set_font('Arial', '', 8)
            pdf.cell(0, 4, 'BOULEVARD MIGUEL ALEMAN 759, COL. CENTRO. VERACRUZ, VER. C.P. 91700', ln=True)
            pdf.cell(0, 4, 'TEL. (229) 935 39 40 | ventas1@grupo-imac.com | www.grupo-imac.com', ln=True)
            
            pdf.set_y(y_base + 40)
            
            if os.path.exists("footer_marcas.png"):
                if pdf.get_y() > 250: pdf.add_page()
                pdf.image("footer_marcas.png", x=10, y=pdf.get_y(), w=190)
            elif os.path.exists("footer_marcas.jpg"):
                if pdf.get_y() > 250: pdf.add_page()
                pdf.image("footer_marcas.jpg", x=10, y=pdf.get_y(), w=190)

            # 📸 --- CONSTRUCCIÓN DEL ANEXO FOTOGRÁFICO ---
            if temp_paths:
                pdf.add_page()
                pdf.set_font('Arial', 'B', 16)
                pdf.set_text_color(15, 60, 140)
                pdf.cell(0, 10, "ANEXO FOTOGRAFICO", ln=True, align='C')
                
                y_pos = 40
                for i, temp_img in enumerate(temp_paths):
                    # Pone 2 imágenes por página para que luzcan grandes y nítidas
                    if i > 0 and i % 2 == 0:
                        pdf.add_page()
                        y_pos = 30
                        
                    pdf.image(temp_img, x=25, y=y_pos, w=160)
                    y_pos += 120 # Espacio hacia abajo para la siguiente foto
                    
            # LIMPIEZA DE ARCHIVOS TEMPORALES
            for temp_img in temp_paths:
                if os.path.exists(temp_img):
                    os.remove(temp_img)

            pdf_output = pdf.output(dest='S').encode('latin-1')
            nombre_file = f"Presupuesto_{folio_actual}_{cliente.replace(' ', '_')}.pdf"

            if hoja:
                resumen = " / ".join([f"{z['area']} ({z['m2']}m2)" for z in zonas_data])
                hoja.append_row([folio_actual, fecha_hoy, asesor, cliente, compania, telefono, correo_cliente, proyecto, resumen, total_final])
            
            enviar_respaldo_correo(pdf_output, nombre_file, cliente, asesor, folio_actual)
            
            st.success(f"✅ Presupuesto {folio_actual} generado con éxito.")
            st.download_button(f"📥 DESCARGAR PRESUPUESTO", data=pdf_output, file_name=nombre_file)
