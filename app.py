import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF
import datetime
import json
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Cotizador Multizona IMAC", page_icon="📝", layout="centered")

# --- TEXTOS PREDEFINIDOS DEL PDF OFICIAL ---
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

# --- CLASE PARA EL PDF (DISEÑO AZUL ELEGANTE) ---
class PDF(FPDF):
    def header(self):
        if os.path.exists("logo_tarc.jpg"):
            self.image("logo_tarc.jpg", x=10, y=8, w=65) 
        else:
            self.set_font('Arial', 'B', 14)
            self.set_text_color(15, 60, 140) # Azul Marino
            self.cell(0, 6, 'TARC S.A. DE C.V.', ln=True, align='L')
            self.set_font('Arial', 'B', 12)
            self.set_text_color(41, 128, 185) # Azul Claro
            self.cell(0, 6, 'IMAC', ln=True, align='L')
        
        self.set_y(28)

# --- CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def conectar_sheets():
    try:
        credenciales_dic = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(credenciales_dic, scopes=scopes)
        cliente = gspread.authorize(creds)
        # ⚠️ REEMPLAZA CON TU ID DE EXCEL DE PRESUPUESTOS
        ID_DEL_EXCEL = "1-grdT2H5dBlGVPvJbZ5wVYDdtVjQEEmUPGpvEm6C0Gc" 
        sheet = cliente.open_by_key(ID_DEL_EXCEL).worksheet("Presupuestos")
        return sheet
    except Exception as e:
        st.error(f"Error técnico: {e}")
        return None

# --- INTERFAZ WEB DINÁMICA ---
st.title("🍊 Presupuestos Multizona")
st.write("Generador de Propuestas Comerciales IMAC")

num_areas = st.number_input("¿Cuántas áreas distintas vas a cotizar en este proyecto?", min_value=1, max_value=10, value=1, step=1)

with st.form("form_presupuesto"):
    st.write("### Datos Generales")
    fecha_validez = st.date_input("Cotización válida hasta:")
    cliente = st.text_input("Nombre del Cliente / Empresa")
    proyecto = st.text_input("Nombre del Proyecto")
    
    st.write("---")
    st.write(f"### Detalles de las {num_areas} Áreas")
    
    zonas_data = []
    for i in range(int(num_areas)):
        st.markdown(f"**Área {i+1}**")
        col1, col2 = st.columns(2)
        with col1:
            nombre_area = st.text_input(f"Nombre de la zona", key=f"nombre_{i}")
            sistema = st.selectbox(f"Sistema", SISTEMAS_CATALOGO, key=f"sist_{i}")
        with col2:
            m2 = st.number_input(f"Metros Cuadrados (m²)", min_value=0.0, key=f"m2_{i}")
            precio = st.number_input(f"Precio Unitario por m²", min_value=0.0, key=f"precio_{i}")
        zonas_data.append({"area": nombre_area, "sistema": sistema, "m2": m2, "precio": precio})
        st.write("") 
    
    boton = st.form_submit_button("GENERAR DOCUMENTO TARC / IMAC")

if boton:
    if not cliente or not zonas_data[0]["area"]:
        st.error("⚠️ Faltan datos del cliente o nombres de las áreas.")
    else:
        with st.spinner("Aplicando diseño corporativo azul y acomodando logos..."):
            subtotal_general = 0
            
            pdf = PDF()
            pdf.set_auto_page_break(auto=True, margin=20)
            pdf.add_page()
            
            fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
            pdf.set_font('Arial', '', 10)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 5, f'VERACRUZ, VER. A {fecha_hoy}', ln=True, align='R')
            pdf.ln(5)
            
            pdf.set_font('Arial', 'B', 11)
            pdf.set_text_color(15, 60, 140) # Azul Marino para el cliente
            pdf.cell(0, 5, cliente.upper(), ln=True)
            if proyecto:
                pdf.cell(0, 5, proyecto.upper(), ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 5, 'PRESENTE', ln=True)
            pdf.ln(5)
            
            pdf.set_font('Arial', '', 10)
            intro = ("POR ESTE MEDIO Y EN RESPUESTA A SU SOLICITUD, NOS PERMITIMOS PONER A SU AMABLE "
                     "CONSIDERACION LA SIGUIENTE COTIZACION, SOBRE TRABAJOS DE IMPERMEABILIZACION EN LOSAS "
                     "DE CONCRETO CONSISTENTE EN:")
            pdf.multi_cell(0, 5, txt=intro)
            pdf.ln(8)
            
            for idx, zona in enumerate(zonas_data):
                area_m2 = zona["m2"]
                precio_u = zona["precio"]
                subtotal_zona = area_m2 * precio_u
                subtotal_general += subtotal_zona
                
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(41, 128, 185) # Azul Acento para subtítulos de área
                pdf.multi_cell(0, 6, txt=f"SUMINISTRO Y APLICACION DE IMPERMEABILIZANTE EN {zona['area'].upper()}:")
                
                pdf.set_font('Arial', 'B', 11)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 6, zona["sistema"], ln=True)
                
                pdf.set_font('Arial', '', 9)
                pdf.multi_cell(0, 4, txt=TEXTO_DESCRIPCION)
                pdf.ln(3)
                
                pdf.set_font('Arial', 'B', 9)
                pdf.set_text_color(15, 60, 140)
                pdf.cell(0, 5, "ESPECIFICACIONES", ln=True)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Arial', '', 9)
                pdf.multi_cell(0, 4, txt=TEXTO_ESPECIFICACIONES)
                pdf.ln(4)
                
                # Tablas con fondo azul muy claro y texto oscuro
                pdf.set_fill_color(235, 245, 255) 
                pdf.set_text_color(15, 60, 140)
                pdf.set_font('Arial', 'B', 9)
                pdf.cell(60, 6, "AREA APROXIMADA LOSA (M2)", border=1, fill=True, align='C')
                pdf.cell(60, 6, "PRECIO POR M2", border=1, fill=True, align='C')
                pdf.cell(70, 6, "SUBTOTAL", border=1, fill=True, align='C')
                pdf.ln()
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Arial', '', 9)
                pdf.cell(60, 6, f"{area_m2:,.2f}", border=1, align='C')
                pdf.cell(60, 6, f"${precio_u:,.2f}", border=1, align='C')
                pdf.cell(70, 6, f"${subtotal_zona:,.2f}", border=1, align='C')
                
                pdf.ln(12) 
            
            iva = subtotal_general * 0.16
            gran_total = subtotal_general + iva
            
            if pdf.get_y() > 220:
                pdf.add_page()

            # Tabla final
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(120, 6, "SUBTOTAL DE PRESUPUESTO", border=1, align='R')
            pdf.cell(70, 6, f"${subtotal_general:,.2f}", border=1, align='R')
            pdf.ln()
            pdf.cell(120, 6, "IVA", border=1, align='R')
            pdf.cell(70, 6, f"${iva:,.2f}", border=1, align='R')
            pdf.ln()
            
            # FILA DE TOTAL PREMIUM (Fondo Azul Marino, Letras Blancas)
            pdf.set_fill_color(15, 60, 140)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(120, 8, "TOTAL", border=1, fill=True, align='R')
            gran_total_redondeado = round(gran_total)
            pdf.cell(70, 8, f"${gran_total_redondeado:,.2f}", border=1, fill=True, align='R')
            pdf.ln(12)
            
            # Regresamos a texto negro para las notas
            pdf.set_text_color(0, 0, 0)
            
            pdf.set_font('Arial', 'B', 9)
            pdf.set_text_color(15, 60, 140)
            pdf.cell(0, 5, "NOTAS:", ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Arial', '', 8)
            pdf.multi_cell(0, 4, txt="- SE DEBERA HACER UN LEVANTAMIENTO FISICO PARA PODER DETERMINAR LOS ALCANCES POR TRABAJO SOLICITADO.\n- ESTO PARA PODER COTIZAR SI EXISTIERAN TRABAJOS EXTRAORDINARIOS, COTIZAR EL SISTEMA MAS ADECUADO Y VERIFICAR LAS MEDIDAS.\n- NO INCLUYE TRABAJOS DE ALBAÑILERIA")
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
            pdf.ln(8)
            
            # --- ZONA DE BANCOS (CORREGIDA PARA NO ENCIMAR) ---
            if pdf.get_y() > 230:
                pdf.add_page()
            
            y_bancos = pdf.get_y()
            
            if os.path.exists("logo_bbva.jpg"):
                # Si existe la imagen, la pega a la derecha y NO escribe el texto manual
                pdf.image("logo_bbva.jpg", x=145, y=y_bancos, w=55)
                pdf.set_y(y_bancos + 35) # Damos el espacio exacto hacia abajo para que la firma no choque
            else:
                # Si no existe la imagen (por si acaso), entonces sí escribe el texto
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(15, 60, 140)
                pdf.cell(0, 5, "BBVA Bancomer", ln=True, align='R')
                pdf.set_font('Arial', 'B', 9)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 5, "CUENTA: 450187690", ln=True, align='R')
                pdf.cell(0, 5, "CLABE: 012905004501876903", ln=True, align='R')
                pdf.cell(0, 5, "RFC: TAR9803175MA", ln=True, align='R')
                pdf.ln(12)

            # --- FIRMA FINAL ---
            if pdf.get_y() > 250:
                pdf.add_page()
                
            pdf.set_font('Arial', 'B', 9)
            pdf.set_text_color(15, 60, 140) # Azul para la firma
            pdf.cell(0, 5, 'CORDIALMENTE', ln=True)
            pdf.cell(0, 5, 'TARC S.A. DE C.V.', ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Arial', '', 8)
            pdf.cell(0, 4, 'BOULEVARD MIGUEL ALEMAN 759, COL. CENTRO. VERACRUZ, VER. C.P. 91700', ln=True)
            pdf.cell(0, 4, 'TEL. (229) 935 39 40 | rh@grupo-imac.com | www.grupo-imac.com', ln=True)
            pdf.ln(10)

            # --- FOOTER DE MARCAS PROVEEDORAS ---
            if pdf.get_y() > 250: 
                pdf.add_page()
            
            if os.path.exists("footer_marcas.jpg"):
                pdf.image("footer_marcas.jpg", x=10, y=pdf.get_y(), w=190)

            # Guardar en Excel
            hoja = conectar_sheets()
            if hoja:
                resumen_zonas = " / ".join([f"{z['area']} ({z['m2']}m2)" for z in zonas_data])
                hoja.append_row([fecha_hoy, "Asesor", cliente, proyecto, resumen_zonas, subtotal_general, gran_total_redondeado])

            pdf_output = pdf.output(dest='S').encode('latin-1')
            st.success("✅ Diseño Azul Premium y bancos corregidos.")
            st.download_button("📥 DESCARGAR PRESUPUESTO TARC / IMAC", data=pdf_output, file_name=f"Presupuesto_{cliente}.pdf")
