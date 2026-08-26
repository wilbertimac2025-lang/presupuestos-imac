import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime
import pandas as pd
from fpdf import FPDF
import os
import io
from PyPDF2 import PdfMerger
from PIL import Image
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="ERP - Gestión de Obras", page_icon="🏗️", layout="wide")

# 🛡️ CANDADO DE SEGURIDAD GENERAL POR ROLES
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ Acceso denegado. Inicia sesión en la página principal.")
    st.stop()

ROLES_PERMITIDOS = ["Admin", "Operativo", "RRHH"]
if st.session_state.get("role") not in ROLES_PERMITIDOS:
    st.error(f"🚫 ACCESO RESTRINGIDO: Este módulo es exclusivo para Dirección (Admin).")
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

# --- CLASE PARA EL PDF DE LA CARTA ---
class PDF_Carta(FPDF):
    def header(self):
        if os.path.exists("logo_tarc.png"): self.image("logo_tarc.png", x=15, y=10, w=70)
        elif os.path.exists("logo_tarc.jpg"): self.image("logo_tarc.jpg", x=15, y=10, w=70)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(15, 60, 140)
        self.cell(0, 10, 'TARC S.A. DE C.V.', ln=True, align='R')
        self.set_font('Arial', '', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 4, 'BOULEVARD MIGUEL ALEMAN 759, COL. CENTRO', ln=True, align='R')
        self.cell(0, 4, 'VERACRUZ, VER. C.P. 91700', ln=True, align='R')
        self.set_y(45)

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

# ☁️ NUEVA FUNCIÓN: GUARDAR EN GOOGLE DRIVE Y OBTENER LINK
def subir_a_drive_y_obtener_link(pdf_bytes, filename):
    try:
        credenciales_dic = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        scopes = ["https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(credenciales_dic, scopes=scopes)
        servicio_drive = build('drive', 'v3', credentials=creds)
        
        file_metadata = {'name': filename}
        media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype='application/pdf')
        
        archivo = servicio_drive.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        id_archivo = archivo.get('id')
        
        # Le damos permiso de lectura para que tú y tu jefe puedan abrir el link sin que les pida contraseña
        servicio_drive.permissions().create(fileId=id_archivo, body={'type': 'anyone', 'role': 'reader'}).execute()
        
        return archivo.get('webViewLink')
    except Exception as e:
        st.error(f"⚠️ Error al guardar en la nube (Drive): {e}")
        return None

st.title("🏗️ Centro de Control de Obras")
st.markdown("---")

doc = conectar_sheets()

if doc:
    try:
        hoja_presupuestos = doc.worksheet("Presupuestos")
        hoja_obras = doc.worksheet("Obras_Activas")
        hoja_convenios = doc.worksheet("Convenios_Adicionales")
        hoja_rp = doc.worksheet("Registros_Patronales") 
    except Exception as e:
        st.error("⚠️ Faltan pestañas en tu Excel. Asegúrate de tener 'Obras_Activas' y 'Registros_Patronales'.")
        st.stop()

    datos_presupuestos = hoja_presupuestos.get_all_records()
    datos_obras = hoja_obras.get_all_records()
    datos_rp = hoja_rp.get_all_records() 
    
    llave_folio_pres = next((k for k in (datos_presupuestos[0].keys() if datos_presupuestos else []) if "FOLIO" in str(k).upper()), None)
    folios_disponibles = [str(fila[llave_folio_pres]) for fila in datos_presupuestos if str(fila.get(llave_folio_pres, "")) != ""] if llave_folio_pres else []

    llave_folio_obra = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "FOLIO" in str(k).upper()), None)
    llave_estatus = next((k for k in (datos_obras[0].keys() if datos_obras else []) if "ESTATUS" in str(k).upper()), None)
    obras_activas = [str(fila[llave_folio_obra]) for fila in datos_obras if str(fila.get(llave_estatus, "")).upper() == "EN EJECUCIÓN"] if llave_folio_obra and llave_estatus else []

    lista_rps = [f'{str(r.get("Registro Patronal", ""))} - {str(r.get("Razón Social", ""))}' for r in datos_rp if str(r.get("Registro Patronal", "")) != ""]

    tab1, tab2, tab3, tab4 = st.tabs(["🚀 Apertura de Obra", "📝 Convenios (Trabajos Extra)", "🏁 Cierre de Proyecto", "🏛️ Catálogo Registros Patronales"])

    # ==========================================
    # PESTAÑA 1: APERTURA DE OBRA
    # ==========================================
    with tab1:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Dar de alta nueva obra")
            folio_seleccionado = st.selectbox("Folio Aprobado:", ["Selecciona un folio..."] + folios_disponibles)

        if folio_seleccionado != "Selecciona un folio...":
            datos_obra = next((item for item in datos_presupuestos if str(item.get(llave_folio_pres, "")) == folio_seleccionado), None)
            if datos_obra:
                with col2:
                    with st.form("form_apertura_obra"):
                        llave_cliente = next((k for k in datos_obra.keys() if "CLIENTE" in str(k).upper()), None)
                        cliente_obtenido = datos_obra.get(llave_cliente, "N/A") if llave_cliente else "N/A"

                        llave_proyecto = next((k for k in datos_obra.keys() if any(p in str(k).upper() for p in ["PROYECTO", "UBICACI", "OBRA", "CONCEPTO", "DESCRIPCI"])), None)
                        proyecto_obtenido = datos_obra.get(llave_proyecto, "N/A") if llave_proyecto else "N/A"

                        llave_monto = next((k for k in datos_obra.keys() if any(p in str(k).upper() for p in ["TOTAL", "PRESUPUESTO", "MONTO"])), None)
                        monto_obtenido = datos_obra.get(llave_monto, 0.0) if llave_monto else 0.0

                        st.write(f"**Cliente:** {cliente_obtenido}")
                        st.write(f"**Proyecto:** {proyecto_obtenido}")
                        
                        fecha_inicio = st.date_input("Fecha Oficial de Arranque")
                        residente = st.text_input("Nombre del Residente / Encargado")
                        
                        if not lista_rps:
                            st.warning("⚠️ No hay Registros Patronales dados de alta. Ve a la pestaña 'Catálogo Registros Patronales' para agregarlos primero.")
                            registro_patronal_sel = ""
                        else:
                            registro_patronal_sel = st.selectbox("Registro Patronal IMSS Asignado:", lista_rps)
                        
                        registro_obra = st.text_input("Registro de Obra (SIROC / Número de Contrato)")
                        
                        boton_arranque = st.form_submit_button("🚀 INICIAR PROYECTO")
                        
                        if boton_arranque:
                            if not residente or not registro_patronal_sel or not registro_obra: 
                                st.warning("⚠️ Debes asignar el residente, el Registro Patronal IMSS y el Registro de Obra.")
                            else:
                                rp_final = registro_patronal_sel.split(" - ")[0].strip()
                                
                                hoja_obras.append_row([
                                    folio_seleccionado, cliente_obtenido, proyecto_obtenido,
                                    "EN EJECUCIÓN", monto_obtenido, fecha_inicio.strftime("%d/%m/%Y"), 
                                    residente.upper(), rp_final.upper(), registro_obra.upper()
                                ])
                                
                                registrar_bitacora(doc, "Gestor de Obras", f"Dio de alta la obra {folio_seleccionado} (RP: {rp_final.upper()}, SIROC: {registro_obra.upper()})")
                                
                                st.success(f"¡Obra dada de alta con éxito! RP: {rp_final.upper()} | Registro Obra: {registro_obra.upper()}")

    # ==========================================
    # PESTAÑA 2: CONVENIOS
    # ==========================================
    with tab2:
        colA, colB = st.columns([1, 2])
        with colA:
            st.subheader("Modificación de Presupuesto")
            folio_convenio = st.selectbox("Selecciona la Obra Activa:", ["..."] + obras_activas, key="sel_conv")
            
        if folio_convenio != "...":
            obra_a_modificar = next((item for item in datos_obras if str(item.get(llave_folio_obra, "")) == folio_convenio), None)
            if obra_a_modificar:
                llave_monto = next((k for k in obra_a_modificar.keys() if "PRESUPUESTO" in str(k).upper() or "AUTORIZADO" in str(k).upper() or "MONTO" in str(k).upper()), None)
                presupuesto_actual = limpiar_monto(obra_a_modificar.get(llave_monto, 0)) if llave_monto else 0.0
                
                with colB:
                    st.info(f"📊 **Presupuesto Actual Autorizado:** ${presupuesto_actual:,.2f} MXN")
                    with st.form("form_convenio"):
                        concepto_conv = st.text_input("Concepto del Convenio", placeholder="Ej. Trabajos extra")
                        monto_conv = st.number_input("Monto Adicional ($ MXN)", min_value=0.0, step=500.0)
                        btn_conv = st.form_submit_button("📝 REGISTRAR CONVENIO")
                        
                        if btn_conv:
                            if not concepto_conv or monto_conv <= 0: st.warning("Escribe un concepto y monto válido.")
                            else:
                                fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
                                hoja_convenios.append_row([fecha_hoy, folio_convenio, concepto_conv.upper(), monto_conv])
                                nuevo_presupuesto = presupuesto_actual + monto_conv
                                
                                fila_excel = next((i + 2 for i, f in enumerate(datos_obras) if str(f.get(llave_folio_obra, "")) == folio_convenio), 0)
                                col_excel = list(datos_obras[0].keys()).index(llave_monto) + 1 if datos_obras and llave_monto in datos_obras[0] else 0
                                
                                if fila_excel > 0 and col_excel > 0:
                                    hoja_obras.update_cell(fila_excel, col_excel, nuevo_presupuesto)
                                    registrar_bitacora(doc, "Gestor de Obras", f"Registró convenio en {folio_convenio} por ${monto_conv:,.2f}. Concepto: {concepto_conv.upper()}")
                                    st.success(f"✅ Presupuesto elevado a ${nuevo_presupuesto:,.2f}")
                                    st.rerun()

    # ==========================================
    # PESTAÑA 3: CIERRE DE OBRA Y GENERACIÓN PDF (ACTUALIZADA)
    # ==========================================
    with tab3:
        colX, colY = st.columns([1, 2])
        with colX:
            st.subheader("Selección de Obra a Cerrar")
            folio_cierre = st.selectbox("Obra a Finalizar:", ["..."] + obras_activas, key="sel_cierre") if obras_activas else "..."
            
            # 🚀 NUEVO: Subida de la carta / responsiva firmada
            if folio_cierre != "...":
                st.markdown("---")
                st.write("📷 **Evidencia de Cierre (Opcional)**")
                foto_responsiva = st.file_uploader("Sube la foto o escaneo de la responsiva firmada por el cliente:", type=["jpg", "jpeg", "png", "pdf"])

        if folio_cierre != "...":
            obra_a_cerrar = next((item for item in datos_obras if str(item.get(llave_folio_obra, "")) == folio_cierre), None)
            if obra_a_cerrar:
                llave_cliente = next((k for k in obra_a_cerrar.keys() if "CLIENTE" in str(k).upper()), None)
                cliente_cierre = obra_a_cerrar.get(llave_cliente, "Estimado Cliente") if llave_cliente else "Estimado Cliente"

                llave_proyecto = next((k for k in obra_a_cerrar.keys() if any(p in str(k).upper() for p in ["PROYECTO", "UBICACI", "OBRA", "CONCEPTO"])), None)
                proyecto_cierre = obra_a_cerrar.get(llave_proyecto, "Proyecto Especificado") if llave_proyecto else "Proyecto Especificado"
                
                with colY:
                    st.info(f"Vas a cerrar definitivamente la obra de **{cliente_cierre}**.")
                    if st.button("🔒 CERRAR OBRA, GUARDAR Y GENERAR CARTA", type="primary"):
                        with st.spinner("Ensamblando PDF, subiendo a la nube y actualizando Excel..."):
                            
                            # 1. Generamos el PDF base (La Carta de Agradecimiento)
                            pdf = PDF_Carta()
                            pdf.add_page()
                            fecha_hoy = datetime.datetime.now().strftime("%d de %B del %Y")
                            
                            pdf.set_font('Arial', '', 11)
                            pdf.cell(0, 5, f"Veracruz, Ver. a {fecha_hoy}", ln=True, align='R')
                            pdf.ln(15)
                            pdf.set_font('Arial', 'B', 12)
                            pdf.set_text_color(15, 60, 140)
                            pdf.cell(0, 6, f"ATENCIÓN: {str(cliente_cierre).upper()}", ln=True)
                            pdf.set_font('Arial', 'B', 10)
                            pdf.set_text_color(100, 100, 100)
                            pdf.cell(0, 6, f"REF: Cierre de Proyecto - Folio {folio_cierre}", ln=True)
                            pdf.ln(10)
                            
                            pdf.set_font('Arial', '', 11)
                            pdf.set_text_color(50, 50, 50)
                            texto_cuerpo = (
                                f"Por medio de la presente, el equipo directivo y operativo de TARC S.A. de C.V. (Grupo IMAC) "
                                f"le extiende nuestro más sincero agradecimiento por la confianza depositada en nosotros para la "
                                f"ejecución de la obra: '{proyecto_cierre}'.\n\n"
                                f"Hacemos de su conocimiento que los trabajos han sido concluidos satisfactoriamente. "
                                f"Nuestro compromiso es brindarle la más alta calidad en materiales y mano de obra, esperando que el resultado final cumpla y supere sus expectativas.\n\n"
                                f"Quedamos a su entera disposición para futuros proyectos y garantías correspondientes.\n\n"
                                f"Sin más por el momento, le enviamos un cordial saludo."
                            )
                            pdf.multi_cell(0, 6, txt=texto_cuerpo)
                            pdf.ln(25)
                            pdf.set_font('Arial', 'B', 11)
                            pdf.set_text_color(15, 60, 140)
                            pdf.cell(0, 5, "Atentamente,", ln=True, align='C')
                            pdf.ln(10)
                            pdf.cell(0, 5, "___________________________________", ln=True, align='C')
                            pdf.cell(0, 5, "Departamento de Operaciones", ln=True, align='C')
                            pdf.cell(0, 5, "TARC S.A. DE C.V.", ln=True, align='C')

                            pdf_base_bytes = pdf.output(dest='S').encode('latin-1')
                            pdf_final_bytes = pdf_base_bytes

                            # 2. Si el residente subió una foto de la responsiva, la fusionamos
                            if foto_responsiva:
                                fusionador = PdfMerger()
                                fusionador.append(io.BytesIO(pdf_base_bytes))
                                
                                ext = foto_responsiva.name.split('.')[-1].lower()
                                if ext in ['jpg', 'jpeg', 'png']:
                                    img = Image.open(foto_responsiva)
                                    if img.mode == 'RGBA': 
                                        img = img.convert('RGB')
                                    img_pdf_io = io.BytesIO()
                                    img.save(img_pdf_io, format='PDF')
                                    img_pdf_io.seek(0)
                                    fusionador.append(img_pdf_io)
                                elif ext == 'pdf':
                                    fusionador.append(io.BytesIO(foto_responsiva.getvalue()))
                                    
                                archivo_salida = io.BytesIO()
                                fusionador.write(archivo_salida)
                                fusionador.close()
                                pdf_final_bytes = archivo_salida.getvalue()

                            # 3. Subimos el PDF fusionado a Google Drive
                            link_drive = subir_a_drive_y_obtener_link(pdf_final_bytes, f"Cierre_{folio_cierre}_{cliente_cierre}.pdf")

                            # 4. Actualizamos el Estatus y pegamos el Link en tu Excel
                            fila_excel = next((i + 2 for i, f in enumerate(datos_obras) if str(f.get(llave_folio_obra, "")) == folio_cierre), 0)
                            col_estatus = list(datos_obras[0].keys()).index(llave_estatus) + 1 if datos_obras and llave_estatus in datos_obras[0] else 0
                            
                            if fila_excel > 0 and col_estatus > 0:
                                hoja_obras.update_cell(fila_excel, col_estatus, "CERRADA")
                                
                                # Buscamos la columna "LINK CARTA" que agregaste en tu Excel
                                headers_obras = list(datos_obras[0].keys()) if datos_obras else []
                                col_link = next((i + 1 for i, h in enumerate(headers_obras) if "LINK" in str(h).upper() or "CARTA" in str(h).upper()), None)
                                
                                if col_link and link_drive:
                                    hoja_obras.update_cell(fila_excel, col_link, link_drive)
                                
                                registrar_bitacora(doc, "Gestor de Obras", f"Cerró definitivamente la obra {folio_cierre}. Documento guardado en Nube.")
                                
                            st.success(f"✅ ¡La obra {folio_cierre} ha sido marcada como CERRADA exitosamente!")
                            if link_drive:
                                st.info(f"☁️ Documento guardado de por vida en la nube. Puedes verlo desde tu Excel.")
                                
                            st.download_button(
                                label="📥 DESCARGAR DOCUMENTO FINAL", 
                                data=pdf_final_bytes, 
                                file_name=f"Cierre_Oficial_{folio_cierre}.pdf", 
                                mime="application/pdf"
                            )

    # ==========================================
    # 🚀 PESTAÑA 4: ALTA DE REGISTROS PATRONALES
    # ==========================================
    with tab4:
        st.subheader("🏛️ Alta de Registros Patronales (IMSS)")
        st.write("Agrega aquí los Registros Patronales (RP) de la empresa o subcontratistas. Al guardarlos, aparecerán como opción múltiple al dar de alta una nueva obra.")
        
        with st.form("form_alta_rp"):
            col1, col2 = st.columns(2)
            with col1:
                nuevo_rp = st.text_input("Clave del Registro Patronal", placeholder="Ej. Y545678910")
            with col2:
                razon_social = st.text_input("Razón Social / Empresa Asociada", placeholder="Ej. TARC S.A. DE C.V.")
            
            notas_rp = st.text_input("Notas o Detalles (Opcional)")
            
            btn_rp = st.form_submit_button("💾 GUARDAR REGISTRO PATRONAL")
            
            if btn_rp:
                if not nuevo_rp or not razon_social:
                    st.error("⚠️ La Clave del RP y la Razón Social son obligatorias.")
                else:
                    claves_existentes = [str(r.get("Registro Patronal", "")).upper() for r in datos_rp]
                    if nuevo_rp.upper() in claves_existentes:
                        st.error(f"⚠️ El Registro Patronal {nuevo_rp.upper()} ya existe en la base de datos.")
                    else:
                        hoja_rp.append_row([nuevo_rp.upper(), razon_social.upper(), notas_rp])
                        registrar_bitacora(doc, "Gestor de Obras", f"Dio de alta el Registro Patronal {nuevo_rp.upper()} ({razon_social.upper()})")
                        st.success(f"✅ Registro Patronal {nuevo_rp.upper()} agregado exitosamente al catálogo.")
                        st.rerun()
        
        st.markdown("---")
        st.subheader("📋 Catálogo Actual de Registros Patronales")
        if datos_rp:
            st.dataframe(pd.DataFrame(datos_rp), use_container_width=True, hide_index=True)
        else:
            st.info("Aún no hay registros patronales guardados.")
