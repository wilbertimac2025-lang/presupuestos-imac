import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime
import pandas as pd
from fpdf import FPDF
import os

st.set_page_config(page_title="Facturación y Estados de Cuenta", page_icon="🧾", layout="wide")

# -----------------------------------------
# 🛡️ CANDADO DE SEGURIDAD POR ROLES
# -----------------------------------------
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ Acceso denegado. Inicia sesión en la página principal.")
    st.stop()

ROLES_PERMITIDOS = ["Admin", "Directivo", "RRHH"]
if st.session_state.get("role") not in ROLES_PERMITIDOS:
    st.error(f"🚫 ACCESO RESTRINGIDO: Tu perfil no tiene autorización para ver estados de cuenta.")
    st.stop()

def limpiar_monto(valor):
    if str(valor).strip() == "" or valor is None: return 0.0
    try: return float(str(valor).replace("$", "").replace(",", "").replace(" ", "").strip())
    except: return 0.0

# 🧠 FUNCIÓN SABUESO: Busca valores en el diccionario
def obtener_valor(diccionario, palabras_clave, default="No registrado"):
    for k, v in diccionario.items():
        if any(p in str(k).upper() for p in palabras_clave):
            if str(v).strip() != "":
                return str(v)
    return default

# --- CLASE PARA EL PDF IDÉNTICO A LA FOTO ---
class PDF_EstadoCuenta(FPDF):
    def header(self):
        # Logo Superior Izquierdo
        if os.path.exists("logo_tarc.png"):
            self.image("logo_tarc.png", x=15, y=10, w=25)
        elif os.path.exists("logo_tarc.jpg"):
            self.image("logo_tarc.jpg", x=15, y=10, w=25)
            
        # Encabezado Superior
        self.set_xy(45, 12)
        self.set_font('Arial', 'B', 24)
        self.set_text_color(100, 100, 100) # Gris oscuro
        self.cell(0, 8, 'TARC, S.A DE C.V.', ln=True, align='C')
        
        self.set_xy(45, 22)
        self.set_font('Arial', '', 10)
        self.cell(0, 5, 'BLVD. MIGUEL ALEMAN No. 306 TEL.: 986-35-72 BOCA DEL RIO, VER.', ln=True, align='C')
        
        # Doble línea separadora
        self.set_draw_color(100, 100, 100)
        self.line(15, 30, 195, 30)
        self.line(15, 31, 195, 31)
        self.set_y(40)

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

st.title("🧾 Cobranza y Estados de Cuenta Finales")
st.markdown("---")

doc = conectar_sheets()

if doc:
    try:
        hoja_obras = doc.worksheet("Obras_Activas")
        hoja_facturas = doc.worksheet("Facturas_Obras")
        hoja_presupuestos = doc.worksheet("Presupuestos") # Para jalar los datos del cliente
    except Exception as e:
        st.error("⚠️ Faltan pestañas en tu Excel (Obras_Activas, Facturas_Obras o Presupuestos).")
        st.stop()

    datos_obras = hoja_obras.get_all_records()
    datos_presupuestos = hoja_presupuestos.get_all_records()
    
    # Juntamos los folios
    llave_folio = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "FOLIO" in str(k).upper()), None)
    obras_disponibles = [str(fila[llave_folio]) for fila in datos_obras if str(fila.get(llave_folio, "")) != ""] if llave_folio else []

    col_sel, _ = st.columns([1, 2])
    with col_sel:
        folio_seleccionado = st.selectbox("Selecciona la Obra a Facturar/Cobrar:", ["Selecciona un folio..."] + obras_disponibles)

    if folio_seleccionado != "Selecciona un folio...":
        
        # 1. CRUZAMOS DATOS PARA ENCONTRAR AL CLIENTE
        obra_activa = next((f for f in datos_obras if str(f.get(llave_folio, "")) == folio_seleccionado), {})
        obra_presupuesto = next((f for f in datos_presupuestos if str(obtener_valor(f, ["FOLIO"])).upper() == folio_seleccionado.upper()), {})
        
        # Combinamos la info (presupuesto tiene más peso en datos de cliente)
        datos_completos = {**obra_activa, **obra_presupuesto}
        
        # Extraemos con el sabueso
        nombre_cliente = obtener_valor(datos_completos, ["CLIENTE", "NOMBRE CLIENTE"], "Cliente Genérico")
        empresa_cliente = obtener_valor(datos_completos, ["EMPRESA", "RAZON SOCIAL", "COMPAÑIA"], "")
        nombre_proyecto = obtener_valor(datos_completos, ["PROYECTO", "OBRA", "CONCEPTO"], "Proyecto en ejecución")
        ubicacion_obra = obtener_valor(datos_completos, ["UBICACION", "DIRECCION", "LUGAR"], "Ubicación Registrada")
        
        presupuesto_total = limpiar_monto(obtener_valor(datos_completos, ["MONTO", "PRESUPUESTO", "AUTORIZADO", "TOTAL"], 0))

        # 2. CÁLCULO DE FACTURACIÓN (PAGOS RECIBIDOS)
        datos_facturas = hoja_facturas.get_all_records()
        facturas_obra = [f for f in datos_facturas if str(f.get("Folio Obra", "")) == folio_seleccionado]
        total_pagos_recibidos = sum(limpiar_monto(f.get("Monto Facturado", 0)) for f in facturas_obra)

        # 3. SALDO PENDIENTE
        saldo_pendiente = presupuesto_total - total_pagos_recibidos

        # --- PANTALLA PRINCIPAL ---
        st.subheader(f"📊 Balance de Cobranza: {nombre_proyecto}")
        m1, m2, m3 = st.columns(3)
        
        with m1:
            st.metric("Costo Total del Proyecto", f"${presupuesto_total:,.2f}")
        with m2:
            st.metric("Total de Pagos / Anticipos Recibidos", f"${total_pagos_recibidos:,.2f}")
        with m3:
            if saldo_pendiente > 0:
                st.metric("🔴 Saldo Pendiente por Liquidar", f"${saldo_pendiente:,.2f}")
            else:
                st.metric("🟢 Saldo Liquidado", f"${saldo_pendiente:,.2f}")

        st.markdown("---")
        
        c_form, c_tabla = st.columns([1, 2])
        with c_form:
            st.subheader("📥 Registrar Nuevo Pago/Factura")
            with st.form("form_facturas"):
                num_factura = st.text_input("Folio Factura o Recibo", placeholder="Ej. FAC-1045 o Anticipo")
                concepto_factura = st.text_input("Concepto", placeholder="Ej. Anticipo inicial")
                monto_factura = st.number_input("Monto Recibido ($)", min_value=0.0, step=1000.0)
                
                btn_facturar = st.form_submit_button("🧾 REGISTRAR PAGO")
                
                if btn_facturar:
                    if not num_factura or monto_factura <= 0:
                        st.warning("⚠️ Debes ingresar un recibo y un monto válido.")
                    else:
                        fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y")
                        hoja_facturas.append_row([fecha_actual, folio_seleccionado, num_factura.upper(), concepto_factura.upper(), monto_factura])
                        st.success(f"✅ Pago de ${monto_factura:,.2f} registrado con éxito.")
                        st.rerun()

        with c_tabla:
            st.subheader("📋 Historial de Pagos / Facturas Emitidas")
            if facturas_obra:
                df_facturas = pd.DataFrame(facturas_obra)[["Fecha", "Folio Factura", "Concepto", "Monto Facturado"]]
                df_facturas["Monto Facturado"] = df_facturas["Monto Facturado"].apply(lambda x: f"${limpiar_monto(x):,.2f}")
                st.dataframe(df_facturas, use_container_width=True, hide_index=True)
            else:
                st.info("Aún no has registrado pagos para este proyecto.")

        # --- GENERACIÓN DE PDF ESTADO DE CUENTA CLIENTE ---
        st.markdown("---")
        st.subheader("📄 Exportar Estado de Cuenta Final (Para el Cliente)")
        st.write("Genera el PDF oficial de Término de Obra con la plantilla corporativa.")
        
        if st.button("🖨️ GENERAR AVISO DE TÉRMINO Y SALDO PENDIENTE"):
            with st.spinner("Creando documento corporativo..."):
                pdf = PDF_EstadoCuenta()
                pdf.add_page()
                
                # Formato de Fecha en Español
                meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                hoy = datetime.datetime.now()
                fecha_espanol = f"{hoy.day:02d} de {meses[hoy.month]} de {hoy.year}"
                
                # Título Principal
                pdf.set_font('Arial', 'B', 12)
                pdf.set_text_color(50, 50, 50)
                pdf.cell(0, 6, "Aviso de Término de Obra y Saldo Pendiente", ln=True, align='C')
                pdf.ln(2)
                
                # Fecha
                pdf.set_font('Arial', 'I', 10)
                pdf.cell(0, 6, f"H. Veracruz, Ver a {fecha_espanol}.", ln=True, align='R')
                pdf.ln(6)
                
                # Destinatario
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 5, f"Ing. {nombre_cliente.title()}", ln=True)
                pdf.set_font('Arial', '', 10)
                pdf.cell(0, 5, "Presente.", ln=True)
                pdf.ln(4)
                
                # Asunto
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(0, 5, "Asunto: Aviso de término de obra y estado de cuenta final.", ln=True)
                pdf.ln(4)
                
                # Saludo a Empresa
                pdf.set_font('Arial', '', 10)
                saludo = "Estimado cliente." if not empresa_cliente else f"Estimada {empresa_cliente.title()}."
                pdf.write(5, saludo + "\n")
                pdf.ln(3)
                
                # Párrafo 1
                pdf.set_font('Arial', '', 10)
                pdf.write(5, "Por medio de la presente, nos complace informarle que los trabajos correspondientes al proyecto ")
                pdf.set_font('Arial', 'B', 10)
                pdf.write(5, f"{nombre_proyecto}")
                pdf.set_font('Arial', '', 10)
                pdf.write(5, ", ubicado en ")
                pdf.set_font('Arial', 'B', 10)
                pdf.write(5, f"{ubicacion_obra}")
                pdf.set_font('Arial', '', 10)
                pdf.write(5, f", han sido concluidos en su totalidad el pasado {hoy.strftime('%d/%m/%Y')}, cumpliendo con las especificaciones técnicas y estándares de calidad acordados.\n")
                pdf.ln(4)
                
                # Párrafo 2
                pdf.multi_cell(0, 5, "Con el objetivo de proceder a la entrega formal del inmueble y la firma del acta de recepción definitiva, nos permitimos presentarle el desglose del balance financiero final del proyecto:\n")
                pdf.ln(3)
                
                # Tabla
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(0, 6, "Resumen de Estado de Cuenta Final:", ln=True)
                
                pdf.set_fill_color(140, 140, 140)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(140, 7, "Concepto", border=1, align='C', fill=True)
                pdf.cell(50, 7, "Monto", border=1, align='C', fill=True, ln=True)
                
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(0, 0, 0)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(140, 7, "Costo Total del Proyecto:", border=1, align='R', fill=True)
                pdf.cell(50, 7, f"$ {presupuesto_total:,.2f}", border=1, align='R', fill=True, ln=True)
                
                pdf.set_font('Arial', '', 10)
                pdf.set_fill_color(255, 255, 255)
                pdf.cell(140, 7, "Total de Pagos / Anticipos Recibidos:", border=1, align='R', fill=True)
                pdf.cell(50, 7, f"$ {total_pagos_recibidos:,.2f}", border=1, align='R', fill=True, ln=True)
                
                pdf.set_font('Arial', 'B', 10)
                pdf.set_fill_color(225, 225, 225)
                pdf.cell(140, 7, "Saldo Pendiente por Liquidar:", border=1, align='R', fill=True)
                pdf.cell(50, 7, f"$ {saldo_pendiente:,.2f}", border=1, align='R', fill=True, ln=True)
                
                pdf.set_font('Arial', 'I', 9)
                pdf.cell(0, 6, "(Nota: Los montos anteriores ya incluyen IVA).", ln=True)
                pdf.ln(5)
                
                # Próximos Pasos
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(0, 6, "Próximos Pasos para la Entrega", ln=True, align='C')
                pdf.ln(2)
                
                pdf.set_font('Arial', '', 10)
                pdf.write(5, "Para realizar la entrega formal de la obra y la póliza de garantía correspondiente, le solicitamos amablemente realizar la liquidación del ")
                pdf.set_font('Arial', 'B', 10)
                pdf.write(5, f"saldo pendiente $ {saldo_pendiente:,.2f} ")
                pdf.set_font('Arial', '', 10)
                pdf.write(5, "mediante las opciones de pago habituales o transferencia a la siguiente cuenta:\n")
                pdf.ln(3)
                
                # Datos Bancarios
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(10)
                pdf.cell(0, 5, chr(149) + " Banco: BBVA.", ln=True)
                pdf.cell(10)
                pdf.cell(0, 5, chr(149) + " A nombre de: TARC, S.A. DE C.V.", ln=True)
                pdf.cell(10)
                pdf.cell(0, 5, chr(149) + " Cuenta: 450187690.", ln=True)
                pdf.cell(10)
                pdf.cell(0, 5, chr(149) + " Clabe interbancaria: 012905004501876903.", ln=True)
                pdf.ln(5)
                
                pdf.set_font('Arial', '', 10)
                pdf.write(5, "Una vez confirmado el pago, coordinaremos la cita para la inspección final en sitio y la firma del ")
                pdf.set_font('Arial', 'B', 10)
                pdf.write(5, "Acta de Entrega-Recepción.\n")
                pdf.ln(4)
                
                pdf.set_font('Arial', '', 10)
                pdf.multi_cell(0, 5, "Agradecemos de antemano su confianza en nuestros servicios y quedamos a su entera disposición para cualquier duda o aclaración respecto a este estado de cuenta.")
                pdf.ln(10)
                
                # Firmas
                pdf.cell(0, 5, "Atentamente,", ln=True)
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(0, 5, "TARC, S.A. DE C.V.", ln=True)
                pdf.cell(0, 5, "Departamento de Obras.", ln=True)
                pdf.set_font('Arial', '', 10)
                pdf.cell(0, 5, "Cel. 229 337 1080", ln=True)
                pdf.cell(0, 5, "rh@grupo-imac.com", ln=True)
                
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                
                st.download_button(
                    label="📥 DESCARGAR AVISO DE TÉRMINO (PDF CLIENTE)", 
                    data=pdf_bytes, 
                    file_name=f"Estado_Cuenta_{folio_seleccionado}.pdf", 
                    mime="application/pdf"
                )
