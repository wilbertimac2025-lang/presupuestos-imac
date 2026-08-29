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
st.set_page_config(page_title="Control de Materiales", page_icon=icono_navegador, layout="wide")

# -----------------------------------------
# 🛡️ CANDADO DE SEGURIDAD POR ROLES
# -----------------------------------------
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ Acceso denegado. Inicia sesión en la página principal.")
    st.stop()

ROLES_PERMITIDOS = ["Admin", "RRHH", "Operativo"]
if st.session_state.get("role") not in ROLES_PERMITIDOS:
    st.error(f"🚫 ACCESO RESTRINGIDO: Tu perfil de {st.session_state.get('role')} no tiene autorización para este módulo.")
    st.stop()
# -----------------------------------------

CLAVE_ADMIN = "2289"

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

# 📋 CATÁLOGO MAESTRO DE IMPERMEABILIZANTES (Sincronizado con Cotizador)
CATALOGO_IMPERMEABILIZANTES = [
    "ACRILTECHO GREEN POWER",
    "IMPAC 3000 FIBRATADO",
    "IMPAC 5000 FIBRATADO",
    "KRIPTOFLEX 3 AÑOS CON MALLA",
    "KRIPTOFLEX 3 AÑOS FIBRATADO",
    "KRIPTOFLEX 5 AÑOS FIBRATADO",
    "KRIPTOFLEX 5 AÑOS CON MALLA",
    "IMPAC 7000 FIBRATADO",
    "IMPAC 7000 FIBRATADO CON MALLA",
    "SELLOTEX",
    "JUNTA LINEAL 30 CM MASTER LASSER 3.0 LISO",
    "JUNTA LINEAL 50 CM MASTER LASSER 3.0 LISO",
    "JUNTA LINEAL 50 CM MASTER LASSER 4.0 LISO",
    "JUNTA LINEAL 15 A 50 CM KRIPTOFLEX",
    "MASTER LASSER 3.5 MM FP",
    "MASTER LASSER 4.0 MM FP",
    "MASTER LASSER 4.5 MM FP",
    "MASTER LASSER 4.0 MM FP (ESCUELAS)",
    "MASTER LASSER 3.0 MM FP LISO SIN ACABADO",
    "MASTER LASSER 4.0 MM FP LISO SIN ACABADO",
    "MASTER LASSER 3.0 MM FV",
    "MASTER LASSER 3.5 MM FV",
    "BITUFLEX",
    "Primario Hidroflex",
    "Gas L.P.",
    "Cemento Plástico",
    "MALLA REFUERZO"
]

# 💵 DICCIONARIO DE PRECIOS DE COSTO (Para Panel Financiero)
PRECIO_BASE = 1200.00

def obtener_precio(nombre_material):
    precios = {
        # --- ACRÍLICOS E IMPAC ---
        "ACRILTECHO GREEN POWER": 1200.00,
        "IMPAC 3000 FIBRATADO": 1200.00,
        "IMPAC 5000 FIBRATADO": 1200.00,
        "KRIPTOFLEX 3 AÑOS CON MALLA": 1200.00,
        "KRIPTOFLEX 3 AÑOS FIBRATADO": 1200.00,
        "KRIPTOFLEX 5 AÑOS FIBRATADO": 1200.00,
        "KRIPTOFLEX 5 AÑOS CON MALLA": 1200.00,
        "IMPAC 7000 FIBRATADO": 1200.00,
        "IMPAC 7000 FIBRATADO CON MALLA": 1200.00,
        
        # --- CEMENTOSOS Y SOLVENTES ---
        "SELLOTEX": 1200.00,
        "BITUFLEX": 1200.00,
        
        # --- PREFABRICADOS (MASTER LASSER) ---
        "MASTER LASSER 3.5 MM FP": 1200.00,
        "MASTER LASSER 4.0 MM FP": 1200.00,
        "MASTER LASSER 4.5 MM FP": 1200.00,
        "MASTER LASSER 4.0 MM FP (ESCUELAS)": 1200.00,
        "MASTER LASSER 3.0 MM FP LISO SIN ACABADO": 1200.00,
        "MASTER LASSER 4.0 MM FP LISO SIN ACABADO": 1200.00,
        "MASTER LASSER 3.0 MM FV": 1200.00,
        "MASTER LASSER 3.5 MM FV": 1200.00,
        
        # --- JUNTAS LINEALES ---
        "JUNTA LINEAL 30 CM MASTER LASSER 3.0 LISO": 1200.00,
        "JUNTA LINEAL 50 CM MASTER LASSER 3.0 LISO": 1200.00,
        "JUNTA LINEAL 50 CM MASTER LASSER 4.0 LISO": 1200.00,
        "JUNTA LINEAL 15 A 50 CM KRIPTOFLEX": 1200.00,
        
        # --- CONSUMIBLES Y EXTRAS ---
        "Primario Hidroflex": 1200.00,
        "Gas L.P.": 1200.00,
        "Cemento Plástico": 1200.00,
        "MALLA REFUERZO": 1200.00
    }
    return precios.get(nombre_material, PRECIO_BASE)

@st.cache_resource
def conectar_sheets():
    try:
        credenciales_dic = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(credenciales_dic, scopes=scopes)
        cliente = gspread.authorize(creds)
        
        ID_DEL_EXCEL = st.secrets["ID_EXCEL"] 
        return cliente.open_by_key(ID_DEL_EXCEL)
    except Exception:
        return None

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
    st.title("Control de Salidas y Materiales")
st.markdown("---")

doc = conectar_sheets()

if doc:
    try:
        hoja_obras = doc.worksheet("Obras_Activas")
        hoja_consumos = doc.worksheet("Consumo_Materiales")
        hoja_limites = doc.worksheet("Limites_Materiales") 
        hoja_gastos = doc.worksheet("Gastos_Financieros")
    except Exception as e:
        st.error("⚠️ Falta crear las pestañas necesarias en tu Excel.")
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
        # 🚀 AQUÍ RENOMBRAMOS LA PESTAÑA A "AJUSTES EXCEPCIONALES"
        tab1, tab2 = st.tabs(["📦 Registro de Movimientos", "🚨 Ajustes Excepcionales"])
        
        # --- PESTAÑA DE LÍMITES / AJUSTES ---
        with tab2:
            st.subheader("Asignación de Presupuesto de Material")
            st.info("💡 Los límites de Impermeabilización ya se calculan y asignan automáticamente al momento de generar la cotización.")
            clave_ingresada = st.text_input("🔑 Ingresa la clave de Administrador para límites manuales:", type="password")
            
            if clave_ingresada == CLAVE_ADMIN:
                with st.form("form_limites"):
                    colA, colB = st.columns(2)
                    with colA:
                        folio_limite = st.selectbox("Selecciona la Obra:", ["..."] + obras_ejecucion, key="folio_lim")
                        categoria_lim = st.selectbox("Categoría", ["Impermeabilización", "Otros / Consumibles"], key="cat_lim")
                    
                    with colB:
                        if categoria_lim == "Impermeabilización":
                            mat_lim = st.selectbox("Insumo", CATALOGO_IMPERMEABILIZANTES, key="mat_lim_imp")
                        else:
                            mat_lim = st.text_input("Especificar Insumo:", key="mat_lim_ot")
                            
                        cant_maxima = st.number_input("Cantidad Máxima a Autorizar:", min_value=0.0, step=1.0)
                        
                        num_requisicion = st.text_input("Número de Requisición:", placeholder="Ej. REQ-1045", key="num_req_lim")
                    
                    btn_limite = st.form_submit_button("🔒 FIJAR LÍMITE MANUAL")
                    
                    if btn_limite:
                        if folio_limite != "...":
                            req_final = num_requisicion.strip().upper() if num_requisicion.strip() else "SIN REQ"
                            hoja_limites.append_row([folio_limite, mat_lim, cant_maxima, req_final])
                            
                            registrar_bitacora(doc, "Control de Materiales", f"Autorizó límite manual de {cant_maxima} de {mat_lim} para la obra {folio_limite}. Req: {req_final}")
                            
                            st.success(f"✅ Límite fijado para {folio_limite} bajo la Requisición: {req_final}.")

        # --- PESTAÑA DE SALIDAS ---
        with tab1:
            col1, col2 = st.columns([1.2, 1.8])
            
            with col1:
                folio_seleccionado = st.selectbox("Obra Activa:", ["Selecciona un folio..."] + obras_ejecucion)

            if folio_seleccionado != "Selecciona un folio...":
                
                limites_data = hoja_limites.get_all_records()
                consumos_data = hoja_consumos.get_all_records()
                
                # --- TABLERO RESUMEN DE INSUMOS ---
                with col1:
                    st.markdown("---")
                    st.markdown("#### 📋 Insumos Autorizados para esta Obra")
                    
                    resumen_obra = []
                    for fila in limites_data:
                        if str(fila.get("Folio Obra", "")) == folio_seleccionado:
                            mat = str(fila.get("Material", ""))
                            max_cant = float(fila.get("Cantidad Maxima", 0))
                            
                            consumido = sum(float(c.get("Cantidad Usada", 0)) for c in consumos_data if str(c.get("Folio Obra", "")) == folio_seleccionado and str(c.get("Material / Insumo", "")) == mat)
                            
                            disponible = max_cant - consumido
                            
                            resumen_obra.append({
                                "Insumo": mat,
                                "Autorizado": max_cant,
                                "Entregado": consumido,
                                "Restante": disponible
                            })
                    
                    if resumen_obra:
                        df_resumen = pd.DataFrame(resumen_obra)
                        st.dataframe(df_resumen, use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay materiales autorizados asignados a esta obra aún.")

                # --- FORMULARIO DE SALIDA ---
                with col2:
                    categoria = st.selectbox("Categoría del Material", ["Impermeabilización", "Otros / Consumibles"])
                    
                    if categoria == "Impermeabilización":
                        material = st.selectbox("Insumo a Entregar", CATALOGO_IMPERMEABILIZANTES)
                        unidad = "Piezas/Litros"
                    else:
                        material = st.text_input("Especificar Insumo:")
                        unidad = "Unidades"

                    limite_actual = 0
                    for fila in limites_data:
                        if str(fila.get("Folio Obra", "")) == folio_seleccionado and str(fila.get("Material", "")) == material:
                            try: limite_actual = float(fila.get("Cantidad Maxima", 0))
                            except: pass
                            
                    consumido_actual = 0
                    for fila in consumos_data:
                        if str(fila.get("Folio Obra", "")) == folio_seleccionado and str(fila.get("Material / Insumo", "")) == material:
                            try: consumido_actual += float(fila.get("Cantidad Usada", 0))
                            except: pass
                            
                    disponible = limite_actual - consumido_actual
                    
                    precio_unitario = obtener_precio(material)
                    st.markdown("---")
                    
                    if limite_actual == 0:
                        st.warning("⚠️ No se ha definido un límite autorizado para este material en esta obra.")
                        bloquear_salida = True
                    else:
                        if disponible > 0:
                            st.info(f"📊 **DISPONIBLE PARA ESTA OBRA: {disponible} {unidad}** | 💵 Costo Unitario: **${precio_unitario:,.2f}**")
                            bloquear_salida = False
                        else:
                            st.error("🛑 **LÍMITE EXCEDIDO (Ya sacaron todo el material autorizado)**")
                            bloquear_salida = True

                    with st.form("form_materiales"):
                        
                        # 🚀 SELECTOR MULTIFUNCIONAL DE ORIGEN DE MATERIAL
                        tipo_movimiento = st.selectbox("Origen del Movimiento (Tipo de Salida):", [
                            "Salida de Almacén",
                            "Compras Internas",
                            "Compras Externas (Factura)",
                            "Traspaso (Carta Porte)",
                            "Ajuste de Inventario / Otro"
                        ])
                        
                        cantidad = st.number_input(f"Cantidad a despachar ({unidad})", min_value=0.0, step=1.0)
                        
                        # 🚀 CAMPO DINÁMICO DE REFERENCIA
                        doc_referencia = st.text_input("Documento de Referencia (Remisión / Factura / Carta Porte):", placeholder="Ej. REM-123, FAC-509, CP-44")
                        
                        btn_guardar = st.form_submit_button("💾 REGISTRAR MOVIMIENTO Y CARGAR COSTO A OBRA")
                        
                        if btn_guardar:
                            if bloquear_salida or cantidad <= 0 or cantidad > disponible:
                                st.error("❌ OPERACIÓN DENEGADA. No hay material autorizado suficiente.")
                            elif not doc_referencia.strip():
                                st.error("⚠️ El Documento de Referencia es obligatorio para poder rastrear este movimiento.")
                            else:
                                fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
                                costo_total_movimiento = cantidad * precio_unitario
                                ref_final = doc_referencia.strip().upper()
                                
                                # Guardamos en Consumos (Unimos el tipo de movimiento y el documento)
                                hoja_consumos.append_row([
                                    fecha_hoy, folio_seleccionado, categoria, material, cantidad, unidad, f"{tipo_movimiento} | {ref_final}"
                                ])
                                
                                # Guardamos en Gastos Financieros para que el contador vea el desglose claro
                                hoja_gastos.append_row([
                                    fecha_hoy, 
                                    folio_seleccionado, 
                                    f"{tipo_movimiento} ({ref_final}): {cantidad} {unidad} de {material}", 
                                    "Costo de Material", 
                                    costo_total_movimiento
                                ])
                                
                                registrar_bitacora(doc, "Control de Materiales", f"Registró {tipo_movimiento} de {cantidad} {material} para {folio_seleccionado}. Ref: {ref_final}")
                                
                                st.success(f"✅ Movimiento exitoso: Se asignaron {cantidad} de {material} mediante {tipo_movimiento} (Ref: {ref_final}). Costo cargado: ${costo_total_movimiento:,.2f}")
