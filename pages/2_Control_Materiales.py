import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime

st.set_page_config(page_title="Control de Materiales", page_icon="📦", layout="wide")

# -----------------------------------------
# 🛡️ CANDADO DE SEGURIDAD POR ROLES
# -----------------------------------------
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ Acceso denegado. Inicia sesión en la página principal.")
    st.stop()

ROLES_PERMITIDOS = ["Admin", "RRHH"]
if st.session_state.get("role") not in ROLES_PERMITIDOS:
    st.error(f"🚫 ACCESO RESTRINGIDO: Tu perfil de {st.session_state.get('role')} no tiene autorización para este módulo.")
    st.stop()
# -----------------------------------------

CLAVE_ADMIN = "2289"

# 📋 LISTA MAESTRA DE MATERIALES (Para que todos los menús sean idénticos)
CATALOGO_IMPERMEABILIZANTES = [
    "MASTER LASSER 3.0 MM FIBRA POLIESTER LISO ARENADO",
    "MASTER LASSER 3.5 MM FIBRA POLIESTER BLANCO",
    "MASTER LASSER 4.0 MM FIBRA POLIESTER BLANCO",
    "MASTER LASSER 4.5 MM FIBRA POLIESTER ROJO",
    "MASTER LASSER 3.5 MM FIBRA POLIESTER ROJO",
    "MASTER LASSER 4.0 MM FIBRA POLIESTER ROJO",
    "MASTER LASSER 4.5 MM FIBRA POLIESTER BLANCO",
    "MASTER LASSER 3.5 MM FIBRA VIDRIO ROJO",
    "MASTER LASSER 3.5 MM FIBRA VIDRIO BLANCO",
    "MASTER PRIM A",
    "MASTER PRIM S",
    "KRIPTOFLEX 5 AÑOS FIBRATADO",
    "MALLA REFUERZO",
    "Primario Hidroflex",
    "Gas L.P.",
    "Cemento Plástico"
]

# 💵 DICCIONARIO DE PRECIOS
PRECIO_BASE = 1200.00

def obtener_precio(nombre_material):
    precios = {
        # --- MATERIALES DE CONSTRUCCIÓN LIGERA Y EXTRAS ---
        "Hoja de Tablaroca (Gypsum Board)": 1200.00,
        "Poste Metálico": 1200.00,
        "Canal de Amarre": 1200.00,
        "Reborde J": 1200.00,
        "Tornillos Bartolos": 1200.00,
        "Cinta Acústica / Accesorios": 1200.00,
        
        # --- EXTRAS DE IMPERMEABILIZACIÓN ---
        "Primario Hidroflex": 1200.00,
        "Gas L.P.": 1200.00,
        "Cemento Plástico": 1200.00,
        
        # --- CATÁLOGO DE IMPERMEABILIZANTES PREFABRICADOS ---
        "MASTER LASSER 3.0 MM FIBRA POLIESTER LISO ARENADO": 1200.00,
        "MASTER LASSER 3.5 MM FIBRA POLIESTER BLANCO": 1200.00,
        "MASTER LASSER 4.0 MM FIBRA POLIESTER BLANCO": 1200.00,
        "MASTER LASSER 4.5 MM FIBRA POLIESTER ROJO": 1200.00,
        "MASTER LASSER 3.5 MM FIBRA POLIESTER ROJO": 1200.00,
        "MASTER LASSER 4.0 MM FIBRA POLIESTER ROJO": 1200.00,
        "MASTER LASSER 4.5 MM FIBRA POLIESTER BLANCO": 1200.00,
        "MASTER LASSER 3.5 MM FIBRA VIDRIO ROJO": 1200.00,
        "MASTER LASSER 3.5 MM FIBRA VIDRIO BLANCO": 1200.00,
        "MASTER PRIM A": 870.00,
        "MASTER PRIM S": 1200.00,
        "KRIPTOFLEX 5 AÑOS FIBRATADO": 1200.00,
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
        
        ID_DEL_EXCEL = "1-grdT2H5dBlGVPvJbZ5wVYDdtVjQEEmUPGpvEm6C0Gc" 
        return cliente.open_by_key(ID_DEL_EXCEL)
    except Exception:
        return None

st.title("📦 Control de Salidas y Materiales")
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
        tab1, tab2 = st.tabs(["📦 Registro de Salidas", "⚙️ Definir Límites Autorizados"])
        
        # --- PESTAÑA DE LÍMITES ---
        with tab2:
            st.subheader("Asignación de Presupuesto de Material")
            clave_ingresada = st.text_input("🔑 Ingresa la clave de Administrador:", type="password")
            
            if clave_ingresada == CLAVE_ADMIN:
                with st.form("form_limites"):
                    colA, colB = st.columns(2)
                    with colA:
                        folio_limite = st.selectbox("Selecciona la Obra:", ["..."] + obras_ejecucion, key="folio_lim")
                        categoria_lim = st.selectbox("Categoría", ["Impermeabilización", "Sistemas Ligeros", "Otros / Consumibles"], key="cat_lim")
                    
                    with colB:
                        if categoria_lim == "Impermeabilización":
                            mat_lim = st.selectbox("Insumo", CATALOGO_IMPERMEABILIZANTES, key="mat_lim_imp")
                        elif categoria_lim == "Sistemas Ligeros":
                            mat_lim = st.selectbox("Insumo", ["Hoja de Tablaroca (Gypsum Board)", "Poste Metálico", "Canal de Amarre", "Reborde J", "Tornillos Bartolos", "Cinta Acústica / Accesorios"], key="mat_lim_sl")
                        else:
                            mat_lim = st.text_input("Especificar Insumo:", key="mat_lim_ot")
                            
                        cant_maxima = st.number_input("Cantidad Máxima a Autorizar:", min_value=0.0, step=1.0)
                        
                        # 🚀 NUEVO: CASILLA DE REQUISICIÓN
                        num_requisicion = st.text_input("Número de Requisición:", placeholder="Ej. REQ-1045", key="num_req_lim")
                    
                    btn_limite = st.form_submit_button("🔒 FIJAR LÍMITE EN SISTEMA")
                    
                    if btn_limite:
                        if folio_limite != "...":
                            # Guardamos en Excel incluyendo la requisición al final
                            req_final = num_requisicion.strip().upper() if num_requisicion.strip() else "SIN REQ"
                            hoja_limites.append_row([folio_limite, mat_lim, cant_maxima, req_final])
                            st.success(f"✅ Límite fijado para {folio_limite} bajo la Requisición: {req_final}.")

        # --- PESTAÑA DE SALIDAS ---
        with tab1:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                folio_seleccionado = st.selectbox("Obra Activa:", ["Selecciona un folio..."] + obras_ejecucion)

            if folio_seleccionado != "Selecciona un folio...":
                with col2:
                    categoria = st.selectbox("Categoría del Material", ["Impermeabilización", "Sistemas Ligeros", "Otros / Consumibles"])
                    
                    if categoria == "Impermeabilización":
                        material = st.selectbox("Insumo", CATALOGO_IMPERMEABILIZANTES)
                        unidad = "Piezas/Litros"
                    elif categoria == "Sistemas Ligeros":
                        material = st.selectbox("Insumo", ["Hoja de Tablaroca (Gypsum Board)", "Poste Metálico", "Canal de Amarre", "Reborde J", "Tornillos Bartolos", "Cinta Acústica / Accesorios"])
                        unidad = "Piezas/Cajas"
                    else:
                        material = st.text_input("Especificar Insumo:")
                        unidad = "Unidades"

                    limites_data = hoja_limites.get_all_records()
                    consumos_data = hoja_consumos.get_all_records()
                    
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
                        st.warning("⚠️ No se ha definido un límite autorizado para este material.")
                        bloquear_salida = True
                    else:
                        if disponible > 0:
                            st.info(f"📊 **DISPONIBLE: {disponible} {unidad}** | 💵 Costo Unitario: **${precio_unitario:,.2f}**")
                            bloquear_salida = False
                        else:
                            st.error("🛑 **LÍMITE EXCEDIDO**")
                            bloquear_salida = True

                    with st.form("form_materiales"):
                        cantidad = st.number_input(f"Cantidad a retirar ({unidad})", min_value=0.0, step=1.0)
                        
                        # 🚀 NUEVO: CASILLA DE REMISIÓN
                        num_remision = st.text_input("Número de Remisión de Entrega:", placeholder="Ej. REM-2089")
                        
                        btn_guardar = st.form_submit_button("💾 REGISTRAR SALIDA Y CARGAR COSTO A OBRA")
                        
                        if btn_guardar:
                            if bloquear_salida or cantidad <= 0 or cantidad > disponible:
                                st.error("❌ OPERACIÓN DENEGADA.")
                            elif not num_remision.strip():
                                st.error("⚠️ El número de Remisión es obligatorio para poder autorizar la salida física.")
                            else:
                                fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
                                costo_total_movimiento = cantidad * precio_unitario
                                rem_final = num_remision.strip().upper()
                                
                                # 1. Guarda la salida de almacén incluyendo la remisión
                                hoja_consumos.append_row([
                                    fecha_hoy, folio_seleccionado, categoria, material, cantidad, unidad, rem_final
                                ])
                                
                                # 2. INYECTA EL COSTO DIRECTO A GASTOS FINANCIEROS (Reflejando la remisión en la descripción)
                                hoja_gastos.append_row([
                                    fecha_hoy, 
                                    folio_seleccionado, 
                                    f"Salida Almacén (Rem. {rem_final}): {cantidad} {unidad} de {material}", 
                                    "Costo de Material", 
                                    costo_total_movimiento
                                ])
                                
                                st.success(f"✅ Se entregaron {cantidad} de {material} bajo la Remisión {rem_final}. Se cargó un costo de ${costo_total_movimiento:,.2f} a la obra.")
