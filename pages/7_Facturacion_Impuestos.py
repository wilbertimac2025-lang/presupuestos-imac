import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime
import pandas as pd
from fpdf import FPDF
import os
import smtplib
from email.message import EmailMessage

st.set_page_config(page_title="Facturación y Estados de Cuenta", page_icon="🧾", layout="wide")

# -----------------------------------------
# 🛡️ CANDADO DE SEGURIDAD POR ROLES
# -----------------------------------------
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ Acceso denegado. Inicia sesión en la página principal.")
    st.stop()

ROLES_PERMITIDOS = ["Admin", "Directivo", "RRHH", "Operativo"]
if st.session_state.get("role") not in ROLES_PERMITIDOS:
    st.error("🚫 ACCESO RESTRINGIDO: Tu perfil no tiene autorización para ver estados de cuenta.")
    st.stop()

# 🕵️ FUNCIÓN DE BITÁCORA SILENCIOSA
def registrar_bitacora(doc, modulo, accion):
    try:
        hoja_bitacora = doc.worksheet("Bitacora_Movimientos")
        fecha_hora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        usuario = st.session_state.get("usuario", st.session_state.get("username", "Usuario Sistema"))
        rol = st.session_state.get("role", "Desconocido")
        hoja_bitacora.append_row([fecha_hora, usuario, rol, modulo, accion])
    except Exception:
        pass 

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

# --- CLASE PARA EL PDF ESTADO DE CUENTA (UN SOLO CLIENTE) ---
class PDF_EstadoCuenta(FPDF):
    def header(self):
        self.set_xy(15, 10)
        self.set_font('Arial', 'B', 20)
        self.set_text_color(15, 60, 140) 
        self.cell(0, 8, 'TARC, S.A. DE C.V.', ln=True, align='C')
        
        self.set_xy(15, 18)
        self.set_font('Arial', '', 9)
        self.set_text_color(80, 80, 80) 
        self.cell(0, 5, 'BLVD. MIGUEL ALEMAN No. 306 TEL.: 986-35-72 BOCA DEL RIO, VER.', ln=True, align='C')
        
        self.set_draw_color(15, 60, 140)
        self.set_line_width(0.4)
        self.line(15, 25, 195, 25)
        self.line(15, 26, 195, 26)
        self.set_y(32)

# --- NUEVA CLASE PARA EL PDF REPORTE GLOBAL DE COBRANZA ---
class PDF_ReporteGlobal(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.set_text_color(15, 60, 140)
        self.cell(0, 8, 'TARC, S.A. DE C.V.', ln=True, align='C')
        
        self.set_font('Arial', 'B', 10)
        self.set_text_color(80, 80, 80)
        self.cell(0, 5, 'REPORTE GLOBAL DE COBRANZA Y SALDOS PENDIENTES', ln=True, align='C')
        
        # --- SECCIÓN NUEVA: LA FECHA EXACTA DEL REPORTE ---
        meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        hoy = datetime.datetime.now()
        fecha_espanol = f"{hoy.day:02d} de {meses[hoy.month]} de {hoy.year}"
        
        self.set_font('Arial', 'I', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f'Fecha de Emisión: {fecha_espanol}', ln=True, align='C')
        self.ln(5) # Espacio antes de la tabla
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Página {self.page_no()}', align='C')

@st.cache_resource
def conectar_sheets():
    try:
        credenciales_dic = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(credenciales_dic, scopes=scopes)
        cliente = gspread.authorize(creds)
        
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
        hoja_presupuestos = doc.worksheet("Presupuestos")
    except Exception as e:
        st.error("⚠️ Faltan pestañas en tu Excel (Obras_Activas, Facturas_Obras o Presupuestos).")
        st.stop()

    datos_obras = hoja_obras.get_all_records()
    datos_presupuestos = hoja_presupuestos.get_all_records()
    
    llave_folio = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "FOLIO" in str(k).upper()), None)
    obras_disponibles = [str(fila[llave_folio]) for fila in datos_obras if str(fila.get(llave_folio, "")) != ""] if llave_folio else []

    # Diccionario para extraer los nombres de las obras para el reporte
    nombres_obras_dict = {}
    if llave_folio:
        for fila in datos_obras:
            folio_actual = str(fila.get(llave_folio, "")).strip()
            if folio_actual:
                nombres_obras_dict[folio_actual] = obtener_valor(fila, ["PROYECTO", "OBRA", "CONCEPTO"], "Proyecto sin nombre")

    col_sel, _ = st.columns([1, 2])
    with col_sel:
        folio_seleccionado = st.selectbox("Selecciona la Obra a Facturar/Cobrar:", ["Selecciona un folio..."] + obras_disponibles)

    if folio_seleccionado != "Selecciona un folio...":
        
        obra_activa = next((f for f in datos_obras if str(f.get(llave_folio, "")) == folio_seleccionado), {})
        obra_presupuesto = next((f for f in datos_presupuestos if str(obtener_valor(f, ["FOLIO"])).upper() == folio_seleccionado.upper()), {})
        
        datos_completos = {**obra_activa, **obra_presupuesto}
        
        nombre_cliente = obtener_valor(datos_completos, ["CLIENTE", "NOMBRE CLIENTE"], "Cliente Genérico")
        empresa_cliente = obtener_valor(datos_completos, ["EMPRESA", "RAZON SOCIAL", "COMPAÑIA"], "")
        nombre_proyecto = obtener_valor(datos_completos, ["PROYECTO", "OBRA", "CONCEPTO"], "Proyecto en ejecución")
        ubicacion_obra = obtener_valor(datos_completos, ["UBICACION", "DIRECCION", "LUGAR"], "Ubicación Registrada")
        
        presupuesto_total = limpiar_monto(obtener_valor(datos_completos, ["MONTO", "PRESUPUESTO", "AUTORIZADO", "TOTAL"], 0))

        datos_facturas = hoja_facturas.get_all_records()
        facturas_obra = [f for f in datos_facturas if str(f.get("Folio Obra", "")) == folio_seleccionado]
        total_pagos_recibidos = sum(limpiar_monto(f.get("Monto Facturado", 0)) for f in facturas_obra)

        saldo_pendiente = presupuesto_total - total_pagos_recibidos

        # --- PANTALLA PRINCIPAL DE STREAMLIT ---
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
                        
                        registrar_bitacora(doc, "Facturación e Impuestos", f"Cobró/Registró pago de ${monto_factura:,.2f} al folio {folio_seleccionado}. Recibo: {num_factura.upper()}")
                        
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

        # --- GENERACIÓN DE PDF ESTADO DE CUENTA (CLIENTE) ---
        st.markdown("---")
        st.subheader("📄 Exportar Estado de Cuenta Final (Para el Cliente)")
        st.write("Genera el PDF oficial de Término de Obra optimizado para encajar en una sola hoja.")
        
        if st.button("🖨️ GENERAR AVISO DE TÉRMINO EN UNA HOJA"):
            with st.spinner("Creando documento estilizado en azul..."):
                
                registrar_bitacora(doc, "Facturación e Impuestos", f"Generó PDF de Estado de Cuenta Final para el folio {folio_seleccionado}")
                
                pdf = PDF_EstadoCuenta()
                pdf.add_page()
                
                meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                hoy = datetime.datetime.now()
                fecha_espanol = f"{hoy.day:02d} de {meses[hoy.month]} de {hoy.year}"
                
                pdf.set_font('Arial', 'B', 12)
                pdf.set_text_color(15, 60, 140)
                pdf.cell(0, 5, "Aviso de Término de Obra y Saldo Pendiente", ln=True, align='C')
                pdf.ln(1)
                
                pdf.set_font('Arial', 'I', 9)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 4, f"H. Veracruz, Ver a {fecha_espanol}.", ln=True, align='R')
                pdf.ln(3)
                
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 4, f"Ing. {nombre_cliente.title()}", ln=True)
                pdf.set_font('Arial', '', 10)
                pdf.cell(0, 4, "Presente.", ln=True)
                pdf.ln(2)
                
                pdf.set_font('Arial', 'B', 10)
                pdf.write(4, "Asunto: ")
                pdf.set_font('Arial', '', 10)
                pdf.write(4, "Aviso de término de obra y estado de cuenta final.\n")
                pdf.ln(2)
                
                pdf.set_font('Arial', '', 10)
                saludo = "Estimado cliente." if not empresa_cliente else f"Estimada {empresa_cliente.title()}."
                pdf.write(4, saludo + "\n")
                pdf.ln(2)
                
                pdf.set_font('Arial', '', 10)
                pdf.write(4.2, "Por medio de la presente, nos complace informarle que los trabajos correspondientes al proyecto ")
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(15, 60, 140) 
                pdf.write(4.2, f"{nombre_proyecto}")
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Arial', '', 10)
                pdf.write(4.2, ", ubicado en ")
                pdf.set_font('Arial', 'B', 10)
                pdf.write(4.2, f"{ubicacion_obra}")
                pdf.set_font('Arial', '', 10)
                pdf.write(4.2, f", han sido concluidos en su totalidad el pasado {hoy.strftime('%d/%m/%Y')}, cumpliendo con las especificaciones técnicas y estándares de calidad acordados.\n")
                pdf.ln(2)
                
                pdf.multi_cell(0, 4.2, "Con el objetivo de proceder a la entrega formal del inmueble y la firma del acta de recepción definitiva, nos permitimos presentarle el desglose del balance financiero final del proyecto:\n")
                pdf.ln(2)
                
                pdf.set_font('Arial', 'B', 9)
                pdf.set_text_color(15, 60, 140)
                pdf.cell(0, 5, "Resumen de Estado de Cuenta Final:", ln=True)
                
                pdf.set_fill_color(15, 60, 140)
                pdf.set_text_color(255, 255, 255)
                pdf.set_draw_color(15, 60, 140)
                pdf.cell(140, 6, "Concepto", border=1, align='C', fill=True)
                pdf.cell(50, 6, "Monto", border=1, align='C', fill=True, ln=True)
                
                pdf.set_font('Arial', 'B', 9)
                pdf.set_text_color(0, 0, 0)
                pdf.set_fill_color(240, 245, 255)
                pdf.cell(140, 6, "Costo Total del Proyecto:", border=1, align='R', fill=True)
                pdf.cell(50, 6, f"$ {presupuesto_total:,.2f}", border=1, align='R', fill=True, ln=True)
                
                pdf.set_font('Arial', '', 9)
                pdf.set_fill_color(255, 255, 255)
                pdf.cell(140, 6, "Total de Pagos / Anticipos Recibidos:", border=1, align='R', fill=True)
                pdf.cell(50, 6, f"$ {total_pagos_recibidos:,.2f}", border=1, align='R', fill=True, ln=True)
                
                pdf.set_font('Arial', 'B', 9)
                pdf.set_fill_color(200, 220, 255)
                pdf.cell(140, 6, "Saldo Pendiente por Liquidar:", border=1, align='R', fill=True)
                pdf.set_text_color(15, 60, 140) 
                pdf.cell(50, 6, f"$ {saldo_pendiente:,.2f}", border=1, align='R', fill=True, ln=True)
                
                pdf.set_font('Arial', 'I', 8.5)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 4, "(Nota: Los montos anteriores ya incluyen IVA).", ln=True)
                pdf.ln(3)
                
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(15, 60, 140)
                pdf.cell(0, 5, "Próximos Pasos para la Entrega", ln=True, align='C')
                pdf.ln(1)
                
                pdf.set_font('Arial', '', 10)
                pdf.set_text_color(0, 0, 0)
                pdf.write(4.2, "Para realizar la entrega formal de la obra y la póliza de garantía correspondiente, le solicitamos amablemente realizar la liquidación del ")
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(15, 60, 140)
                pdf.write(4.2, f"saldo pendiente $ {saldo_pendiente:,.2f} ")
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Arial', '', 10)
                pdf.write(4.2, "mediante las opciones de pago habituales o transferencia a la siguiente cuenta:\n")
                pdf.ln(1.5)
                
                pdf.set_font('Arial', '', 9.5)
                pdf.cell(10)
                pdf.write(4.5, "  -  Banco: ")
                pdf.set_font('Arial', 'B', 9.5); pdf.write(4.5, "BBVA.\n"); pdf.set_font('Arial', '', 9.5); pdf.cell(10)
                pdf.write(4.5, "  -  A nombre de: ")
                pdf.set_font('Arial', 'B', 9.5); pdf.write(4.5, "TARC, S.A. DE C.V.\n"); pdf.set_font('Arial', '', 9.5); pdf.cell(10)
                pdf.write(4.5, "  -  Cuenta: ")
                pdf.set_font('Arial', 'B', 9.5); pdf.write(4.5, "450187690.\n"); pdf.set_font('Arial', '', 9.5); pdf.cell(10)
                pdf.write(4.5, "  -  Clabe interbancaria: ")
                pdf.set_font('Arial', 'B', 9.5); pdf.write(4.5, "012905004501876903.\n")
                pdf.ln(2.5)
                
                pdf.set_font('Arial', '', 10)
                pdf.write(4.2, "Una vez confirmado el pago, coordinaremos la cita para la inspección final en sitio y la firma del ")
                pdf.set_font('Arial', 'B', 10)
                pdf.write(4.2, "Acta de Entrega-Recepción.\n")
                pdf.ln(1.5)
                
                pdf.multi_cell(0, 4.2, "Agradecemos de antemano su confianza en nuestros servicios y quedamos a su entera disposición para cualquier duda o aclaración respecto a este estado de cuenta.")
                pdf.ln(5)
                
                pdf.set_font('Arial', '', 9.5)
                pdf.cell(0, 4, "Atentamente,", ln=True)
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(15, 60, 140)
                pdf.cell(0, 4.5, "TARC, S.A. DE C.V.", ln=True)
                pdf.cell(0, 4.5, "Departamento de Obras.", ln=True)
                pdf.set_font('Arial', '', 9)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 4, "Cel. 229 337 1080  |  rh@grupo-imac.com", ln=True)
                
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                
                st.download_button(
                    label="📥 DESCARGAR AVISO DE TÉRMINO (PDF CLIENTE)", 
                    data=pdf_bytes, 
                    file_name=f"Estado_Cuenta_{folio_seleccionado}.pdf", 
                    mime="application/pdf"
                )

# -----------------------------------------------------------------
# 📬 MÓDULO DE ENVÍO DE REPORTE DE COBRANZA (AHORA CON PDF ADJUNTO)
# -----------------------------------------------------------------
st.markdown("---")
st.subheader("📬 Reporte Global de Cobranza (Dirección)")
st.write("Genera el PDF con la tabla oficial de obras y envíalo automáticamente por correo a dirección.")

if st.button("🚀 Generar PDF y Enviar por Correo"):
    with st.spinner("Calculando saldos, dibujando tabla PDF y armando el correo..."):
        try:
            hoja_presup = doc.worksheet("Presupuestos")
            hoja_fact = doc.worksheet("Facturas_Obras")
            
            filas_presup = hoja_presup.get_all_records()
            filas_fact = hoja_fact.get_all_records()
            
            # Extraemos costo total
            obras_totales = {}
            for fila in filas_presup:
                claves = list(fila.keys())
                if claves:
                    folio = str(fila.get(claves[0], "")).strip()
                    total = 0.0
                    for k, v in fila.items():
                        if "TOTAL" in str(k).upper() or "INVERSIÓN" in str(k).upper():
                            try: total = float(str(v).replace("$", "").replace(",", "").strip())
                            except: pass
                    if folio: obras_totales[folio] = total

            # Sumamos lo pagado
            obras_pagadas = {}
            for fila in filas_fact:
                folio_obra = str(fila.get("Folio Obra", "")).strip()
                monto = 0.0
                try: monto = float(str(fila.get("Monto Facturado", 0)).replace("$", "").replace(",", "").strip())
                except: pass
                if folio_obra: obras_pagadas[folio_obra] = obras_pagadas.get(folio_obra, 0.0) + monto

            # Filtramos solo las que tienen deuda y preparamos datos para la tabla
            lista_reporte = []
            gran_total_costo = 0.0
            gran_total_pagado = 0.0
            gran_total_pendiente = 0.0

            for folio, costo_total in obras_totales.items():
                pagado = obras_pagadas.get(folio, 0.0)
                saldo_pendiente = costo_total - pagado
                
                if saldo_pendiente > 0: 
                    gran_total_costo += costo_total
                    gran_total_pagado += pagado
                    gran_total_pendiente += saldo_pendiente
                    
                    nombre_obra = nombres_obras_dict.get(folio, "Proyecto sin nombre")
                    
                    lista_reporte.append({
                        "folio": folio,
                        "nombre": nombre_obra,
                        "costo": costo_total,
                        "pagado": pagado,
                        "saldo": saldo_pendiente
                    })

            if not lista_reporte:
                st.info("¡Excelente noticia equipo! No hay saldos pendientes por cobrar en este momento.")
            else:
                # --- CREACIÓN DEL PDF ---
                pdf = PDF_ReporteGlobal()
                pdf.add_page()
                
                # Encabezados de Tabla en Azul Fuerte
                pdf.set_fill_color(15, 60, 140)
                pdf.set_text_color(255, 255, 255)
                pdf.set_draw_color(15, 60, 140)
                pdf.set_font('Arial', 'B', 8)
                
                # Ancho total: 190mm (Encaja perfecto en hoja A4)
                pdf.cell(25, 8, "FOLIO", border=1, align='C', fill=True)
                pdf.cell(75, 8, "NOMBRE DE LA OBRA", border=1, align='C', fill=True)
                pdf.cell(30, 8, "PRESUPUESTO", border=1, align='C', fill=True)
                pdf.cell(30, 8, "PAGADO", border=1, align='C', fill=True)
                pdf.cell(30, 8, "POR COBRAR", border=1, align='C', fill=True)
                pdf.ln()
                
                # Filas de la tabla
                pdf.set_font('Arial', '', 7)
                fill = False
                for item in lista_reporte:
                    pdf.set_fill_color(240, 245, 255) if fill else pdf.set_fill_color(255, 255, 255)
                    pdf.set_text_color(0, 0, 0)
                    
                    pdf.cell(25, 6, str(item['folio']), border=1, align='C', fill=fill)
                    
                    # Recortamos el nombre si es muy largo para que no rompa la tabla
                    nombre_corto = (item['nombre'][:45] + '..') if len(item['nombre']) > 45 else item['nombre']
                    pdf.cell(75, 6, str(nombre_corto), border=1, align='L', fill=fill)
                    
                    pdf.cell(30, 6, f"${item['costo']:,.2f}", border=1, align='R', fill=fill)
                    pdf.cell(30, 6, f"${item['pagado']:,.2f}", border=1, align='R', fill=fill)
                    
                    # Resaltar en rojo el saldo pendiente
                    pdf.set_text_color(200, 0, 0)
                    pdf.set_font('Arial', 'B', 7)
                    pdf.cell(30, 6, f"${item['saldo']:,.2f}", border=1, align='R', fill=fill)
                    pdf.set_font('Arial', '', 7)
                    
                    pdf.ln()
                    fill = not fill
                    
                # Fila de TOTALES GLOBALES
                pdf.set_font('Arial', 'B', 8)
                pdf.set_fill_color(15, 60, 140)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(100, 8, "TOTALES GLOBALES DE CARTERA", border=1, align='R', fill=True)
                pdf.cell(30, 8, f"${gran_total_costo:,.2f}", border=1, align='R', fill=True)
                pdf.cell(30, 8, f"${gran_total_pagado:,.2f}", border=1, align='R', fill=True)
                pdf.cell(30, 8, f"${gran_total_pendiente:,.2f}", border=1, align='R', fill=True)
                pdf.ln()
                
                # --- PREPARACIÓN DEL CORREO ---
                cuerpo_mensaje = (
                    "Estimado equipo directivo y comercial,\n\n"
                    "Adjunto a este correo encontrarán el reporte oficial de cobranza en formato PDF.\n\n"
                    "Este documento detalla el estado financiero de cada proyecto activo, "
                    "indicando el presupuesto total, los anticipos recibidos y los saldos pendientes por liquidar.\n\n"
                    f"💰 SALDO GLOBAL PENDIENTE EN LA CALLE: ${gran_total_pendiente:,.2f} MXN\n\n"
                    "Por favor dar seguimiento con los clientes correspondientes.\n\n"
                    "Atentamente,\nERP Comercial - Grupo IMAC"
                )

                remitente = st.secrets["CORREO_BOT"] 
                password = st.secrets["PASS_BOT"]              
                
                destinatarios = [
                    "comercial@grupo-imac.com",
                    "ejemplo1@grupo-imac.com",
                    "ejemplo2@grupo-imac.com",
                    "ejemplo3@grupo-imac.com"
                ]

                msg = EmailMessage()
                fecha_str = datetime.datetime.now().strftime("%d/%m/%Y")
                msg['Subject'] = f'📊 REPORTE GLOBAL DE COBRANZA (PDF) - ({fecha_str})'
                msg['From'] = remitente
                msg['To'] = ", ".join(destinatarios)
                msg.set_content(cuerpo_mensaje)
                
                # Generar los bytes del PDF y adjuntarlo
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=f'Reporte_Cobranza_IMAC.pdf')

                with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
                    smtp.starttls()
                    smtp.login(remitente, password)
                    smtp.send_message(msg)
                    
                st.success("✅ ¡El PDF con la tabla oficial y la fecha de hoy fue generado y enviado con éxito a los correos!")
                st.balloons() 
                
        except Exception as e:
            st.error(f"❌ Ocurrió un error al enviar el correo: {e}")
