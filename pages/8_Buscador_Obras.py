import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import pandas as pd

st.set_page_config(page_title="Buscador Maestro", page_icon="🔍", layout="wide")

# -----------------------------------------
# 🛡️ CANDADO DE SEGURIDAD POR ROLES
# -----------------------------------------
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ Acceso denegado. Inicia sesión en la página principal.")
    st.stop()

# Este buscador es útil para casi todos, así que le damos acceso amplio
ROLES_PERMITIDOS = ["Admin", "Directivo", "RRHH", "Auxiliar"]
if st.session_state.get("role") not in ROLES_PERMITIDOS:
    st.error(f"🚫 ACCESO RESTRINGIDO: Tu perfil de {st.session_state.get('role')} no tiene autorización.")
    st.stop()

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

# 🧠 FUNCIÓN SABUESO: Busca el valor aunque la columna tenga un nombre ligeramente distinto
def obtener_valor(diccionario, palabras_clave, default="No registrado"):
    for k, v in diccionario.items():
        if any(p in str(k).upper() for p in palabras_clave):
            if str(v).strip() != "":
                return str(v)
    return default

st.title("🔍 Buscador Maestro de Obras y Clientes")
st.markdown("---")

doc = conectar_sheets()

if doc:
    try:
        hoja_obras = doc.worksheet("Obras_Activas")
        hoja_presupuestos = doc.worksheet("Presupuestos")
    except Exception as e:
        st.error("⚠️ Faltan las pestañas 'Obras_Activas' o 'Presupuestos' en tu Excel.")
        st.stop()

    # Extraemos todos los datos
    datos_obras = hoja_obras.get_all_records()
    datos_presupuestos = hoja_presupuestos.get_all_records()
    
    # Consolidamos la información cruzando ambas bases por FOLIO
    obras_consolidadas = {}
    
    # 1. Metemos todo lo de presupuestos (que suele tener los datos del cliente)
    for fila in datos_presupuestos:
        folio = obtener_valor(fila, ["FOLIO"], None)
        if folio:
            obras_consolidadas[str(folio).upper()] = fila.copy()
            
    # 2. Actualizamos con los datos de Obras Activas (Residente, Fechas reales, Estatus)
    for fila in datos_obras:
        folio = obtener_valor(fila, ["FOLIO"], None)
        if folio:
            folio_str = str(folio).upper()
            if folio_str not in obras_consolidadas:
                obras_consolidadas[folio_str] = {}
            obras_consolidadas[folio_str].update(fila)

    # --- BARRA DE BÚSQUEDA ---
    col_busqueda, _ = st.columns([2, 1])
    with col_busqueda:
        busqueda = st.text_input("Ingresa el Folio o Nombre del Proyecto:", placeholder="Ej. OBRA01-26 o Costa de Oro...").strip().upper()

    if busqueda:
        resultados = []
        for folio, datos in obras_consolidadas.items():
            proyecto = obtener_valor(datos, ["PROYECTO", "UBICACION", "OBRA", "CONCEPTO"], "").upper()
            cliente = obtener_valor(datos, ["CLIENTE"], "").upper()
            
            # Filtramos si la búsqueda coincide con folio, proyecto o cliente
            if busqueda in folio or busqueda in proyecto or busqueda in cliente:
                resultados.append({"folio": folio, "datos": datos})
                
        if not resultados:
            st.warning(f"No se encontraron obras que coincidan con '{busqueda}'.")
        else:
            st.success(f"✅ Se encontraron {len(resultados)} coincidencias.")
            
            for res in resultados:
                d = res["datos"]
                
                # Extracción inteligente de todos los campos que pediste
                val_proyecto = obtener_valor(d, ["PROYECTO", "OBRA", "CONCEPTO"])
                val_ubicacion = obtener_valor(d, ["UBICACION", "DIRECCION", "LUGAR"], val_proyecto) # Si no hay ubicación, repite proyecto
                val_residente = obtener_valor(d, ["RESIDENTE", "ENCARGADO", "SUPERVISOR"])
                val_fecha = obtener_valor(d, ["FECHA DE INICIO", "ARRANQUE", "FECHA"], "Sin fecha de inicio")
                
                val_cliente = obtener_valor(d, ["CLIENTE", "NOMBRE CLIENTE"])
                val_numero = obtener_valor(d, ["NUMERO", "TELEFONO", "CELULAR"])
                val_correo = obtener_valor(d, ["CORREO", "EMAIL", "E-MAIL"])
                val_empresa = obtener_valor(d, ["EMPRESA", "RAZON SOCIAL", "COMPAÑIA", "CONSTRUCTORA"])
                val_asesor = obtener_valor(d, ["ASESOR", "VENDEDOR", "EJECUTIVO"])
                
                # --- TARJETA DE RESULTADOS ---
                st.markdown(f"### 🏗️ {val_proyecto} (Folio: {res['folio']})")
                
                c1, c2, c3 = st.columns(3)
                
                with c1:
                    st.markdown("#### 🏢 Datos de la Obra")
                    st.write(f"**Folio:** {res['folio']}")
                    st.write(f"**Ubicación:** {val_ubicacion}")
                    st.write(f"**Fecha de Inicio:** {val_fecha}")
                    st.write(f"**Encargado (Residente):** {val_residente}")
                    
                with c2:
                    st.markdown("#### 👤 Perfil del Cliente")
                    st.write(f"**Nombre:** {val_cliente}")
                    st.write(f"**Empresa:** {val_empresa}")
                    st.write(f"**Teléfono:** {val_numero}")
                    st.write(f"**Correo:** {val_correo}")
                    
                with c3:
                    st.markdown("#### 💼 Gestión Comercial")
                    st.write(f"**Asesor a cargo:** {val_asesor}")
                    
                    # Pequeño extra visual para el estatus de la obra
                    estatus = obtener_valor(d, ["ESTATUS"], "DESCONOCIDO").upper()
                    if "EJECU" in estatus:
                        st.success(f"**Estatus:** {estatus} 🟢")
                    elif "CERRA" in estatus:
                        st.error(f"**Estatus:** {estatus} 🔒")
                    else:
                        st.info(f"**Estatus:** {estatus}")
                
                st.markdown("---")
