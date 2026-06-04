import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime
import pandas as pd

st.set_page_config(page_title="Panel Financiero", page_icon="💰", layout="wide")

def limpiar_monto(valor):
    if str(valor).strip() == "" or valor is None: return 0.0
    try: return float(str(valor).replace("$", "").replace(",", "").replace(" ", "").strip())
    except: return 0.0

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

st.title("💰 Panel Financiero y Rentabilidad de Obras")
st.markdown("---")

doc = conectar_sheets()

if doc:
    try:
        hoja_obras = doc.worksheet("Obras_Activas")
        hoja_gastos = doc.worksheet("Gastos_Financieros")
    except Exception as e:
        st.error("⚠️ Faltan pestañas en tu Excel.")
        st.stop()

    datos_obras = hoja_obras.get_all_records()
    
    llave_folio = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "FOLIO" in str(k).upper()), None)
    llave_estatus = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "ESTATUS" in str(k).upper()), None)
    
    obras_ejecucion = []
    if llave_folio and llave_estatus:
        obras_ejecucion = [str(fila[llave_folio]) for fila in datos_obras if str(fila.get(llave_estatus, "")).upper() == "EN EJECUCIÓN"]

    if not obras_ejecucion:
        st.info("No hay obras en ejecución en este momento.")
    else:
        col_sel, _ = st.columns([1, 2])
        with col_sel:
            folio_seleccionado = st.selectbox("Selecciona la Obra Financiera:", ["Selecciona un folio..."] + obras_ejecucion)

        if folio_seleccionado != "Selecciona un folio...":
            obra_info = next((f for f in datos_obras if str(f.get(llave_folio, "")) == folio_seleccionado), None)
            llave_monto = next((k for k in (obra_info.keys() if obra_info else []) if "PRESUPUESTO" in str(k).upper() or "AUTORIZADO" in str(k).upper() or "MONTO" in str(k).upper()), None)
            presupuesto_total = limpiar_monto(obra_info.get(llave_monto, 0)) if llave_monto else 0.0

            datos_gastos = hoja_gastos.get_all_records()
            gastos_filtrados = [g for g in datos_gastos if str(g.get("Folio Obra", "")) == folio_seleccionado]
            
            # 🔍 EL NUEVO FILTRO FINANCIERO: Separar Materiales de otros gastos
            costo_materiales = sum(limpiar_monto(g.get("Monto ($)", 0)) for g in gastos_filtrados if str(g.get("Categoría", "")).upper() == "COSTO DE MATERIAL")
            gastos_operativos = sum(limpiar_monto(g.get("Monto ($)", 0)) for g in gastos_filtrados if str(g.get("Categoría", "")).upper() != "COSTO DE MATERIAL")
            
            total_gastado = costo_materiales + gastos_operativos
            utilidad_disponible = presupuesto_total - total_gastado

            # ==========================================
            # NUEVAS TARJETAS DE INDICADORES (CON COSTO DE MATERIAL)
            # ==========================================
            st.subheader("📊 Estado de Cuenta del Proyecto")
            m1, m2, m3, m4 = st.columns(4)
            
            with m1:
                st.metric("Presupuesto Cobrado", f"${presupuesto_total:,.2f}")
            with m2:
                st.metric("Costo de Material", f"${costo_materiales:,.2f}", delta="- Salidas de Almacén", delta_color="normal")
            with m3:
                st.metric("Gasto Operativo", f"${gastos_operativos:,.2f}", delta="- Nóminas/Viáticos", delta_color="normal")
            with m4:
                if utilidad_disponible >= 0:
                    st.metric("Utilidad / Ganancia Libre", f"${utilidad_disponible:,.2f}")
                else:
                    st.metric("⚠️ DÉFICIT / PÉRDIDA", f"${utilidad_disponible:,.2f}")

            if presupuesto_total > 0:
                porcentaje_gastado = min(total_gastado / presupuesto_total, 1.0)
                st.progress(porcentaje_gastado)

            st.markdown("---")
            c_form, c_tabla = st.columns([1, 2])
            
            with c_form:
                st.subheader("📥 Registrar Nuevo Gasto")
                with st.form("form_gastos_fin"):
                    concepto = st.text_input("Concepto", placeholder="Ej. Pago de raya Semana 22")
                    # Quitamos costo de material de aquí porque se hace automático desde el almacén
                    categoria_gasto = st.selectbox("Categoría de Cuenta", ["Mano de Obra / Destajos", "Viáticos y Comidas", "Gasolina y Fletes", "Herramientas y Equipos", "Otros Gastos Extras"])
                    monto_gasto = st.number_input("Monto en Pesos ($ MXN)", min_value=0.0, step=50.0)
                    
                    btn_gasto = st.form_submit_button("💰 INYECTAR GASTO")
                    
                    if btn_gasto:
                        if monto_gasto > 0:
                            fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y")
                            hoja_gastos.append_row([fecha_actual, folio_seleccionado, concepto.upper(), categoria_gasto, monto_gasto])
                            st.success(f"✅ Gasto de ${monto_gasto:,.2f} registrado.")
                            st.rerun()

            with c_tabla:
                st.subheader("📋 Historial Desglosado")
                if gastos_filtrados:
                    df = pd.DataFrame(gastos_filtrados)[["Fecha", "Concepto", "Categoría", "Monto ($)"]]
                    st.dataframe(df, use_container_width=True)
