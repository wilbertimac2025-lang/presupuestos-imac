import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime
import pandas as pd

st.set_page_config(page_title="Panel Financiero", page_icon="💰", layout="wide")

def limpiar_monto(valor):
    """Función auxiliar para limpiar signos de pesos y comas del Excel"""
    if str(valor).strip() == "" or valor is None:
        return 0.0
    try:
        texto_limpio = str(valor).replace("$", "").replace(",", "").replace(" ", "").strip()
        return float(texto_limpio)
    except:
        return 0.0

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
    except Exception:
        return None

st.title("💰 Panel Financiero y Rentabilidad de Obras")
st.markdown("---")

doc = conectar_sheets()

if doc:
    try:
        hoja_obras = doc.worksheet("Obras_Activas")
        hoja_gastos = doc.worksheet("Gastos_Financieros")
    except Exception as e:
        st.error("⚠️ Falta crear la pestaña 'Gastos_Financieros' u 'Obras_Activas' en tu Excel.")
        st.stop()

    datos_obras = hoja_obras.get_all_records()
    
    llave_folio = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "FOLIO" in str(k).upper()), None)
    llave_estatus = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "ESTATUS" in str(k).upper()), None)
    
    obras_ejecucion = []
    if llave_folio and llave_estatus:
        obras_ejecucion = [str(fila[llave_folio]) for fila in datos_obras if str(fila.get(llave_estatus, "")).upper() == "EN EJECUCIÓN"]

    if not obras_ejecucion:
        st.info("No hay obras en ejecución en este momento. Registra una apertura primero.")
    else:
        col_sel, _ = st.columns([1, 2])
        with col_sel:
            folio_seleccionado = st.selectbox("Selecciona la Obra Financiera:", ["Selecciona un folio..."] + obras_ejecucion)

        if folio_seleccionado != "Selecciona un folio...":
            # Obtener datos de la obra seleccionada para el presupuesto base
            obra_info = next((f for f in datos_obras if str(f.get(llave_folio, "")) == folio_seleccionado), None)
            
            # Buscar la columna del presupuesto autorizado de forma inteligente
            llave_monto = next((k for k in (obra_info.keys() if obra_info else []) if "PRESUPUESTO" in str(k).upper() or "AUTORIZADO" in str(k).upper() or "MONTO" in str(k).upper()), None)
            
            presupuesto_total = limpiar_monto(obra_info.get(llave_monto, 0)) if llave_monto else 0.0

            # Cargar los gastos registrados hasta hoy en Excel
            datos_gastos = hoja_gastos.get_all_records()
            gastos_filtrados = [g for g in datos_gastos if str(g.get("Folio Obra", "")) == folio_seleccionado]
            
            total_gastado = sum(limpiar_monto(g.get("Monto ($)", 0)) for g in gastos_filtrados)
            utilidad_disponible = presupuesto_total - total_gastado

            # ==========================================
            # VOLANTE DE INDICADORES (TARJETAS EN VIVO)
            # ==========================================
            st.subheader("📊 Estado de Cuenta del Proyecto")
            m1, m2, m3 = st.columns(3)
            
            with m1:
                st.metric(label="Presupuesto Cobrado (Ingreso)", value=f"${presupuesto_total:,.2f} MXN")
            with m2:
                st.metric(label="Total Gastado Operativo", value=f"${total_gastado:,.2f} MXN", delta=f"${total_gastado:,.2f}", delta_color="inverse")
            with m3:
                if utilidad_disponible >= 0:
                    st.metric(label="Margen / Utilidad Disponible", value=f"${utilidad_disponible:,.2f} MXN")
                else:
                    st.metric(label="⚠️ DÉFICIT / PÉRDIDA", value=f"${utilidad_disponible:,.2f} MXN", delta="¡Presupuesto rebasado!", delta_color="normal")

            # Barra visual de progreso financiero
            if presupuesto_total > 0:
                porcentaje_gastado = min(total_gastado / presupuesto_total, 1.0)
                st.write(f"**Uso del presupuesto autorizado ({porcentaje_gastado*100:.1f}%)**")
                st.progress(porcentaje_gastado)

            st.markdown("---")
            
            # Division de pantallas: Formulario a la izquierda, Historial a la derecha
            c_form, c_tabla = st.columns([1, 2])
            
            with c_form:
                st.subheader("📥 Registrar Nuevo Gasto")
                with st.form("form_gastos_fin"):
                    concepto = st.text_input("Concepto / Descripción del Gasto", placeholder="Ej. Pago de raya Semana 22")
                    categoria_gasto = st.selectbox("Categoría de Cuenta", ["Mano de Obra / Destajos", "Viáticos y Comidas", "Gasolina y Fletes", "Herramientas y Equipos", "Otros Gastos Extras"])
                    monto_gasto = st.number_input("Monto en Pesos ($ MXN)", min_value=0.0, step=50.0)
                    
                    btn_gasto = st.form_submit_button("💰 INYECTAR GASTO A LA OBRA")
                    
                    if btn_gasto:
                        if not concepto:
                            st.warning("Escribe un concepto para justificar el gasto.")
                        elif monto_gasto <= 0:
                            st.warning("El monto debe ser mayor a $0.00")
                        else:
                            fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y")
                            hoja_gastos.append_row([
                                fecha_actual,
                                folio_seleccionado,
                                concepto.upper(),
                                categoria_gasto,
                                monto_gasto
                            ])
                            st.success(f"✅ Gasto de ${monto_gasto:,.2f} registrado con éxito.")
                            st.rerun()

            with c_tabla:
                st.subheader("📋 Historial Desglosado de Egresos")
                if not gastos_filtrados:
                    st.info("No se han registrado egresos o gastos administrativos en esta obra todavía.")
                else:
                    df = pd.DataFrame(gastos_filtrados)
                    # Formatear la tabla visual para que se vea premium
                    df_mostrar = df[["Fecha", "Concepto", "Categoría", "Monto ($)"]].copy()
                    st.dataframe(df_mostrar, use_container_width=True)
