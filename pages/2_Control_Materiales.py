import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime

st.set_page_config(page_title="Control de Materiales", page_icon="📦", layout="wide")

# 🔐 CONTRASEÑA MAESTRA PARA AUTORIZAR LÍMITES
# Puedes cambiar "IMAC2026" por la clave que tú quieras
CLAVE_ADMIN = "2289"

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

st.title("📦 Control de Salidas y Materiales")
st.markdown("---")

doc = conectar_sheets()

if doc:
    try:
        hoja_obras = doc.worksheet("Obras_Activas")
        hoja_consumos = doc.worksheet("Consumo_Materiales")
        hoja_limites = doc.worksheet("Limites_Materiales") 
    except Exception as e:
        st.error("⚠️ Falta crear la pestaña 'Consumo_Materiales' o 'Limites_Materiales' en tu Excel.")
        st.stop()

    datos_obras = hoja_obras.get_all_records()
    
    llave_folio = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "FOLIO" in str(k).upper()), None)
    llave_estatus = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "ESTATUS" in str(k).upper()), None)
    
    obras_ejecucion = []
    if llave_folio and llave_estatus:
        obras_ejecucion = [str(fila[llave_folio]) for fila in datos_obras if str(fila.get(llave_estatus, "")).upper() == "EN EJECUCIÓN"]

    if not obras_ejecucion:
        st.info("No hay obras en ejecución en este momento. Da de alta una en el módulo '1. ERP Gestor Obras'.")
    else:
        tab1, tab2 = st.tabs(["📦 Registro de Salidas", "⚙️ Definir Límites Autorizados"])
        
        # ==========================================
        # PESTAÑA 2: DEFINIR LÍMITES (PROTEGIDA CON CONTRASEÑA)
        # ==========================================
        with tab2:
            st.subheader("Asignación de Presupuesto de Material")
            st.write("Establece el tope máximo de material que la cuadrilla puede retirar para una obra.")
            
            # --- CANDADO DE SEGURIDAD ---
            clave_ingresada = st.text_input("🔑 Ingresa la clave de Administrador para habilitar esta sección:", type="password")
            
            if clave_ingresada == CLAVE_ADMIN:
                st.success("🔓 Acceso de Administrador Concedido")
                with st.form("form_limites"):
                    colA, colB = st.columns(2)
                    with colA:
                        folio_limite = st.selectbox("Selecciona la Obra:", ["..."] + obras_ejecucion, key="folio_lim")
                        categoria_lim = st.selectbox("Categoría", ["Impermeabilización", "Sistemas Ligeros", "Otros / Consumibles"], key="cat_lim")
                    
                    with colB:
                        if categoria_lim == "Impermeabilización":
                            mat_lim = st.selectbox("Insumo", ["Rollo Master Lasser 3.0mm", "Rollo Master Lasser 3.5mm", "Rollo Master Lasser 4.0mm", "Rollo Master Lasser 4.5mm", "Primario Hidroflex", "Gas L.P.", "Cemento Plástico"], key="mat_lim_imp")
                        elif categoria_lim == "Sistemas Ligeros":
                            mat_lim = st.selectbox("Insumo", ["Hoja de Tablaroca (Gypsum Board)", "Poste Metálico", "Canal de Amarre", "Reborde J", "Tornillos Bartolos", "Cinta Acústica / Accesorios"], key="mat_lim_sl")
                        else:
                            mat_lim = st.text_input("Especificar Insumo:", key="mat_lim_ot")
                            
                        cant_maxima = st.number_input("Cantidad Máxima a Autorizar:", min_value=0.0, step=1.0)
                    
                    btn_limite = st.form_submit_button("🔒 FIJAR LÍMITE EN SISTEMA")
                    
                    if btn_limite:
                        if folio_limite == "...":
                            st.warning("Selecciona una obra primero.")
                        elif cant_maxima <= 0:
                            st.warning("La cantidad debe ser mayor a cero.")
                        else:
                            hoja_limites.append_row([folio_limite, mat_lim, cant_maxima])
                            st.success(f"✅ Límite fijado: {cant_maxima} de {mat_lim} para la obra {folio_limite}.")
            elif clave_ingresada != "":
                st.error("❌ Contraseña incorrecta. Acceso denegado.")

        # ==========================================
        # PESTAÑA 1: SALIDAS DE ALMACÉN (LIBRE PARA BODEGA)
        # ==========================================
        with tab1:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("1. Selección")
                folio_seleccionado = st.selectbox("Obra Activa:", ["Selecciona un folio..."] + obras_ejecucion)

            if folio_seleccionado != "Selecciona un folio...":
                with col2:
                    st.subheader("2. Petición de Almacén")
                    
                    categoria = st.selectbox("Categoría del Material", ["Impermeabilización", "Sistemas Ligeros", "Otros / Consumibles"])
                    
                    if categoria == "Impermeabilización":
                        material = st.selectbox("Insumo", ["Rollo Master Lasser 3.0mm", "Rollo Master Lasser 3.5mm", "Rollo Master Lasser 4.0mm", "Rollo Master Lasser 4.5mm", "Primario Hidroflex", "Gas L.P.", "Cemento Plástico"])
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
                            try:
                                limite_actual = float(fila.get("Cantidad Maxima", 0))
                            except: pass
                            
                    consumido_actual = 0
                    for fila in consumos_data:
                        if str(fila.get("Folio Obra", "")) == folio_seleccionado and str(fila.get("Material / Insumo", "")) == material:
                            try:
                                consumido_actual += float(fila.get("Cantidad Usada", 0))
                            except: pass
                            
                    disponible = limite_actual - consumido_actual
                    
                    st.markdown("---")
                    if limite_actual == 0:
                        st.warning("⚠️ **ATENCIÓN:** No se ha definido un límite autorizado para este material. Pide autorización al administrador.")
                        bloquear_salida = True
                    else:
                        if disponible > 0:
                            st.info(f"📊 **ESTADO DEL MATERIAL:** \n* Límite Autorizado: **{limite_actual}** \n* Ya entregado: **{consumido_actual}** \n* **DISPONIBLE: {disponible} {unidad}**")
                            bloquear_salida = False
                        else:
                            st.error(f"🛑 **LÍMITE EXCEDIDO:** \nSe autorizaron {limite_actual} y ya se entregaron {consumido_actual}. **No hay material disponible para retirar.**")
                            bloquear_salida = True

                    with st.form("form_materiales"):
                        cantidad = st.number_input(f"Cantidad a retirar ({unidad})", min_value=0.0, step=1.0)
                        btn_guardar = st.form_submit_button("💾 REGISTRAR SALIDA A OBRA")
                        
                        if btn_guardar:
                            if bloquear_salida:
                                st.error("❌ OPERACIÓN DENEGADA. Revisa los límites autorizados.")
                            elif cantidad <= 0:
                                st.warning("⚠️ La cantidad debe ser mayor a 0.")
                            elif cantidad > disponible:
                                st.error(f"❌ ¡ALTO! Estás intentando sacar {cantidad}, pero solo quedan {disponible} disponibles.")
                            else:
                                fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
                                hoja_consumos.append_row([
                                    fecha_hoy,
                                    folio_seleccionado,
                                    categoria,
                                    material,
                                    cantidad,
                                    unidad
                                ])
                                st.success(f"✅ SALIDA APROBADA: Se han entregado {cantidad} de {material}. Restan {disponible - cantidad} en el presupuesto.")
      
