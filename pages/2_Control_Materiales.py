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

# 🚀 NUEVO: TRADUCTOR COMERCIAL A INVENTARIO FÍSICO
def traducir_a_fisico(nombre):
    nombre = str(nombre).strip()
    
    # 1. Quitamos la etiqueta de Escuelas (es el mismo rollo físico)
    if "(ESCUELAS)" in nombre:
        nombre = nombre.replace(" (ESCUELAS)", "").replace("(ESCUELAS)", "")
        
    # 2. Traducimos las Juntas Lineales a sus rollos o cubetas base reales
    if "JUNTA LINEAL 30 CM MASTER LASSER 3.0 LISO" in nombre:
        nombre = nombre.replace("JUNTA LINEAL 30 CM MASTER LASSER 3.0 LISO", "MASTER LASSER 3.0 MM FP LISO SIN ACABADO")
    elif "JUNTA LINEAL 50 CM MASTER LASSER 3.0 LISO" in nombre:
        nombre = nombre.replace("JUNTA LINEAL 50 CM MASTER LASSER 3.0 LISO", "MASTER LASSER 3.0 MM FP LISO SIN ACABADO")
    elif "JUNTA LINEAL 50 CM MASTER LASSER 4.0 LISO" in nombre:
        nombre = nombre.replace("JUNTA LINEAL 50 CM MASTER LASSER 4.0 LISO", "MASTER LASSER 4.0 MM FP LISO SIN ACABADO")
    elif "JUNTA LINEAL 15 A 50 CM KRIPTOFLEX" in nombre:
        nombre = nombre.replace("JUNTA LINEAL 15 A 50 CM KRIPTOFLEX", "KRIPTOFLEX 3 AÑOS FIBRATADO")
        
    return nombre.strip()

# 📋 CATÁLOGO MAESTRO BODEGA (Puros insumos físicos reales)
CATALOGO_BODEGA = [
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
    "MASTER LASSER 3.5 MM FP",
    "MASTER LASSER 4.0 MM FP",
    "MASTER LASSER 4.5 MM FP",
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

def obtener_precio(nombre_material):
    # 🚀 CIRUGÍA DE PRECIOS: Limpiamos los colores y apellidos para cruzar con el precio base exacto
    nombre_base = str(nombre_material)
    colores = ["(BLANCO / ROJO)", "(BLANCO)", "(ROJO)", "(NEGRO)", "(GRIS)", "(NO APLICA)"]
    for col in colores:
        if col in nombre_base:
            nombre_base = nombre_base.replace(col, "").strip()
            break
            
    precios = {
        # --- ACRÍLICOS E IMPAC ---
        "ACRILTECHO GREEN POWER": 1200.00,
        "IMPAC 3000 FIBRATADO": 1108.86,
        "IMPAC 5000 FIBRATADO": 1318.25,
        "KRIPTOFLEX 3 AÑOS CON MALLA": 1169.23,
        "KRIPTOFLEX 3 AÑOS FIBRATADO": 1169.23,
        "KRIPTOFLEX 5 AÑOS FIBRATADO": 1284.62,
        "KRIPTOFLEX 5 AÑOS CON MALLA": 1284.62,
        "IMPAC 7000 FIBRATADO": 1473.56,
        "IMPAC 7000 FIBRATADO CON MALLA": 1473.56,
        
        # --- CEMENTOSOS Y SOLVENTES ---
        "SELLOTEX": 1200.00,
        "BITUFLEX": 1423.00,
        
        # --- PREFABRICADOS (Solo Bases Físicas) ---
        "MASTER LASSER 3.5 MM FP": 824.97,
        "MASTER LASSER 4.0 MM FP": 950.08,
        "MASTER LASSER 4.5 MM FP": 1066.04,
        "MASTER LASSER 3.0 MM FP LISO SIN ACABADO": 870.28,
        "MASTER LASSER 4.0 MM FP LISO SIN ACABADO": 965.72,
        "MASTER LASSER 3.0 MM FV": 608.64,
        "MASTER LASSER 3.5 MM FV": 620.00,
        
        # --- CONSUMIBLES Y EXTRAS ---
        "Primario Hidroflex": 830.77,
        "Gas L.P.": 1200.00,
        "Cemento Plástico": 1200.00,
        "MALLA REFUERZO": 1200.00
    }
    return precios.get(nombre_base, 1200.00)

@st.cache_resource
def conectar_sheets():
    try:
        # 🚀 BLINDAJE PARA RENDER
        credenciales_dic = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(credenciales_dic, scopes=scopes)
        cliente = gspread.authorize(creds)
        
        ID_DEL_EXCEL = os.environ.get("ID_EXCEL") 
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
                            mat_lim = st.selectbox("Insumo Físico", CATALOGO_BODEGA, key="mat_lim_imp")
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
                    
                    # 🚀 TRADUCTOR Y AGRUPADOR INTELIGENTE
                    limites_agrupados = {}
                    for fila in limites_data:
                        if str(fila.get("Folio Obra", "")) == folio_seleccionado:
                            mat_original = str(fila.get("Material", ""))
                            # Pasamos el material por el traductor para juntar Escuelas y Juntas con sus bases
                            mat_traducido = traducir_a_fisico(mat_original)
                            
                            try: cant = float(fila.get("Cantidad Maxima", 0))
                            except: cant = 0.0
                            
                            if mat_traducido in limites_agrupados:
                                limites_agrupados[mat_traducido] += cant
                            else:
                                limites_agrupados[mat_traducido] = cant
                    
                    resumen_obra = []
                    for mat, max_cant in limites_agrupados.items():
                        # Buscamos los consumos también pasándolos por el traductor por si hay registros viejos
                        consumido = sum(float(c.get("Cantidad Usada", 0)) for c in consumos_data if str(c.get("Folio Obra", "")) == folio_seleccionado and traducir_a_fisico(str(c.get("Material / Insumo", ""))) == mat)
                        
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
                        # 🚀 MENÚ HÍBRIDO BODEGA: Pone los autorizados primero, y el resto abajo
                        insumos_autorizados = list(limites_agrupados.keys())
                        opciones_menu = insumos_autorizados.copy()
                        
                        for item_cat in CATALOGO_BODEGA:
                            ya_esta = False
                            for auth in insumos_autorizados:
                                if item_cat in auth:
                                    ya_esta = True
                                    break
                            if not ya_esta:
                                opciones_menu.append(item_cat)
                                
                        if not opciones_menu: 
                            opciones_menu = CATALOGO_BODEGA
                            
                        material = st.selectbox("Insumo a Entregar (Inventario Físico)", opciones_menu)
                        unidad = "Piezas/Litros"
                    else:
                        material = st.text_input("Especificar Insumo:")
                        unidad = "Unidades"

                    # 🚀 VALIDACIÓN DE LÍMITES CON EL TRADUCTOR
                    mat_seleccionado_traducido = traducir_a_fisico(material)
                    limite_actual = limites_agrupados.get(mat_seleccionado_traducido, 0.0)
                            
                    consumido_actual = sum(float(c.get("Cantidad Usada", 0)) for c in consumos_data if str(c.get("Folio Obra", "")) == folio_seleccionado and traducir_a_fisico(str(c.get("Material / Insumo", ""))) == mat_seleccionado_traducido)
                            
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
                        
                        tipo_movimiento = st.selectbox("Origen del Movimiento (Tipo de Salida):", [
                            "Salida de Almacén",
                            "Compras Internas",
                            "Compras Externas (Factura)",
                            "Traspaso (Carta Porte)",
                            "Ajuste de Inventario / Otro"
                        ])
                        
                        cantidad = st.number_input(f"Cantidad a despachar ({unidad})", min_value=0.0, step=1.0)
                        
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
                                
                                # Guardamos en Consumos (Guardamos el nombre Físico Traducido para limpiar la BD)
                                hoja_consumos.append_row([
                                    fecha_hoy, folio_seleccionado, categoria, mat_seleccionado_traducido, cantidad, unidad, f"{tipo_movimiento} | {ref_final}"
                                ])
                                
                                # Guardamos en Gastos Financieros
                                hoja_gastos.append_row([
                                    fecha_hoy, 
                                    folio_seleccionado, 
                                    f"{tipo_movimiento} ({ref_final}): {cantidad} {unidad} de {mat_seleccionado_traducido}", 
                                    "Costo de Material", 
                                    costo_total_movimiento
                                ])
                                
                                registrar_bitacora(doc, "Control de Materiales", f"Registró {tipo_movimiento} de {cantidad} {mat_seleccionado_traducido} para {folio_seleccionado}. Ref: {ref_final}")
                                
                                st.success(f"✅ Movimiento exitoso: Se asignaron {cantidad} de {mat_seleccionado_traducido} mediante {tipo_movimiento} (Ref: {ref_final}). Costo cargado: ${costo_total_movimiento:,.2f}")
