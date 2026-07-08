import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime
import pandas as pd
from fpdf import FPDF
import os

st.set_page_config(page_title="Facturación y Utilidad", page_icon="🧾", layout="wide")

# -----------------------------------------
# 🛡️ CANDADO DE SEGURIDAD POR ROLES
# -----------------------------------------
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ Acceso denegado. Inicia sesión en la página principal.")
    st.stop()

# Solo Dirección y Directivos deberían ver la Utilidad Real
ROLES_PERMITIDOS = ["Admin", "Directivo"]
if st.session_state.get("role") not in ROLES_PERMITIDOS:
    st.error(f"🚫 ACCESO RESTRINGIDO: Tu perfil de {st.session_state.get('role')} no tiene autorización para ver facturación y utilidades netas.")
    st.stop()

def limpiar_monto(valor):
    if str(valor).strip() == "" or valor is None: return 0.0
    try: return float(str(valor).replace("$", "").replace(",", "").replace(" ", "").strip())
    except: return 0.0

# --- CLASE PARA EL PDF DE FACTURACIÓN ---
class PDF_Facturas(FPDF):
    def header(self):
        if os.path.exists("logo_tarc.png"): self.image("logo_tarc.png", x=15, y=10, w=70)
        elif os.path.exists("logo_tarc.jpg"): self.image("logo_tarc.jpg", x=15, y=10, w=70)
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
        
        # ⚠️ REEMPLAZA CON TU ID DE EXCEL AQUÍ
        ID_DEL_EXCEL = "1-grdT2H5dBlGVPvJbZ5wVYDdtVjQEEmUPGpvEm6C0Gc" 
        return cliente.open_by_key(ID_DEL_EXCEL)
    except Exception: return None

st.title("🧾 Control de Facturación y Utilidad Real")
st.markdown("---")

doc = conectar_sheets()

if doc:
    try:
        hoja_obras = doc.worksheet("Obras_Activas")
        hoja_gastos = doc.worksheet("Gastos_Financieros")
        hoja_facturas = doc.worksheet("Facturas_Obras")
    except Exception as e:
        st.error("⚠️ Falta crear la pestaña 'Facturas_Obras' en tu Excel.")
        st.stop()

    datos_obras = hoja_obras.get_all_records()
    llave_folio = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "FOLIO" in str(k).upper()), None)
    obras_disponibles = [str(fila[llave_folio]) for fila in datos_obras if str(fila.get(llave_folio, "")) != ""] if llave_folio else []

    col_sel, _ = st.columns([1, 2])
    with col_sel:
        folio_seleccionado = st.selectbox("Selecciona la Obra a Evaluar:", ["Selecciona un folio..."] + obras_disponibles)

    if folio_seleccionado != "Selecciona un folio...":
        obra_info = next((f for f in datos_obras if str(f.get(llave_folio, "")) == folio_seleccionado), None)
        
        llave_monto = next((k for k in (obra_info.keys() if obra_info else []) if "PRESUPUESTO" in str(k).upper() or "AUTORIZADO" in str(k).upper() or "MONTO" in str(k).upper()), None)
        presupuesto_total = limpiar_monto(obra_info.get(llave_monto, 0)) if llave_monto else 0.0
        llave_proyecto = next((k for k in (obra_info.keys() if obra_info else []) if "PROYECTO" in str(k).upper() or "UBICACI" in str(k).upper()), None)
        proyecto_nombre = obra_info.get(llave_proyecto, "Proyecto Especificado") if llave_proyecto else "Proyecto Especificado"

        # 1. CÁLCULO DE GASTOS TOTALES (Incluye el 1% Administrativo)
        gasto_administrativo = presupuesto_total * 0.01
        datos_gastos = hoja_gastos.get_all_records()
        gastos_obra = [g for g in datos_gastos if str(g.get("Folio Obra", "")) == folio_seleccionado]
        suma_gastos_directos = sum(limpiar_monto(g.get("Monto ($)", 0)) for g in gastos_obra)
        total_gastos_reales = suma_gastos_directos + gasto_administrativo

        # 2. CÁLCULO DE FACTURACIÓN
        datos_facturas = hoja_facturas.get_all_records()
        facturas_obra = [f for f in datos_facturas if str(f.get("Folio Obra", "")) == folio_seleccionado]
        total_facturado = sum(limpiar_monto(f.get("Monto Facturado", 0)) for f in facturas_obra)

        # 3. UTILIDAD REAL
        utilidad_real = total_facturado - total_gastos_reales

        # --- PANTALLA PRINCIPAL ---
        st.subheader("📊 Balance de Utilidad Real (Ingresos vs Egresos)")
        m1, m2, m3 = st.columns(3)
        
        with m1:
            st.metric("Total Facturado (Ingresos)", f"${total_facturado:,.2f}")
        with m2:
            st.metric("Total Gastos (Operación + Adm)", f"${total_gastos_reales:,.2f}")
        with m3:
            if utilidad_real >= 0:
                st.metric("Utilidad Real Neta", f"${utilidad_real:,.2f}")
            else:
                st.metric("⚠️ Déficit / Pérdida", f"${utilidad_real:,.2f}")

        st.markdown("---")
        
        c_form, c_tabla = st.columns([1, 2])
        with c_form:
            st.subheader("📥 Agregar Nueva Factura")
            with st.form("form_facturas"):
                num_factura = st.text_input("Folio de la Factura", placeholder="Ej. FAC-1045")
                concepto_factura = st.text_input("Concepto Facturado", placeholder="Ej. Estimación 1 - Tablaroca")
                monto_factura = st.number_input("Monto Subtotal Facturado ($)", min_value=0.0, step=1000.0)
                
                btn_facturar = st.form_submit_button("🧾 REGISTRAR FACTURA")
                
                if btn_facturar:
                    if not num_factura or monto_factura <= 0:
                        st.warning("⚠️ Debes ingresar un folio de factura y un monto válido.")
                    else:
                        fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y")
                        hoja_facturas.append_row([fecha_actual, folio_seleccionado, num_factura.upper(), concepto_factura.upper(), monto_factura])
                        st.success(f"✅ Factura {num_factura.upper()} registrada por ${monto_factura:,.2f}")
                        st.rerun()

        with c_tabla:
            st.subheader("📋 Relación de Facturas Emitidas")
            if facturas_obra:
                df_facturas = pd.DataFrame(facturas_obra)[["Fecha", "Folio Factura", "Concepto", "Monto Facturado"]]
                df_facturas["Monto Facturado"] = df_facturas["Monto Facturado"].apply(lambda x: f"${limpiar_monto(x):,.2f}")
                st.dataframe(df_facturas, use_container_width=True, hide_index=True)
            else:
                st.info("Aún no has registrado facturas para este proyecto.")

        # --- GENERACIÓN DE PDF ---
        st.markdown("---")
        st.subheader("📄 Exportar Reporte de Utilidad")
        st.write("Genera un reporte PDF con la relación de facturas y la utilidad real de la obra. **El detalle de gastos operativos quedará oculto por seguridad.**")
        
        if st.button("🖨️ GENERAR PDF DE FACTURACIÓN Y UTILIDAD"):
            with st.spinner("Creando documento blindado..."):
                pdf = PDF_Facturas()
                pdf.add_page()
                
                # Título
                pdf.set_font('Arial', 'B', 14)
                pdf.set_text_color(15, 60, 140)
                pdf.cell(0, 10, f"REPORTE FINANCIERO DE FACTURACION", ln=True, align='C')
                pdf.set_font('Arial', 'B', 11)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 6, f"Folio de Proyecto: {folio_seleccionado}", ln=True, align='C')
                pdf.cell(0, 6, f"Proyecto: {str(proyecto_nombre).upper()}", ln=True, align='C')
                pdf.ln(10)
                
                # Tabla de Facturas
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(0, 0, 0)
                pdf.set_fill_color(220, 230, 245)
                pdf.cell(30, 8, "FECHA", border=1, fill=True, align='C')
                pdf.cell(35, 8, "FACTURA", border=1, fill=True, align='C')
                pdf.cell(85, 8, "CONCEPTO", border=1, fill=True, align='C')
                pdf.cell(40, 8, "MONTO ($)", border=1, fill=True, align='C')
                pdf.ln()
                
                pdf.set_font('Arial', '', 9)
                if facturas_obra:
                    for f in facturas_obra:
                        pdf.cell(30, 8, str(f.get("Fecha", "")), border=1, align='C')
                        pdf.cell(35, 8, str(f.get("Folio Factura", "")), border=1, align='C')
                        # Cortamos el concepto si es muy largo para que no rompa la tabla
                        concepto_str = str(f.get("Concepto", ""))
                        if len(concepto_str) > 42: concepto_str = concepto_str[:39] + "..."
                        pdf.cell(85, 8, concepto_str, border=1)
                        
                        monto_f = limpiar_monto(f.get("Monto Facturado", 0))
                        pdf.cell(40, 8, f"${monto_f:,.2f}", border=1, align='R')
                        pdf.ln()
                else:
                    pdf.cell(190, 8, "SIN FACTURAS REGISTRADAS", border=1, align='C')
                    pdf.ln()
                    
                # Resumen Financiero Ocultando Detalle de Gastos
                pdf.ln(15)
                pdf.set_font('Arial', 'B', 12)
                pdf.set_text_color(15, 60, 140)
                pdf.cell(0, 8, "RESUMEN DE UTILIDAD DEL PROYECTO", ln=True)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(2)
                
                pdf.set_font('Arial', 'B', 11)
                pdf.cell(140, 8, "TOTAL FACTURADO (INGRESOS):", border=0, align='R')
                pdf.cell(50, 8, f"${total_facturado:,.2f}", border=1, align='R')
                pdf.ln()
                
                pdf.cell(140, 8, "TOTAL EGRESOS (OPERATIVOS Y ADM):", border=0, align='R')
                pdf.set_text_color(200, 0, 0) # Rojo para gastos
                pdf.cell(50, 8, f"- ${total_gastos_reales:,.2f}", border=1, align='R')
                pdf.ln()
                
                # Color de Utilidad (Verde o Rojo)
                if utilidad_real >= 0:
                    pdf.set_text_color(0, 120, 0)
                    texto_utilidad = "UTILIDAD REAL NETA:"
                else:
                    pdf.set_text_color(200, 0, 0)
                    texto_utilidad = "DEFICIT / PERDIDA FINANCIERA:"
                    
                pdf.cell(140, 8, texto_utilidad, border=0, align='R')
                pdf.cell(50, 8, f"${utilidad_real:,.2f}", border=1, align='R')
                
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                
                st.download_button(
                    label="📥 DESCARGAR REPORTE DE FACTURACIÓN (PDF)", 
                    data=pdf_bytes, 
                    file_name=f"Utilidad_Real_{folio_seleccionado}.pdf", 
                    mime="application/pdf"
                )
