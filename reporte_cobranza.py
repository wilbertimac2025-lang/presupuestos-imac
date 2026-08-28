import gspread
from google.oauth2.service_account import Credentials
import json
import datetime
import smtplib
from email.message import EmailMessage
import streamlit as st

def enviar_reporte_cobranza():
    try:
        # 1. CONEXIÓN A GOOGLE SHEETS UTILIZANDO TUS SECRETOS DE RENDER
        credenciales_dic = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(credenciales_dic, scopes=scopes)
        cliente = gspread.authorize(creds)
        
        ID_DEL_EXCEL = "1-grdT2H5dBlGVPvJbZ5wVYDdtVjQEEmUPGpvEm6C0Gc" 
        doc = cliente.open_by_key(ID_DEL_EXCEL)

        # 2. LEER DATOS DE PRESUPUESTOS Y FACTURAS
        hoja_presupuestos = doc.worksheet("Presupuestos")
        hoja_facturas = doc.worksheet("Facturas_Obras")

        filas_presupuestos = hoja_presupuestos.get_all_records()
        filas_facturas = hoja_facturas.get_all_records()

        # Extraer costo total por obra
        obras_totales = {}
        for fila in filas_presupuestos:
            # Detectar la columna del folio (normalmente es la primera)
            claves = list(fila.keys())
            folio = str(fila.get(claves[0], "")).strip()
            
            # Buscar el costo total (asumiendo que la columna dice "TOTAL" o similar)
            total = 0.0
            for k, v in fila.items():
                if "TOTAL" in str(k).upper() or "INVERSIÓN" in str(k).upper():
                    try:
                        total = float(str(v).replace("$", "").replace(",", "").strip())
                    except: pass
            if folio:
                obras_totales[folio] = total

        # Sumar los pagos/anticipos realizados por obra
        obras_pagadas = {}
        for fila in filas_facturas:
            folio_obra = str(fila.get("Folio Obra", "")).strip()
            monto = 0.0
            try:
                monto = float(str(fila.get("Monto Facturado", 0)).replace("$", "").replace(",", "").strip())
            except: pass
            
            if folio_obra:
                obras_pagadas[folio_obra] = obras_pagadas.get(folio_obra, 0.0) + monto

        # 3. CALCULAR SALDOS PENDIENTES
        reporte_lineas = []
        gran_total_pendiente = 0.0

        for folio, costo_total in obras_totales.items():
            pagado = obras_pagadas.get(folio, 0.0)
            saldo_pendiente = costo_total - pagado
            
            # Solo metemos al reporte las obras que aún deben dinero
            if saldo_pendiente > 0: 
                gran_total_pendiente += saldo_pendiente
                reporte_lineas.append(f"• Obra: {folio} | Costo: ${costo_total:,.2f} | Cobrado: ${pagado:,.2f} | 🔴 Pendiente: ${saldo_pendiente:,.2f}")

        # Armar el texto del correo
        if not reporte_lineas:
            cuerpo_mensaje = "¡Excelente noticia equipo! No hay saldos pendientes por cobrar en ninguna obra activa en este momento."
        else:
            cuerpo_mensaje = (
                "Estimado equipo directivo y comercial,\n\n"
                "A continuación se presenta el estado de cuenta y saldos pendientes de las obras activas:\n\n" +
                "\n".join(reporte_lineas) +
                f"\n\n💰 SALDO GLOBAL PENDIENTE DE COBRO: ${gran_total_pendiente:,.2f} MXN\n\n" +
                "Por favor dar seguimiento a la cobranza con los clientes correspondientes.\n\n"
                "Atentamente,\nERP Grupo IMAC"
            )

        # 4. CONFIGURACIÓN DE CORREOS
        remitente = st.secrets["CORREO_BOT"] 
        password = st.secrets["PASS_BOT"]              
        
        # Correos institucionales a los que llegará el reporte
        destinatarios = [
            "comercial@grupo-imac.com",
            "direccion@ejemplo-imac.com",
            "finanzas@ejemplo-imac.com",
            "auditoria@ejemplo-imac.com"
        ]

        msg = EmailMessage()
        msg['Subject'] = f'📊 REPORTE DE COBRANZA - GRUPO IMAC ({datetime.datetime.now().strftime("%d/%m/%Y")})'
        msg['From'] = remitente
        msg['To'] = ", ".join(destinatarios)
        msg.set_content(cuerpo_mensaje)

        # Disparo del correo
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls()
            smtp.login(remitente, password)
            smtp.send_message(msg)
            
        print("✅ Reporte de cobranza enviado con éxito.")
        return True
    except Exception as e:
        print(f"❌ Error al enviar reporte: {e}")
        return False

if __name__ == "__main__":
    enviar_reporte_cobranza()
