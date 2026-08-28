import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime
import pandas as pd
import os

# --- CONFIGURACIÓN CORPORATIVA ---
icono_navegador = "logo_imac_2026.png" if os.path.exists("logo_imac_2026.png") else ("logo_tarc.png" if os.path.exists("logo_tarc.png") else "🏢")
st.set_page_config(page_title="Panel Financiero", page_icon=icono_navegador, layout="wide")

# -----------------------------------------
# 🛡️ CANDADO DE SEGURIDAD POR ROLES
# -----------------------------------------
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ Acceso denegado. Inicia sesión en la página principal.")
    st.stop()

ROLES_PERMITIDOS = ["Admin", "RRHH", "Auxiliar", "Operativo"]
if st.session_state.get("role") not in ROLES_PERMITIDOS:
    st.error(f"🚫 ACCESO RESTRINGIDO: Tu perfil de {st.session_state.get('role')} no tiene autorización para este módulo.")
    st.stop()

# 🕵️ FUNCIÓN DE BITÁCORA SILENCIOSA
def registrar_bitacora(doc, modulo, accion):
    try:
        if doc:
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

def obtener_valor(diccionario, palabras_clave, default=0.0):
    for k, v in diccionario.items():
        if any(p in str(k).upper() for p in palabras_clave):
            if str(v).strip() != "":
                return v
    return default

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

# --- ENCABEZADO OFICIAL ---
col_logo, col_tit = st.columns([1, 5])
with col_logo:
    if os.path.exists("logo_imac_2026.png"):
        st.image("logo_imac_2026.png", use_container_width=True)
    elif os.path.exists("logo_tarc.png"):
        st.image("logo_tarc.png", use_container_width=True)
    elif os.path.exists("logo_tarc.jpg"):
        st.image("logo_tarc.jpg", use_container_width=True)
with col_tit:
    st.title("Panel Financiero y Rentabilidad de Obras")
st.markdown("---")

doc = conectar_sheets()

if doc:
    try:
        hoja_obras = doc.worksheet("Obras_Activas")
        hoja_gastos = doc.worksheet("Gastos_Financieros")
        hoja_presupuestos = doc.worksheet("Presupuestos") 
    except Exception as e:
        st.error("⚠️ Faltan pestañas en tu Excel.")
        st.stop()

    datos_obras = hoja_obras.get_all_records()
    datos_presupuestos = hoja_presupuestos.get_all_records()
    
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
            
            obra_activa = next((f for f in datos_obras if str(f.get(llave_folio, "")) == folio_seleccionado), {})
            obra_presupuesto = next((f for f in datos_presupuestos if str(obtener_valor(f, ["FOLIO"], "")).upper() == folio_seleccionado.upper()), {})
            
            datos_completos = {**obra_activa, **obra_presupuesto}
            
            valor_monto = obtener_valor(datos_completos, ["TOTAL", "MONTO", "PRESUPUESTO", "AUTORIZADO"], 0.0)
            presupuesto_total = limpiar_monto(valor_monto)

            gasto_financiamiento = presupuesto_total * 0.01
            gasto_administrativo = presupuesto_total * 0.10
            costo_imss = (presupuesto_total * 0.18) * 0.35

            datos_gastos = hoja_gastos.get_all_records()
            gastos_filtrados = [g for g in datos_gastos if str(g.get("Folio Obra", "")) == folio_seleccionado]
            
            costo_materiales = 0.0
            costo_nomina = 0.0
            gastos_operativos = 0.0
            
            for g in gastos_filtrados:
                monto = limpiar_monto(g.get("Monto ($)", 0))
                categoria = str(g.get("Categoría", "")).upper().strip()
                
                if categoria == "NÓMINA":
                    costo_nomina += monto
                elif categoria == "COSTO DE MATERIAL":
                    costo_materiales += monto
                elif categoria == "FSR":
                    pass 
                else:
                    gastos_operativos += monto
            
            total_gastado = costo_materiales + costo_nomina + costo_imss + gastos_operativos + gasto_financiamiento + gasto_administrativo

            # 🚀 LECTURA DE LA BOLSA DE MANO DE OBRA
            bolsa_mano_obra = limpiar_monto(obtener_valor(datos_completos, ["BOLSA MANO DE OBRA", "BOLSA", "DESTAJO"], 0.0))
            saldo_mano_obra = bolsa_mano_obra - costo_nomina

            st.subheader("📊 Estado de Cuenta del Proyecto")
            
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Presupuesto Total", f"${presupuesto_total:,.2f}")
            with m2:
                st.metric("Costo Material", f"${costo_materiales:,.2f}")
            with m3:
                st.metric("Gastos Operativos", f"${gastos_operativos:,.2f}")

            st.write("") 

            m4, m5, m6 = st.columns(3)
            with m4:
                st.metric("Costos IMSS y Prest. Sociales", f"${costo_imss:,.2f}")
            with m5:
                st.metric("Financiamiento (1%)", f"${gasto_financiamiento:,.2f}")
            with m6:
                st.metric("Gasto Indirectos. (10%)", f"${gasto_administrativo:,.2f}")

            st.write("")
            if presupuesto_total > 0:
                porcentaje_gastado = min(total_gastado / presupuesto_total, 1.0)
                st.write(f"**Consumo Financiero Global:** {porcentaje_gastado*100:.1f}%")
                st.progress(porcentaje_gastado)

            # ==========================================
            # 👷‍♂️ SECCIÓN VIP: AUDITORÍA DE DESTAJO (NÓMINA)
            # ==========================================
            st.markdown("---")
            st.subheader("👷‍♂️ Control de Mano de Obra a Destajo")
            st.write("Auditoría en tiempo real del dinero autorizado para aplicadores según los m² vs. la nómina real pagada.")
            
            c_bolsa1, c_bolsa2, c_bolsa3 = st.columns(3)
            c_bolsa1.metric("Bolsa Autorizada (Por m²)", f"${bolsa_mano_obra:,.2f}")
            c_bolsa2.metric("Nómina Pagada (Total)", f"${costo_nomina:,.2f}")
            
            if saldo_mano_obra >= 0:
                c_bolsa3.metric("Saldo Disponible a Favor", f"${saldo_mano_obra:,.2f}", "Rentable")
            else:
                c_bolsa3.metric("Sobregiro de Nómina", f"${saldo_mano_obra:,.2f}", "-Pérdida")
                st.error("⚠️ ALERTA: Se ha pagado más nómina de la que el presupuesto de metros cuadrados permitía.")
            
            if bolsa_mano_obra > 0:
                pct_nomina = min(costo_nomina / bolsa_mano_obra, 1.0)
                st.progress(pct_nomina)

            # ==========================================
            # 📥 REGISTRO DE GASTOS
            # ==========================================
            st.markdown("---")
            c_form, c_tabla = st.columns([1, 2])
            
            with c_form:
                st.subheader("📥 Registrar Nuevo Gasto")
                with st.form("form_gastos_fin"):
                    concepto = st.text_input("Concepto (o Nombre del Trabajador)", placeholder="Ej. Pago a Juan Pérez")
                    categoria_gasto = st.selectbox("Categoría de Cuenta", ["NÓMINA", "Costo de Material", "Viáticos y Comidas", "Gasolina y Fletes", "Herramientas y Equipos", "Otros Gastos Extras"])
                    monto_gasto = st.number_input("Monto de Gasto / Nómina ($ MXN)", min_value=0.0, step=500.0)
                    
                    btn_gasto = st.form_submit_button("💰 INYECTAR GASTO")
                    
                    if btn_gasto:
                        if monto_gasto > 0:
                            fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y")
                            
                            hoja_gastos.append_row([fecha_actual, folio_seleccionado, concepto.upper(), categoria_gasto.upper(), monto_gasto])
                            st.success(f"✅ Transacción de ${monto_gasto:,.2f} registrada con éxito.")
                            
                            registrar_bitacora(doc, "Panel Financiero", f"Inyectó gasto de ${monto_gasto:,.2f} a {folio_seleccionado} ({categoria_gasto}). Concepto: {concepto.upper()}")
                            
                            st.rerun()

            with c_tabla:
                st.subheader("📋 Historial Desglosado de Egresos")
                if gastos_filtrados:
                    df = pd.DataFrame(gastos_filtrados)[["Fecha", "Concepto", "Categoría", "Monto ($)"]]
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay transacciones registradas de forma manual en esta obra.")
