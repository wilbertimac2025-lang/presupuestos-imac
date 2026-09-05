import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF
import datetime
import json
import os
import smtplib
from email.message import EmailMessage
from PIL import Image
import io
from PyPDF2 import PdfMerger
import math

# --- CONFIGURACIÓN CORPORATIVA ---
icono_navegador = "logo_imac_2026.png" if os.path.exists("logo_imac_2026.png") else ("logo_tarc.png" if os.path.exists("logo_tarc.png") else "🏢")
st.set_page_config(page_title="Cotizador Multizona IMAC", page_icon=icono_navegador, layout="centered")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ Acceso denegado. Inicia sesión en la página principal.")
    st.stop()

ROLES_PERMITIDOS = ["Admin", "RRHH", "Auxiliar", "Operativo", "Directivo"]
if st.session_state.get("role") not in ROLES_PERMITIDOS:
    st.error(f"🚫 ACCESO RESTRINGIDO: Tu perfil de {st.session_state.get('role')} no tiene autorización para este módulo.")
    st.stop()

def registrar_bitacora(doc, modulo, accion):
    try:
        if doc:
            hoja_bitacora = doc.worksheet("Bitacora_Movimientos")
            fecha_hora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            usuario = st.session_state.get("usuario", st.session_state.get("user", "Usuario Sistema"))
            rol = st.session_state.get("role", "Desconocido")
            hoja_bitacora.append_row([fecha_hora, usuario, rol, modulo, accion])
    except Exception:
        pass 

DESC_ACRILICO = "RECUBRIMIENTO ELASTICO IMPERMEABLE CON BASE EN RESINAS ACRILICAS..."
ESPEC_ACRILICO = "PREPARACION DE LA SUPERFICIE...\n- LIMPIEZA DEL AREA..."
DESC_PREFAB_FV = "ES UN SISTEMA DE IMPERMEABILIZACION PREFABRICADO FIBRA DE VIDRIO..."
DESC_PREFAB_FP = "ES UN SISTEMA DE IMPERMEABILIZACION PREFABRICADO POLIESTER..."
ESPEC_PREFAB = "PREPARACION DE LA SUPERFICIE...\n- APLICACIÓN DE HIDROFLEX..."
DESC_GENERAL = "SUMINISTRO Y APLICACIÓN DE MATERIAL DE ACUERDO A REQUERIMIENTOS."
ESPEC_GENERAL = "PREPARACION DE SUPERFICIE.\n- APLICACIÓN DE MATERIAL."

CATALOGO_SISTEMAS = {
    "LEVANTAMIENTO": {"precio": 30.00, "garantia": "NO APLICA", "desc": "PREPARACIÓN DE SUPERFICIE...", "espec": "TOMA DE MEDIDAS...", "ficha": "NO APLICA"},
    "ACRILTECHO GREEN POWER": {"precio": 244.00, "garantia": "5 AÑOS CONTRA DEFECTOS DE FABRICACIÓN", "desc": DESC_ACRILICO, "espec": ESPEC_ACRILICO, "ficha": "ficha_acriltecho.pdf"},
    "IMPAC 3000 FIBRATADO": {"precio": 198.00, "garantia": "3 AÑOS CONTRA DEFECTOS DE FABRICACIÓN", "desc": DESC_ACRILICO, "espec": ESPEC_ACRILICO, "ficha": "ficha_impac_3000.pdf"},
    "IMPAC 5000 FIBRATADO": {"precio": 219.00, "garantia": "5 AÑOS CONTRA DEFECTOS DE FABRICACIÓN", "desc": DESC_ACRILICO, "espec": ESPEC_ACRILICO, "ficha": "ficha_impac_5000.pdf"},
    "KRIPTOFLEX 3 AÑOS CON MALLA": {"precio": 189.00, "garantia": "3 AÑOS CONTRA DEFECTOS DE FABRICACIÓN", "desc": DESC_ACRILICO, "espec": ESPEC_ACRILICO, "ficha": "ficha_kriptoflex.pdf"},
    "KRIPTOFLEX 3 AÑOS FIBRATADO": {"precio": 171.00, "garantia": "3 AÑOS CONTRA DEFECTOS DE FABRICACIÓN", "desc": DESC_ACRILICO, "espec": ESPEC_ACRILICO, "ficha": "ficha_kriptoflex.pdf"},
    "KRIPTOFLEX 5 AÑOS FIBRATADO": {"precio": 209.00, "garantia": "12 MESES CONTRA DEFECTOS DE FABRICACIÓN", "desc": DESC_ACRILICO, "espec": ESPEC_ACRILICO, "ficha": "ficha_kriptoflex.pdf"},
    "KRIPTOFLEX 5 AÑOS CON MALLA": {"precio": 219.00, "garantia": "12 MESES CONTRA DEFECTOS DE FABRICACIÓN", "desc": DESC_ACRILICO, "espec": ESPEC_ACRILICO, "ficha": "ficha_kriptoflex.pdf"},
    "IMPAC 7000 FIBRATADO": {"precio": 239.00, "garantia": "12 MESES CONTRA DEFECTOS DE FABRICACIÓN", "desc": DESC_ACRILICO, "espec": ESPEC_ACRILICO, "ficha": "ficha_impac_7000.pdf"},
    "IMPAC 7000 FIBRATADO CON MALLA": {"precio": 265.00, "garantia": "12 MESES CONTRA DEFECTOS DE FABRICACIÓN", "desc": DESC_ACRILICO, "espec": ESPEC_ACRILICO, "ficha": "ficha_impac_7000.pdf"},
    "SELLOTEX": {"precio": 334.00, "garantia": "NO APLICA", "desc": DESC_GENERAL, "espec": ESPEC_GENERAL, "ficha": "ficha_sellotex.pdf"},
    "JUNTA LINEAL 30 CM MASTER LASSER 3.0 LISO": {"precio": 148.00, "garantia": "NO APLICA", "desc": DESC_PREFAB_FP, "espec": ESPEC_PREFAB, "ficha": "NO APLICA"},
    "JUNTA LINEAL 50 CM MASTER LASSER 3.0 LISO": {"precio": 184.00, "garantia": "NO APLICA", "desc": DESC_PREFAB_FP, "espec": ESPEC_PREFAB, "ficha": "NO APLICA"},
    "JUNTA LINEAL 50 CM MASTER LASSER 4.0 LISO": {"precio": 203.00, "garantia": "NO APLICA", "desc": DESC_PREFAB_FP, "espec": ESPEC_PREFAB, "ficha": "NO APLICA"},
    "JUNTA LINEAL 15 A 50 CM KRIPTOFLEX": {"precio": 125.00, "garantia": "NO APLICA", "desc": DESC_ACRILICO, "espec": ESPEC_ACRILICO, "ficha": "NO APLICA"},
    "MASTER LASSER 3.5 MM FP": {"precio": 250.00, "garantia": "5 AÑOS CONTRA DEFECTOS DE FABRICACIÓN", "desc": DESC_PREFAB_FP, "espec": ESPEC_PREFAB, "ficha": "DINAMICA_LOCAL_FORANEA"},
    "MASTER LASSER 4.0 MM FP": {"precio": 294.00, "garantia": "8 AÑOS CONTRA DEFECTOS DE FABRICACIÓN", "desc": DESC_PREFAB_FP, "espec": ESPEC_PREFAB, "ficha": "DINAMICA_LOCAL_FORANEA"},
    "MASTER LASSER 4.5 MM FP": {"precio": 325.00, "garantia": "10 AÑOS CONTRA DEFECTOS DE FABRICACIÓN", "desc": DESC_PREFAB_FP, "espec": ESPEC_PREFAB, "ficha": "DINAMICA_LOCAL_FORANEA"},
    "MASTER LASSER 4.0 MM FP (ESCUELAS)": {"precio": 238.00, "garantia": "8 AÑOS CONTRA DEFECTOS DE FABRICACIÓN", "desc": DESC_PREFAB_FP, "espec": ESPEC_PREFAB, "ficha": "DINAMICA_LOCAL_FORANEA"},
    "MASTER LASSER 3.0 MM FP LISO SIN ACABADO": {"precio": 230.00, "garantia": "5 AÑOS CONTRA DEFECTOS DE FABRICACIÓN", "desc": DESC_PREFAB_FP, "espec": ESPEC_PREFAB, "ficha": "DINAMICA_LOCAL_FORANEA"},
    "MASTER LASSER 4.0 MM FP LISO SIN ACABADO": {"precio": 280.00, "garantia": "8 AÑOS CONTRA DEFECTOS DE FABRICACIÓN", "desc": DESC_PREFAB_FP, "espec": ESPEC_PREFAB, "ficha": "DINAMICA_LOCAL_FORANEA"},
    "MASTER LASSER 3.0 MM FV": {"precio": 169.00, "garantia": "NO APLICA", "desc": DESC_PREFAB_FV, "espec": ESPEC_PREFAB, "ficha": "DINAMICA_LOCAL_FORANEA"},
    "MASTER LASSER 3.5 MM FV": {"precio": 211.00, "garantia": "3 AÑOS CONTRA DEFECTOS DE FABRICACIÓN", "desc": DESC_PREFAB_FV, "espec": ESPEC_PREFAB, "ficha": "DINAMICA_LOCAL_FORANEA"},
    "BITUFLEX": {"precio": 252.00, "garantia": "NO APLICA", "desc": "SUMINISTRO DE SOLVENTE Y/O MATERIAL BASE.", "espec": "APLICACIÓN SEGÚN REQUERIMIENTOS EN OBRA.", "ficha": "ficha_bituflex.pdf"}
}

class PDF(FPDF):
    def header(self):
        if os.path.exists("marca_agua.jpg"): self.image("marca_agua.jpg", x=5, y=5, w=200, h=287)
        self.set_draw_color(15, 60, 140) 
        self.set_line_width(0.7) 
        self.rect(5, 5, 200, 287) 
        self.set_line_width(0.2) 
        if os.path.exists("logo_tarc.png"): self.image("logo_tarc.png", x=10, y=8, w=85) 
        elif os.path.exists("logo_tarc.jpg"): self.image("logo_tarc.jpg", x=10, y=8, w=85)
        else:
            self.set_font('Arial', 'B', 14)
            self.set_text_color(15, 60, 140)
            self.cell(0, 6, 'TARC S.A. DE C.V.', ln=True, align='L')
        self.set_y(38)

@st.cache_resource
def conectar_sheets():
    try:
        # 🚀 CAMBIO PARA RENDER: os.environ.get
        credenciales_dic = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(credenciales_dic, scopes=scopes)
        cliente = gspread.authorize(creds)
        ID_DEL_EXCEL = os.environ.get("ID_EXCEL")
        return cliente.open_by_key(ID_DEL_EXCEL)
    except Exception: return None

def obtener_nuevo_folio(hoja):
    try:
        anio_corto = datetime.datetime.now().strftime("%y") 
        if hoja:
            filas = hoja.get_all_values()
            numero_obra = len(filas) if len(filas) > 0 else 1
            return f"OBRA{numero_obra:02d}-{anio_corto}"
    except Exception: pass
    anio_corto = datetime.datetime.now().strftime("%y")
    return f"OBRA-TEMP-{datetime.datetime.now().strftime('%H%M')}-{anio_corto}"

def enviar_respaldo_correo(pdf_bytes, nombre_archivo, cliente, asesor, folio, tipo_obra, proyecto, ubicacion):
    try:
        # 🚀 CAMBIO PARA RENDER: os.environ.get
        remitente = os.environ.get("CORREO_BOT")
        password = os.environ.get("PASS_BOT")
        
        if tipo_obra == "LOCAL": correo_destino = "comercial@grupo-imac.com, pue@grupo-imac.com, act@grupo-imac.com, pue1@grupo-imac.com"
        else: correo_destino = "comercial@grupo-imac.com, foraneos@grupo-imac.com, direccion@grupo-imac.com"
        
        msg = EmailMessage()
        msg['Subject'] = f'NUEVO FOLIO {folio}: Presupuesto {cliente} - Zona: {tipo_obra}'
        msg['From'] = remitente
        msg['To'] = correo_destino
        msg.set_content(f"Se ha registrado un nuevo presupuesto en el sistema.\n\nFolio Asignado: {folio}\nCliente: {cliente}\nAsesor: {asesor}\nProyecto: {proyecto}\nUbicación: {ubicacion}\nZona Logística: {tipo_obra}\n\nSe adjunta el documento oficial.")
        msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=nombre_archivo)
        
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls()
            smtp.login(remitente, password)
            smtp.send_message(msg)
        return True, "OK"
    except Exception as e: return False, str(e)

col_logo, col_tit = st.columns([1, 4])
with col_logo:
    try:
        if os.path.exists("logo_imac_2026.png"):
            st.image(Image.open("logo_imac_2026.png"), use_container_width=True)
        elif os.path.exists("logo_tarc.png"):
            st.image(Image.open("logo_tarc.png"), use_container_width=True)
    except Exception: st.write("🏢 GRUPO IMAC")
with col_tit: st.title("Presupuestos Obras Grupo IMAC")
st.markdown("---")

num_areas = st.number_input("¿Cuántas áreas distintas vas a cotizar?", min_value=1, max_value=10, value=1)
st.write("### 1. Datos de Contacto y Asignación")
fecha_validez = st.date_input("Presupuesto válido hasta:", value=datetime.date.today() + datetime.timedelta(days=15))
cliente = st.text_input("Nombre del Cliente")
compania = st.text_input("Compañía / Empresa")
telefono = st.text_input("Teléfono de Contacto")
correo_cliente = st.text_input("Correo Electrónico del Cliente")
asesor = st.selectbox("Nombre del Asesor", ["JOSE CARLOS MORALES MORALES", "FRANCISCO JAVIER CARO YAÑEZ"])
tipo_obra = st.selectbox("Tipo de Proyecto / Logística:", ["LOCAL", "FORÁNEA"])

st.write("---")
st.write("### 2. Información del Proyecto")
proyecto = st.text_input("Nombre del Proyecto / Obra")
ubicacion = st.text_input("Ubicación / Dirección de la Obra")

st.write("---")
st.write("### 3. Desglose de Áreas")
zonas_data = []
opciones_sistemas = list(CATALOGO_SISTEMAS.keys()) 

# 🚀 LÓGICA DE ACTUALIZACIÓN DINÁMICA DE PRECIOS
for i in range(int(num_areas)):
    st.markdown(f"**Área {i+1}**")
    col1, col2 = st.columns(2)
    
    with col1:
        n = st.text_input(f"Nombre de la zona", key=f"n_{i}")
        # Usamos el key s_i para que Streamlit sepa que cambió, y mostramos el valor actualizado en la variable
        s = st.selectbox(f"Sistema", opciones_sistemas, key=f"s_{i}")
        
    with col2:
        m = st.number_input(f"Metros (m²)", min_value=0.0, key=f"m_{i}")
        # Aquí forzamos a que siempre lea el precio del diccionario basado en la selección actual 's'
        precio_dinamico = float(CATALOGO_SISTEMAS[s]["precio"])
        
        st.info(f"**Precio x m² (Fijo + IVA):** ${precio_dinamico:,.2f}")
        
        desc_pct = st.number_input(f"Descuento para esta área (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key=f"desc_{i}")
        
    zonas_data.append({"area": n, "sistema": s, "m2": m, "descuento_pct": desc_pct})

st.write("---")
st.write("### 4. Ajustes y Anexos")
costo_extra = st.number_input("Costo Extra Adicional (Pesos $)", min_value=0.0)
desc_extra = st.text_input("Concepto del Costo Extra")
anotaciones_asesor = st.text_area("Anotaciones Especiales para el Cliente")

st.write("**Evidencia Fotográfica de la Obra:**")
fotos_subidas = st.file_uploader("📸 Subir Evidencia (Opcional)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
colA, colB = st.columns(2)
with colA:
    c0 = st.text_input("Nota para Foto 1"); c2 = st.text_input("Nota para Foto 3"); c4 = st.text_input("Nota para Foto 5")
with colB:
    c1 = st.text_input("Nota para Foto 2"); c3 = st.text_input("Nota para Foto 4"); c5 = st.text_input("Nota para Foto 6")
comentarios_fotos = [c0, c1, c2, c3, c4, c5]

if st.button("GENERAR PRESUPUESTO OFICIAL", type="primary"):
    c_valido = cliente.strip(); a_valido = asesor.strip(); u_valido = ubicacion.strip(); p_valido = proyecto.strip()
    if not c_valido or not a_valido or not u_valido or not p_valido: st.error("⚠️ El Cliente, Asesor, Nombre del Proyecto y Ubicación son obligatorios.")
    else:
        with st.spinner("Calculando Rendimientos, Aplicando Descuentos y Ensamblando PDF..."):
            temp_paths = []
            if fotos_subidas:
                for idx, foto in enumerate(fotos_subidas):
                    ext = foto.name.split('.')[-1]
                    temp_path = f"temp_img_{idx}.{ext}"
                    with open(temp_path, "wb") as f: f.write(foto.getbuffer())
                    temp_paths.append(temp_path)

            doc = conectar_sheets()
            hoja = doc.worksheet("Presupuestos") if doc else None
            folio_actual = obtener_nuevo_folio(hoja)

            subtotal_obras = sum(z["m2"] * CATALOGO_SISTEMAS[z["sistema"]]["precio"] for z in zonas_data)
            total_descuento = sum((z["m2"] * CATALOGO_SISTEMAS[z["sistema"]]["precio"]) * (z["descuento_pct"] / 100.0) for z in zonas_data)
            
            bolsa_mano_obra = 0.0
            materiales_calculados = {}
            
            for z in zonas_data:
                sis = z["sistema"]
                m2 = float(z["m2"])
                if sis == "LEVANTAMIENTO": tarifa = 12.0
                elif sis == "SELLOTEX": tarifa = 0.0
                else: tarifa = 28.0
                bolsa_mano_obra += m2 * tarifa
                
                if sis == "LEVANTAMIENTO": continue
                if "SELLOTEX" in sis: cant = math.ceil(m2 / 10.0); unidad = "BULTOS"
                elif "JUNTA" in sis:
                    if "30 CM" in sis: cant = math.ceil(m2 / 30.0); unidad = "ROLLOS"
                    elif "KRIPTOFLEX" in sis: cant = math.ceil(m2 / 19.0); unidad = "CUBETAS"
                    else: cant = math.ceil(m2 / 20.0); unidad = "ROLLOS"
                elif "FP" in sis or "FV" in sis or "MASTER LASSER" in sis: cant = math.ceil(m2 / 8.5); unidad = "ROLLOS"
                else: cant = math.ceil(m2 / 19.0); unidad = "CUBETAS"
                    
                if sis in materiales_calculados: materiales_calculados[sis]["cant"] += cant
                else: materiales_calculados[sis] = {"cant": cant, "unidad": unidad}
            
            lista_textos_mat = [f"{v['cant']} {v['unidad']} DE {k}" for k, v in materiales_calculados.items()]
            resumen_insumos_str = " / ".join(lista_textos_mat) if lista_textos_mat else "SIN MATERIAL ASIGNADO"
            
            pdf = PDF()
            pdf.set_auto_page_break(auto=True, margin=20)
            pdf.add_page()
            
            pdf.set_font('Arial', 'B', 12); pdf.set_text_color(200, 30, 30); pdf.cell(0, 5, f"FOLIO: {folio_actual}", ln=True, align='R')
            fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
            pdf.set_font('Arial', 'I', 10); pdf.set_text_color(100, 100, 100); pdf.cell(0, 5, f'Veracruz, Ver. a {fecha_hoy}', ln=True, align='R'); pdf.ln(5)
            
            pdf.set_font('Arial', 'B', 12); pdf.set_text_color(15, 60, 140); pdf.cell(0, 5, f"CLIENTE: {cliente.upper()}", ln=True)
            if compania: pdf.set_font('Arial', 'B', 10); pdf.set_text_color(0, 150, 255); pdf.cell(0, 5, f"{compania.upper()}", ln=True)
            pdf.set_font('Arial', '', 10); pdf.set_text_color(50, 50, 50)
            if telefono: pdf.cell(0, 5, f"Tel: {telefono}", ln=True)
            if correo_cliente: pdf.cell(0, 5, f"Email: {correo_cliente}", ln=True)
            pdf.ln(2); pdf.set_font('Arial', 'B', 10); pdf.set_text_color(15, 60, 140); pdf.cell(0, 5, f"ASESOR COMERCIAL: {asesor.upper()}", ln=True)
            
            pdf.ln(3); pdf.set_font('Arial', 'B', 11); pdf.set_text_color(0, 0, 0); pdf.cell(0, 5, f"PROYECTO: {proyecto.upper()}", ln=True)
            pdf.set_font('Arial', 'I', 10); pdf.cell(0, 5, f"UBICACIÓN: {ubicacion.upper()}", ln=True)

            pdf.ln(5); pdf.set_font('Arial', 'I', 10); pdf.set_text_color(80, 80, 80); pdf.multi_cell(0, 5, txt="Nos permitimos poner a su amable consideración el siguiente presupuesto:"); pdf.ln(5)

            for z in zonas_data:
                precio_unitario_real = CATALOGO_SISTEMAS[z["sistema"]]["precio"]
                subtotal_area_real = z["m2"] * precio_unitario_real
                pdf.set_font('Arial', 'B', 11); pdf.set_text_color(0, 150, 255); pdf.multi_cell(0, 6, txt=f"SUMINISTRO Y APLICACIÓN EN {z['area'].upper()}:")
                pdf.set_font('Arial', 'B', 11); pdf.set_text_color(15, 60, 140); pdf.cell(0, 6, z["sistema"], ln=True)
                pdf.set_font('Arial', 'I', 9); pdf.set_text_color(80, 80, 80); pdf.multi_cell(0, 4, txt=CATALOGO_SISTEMAS[z["sistema"]]["desc"])
                pdf.ln(3); pdf.set_font('Arial', 'B', 9); pdf.set_text_color(0, 150, 255); pdf.cell(0, 5, "Especificaciones Técnicas:", ln=True)
                pdf.set_text_color(50, 50, 50); pdf.set_font('Arial', '', 9); pdf.multi_cell(0, 4, txt=CATALOGO_SISTEMAS[z["sistema"]]["espec"])
                pdf.ln(4)
                
                pdf.set_fill_color(240, 248, 255); pdf.set_text_color(15, 60, 140); pdf.set_font('Arial', 'B', 9); pdf.set_draw_color(200, 200, 200) 
                pdf.cell(60, 6, "AREA (M2)", 'B', 0, 'C', True); pdf.cell(60, 6, "PRECIO UNIT.", 'B', 0, 'C', True); pdf.cell(70, 6, "SUBTOTAL", 'B', 1, 'C', True)
                pdf.set_text_color(0,0,0); pdf.set_font('Arial', '', 9)
                pdf.cell(60, 6, f"{z['m2']:,.2f}", 'B', 0, 'C'); pdf.cell(60, 6, f"${precio_unitario_real:,.2f}", 'B', 0, 'C'); pdf.cell(70, 6, f"${subtotal_area_real:,.2f}", 'B', 1, 'C')
                pdf.ln(8)

            subtotal_neto = subtotal_obras - total_descuento + costo_extra
            iva = subtotal_neto * 0.16
            total_final = round(subtotal_neto + iva)

            if pdf.get_y() > 210: pdf.add_page()
            
            if total_descuento > 0:
                pdf.set_font('Arial', 'B', 10); pdf.set_text_color(50, 50, 50); pdf.cell(120, 6, "IMPORTE SISTEMAS:", border=0, align='R'); pdf.cell(70, 6, f"${subtotal_obras:,.2f}", border=0, align='R', ln=True)
                pdf.set_text_color(200, 30, 30); pdf.cell(120, 6, "DESCUENTO APLICADO:", border=0, align='R'); pdf.cell(70, 6, f"-${total_descuento:,.2f}", border=0, align='R', ln=True)
                pdf.set_text_color(50, 50, 50) 
            
            if costo_extra > 0:
                pdf.set_font('Arial', 'B', 10); pdf.set_text_color(15, 60, 140)
                pdf.cell(120, 6, f"COSTO ADICIONAL: {desc_extra.upper() if desc_extra else 'OTROS'}", border=0, align='R'); pdf.cell(70, 6, f"${costo_extra:,.2f}", border=0, align='R', ln=True)

            pdf.set_font('Arial', 'B', 10); pdf.set_text_color(50, 50, 50)
            pdf.cell(120, 6, "SUBTOTAL:", border=0, align='R'); pdf.cell(70, 6, f"${subtotal_neto:,.2f}", border=0, align='R', ln=True)
            pdf.cell(120, 6, "IVA (16%):", border=0, align='R'); pdf.cell(70, 6, f"${iva:,.2f}", border=0, align='R', ln=True)
            pdf.ln(2)

            x_i = pdf.get_x(); y_i = pdf.get_y()
            pdf.set_fill_color(200, 200, 200); pdf.rect(x_i + 60 + 1.5, y_i + 1.5, 130, 9, 'F')
            pdf.set_fill_color(15, 60, 140); pdf.set_text_color(255, 255, 255); pdf.set_font('Arial', 'B', 11); pdf.set_xy(x_i + 60, y_i)
            pdf.cell(60, 9, "INVERSIÓN TOTAL", border=0, fill=True, align='R'); pdf.set_fill_color(0, 150, 255); pdf.cell(70, 9, f"${total_final:,.2f} MXN", border=0, fill=True, align='C', ln=True)
            
            pdf.ln(8); pdf.set_text_color(15, 60, 140); pdf.set_font('Arial', 'B', 9); pdf.cell(0, 5, "Consideraciones Importantes:", ln=True)
            pdf.set_text_color(80, 80, 80); pdf.set_font('Arial', 'I', 8)
            pdf.multi_cell(0, 4, txt="- Se deberá hacer un levantamiento físico...\n- No incluye trabajos de albañilería...\n- Trabajos no cotizados."); pdf.ln(3)
            
            garantias_unicas = {}
            for z in zonas_data:
                sis = z["sistema"]; gar = CATALOGO_SISTEMAS[sis]["garantia"]
                if gar != "NO APLICA" and sis not in garantias_unicas: garantias_unicas[sis] = gar
                    
            pdf.set_font('Arial', 'B', 9); pdf.set_text_color(50, 50, 50); pdf.cell(60, 5, "Garantías por Sistema:")
            pdf.set_font('Arial', '', 9); pdf.set_text_color(15, 60, 140)
            if not garantias_unicas: pdf.cell(0, 5, "NO APLICA", ln=True)
            else:
                primer_item = True
                for sis, gar in garantias_unicas.items():
                    if primer_item: pdf.cell(0, 5, f"{sis}: {gar}", ln=True); primer_item = False
                    else: pdf.cell(60, 5, ""); pdf.cell(0, 5, f"{sis}: {gar}", ln=True)
            
            pdf.set_font('Arial', 'B', 9); pdf.set_text_color(50, 50, 50); pdf.cell(60, 5, "Condiciones de Pago:"); pdf.set_font('Arial', '', 9); pdf.set_text_color(15, 60, 140); pdf.cell(0, 5, "70% DE ANTICIPO, 30% CONTRA ENTREGA", ln=True)
            pdf.set_font('Arial', 'B', 9); pdf.set_text_color(50, 50, 50); pdf.cell(60, 5, "Presupuesto válido hasta:"); pdf.set_font('Arial', '', 9); pdf.set_text_color(15, 60, 140); pdf.cell(0, 5, fecha_validez.strftime("%d/%m/%Y"), ln=True)
            pdf.set_font('Arial', 'I', 8); pdf.set_text_color(200, 30, 30); pdf.cell(60, 4, ""); pdf.cell(0, 4, "* Precio sujeto a cambios sin previo aviso.", ln=True); pdf.ln(5)

            if anotaciones_asesor:
                pdf.set_text_color(0, 150, 255); pdf.set_font('Arial', 'B', 10); pdf.cell(0, 6, "Anotaciones Especiales:", ln=True)
                pdf.set_text_color(80, 80, 80); pdf.set_font('Arial', 'I', 9); pdf.multi_cell(0, 5, txt=anotaciones_asesor); pdf.ln(5)

            if pdf.get_y() > 230: pdf.add_page()
            y_base = pdf.get_y() + 10 
            if os.path.exists("logo_bbva.png"): pdf.image("logo_bbva.png", x=145, y=y_base, w=55)
            
            pdf.set_y(y_base); pdf.set_font('Arial', 'B', 10); pdf.set_text_color(15, 60, 140); pdf.cell(0, 5, 'Atentamente,', ln=True)
            pdf.set_font('Arial', 'B', 12); pdf.set_text_color(0, 150, 255); pdf.cell(0, 5, 'TARC S.A. DE C.V.', ln=True)
            pdf.set_text_color(100, 100, 100); pdf.set_font('Arial', '', 8)
            if tipo_obra == "LOCAL":
                pdf.cell(0, 4, 'BOULEVARD MIGUEL ALEMAN 759, COL. CENTRO. VERACRUZ', ln=True)
                pdf.cell(0, 4, 'Cel. 229 935 3940 / 229 337 1080 | rh@grupo-imac.com', ln=True)
            else:
                pdf.cell(0, 4, 'DIRECCIÓN DE SUCURSAL FORÁNEA O FISCAL, ESTADO', ln=True)
                pdf.cell(0, 4, 'TEL. (000) 000 00 00 | correo_foraneo@grupo-imac.com', ln=True)
            
            pdf.set_y(y_base + 40)
            if os.path.exists("footer_marcas.png"):
                if pdf.get_y() > 250: pdf.add_page()
                pdf.image("footer_marcas.png", x=10, y=pdf.get_y(), w=190)

            if temp_paths:
                for i, temp_img in enumerate(temp_paths):
                    if i % 2 == 0:
                        pdf.add_page(); pdf.set_font('Arial', 'B', 14); pdf.set_text_color(15, 60, 140); pdf.set_xy(0, 35)
                        pdf.cell(210, 10, "ANEXO FOTOGRÁFICO", ln=True, align='C')
                        y_pos = 50
                    else: y_pos = 165
                    try:
                        img = Image.open(temp_img)
                        w_px, h_px = img.size; ratio = min(160 / w_px, 95 / h_px)
                        w_mm = w_px * ratio; h_mm = h_px * ratio; x_mm = (210 - w_mm) / 2 
                        pdf.image(temp_img, x=x_mm, y=y_pos, w=w_mm, h=h_mm)
                        if i < len(comentarios_fotos) and comentarios_fotos[i].strip():
                            pdf.set_xy(25, y_pos + h_mm + 2); pdf.set_font('Arial', 'I', 10); pdf.set_text_color(80, 80, 80)
                            pdf.multi_cell(160, 5, txt=f"Nota: {comentarios_fotos[i]}", align='C')
                    except: pass
            for temp_img in temp_paths:
                if os.path.exists(temp_img): os.remove(temp_img)

            pdf_base_bytes = pdf.output(dest='S').encode('latin-1')

            archivos_unicos_a_fusionar = []
            sistemas_con_alerta = []
            for z in zonas_data:
                sis = z["sistema"]; ficha_asignada = CATALOGO_SISTEMAS[sis]["ficha"]
                if ficha_asignada == "DINAMICA_LOCAL_FORANEA": archivo_ficha = "ficha_tecnica_local.pdf" if tipo_obra == "LOCAL" else "ficha_tecnica_foranea.pdf"
                else: archivo_ficha = ficha_asignada
                if archivo_ficha != "NO APLICA" and archivo_ficha not in [f[1] for f in archivos_unicos_a_fusionar]: archivos_unicos_a_fusionar.append((sis, archivo_ficha))

            if archivos_unicos_a_fusionar:
                fusionador = PdfMerger(); fusionador.append(io.BytesIO(pdf_base_bytes))
                for sis, archivo in archivos_unicos_a_fusionar:
                    if os.path.exists(archivo): fusionador.append(archivo)
                    else: sistemas_con_alerta.append(f"{sis}")
                archivo_salida = io.BytesIO()
                fusionador.write(archivo_salida); fusionador.close(); pdf_final_para_descargar = archivo_salida.getvalue()
                if sistemas_con_alerta: st.warning(f"⚠️ Alerta: Faltan fichas técnicas en GitHub: {', '.join(sistemas_con_alerta)}")
            else: pdf_final_para_descargar = pdf_base_bytes

            nombre_file = f"Presupuesto_{folio_actual}_{cliente.replace(' ', '_')}.pdf"
            
            if doc:
                try:
                    hoja_limites = doc.worksheet("Limites_Materiales")
                    for mat_sis, info in materiales_calculados.items(): hoja_limites.append_row([folio_actual, mat_sis, info["cant"], "AUTORIZADO COTIZADOR"])
                except Exception: pass

            if hoja:
                resumen = " / ".join([f"{z['area']} ({z['m2']}m2)" for z in zonas_data])
                hoja.append_row([folio_actual, fecha_hoy, asesor, cliente, compania, telefono, correo_cliente, proyecto.upper(), ubicacion.upper(), resumen, total_final, tipo_obra, bolsa_mano_obra, resumen_insumos_str])
                registrar_bitacora(doc, "Cotizador", f"Generó presupuesto {folio_actual}")
            
            enviar_respaldo_correo(pdf_final_para_descargar, nombre_file, cliente, asesor, folio_actual, tipo_obra, proyecto, ubicacion)
            
        st.success(f"✅ Presupuesto {folio_actual} generado y Límites autorizados con éxito.")
        st.download_button(label="📄 DESCARGAR PRESUPUESTO", data=pdf_final_para_descargar, file_name=nombre_file, mime="application/pdf")
