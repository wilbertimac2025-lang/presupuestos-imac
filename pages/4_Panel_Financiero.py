import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime
import pandas as pd
import os
from PIL import Image

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
        credenciales_dic = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(credenciales_dic, scopes=scopes)
        cliente = gspread.authorize(creds)
        
        ID_DEL_EXCEL = os.environ.get("ID_EXCEL") 
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
            
            total_devoluciones = 0.0
            total_ajustes = 0.0
            total_desperdicio = 0.0
            descuento_destajo_desperdicio = 0.0
            
            CATEGORIAS_LOGISTICAS = [
                "DEVOLUCIÓN DE MATERIAL",
                "AJUSTE EXCEPCIONAL",
                "DESPERDICIO DE MATERIAL",
                "DESPERDICIO CARGO DESTAJO"
            ]
            
            for g in gastos_filtrados:
                monto = limpiar_monto(g.get("Monto ($)", 0))
                categoria = str(g.get("Categoría", "")).upper().strip()
                
                if categoria == "NÓMINA":
                    costo_nomina += monto
                elif categoria == "COSTO DE MATERIAL":
                    costo_materiales += monto
                elif categoria == "DEVOLUCIÓN DE MATERIAL":
                    costo_materiales -= monto
                    total_devoluciones += monto
                elif categoria == "AJUSTE EXCEPCIONAL":
                    costo_materiales += monto
                    total_ajustes += monto
                elif categoria == "DESPERDICIO DE MATERIAL":
                    costo_materiales += monto
                    total_desperdicio += monto
                elif categoria == "DESPERDICIO CARGO DESTAJO":
                    costo_materiales += monto
                    total_desperdicio += monto
                    descuento_destajo_desperdicio += monto
                elif categoria == "FSR":
                    pass 
                else:
                    gastos_operativos += monto
            
            total_gastado = costo_materiales + costo_nomina + costo_imss + gastos_operativos + gasto_financiamiento + gasto_administrativo
            utilidad_estimada = presupuesto_total - total_gastado

            bolsa_mano_obra = limpiar_monto(obtener_valor(datos_completos, ["BOLSA MANO DE OBRA", "BOLSA", "DESTAJO"], 0.0))
            bolsa_mano_obra_ajustada = bolsa_mano_obra - descuento_destajo_desperdicio
            saldo_mano_obra = bolsa_mano_obra_ajustada - costo_nomina

            # ==========================================
            # 📊 SECCIÓN 1: ESTADO DE CUENTA
            # ==========================================
            st.subheader("📊 Estado de Cuenta del Proyecto")
            
            if total_devoluciones > 0:
                st.success(f"✅ **MATERIAL DEVUELTO (SOBRANTE EN BODEGA):** Se han recuperado **${total_devoluciones:,.2f} MXN** a favor de la rentabilidad de la obra.")
            if total_desperdicio > 0:
                st.warning(f"⚠️ **MERMA / DESPERDICIO POR DESTAJO ACUMULADO:** Se han registrado **${total_desperdicio:,.2f} MXN** en desperdicio de material (${descuento_destajo_desperdicio:,.2f} con cargo a destajo del aplicador).")
            
            m1, m2, m3, m4 = st.columns(4)
            with m1: st.metric("Presupuesto Total", f"${presupuesto_total:,.2f}")
            with m2: st.metric("Costo de Material (Neto)", f"${costo_materiales:,.2f}")
            with m3: st.metric("Gasto Total Acumulado", f"${total_gastado:,.2f}")
            with m4: st.metric("UTILIDAD / GANANCIA", f"${utilidad_estimada:,.2f}")

            st.write("") 

            m4_b, m5, m6, m7 = st.columns(4)
            with m4_b: st.metric("Costos IMSS y Prest. Sociales", f"${costo_imss:,.2f}")
            with m5: st.metric("Financiamiento (1%)", f"${gasto_financiamiento:,.2f}")
            with m6: st.metric("Gasto Indirectos. (10%)", f"${gasto_administrativo:,.2f}")
            with m7: st.metric("Desperdicio Total (Merma)", f"${total_desperdicio:,.2f}")

            st.write("")
            if presupuesto_total > 0:
                porcentaje_gastado = min(max(total_gastado / presupuesto_total, 0.0), 1.0)
                st.write(f"**Consumo Financiero Global:** {porcentaje_gastado*100:.1f}%")
                st.progress(porcentaje_gastado)

            # ==========================================
            # 👷‍♂️ SECCIÓN 2: AUDITORÍA DE DESTAJO (NÓMINA)
            # ==========================================
            st.markdown("---")
            st.subheader("👷‍♂️ Control de Mano de Obra a Destajo")
            st.write("Auditoría en tiempo real del dinero autorizado para aplicadores según los m² vs. la nómina real pagada y descuentos por desperdicio.")
            
            c_bolsa1, c_bolsa2, c_bolsa3, c_bolsa4 = st.columns(4)
            c_bolsa1.metric("Bolsa Autorizada (Por m²)", f"${bolsa_mano_obra:,.2f}")
            c_bolsa2.metric("Cargo por Desperdicio", f"-${descuento_destajo_desperdicio:,.2f}")
            c_bolsa3.metric("Nómina Pagada (Total)", f"${costo_nomina:,.2f}")
            
            if saldo_mano_obra >= 0:
                c_bolsa4.metric("Saldo Disponible a Favor", f"${saldo_mano_obra:,.2f}", "Rentable")
            else:
                c_bolsa4.metric("Sobregiro de Nómina", f"${saldo_mano_obra:,.2f}", "-Pérdida")
                st.error("⚠️ ALERTA: Se ha superado la bolsa de destajo autorizada (considerando nómina pagada y cargos por desperdicio de material).")
            
            if bolsa_mano_obra_ajustada > 0:
                pct_nomina = min(max(costo_nomina / bolsa_mano_obra_ajustada, 0.0), 1.0)
                st.progress(pct_nomina)

            # ==========================================
            # 📥 SECCIÓN 3: REGISTRO DE GASTOS GENERALES
            # ==========================================
            st.markdown("---")
            c_form, c_tabla = st.columns([1, 2])
            
            with c_form:
                st.subheader("📥 Registrar Gasto Operativo / Nómina")
                with st.form("form_gastos_fin"):
                    concepto = st.text_input("Concepto (o Nombre del Trabajador)", placeholder="Ej. Pago Destajo 1 a Juan Pérez")
                    categoria_gasto = st.selectbox("Categoría de Cuenta", ["NÓMINA", "Costo de Material", "Viáticos y Comidas", "Gasolina y Fletes", "Herramientas y Equipos", "Otros Gastos Extras"])
                    monto_gasto = st.number_input("Monto de Gasto / Nómina ($ MXN)", min_value=0.0, step=100.0, format="%.2f")
                    
                    btn_gasto = st.form_submit_button("💰 INYECTAR GASTO")
                    
                    if btn_gasto:
                        if monto_gasto > 0:
                            fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y")
                            hoja_gastos.append_row([fecha_actual, folio_seleccionado, concepto.upper(), categoria_gasto.upper(), round(monto_gasto, 2)])
                            st.success(f"✅ Transacción de ${monto_gasto:,.2f} registrada con éxito.")
                            registrar_bitacora(doc, "Panel Financiero", f"Inyectó gasto de ${monto_gasto:,.2f} a {folio_seleccionado} ({categoria_gasto}). Concepto: {concepto.upper()}")
                            st.rerun()

            with c_tabla:
                st.subheader("📋 Historial Completo de Egresos")
                gastos_operativos_lista = [g for g in gastos_filtrados if str(g.get("Categoría", "")).upper().strip() not in CATEGORIAS_LOGISTICAS]
                
                if gastos_operativos_lista:
                    df = pd.DataFrame(gastos_operativos_lista)[["Fecha", "Concepto", "Categoría", "Monto ($)"]]
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay transacciones operativas registradas en esta obra.")

            # ==========================================
            # 📦 SECCIÓN 4: CONTROL LOGÍSTICO Y DESTAJO DE DESPERDICIO
            # ==========================================
            st.markdown("---")
            st.subheader("📦 Radiografía de Materiales, Devoluciones y Destajo de Desperdicio")
            st.write("Control exacto (admite decimales y fracciones por destajo) del inventario despachado, recuperado y desperdiciado en obra.")
            
            col_aut, col_dev, col_desp = st.columns(3)
            
            # --- PROCESO 1: LO AUTORIZADO Y LOS EXTRAS (ADMITE FRACCIONES) ---
            with col_aut:
                st.markdown("#### 1️⃣ Material Autorizado (Teórico vs Extra)")
                llave_insumo = next((k for k in datos_completos.keys() if "INSUMO" in str(k).upper() or "MATERIAL" in str(k).upper()), None)
                insumos_iniciales = str(datos_completos.get(llave_insumo, "No especificado / Sin material asignado")) if llave_insumo else "No especificado en sistema"
                st.info(f"📋 **Base Inicial (Desde Cotizador):**\n{insumos_iniciales}")
                
                ajustes_mat = [g for g in gastos_filtrados if str(g.get("Categoría", "")).upper().strip() == "AJUSTE EXCEPCIONAL"]
                if ajustes_mat:
                    st.warning(f"⚠️ **Ajustes Excepcionales (Total: ${total_ajustes:,.2f}):**")
                    df_ajustes = pd.DataFrame(ajustes_mat)[["Fecha", "Concepto", "Monto ($)"]]
                    st.dataframe(df_ajustes, use_container_width=True, hide_index=True)
                
                with st.expander("➕ Autorizar Material Extra (Admite Fracciones)"):
                    with st.form("form_ajuste_ext"):
                        cant_ext = st.number_input("Cantidad Extra (Ej. 0.5, 1.25, 2.0)", min_value=0.05, value=1.0, step=0.25, format="%.2f")
                        unidad_ext = st.selectbox("Unidad", ["ROLLOS", "CUBETAS", "BULTOS", "LITROS", "M2", "PIEZAS"], key="uni_ext")
                        desc_ext = st.text_input("Nombre del Material Extra", placeholder="Ej. MASTER LASSER 4.0")
                        monto_ext = st.number_input("Costo del Material Extra ($)", min_value=0.0, step=50.0, format="%.2f")
                        
                        # 🔒 CANDADO DE SEGURIDAD
                        clave_auth_ext = st.text_input("🔑 Clave de Autorización (Dirección)", type="password")
                        
                        if st.form_submit_button("Autorizar Extra"):
                            if clave_auth_ext != "IMAC2026":
                                st.error("🚫 Clave de autorización incorrecta. Movimiento denegado.")
                            elif desc_ext and monto_ext > 0:
                                cant_ext_str = f"{cant_ext:g}"
                                concepto_ext = f"{cant_ext_str} {unidad_ext} - {desc_ext.upper()}"
                                fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y")
                                hoja_gastos.append_row([fecha_actual, folio_seleccionado, concepto_ext, "AJUSTE EXCEPCIONAL", round(monto_ext, 2)])
                                registrar_bitacora(doc, "Panel Financiero", f"Autorizó material extra: {concepto_ext} por ${monto_ext:,.2f} ({folio_seleccionado})")
                                st.success("✅ Ajuste Excepcional autorizado y cargado al costo de la obra.")
                                st.rerun()
                            else:
                                st.error("Llenar descripción y costo válido.")

            # --- PROCESO 2: DEVOLUCIONES DE MATERIAL (ADMITE FRACCIONES / DESTAJOS) ---
            with col_dev:
                st.markdown("#### 2️⃣ Devoluciones a Bodega (Sobrantes)")
                
                with st.form("form_devolucion"):
                    st.write("**Registrar Material Devuelto (Entero o Fracción)**")
                    cant_dev = st.number_input("Cantidad Devuelta (Ej. 0.25, 0.5, 1.0)", min_value=0.05, value=1.0, step=0.25, format="%.2f")
                    unidad_dev = st.selectbox("Unidad Devuelta", ["ROLLOS", "CUBETAS", "BULTOS", "LITROS", "M2", "PIEZAS"], key="uni_dev")
                    desc_dev = st.text_input("Nombre del Material Devuelto", placeholder="Ej. IMPAC 5000")
                    monto_dev = st.number_input("Valor Recuperado ($)", min_value=0.0, step=50.0, format="%.2f")
                    
                    # 🔒 CANDADO DE SEGURIDAD
                    clave_auth_dev = st.text_input("🔑 Clave de Autorización (Almacén/Dirección)", type="password")
                    
                    if st.form_submit_button("♻️ Aplicar Devolución a Utilidad"):
                        if clave_auth_dev != "IMAC2026":
                            st.error("🚫 Clave de autorización incorrecta. Movimiento denegado.")
                        elif desc_dev and monto_dev > 0:
                            cant_dev_str = f"{cant_dev:g}"
                            concepto_dev = f"{cant_dev_str} {unidad_dev} - {desc_dev.upper()}"
                            fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y")
                            hoja_gastos.append_row([fecha_actual, folio_seleccionado, concepto_dev, "DEVOLUCIÓN DE MATERIAL", round(monto_dev, 2)])
                            registrar_bitacora(doc, "Panel Financiero", f"Registró devolución fraccionada: {concepto_dev} recuperando ${monto_dev:,.2f} ({folio_seleccionado})")
                            st.success("✅ Devolución registrada con éxito. Utilidad aumentada.")
                            st.rerun()
                        else:
                            st.error("Llenar descripción y monto válido.")
                
                devoluciones_mat = [g for g in gastos_filtrados if str(g.get("Categoría", "")).upper().strip() == "DEVOLUCIÓN DE MATERIAL"]
                if devoluciones_mat:
                    st.success(f"💰 **Historial de Devoluciones (Total: ${total_devoluciones:,.2f}):**")
                    df_dev = pd.DataFrame(devoluciones_mat)[["Fecha", "Concepto", "Monto ($)"]]
                    st.dataframe(df_dev, use_container_width=True, hide_index=True)
                else:
                    st.info("Aún no hay devoluciones registradas en esta obra.")

            # --- PROCESO 3: DESTAJO DE DESPERDICIO DE MATERIAL (FRACCIONADO / POR ETAPA) ---
            with col_desp:
                st.markdown("#### 3️⃣ Destajo de Desperdicio (Merma)")
                
                with st.form("form_desperdicio_destajo"):
                    st.write("**Registrar Desperdicio de Material por Destajo**")
                    corte_destajo = st.selectbox(
                        "Corte / Etapa de Destajo",
                        ["DESTAJO 1 (AVANCE)", "DESTAJO 2 (AVANCE)", "DESTAJO 3 (AVANCE)", "DESTAJO 4 (AVANCE)", "CIERRE / FINIQUITO DE OBRA"]
                    )
                    cant_desp = st.number_input("Cantidad Desperdiciada (Fracción o Entero)", min_value=0.05, value=0.25, step=0.05, format="%.2f")
                    unidad_desp = st.selectbox("Unidad de Medida", ["CUBETAS", "ROLLOS", "BULTOS", "LITROS", "M2", "PIEZAS"], key="uni_desp")
                    desc_desp = st.text_input("Material / Responsable", placeholder="Ej. ACRILTECHO - Cuadrilla Juan")
                    
                    st.caption("💡 Ingresa el Costo por Unidad Completa para cálculo automático (Cantidad × Costo), o pon el Monto Directo:")
                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        costo_unit_desp = st.number_input("Costo x Unidad ($)", min_value=0.0, step=50.0, format="%.2f")
                    with col_c2:
                        monto_directo_desp = st.number_input("O Monto Directo ($)", min_value=0.0, step=50.0, format="%.2f")
                    
                    tipo_cargo_desp = st.radio(
                        "Aplicación del Desperdicio:",
                        [" Cargo a Destajo (Descuenta al Aplicador)", "🏢 Merma Operativa (Absorbe la Obra)"]
                    )
                    
                    # 🔒 CANDADO DE SEGURIDAD
                    clave_auth_desp = st.text_input("🔑 Clave de Autorización ( Auditoría/Dirección)", type="password")
                    
                    if st.form_submit_button("📉 Registrar Destajo de Desperdicio"):
                        monto_final_desp = round(monto_directo_desp if monto_directo_desp > 0 else (cant_desp * costo_unit_desp), 2)
                        if clave_auth_desp != "IMAC2026":
                            st.error("🚫 Clave de autorización incorrecta. Movimiento denegado.")
                        elif not desc_desp.strip() or monto_final_desp <= 0:
                            st.error("⚠️ Ingresa el nombre del material y un costo unitario o monto directo mayor a $0.")
                        else:
                            cant_desp_str = f"{cant_desp:g}"
                            concepto_desp = f"[{corte_destajo}] {cant_desp_str} {unidad_desp} - {desc_desp.upper()}"
                            categoria_desp = "DESPERDICIO CARGO DESTAJO" if "Cargo a Destajo" in tipo_cargo_desp else "DESPERDICIO DE MATERIAL"
                            fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y")
                            
                            hoja_gastos.append_row([fecha_actual, folio_seleccionado, concepto_desp, categoria_desp, monto_final_desp])
                            registrar_bitacora(doc, "Panel Financiero", f"Registró desperdicio por destajo ({categoria_desp}): {concepto_desp} por ${monto_final_desp:,.2f} ({folio_seleccionado})")
                            st.success(f"✅ Desperdicio de ${monto_final_desp:,.2f} registrado en {corte_destajo}.")
                            st.rerun()
                
                desperdicios_mat = [g for g in gastos_filtrados if str(g.get("Categoría", "")).upper().strip() in ["DESPERDICIO DE MATERIAL", "DESPERDICIO CARGO DESTAJO"]]
                if desperdicios_mat:
                    st.error(f"📉 **Historial de Desperdicios por Destajo (Total: ${total_desperdicio:,.2f}):**")
                    df_desp = pd.DataFrame(desperdicios_mat)[["Fecha", "Concepto", "Categoría", "Monto ($)"]]
                    st.dataframe(df_desp, use_container_width=True, hide_index=True)
                else:
                    st.info("Sin desperdicios registrados en los destajos de esta obra.")
