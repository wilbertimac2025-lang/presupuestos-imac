import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import pandas as pd
import os
from PIL import Image

# --- CONFIGURACIÓN CORPORATIVA ---
icono_navegador = "logo_imac_2026.png" if os.path.exists("logo_imac_2026.png") else ("logo_tarc.png" if os.path.exists("logo_tarc.png") else "🏢")
st.set_page_config(page_title="Reporte de Obra", page_icon=icono_navegador, layout="wide")

# -----------------------------------------
# 🛡️ CANDADO DE SEGURIDAD POR ROLES
# -----------------------------------------
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ Acceso denegado. Inicia sesión en la página principal.")
    st.stop()

# Nota: Si el Tablero General no lo debe ver RRHH, quita "RRHH" de esta lista en ese archivo.
ROLES_PERMITIDOS = ["Admin", "Directivo", "RRHH", "Operativo"]
if st.session_state.get("role") not in ROLES_PERMITIDOS:
    st.error(f"🚫 ACCESO RESTRINGIDO: Tu perfil de {st.session_state.get('role')} no tiene autorización para este módulo.")
    st.stop()
# -----------------------------------------

# 🔐 CONTRASEÑA MAESTRA
CLAVE_ADMIN = "2289"

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
        
        # ⚠️ REEMPLAZA CON TU ID DE EXCEL AQUÍ
        ID_DEL_EXCEL = st.secrets["ID_EXCEL"] 
        return cliente.open_by_key(ID_DEL_EXCEL)
    except Exception: return None

# --- ENCABEZADO OFICIAL BLINDADO ---
col_logo, col_tit = st.columns([1, 5])
with col_logo:
    try:
        if os.path.exists("logo_imac_2026.png"):
            img_logo = Image.open("logo_imac_2026.png")
            st.image(img_logo, use_container_width=True)
        elif os.path.exists("logo_tarc.png"):
            img_logo = Image.open("logo_tarc.png")
            st.image(img_logo, use_container_width=True)
        elif os.path.exists("logo_tarc.jpg"):
            img_logo = Image.open("logo_tarc.jpg")
            st.image(img_logo, use_container_width=True)
    except Exception:
        st.write("🏢 GRUPO IMAC")
with col_tit:
    st.title("Expediente y Reporte Total de Obra")
st.markdown("---")

# --- CANDADO DE SEGURIDAD ---
clave_ingresada = st.text_input("🔑 Ingresa la clave de Administrador para acceder a los expedientes:", type="password")

if clave_ingresada == CLAVE_ADMIN:
    st.success("🔓 Acceso de Administrador Concedido")
    
    doc = conectar_sheets()

    if doc:
        try:
            hoja_obras = doc.worksheet("Obras_Activas")
            hoja_gastos = doc.worksheet("Gastos_Financieros")
            hoja_consumos = doc.worksheet("Consumo_Materiales")
            hoja_trabajadores = doc.worksheet("Registro_Trabajadores")
            hoja_convenios = doc.worksheet("Convenios_Adicionales")
        except Exception as e:
            st.error("⚠️ Faltan algunas pestañas en tu Excel para generar el reporte completo.")
            st.stop()

        datos_obras = hoja_obras.get_all_records()
        
        llave_folio = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "FOLIO" in str(k).upper()), None)
        folios_disponibles = [str(fila[llave_folio]) for fila in datos_obras if str(fila.get(llave_folio, "")) != ""] if llave_folio else []

        col_sel, _ = st.columns([1, 2])
        with col_sel:
            folio_seleccionado = st.selectbox("Selecciona el Folio de la Obra:", ["Selecciona un folio..."] + folios_disponibles)

        if folio_seleccionado != "Selecciona un folio...":
            obra_info = next((f for f in datos_obras if str(f.get(llave_folio, "")) == folio_seleccionado), None)
            
            # 🔍 BUSCADOR INTELIGENTE DE COLUMNAS
            llave_cliente = next((k for k in (obra_info.keys() if obra_info else []) if "CLIENTE" in str(k).upper()), None)
            cliente = obra_info.get(llave_cliente, "No Especificado") if llave_cliente else "No Especificado"

            llave_proyecto = next((k for k in (obra_info.keys() if obra_info else []) if "PROYECTO" in str(k).upper() or "UBICACI" in str(k).upper()), None)
            proyecto = obra_info.get(llave_proyecto, "No Especificado") if llave_proyecto else "No Especificado"

            llave_estatus = next((k for k in (obra_info.keys() if obra_info else []) if "ESTATUS" in str(k).upper()), None)
            estatus = obra_info.get(llave_estatus, "N/A") if llave_estatus else "N/A"

            fecha_inicio = next((v for k, v in obra_info.items() if "FECHA" in str(k).upper()), "N/A")
            residente = next((v for k, v in obra_info.items() if "RESIDENTE" in str(k).upper() or "ENCARGADO" in str(k).upper()), "N/A")
            
            llave_rp = next((k for k in (obra_info.keys() if obra_info else []) if "PATRONAL" in str(k).upper() or "REGISTRO" in str(k).upper()), None)
            registro_patronal = obra_info.get(llave_rp, "NO ASIGNADO") if llave_rp else "NO ASIGNADO"
            
            llave_monto = next((k for k in (obra_info.keys() if obra_info else []) if "PRESUPUESTO" in str(k).upper() or "AUTORIZADO" in str(k).upper() or "MONTO" in str(k).upper()), None)
            presupuesto_total = limpiar_monto(obra_info.get(llave_monto, 0)) if llave_monto else 0.0

            # 🧠 INYECCIÓN DE LOS COSTOS INDIRECTOS AUTOMÁTICOS
            gasto_financiamiento = presupuesto_total * 0.01
            gasto_administrativo = presupuesto_total * 0.10

            # --- ENCABEZADO OFICIAL DEL REPORTE ---
            st.subheader(f"🏢 Proyecto: {proyecto}")
            c_info1, c_info2, c_info3 = st.columns(3)
            c_info1.write(f"**Cliente:** {cliente}")
            c_info1.write(f"**Folio Asignado:** {folio_seleccionado}")
            c_info2.write(f"**Residente:** {residente}")
            c_info2.write(f"**Fecha de Arranque:** {fecha_inicio}")
            c_info3.write(f"🏛️ **Reg. Patronal:** {registro_patronal}")
            
            if estatus.upper() == "CERRADA":
                c_info3.error(f"**Estatus:** {estatus} 🔒")
            else:
                c_info3.success(f"**Estatus:** {estatus} 🟢")

            st.markdown("---")

            # --- CÁLCULOS FINANCIEROS (AHORA CON FINANCIAMIENTO Y ADMINISTRATIVO INCLUIDO) ---
            datos_gastos = hoja_gastos.get_all_records()
            gastos_obra = [g for g in datos_gastos if str(g.get("Folio Obra", "")) == folio_seleccionado]
            
            gastos_registrados = sum(limpiar_monto(g.get("Monto ($)", 0)) for g in gastos_obra)
            
            # Se suman los registrados en Excel + los calculados en el momento
            total_gastos = gastos_registrados + gasto_financiamiento + gasto_administrativo 
            
            utilidad_calculada = presupuesto_total - total_gastos
            
            # ==========================================
            # 📊 BALANCE GENERAL CON BARRA AZUL (PROGRESO)
            # ==========================================
            st.write("### 📊 Balance General del Proyecto")
            c1, c2, c3 = st.columns(3)
            c1.metric("Presupuesto Actual Autorizado", f"${presupuesto_total:,.2f}")
            c2.metric("Egresos Totales Ejecutados", f"${total_gastos:,.2f}")
            
            if utilidad_calculada >= 0:
                c3.metric("Utilidad Financiera Libre", f"${utilidad_calculada:,.2f}")
            else:
                c3.metric("⚠️ Déficit / Pérdida en Obra", f"${utilidad_calculada:,.2f}")

            # 🚀 AQUÍ ESTÁ LA LÍNEA AZUL DE PROGRESO
            if presupuesto_total > 0:
                # Calculamos el porcentaje consumido
                porcentaje_consumido = min(total_gastos / presupuesto_total, 1.0)
                porcentaje_texto = porcentaje_consumido * 100
                st.write(f"**Consumo del Presupuesto (Incluye Financiamento y Gastos Adm.):** {porcentaje_texto:.1f}%")
                st.progress(porcentaje_consumido)
            
            st.markdown("---")
            
            # --- TABS DE DESGLOSE ---
            st.write("### 🗂️ Desglose del Expediente")
            tab1, tab2, tab3, tab4 = st.tabs(["💰 Finanzas y Egresos", "📦 Almacén y Materiales", "👷 Cuadrilla e IMSS", "📝 Convenios Extra"])
            
            with tab1:
                # NOTA PARA EL USUARIO: Añadimos una leyenda para que quede claro de dónde vienen los números
                st.info(f"💡 **Nota Técnica:** Además de los egresos listados abajo, el Balance General ya contempla **${gasto_financiamiento:,.2f}** de Financiamiento (1%) y **${gasto_administrativo:,.2f}** de Gastos Administrativos (10%).")
                
                if gastos_obra:
                    df_gastos = pd.DataFrame(gastos_obra)[["Fecha", "Concepto", "Categoría", "Monto ($)"]]
                    df_gastos["Monto ($)"] = df_gastos["Monto ($)"].apply(lambda x: f"${limpiar_monto(x):,.2f}")
                    st.dataframe(df_gastos, use_container_width=True, hide_index=True)
                else:
                    st.warning("No hay gastos registrados manualmente en esta obra.")

            with tab2:
                datos_consumos = hoja_consumos.get_all_records()
                consumos_obra = [c for c in datos_consumos if str(c.get("Folio Obra", "")) == folio_seleccionado]
                if consumos_obra:
                    df_consumos = pd.DataFrame(consumos_obra)
                    # 🚀 MODIFICACIÓN: Mostrar todas las columnas excepto el "Folio Obra" y las vacías
                    cols_a_mostrar = [c for c in df_consumos.columns if "FOLIO" not in str(c).upper() and str(c).strip() != ""]
                    st.dataframe(df_consumos[cols_a_mostrar], use_container_width=True, hide_index=True)
                else:
                    st.info("Aún no hay salidas de almacén para esta obra.")

            with tab3:
                datos_trabajadores = hoja_trabajadores.get_all_records()
                trabajadores_obra = [t for t in datos_trabajadores if str(t.get("Folio Obra", "")) == folio_seleccionado]
                if trabajadores_obra:
                    df_trabajadores = pd.DataFrame(trabajadores_obra)
                    columnas_mostrar = ["Nombre del Trabajador", "Puesto / Rol", "NSS"]
                    if "Registro Patronal" in df_trabajadores.columns:
                        columnas_mostrar.append("Registro Patronal")
                    columnas_mostrar.extend(["Estatus IMSS", "Fecha de Asignación"])
                    
                    columnas_finales = [c for c in columnas_mostrar if c in df_trabajadores.columns]
                    st.dataframe(df_trabajadores[columnas_finales], use_container_width=True, hide_index=True)
                else:
                    st.info("No se ha asignado personal a esta obra.")

            with tab4:
                datos_convenios = hoja_convenios.get_all_records()
                convenios_obra = [c for c in datos_convenios if str(c.get("Folio Obra", "")) == folio_seleccionado]
                if convenios_obra:
                    df_convenios = pd.DataFrame(convenios_obra)[["Fecha", "Concepto del Convenio", "Monto Adicional"]]
                    df_convenios["Monto Adicional"] = df_convenios["Monto Adicional"].apply(lambda x: f"${limpiar_monto(x):,.2f}")
                    st.dataframe(df_convenios, use_container_width=True, hide_index=True)
                else:
                    st.info("No existen convenios o trabajos extra en este proyecto.")

elif clave_ingresada != "":
    st.error("❌ Contraseña incorrecta. Acceso denegado a los expedientes de obra.")
