import streamlit as st
from supabase import create_client, Client
import pandas as pd
from fpdf import FPDF
from datetime import datetime, timedelta
import os
import json
import unicodedata

# ==========================================
# 🔗 CONFIGURACIÓN DE FEEDBACK (TU ENLACE TALLY)
# ==========================================
LINK_FEEDBACK = "https://tally.so/r/MeDqZX" 

# ==========================================
# 📝 DATOS DE LA EMPRESA
# ==========================================
LAB_NOMBRE = "Laboratorio de Análisis Clínicos Santa Fe"
LAB_DIRECCION = "Calle Miguel Cabrera 409 D, Col. Centro, Oaxaca de Juárez, Oaxaca"
LAB_CONTACTO = "Tel: 9511895316 | labclinicosantafe@gmail.com"
LAB_LEYENDA_LEGAL = "Responsable Sanitario: QB. Olga Lidia Mendoza Velázquez. Cédula Prof: 1234567."

# ==========================================
# 🔽 CONFIGURACIÓN DE LISTAS ESTÁNDAR
# ==========================================
OPCIONES_BASE = {
    "lugar_proceso": ["Laboratorio Santa Fe", "Referencia (Maquila)", "Gabinete Externo"],
    "tipo_muestra": [
        "Suero", "Sangre Total (EDTA)", "Sangre Total (Heparina)", "Plasma (Citrato)",
        "Plasma (EDTA)", "Orina (Casual)", "Orina (24 Horas)", "Heces / Materia Fecal",
        "Exudado Faríngeo", "Exudado Vaginal / Uretral", "Esputo", "Otro"
    ],
    "temperatura": ["Ambiente", "Refrigerada (2-8°C)", "Congelada (-20°C)"],
    "tiempo_proceso": ["1 hora", "2 horas", "4 horas", "8 horas", "24 horas", "1 día", "2 días", "3 días", "5 días"],
    "tiempo_entrega": ["Mismo día", "Día siguiente (24h)", "2 días hábiles", "3 a 5 días hábiles", "1 semana"]
}

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sistema de Laboratorio", layout="wide", page_icon="🧬", initial_sidebar_state="expanded")

# --- ESTILOS CSS ---
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .precio-lista { font-weight: bold; color: #333; }
    div[data-testid="stForm"] { border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px; }
    button[title="Editar"] { border-color: #4CAF50; color: #4CAF50; }
    /* Ajuste para que el scroll interno se vea limpio */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        scrollbar-width: thin;
    }
    /* Estilo para tus créditos */
    .credits { font-size: 12px; color: #666; margin-top: 20px; margin-bottom: 10px; }
    .credits b { color: #333; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- CONEXIÓN SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- UTILIDADES ---
def normalizar_texto(texto):
    if not isinstance(texto, str): return str(texto)
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower().strip()

# --- FUNCIONES BASE DE DATOS (CRUD) ---
def guardar_en_supabase(paciente, total, descuento_tipo):
    if not paciente:
        st.error("⚠️ Falta el nombre del paciente.")
        return False
    datos = {
        "nombre_paciente": paciente,
        "total": total,
        "tipo_descuento": descuento_tipo,
        "items": st.session_state['carrito'],
        "estado": "Pendiente"
    }
    try:
        supabase.table("cotizaciones").insert(datos).execute()
        st.success(f"✅ Cotización creada.")
        st.session_state['carrito'] = [] 
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def registrar_estudio(datos):
    try:
        supabase.table("catalogo_servicios").insert(datos).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def actualizar_estudio_bd(id_estudio, datos_actualizados):
    try:
        supabase.table("catalogo_servicios").update(datos_actualizados).eq("id", id_estudio).execute()
        return True
    except Exception as e:
        st.error(f"Error actualizando estudio: {e}")
        return False

def actualizar_cotizacion_completa(id_cot, nuevos_items, nuevo_total, nuevo_tipo_desc):
    try:
        supabase.table("cotizaciones").update({
            "items": nuevos_items,
            "total": nuevo_total,
            "tipo_descuento": nuevo_tipo_desc
        }).eq("id", id_cot).execute()
        return True
    except Exception as e:
        st.error(f"Error guardando cambios: {e}")
        return False

def obtener_historial():
    try:
        response = supabase.table("cotizaciones").select("*").order("created_at", desc=True).limit(50).execute()
        return response.data
    except Exception as e: return []

def actualizar_estado_cotizacion(id_cot, nuevo_estado):
    try:
        supabase.table("cotizaciones").update({"estado": nuevo_estado}).eq("id", id_cot).execute()
        st.toast(f"Estado actualizado", icon="🔄")
        return True
    except Exception as e: return False

def eliminar_cotizacion(id_cot):
    try:
        supabase.table("cotizaciones").delete().eq("id", id_cot).execute()
        st.toast("Eliminado", icon="🗑️")
        return True
    except Exception as e: return False

# --- MOTOR PDF ---
def limpiar_texto(t):
    if not isinstance(t, str): return str(t)
    return t.encode('latin-1', 'replace').decode('latin-1')

class PDF(FPDF):
    def header(self):
        if os.path.exists("logo.png"): self.image('logo.png', 10, 8, 30)
        self.set_xy(45, 10)
        self.set_font('Arial', 'B', 16)
        self.cell(0, 8, limpiar_texto(LAB_NOMBRE), 0, 1, 'L')
        self.set_x(45)
        self.set_font('Arial', '', 9)
        self.cell(0, 5, limpiar_texto(LAB_DIRECCION), 0, 1, 'L')
        self.set_x(45)
        self.cell(0, 5, limpiar_texto(LAB_CONTACTO), 0, 1, 'L')
        self.ln(15)

    def footer(self):
        self.set_y(-25)
        self.set_font('Arial', 'I', 8)
        self.multi_cell(0, 4, limpiar_texto(LAB_LEYENDA_LEGAL), 0, 'C')
        self.set_y(-15)
        self.set_font('Arial', 'B', 8)
        fecha_exp = datetime.now() + timedelta(days=30)
        self.cell(0, 10, f"Vigencia: 30 dias. Valido hasta: {fecha_exp.strftime('%d/%m/%Y')}", 0, 0, 'C')

def generar_pdf(paciente, items, subtotal, desc, total, tipo_desc, fecha_custom=None):
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()
    fecha_str = fecha_custom if fecha_custom else datetime.now().strftime('%d/%m/%Y %H:%M')
    
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, f"Fecha: {fecha_str}", 0, 1, 'R')
    pdf.ln(5)
    pdf.set_fill_color(230, 240, 255)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, limpiar_texto(f"  Paciente: {paciente}"), 0, 1, 'L', 1)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, limpiar_texto(f"  Tarifa aplicada: {tipo_desc}"), 0, 1, 'L')
    pdf.ln(5)
    pdf.set_fill_color(50, 50, 50)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(140, 8, "Estudio / Servicio", 1, 0, 'C', 1)
    pdf.cell(50, 8, "Precio", 1, 1, 'C', 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", size=9)
    for item in items:
        nombre = limpiar_texto(str(item.get('nombre_estudio', 'Estudio')))
        precio = item.get('precio_publico', 0)
        pdf.cell(140, 7, nombre[:85], 1, 0, 'L')
        pdf.cell(50, 7, f"${precio:,.2f}", 1, 1, 'R')
    pdf.ln(5)
    offset = 140
    pdf.set_font("Arial", size=10)
    pdf.cell(offset)
    pdf.cell(25, 6, "Subtotal:", 0, 0, 'R')
    pdf.cell(25, 6, f"${subtotal:,.2f}", 0, 1, 'R')
    if desc > 0:
        pdf.set_text_color(200, 0, 0)
        pdf.cell(offset)
        pdf.cell(25, 6, "Descuento:", 0, 0, 'R')
        pdf.cell(25, 6, f"- ${desc:,.2f}", 0, 1, 'R')
        pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(offset)
    pdf.cell(25, 10, "TOTAL:", 0, 0, 'R')
    pdf.cell(25, 10, f"${total:,.2f}", 1, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

# --- CARGA DATOS ---
@st.cache_data(ttl=600)
def get_data():
    if not supabase: return pd.DataFrame()
    r = supabase.table("catalogo_servicios").select("*").execute()
    df = pd.DataFrame(r.data)
    if not df.empty:
        if 'lugar_proceso' in df.columns:
            df['lugar_proceso'] = df['lugar_proceso'].fillna('').astype(str).str.strip()
        df['search_index'] = df.apply(lambda row: normalizar_texto(f"{row['nombre_estudio']}"), axis=1)
    return df

df = get_data()

if 'carrito' not in st.session_state: st.session_state['carrito'] = []

def agregar_item(item):
    identificador = item.get('id', item['nombre_estudio']) 
    ids_en_carrito = [x.get('id', x['nombre_estudio']) for x in st.session_state['carrito']]
    if identificador not in ids_en_carrito:
        st.session_state['carrito'].append(item)
        st.toast(f"Agregado", icon="✅")

def borrar_item(identificador):
    st.session_state['carrito'] = [x for x in st.session_state['carrito'] if x.get('id', x['nombre_estudio']) != identificador]
    st.rerun()

# ==========================================
# 🛑 MODALES DE EDICIÓN
# ==========================================

@st.dialog("Editar Estudio")
def editar_estudio_dialog(study_data):
    st.caption(f"Editando: {study_data.get('nombre_estudio', 'Registro')}")
    cols_sistema = ['id', 'created_at', 'uuid', 'search_index', 'id_interno', 'clave_interna']
    cols_editables = [c for c in df.columns if c not in cols_sistema]
    updates = {}
    
    with st.form("form_edit_full"):
        cols_grid = st.columns(2)
        for idx, col in enumerate(cols_editables):
            val_actual = study_data.get(col)
            label = col.replace("_", " ").title()
            c_actual = cols_grid[idx % 2]
            with c_actual:
                if col in OPCIONES_BASE:
                    opciones = list(OPCIONES_BASE[col])
                    index_default = 0
                    if val_actual and val_actual not in opciones: opciones.insert(0, val_actual)
                    elif val_actual in opciones: index_default = opciones.index(val_actual)
                    updates[col] = st.selectbox(label, opciones, index=index_default)
                elif pd.api.types.is_numeric_dtype(df[col]):
                    val_num = float(val_actual) if pd.notna(val_actual) else 0.0
                    if pd.api.types.is_integer_dtype(df[col]): updates[col] = st.number_input(label, value=int(val_num), step=1)
                    else: updates[col] = st.number_input(label, value=val_num, format="%.2f")
                elif pd.api.types.is_bool_dtype(df[col]):
                    val_bool = bool(val_actual) if pd.notna(val_actual) else False
                    updates[col] = st.checkbox(label, value=val_bool)
                else:
                    val_str = str(val_actual) if pd.notna(val_actual) else ""
                    updates[col] = st.text_input(label, value=val_str)
        st.divider()
        if st.form_submit_button("💾 Guardar Cambios"):
            if actualizar_estudio_bd(study_data['id'], updates):
                st.success("Estudio actualizado.")
                st.cache_data.clear()
                st.rerun()

@st.dialog("Modificar Cotización Completa")
def editar_cotizacion_dialog(cot_data):
    st.caption(f"Paciente: {cot_data['nombre_paciente']}")
    key_items = f"edit_items_{cot_data['id']}"
    if key_items not in st.session_state:
        st.session_state[key_items] = cot_data['items']

    st.subheader("1. Modificar Estudios")
    current_items = st.session_state[key_items]
    if not current_items:
        st.warning("La cotización está vacía.")
    else:
        for idx, item in enumerate(current_items):
            c1, c2, c3 = st.columns([4, 2, 1])
            c1.text(item['nombre_estudio'])
            c2.text(f"${item.get('precio_publico', 0):,.2f}")
            if c3.button("🗑️", key=f"del_edit_{cot_data['id']}_{idx}"):
                st.session_state[key_items].pop(idx)
                st.rerun()
    
    st.markdown("---")
    c_search, c_add = st.columns([4, 1])
    opciones_estudios = df['nombre_estudio'].tolist() if not df.empty else []
    study_add = c_search.selectbox("Agregar estudio:", opciones_estudios, key=f"search_add_{cot_data['id']}", index=None, placeholder="Escribe para buscar...")
    
    if c_add.button("Agregar", key=f"btn_add_{cot_data['id']}"):
        if study_add:
            row = df[df['nombre_estudio'] == study_add].iloc[0]
            nuevo_item = {
                "id": int(row.get('id', 0)),
                "nombre_estudio": row['nombre_estudio'],
                "precio_publico": float(row['precio_publico'])
            }
            st.session_state[key_items].append(nuevo_item)
            st.rerun()

    st.markdown("---")
    st.subheader("2. Recalcular Totales")
    subtotal_calc = sum([float(x.get('precio_publico', 0)) for x in st.session_state[key_items]])
    
    descuentos = {"Público General": 0, "👴 INAPAM (10%)": 0.10, "🤝 Convenio (15%)": 0.15, "💐 Promo (20%)": 0.20, "💎 Médico (25%)": 0.25}
    idx_desc = 0
    if cot_data['tipo_descuento'] in descuentos:
        idx_desc = list(descuentos.keys()).index(cot_data['tipo_descuento'])
    
    new_tipo_desc = st.selectbox("Tarifa Aplicada:", list(descuentos.keys()), index=idx_desc, key=f"desc_{cot_data['id']}")
    new_tasa = descuentos[new_tipo_desc]
    desc_monto = subtotal_calc * new_tasa
    new_total = subtotal_calc - desc_monto
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Subtotal", f"${subtotal_calc:,.2f}")
    c2.metric("Descuento", f"-${desc_monto:,.2f}")
    c3.metric("Nuevo Total", f"${new_total:,.2f}")
    
    if st.button("💾 Guardar Cambios Definitivos", type="primary", use_container_width=True):
        if actualizar_cotizacion_completa(cot_data['id'], st.session_state[key_items], new_total, new_tipo_desc):
            st.success("¡Cotización actualizada con éxito!")
            del st.session_state[key_items]
            st.rerun()

# ==========================================
# 🖥️ ESTRUCTURA PRINCIPAL
# ==========================================
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.image("https://cdn-icons-png.flaticon.com/512/3004/3004458.png", width=50)
        
    st.header("Laboratorio Santa Fe")
    menu_seleccionado = st.radio(
        "Ir a:",
        ["📝 Cotizador y Catálogo", "🗄️ Historial Guardado", "➕ Alta de Estudios", "🛠️ Sanitización de Datos"],
        index=0
    )
    
    # CRÉDITOS Y FEEDBACK INTEGRADOS
    st.markdown("---")
    st.markdown("""
        <div class='credits'>
            Desarrollado por:<br>
            <b>Francisco Javier García Santos</b>
        </div>
    """, unsafe_allow_html=True)
    
    with st.expander("💬 Feedback / Soporte"):
        st.markdown(f"¿Tienes una idea o encontraste un error?<br>[👉 Ir al Formulario de Mejora]({LINK_FEEDBACK})", unsafe_allow_html=True)

# ---------------------------------------------------------
# VISTA 1: COTIZADOR (LAYOUT INMOVILIZADO)
# ---------------------------------------------------------
if menu_seleccionado == "📝 Cotizador y Catálogo":
    st.title("📝 Cotizador de Estudios")
    col_catalogo, col_cotizador = st.columns([1.5, 1], gap="medium")

    with col_catalogo:
        st.subheader("📂 Catálogo")
        c1, c2 = st.columns([1, 2])
        opciones_lab = ["Todos"]
        if not df.empty and 'lugar_proceso' in df.columns: opciones_lab += sorted(df['lugar_proceso'].unique().tolist())
        filtro_lab = c1.selectbox("Filtrar Origen", opciones_lab)
        busqueda = c2.text_input("🔍 Buscar...", placeholder="Escribe nombre del estudio...")

        df_ver = df.copy() if not df.empty else pd.DataFrame()
        if not df_ver.empty:
            if filtro_lab != "Todos": df_ver = df_ver[df_ver['lugar_proceso'] == filtro_lab]
            if busqueda:
                q = normalizar_texto(busqueda)
                df_ver = df_ver[df_ver['search_index'].str.contains(q)]
        
        st.divider()
        
        # SCROLL INTERNO (600px)
        with st.container(height=600, border=False):
            if df_ver.empty: st.warning("No hay resultados")
            else:
                h1, h2, h3, h4 = st.columns([4, 1.5, 1.5, 1.2])
                h1.caption("**Estudio**")
                h2.caption("**Tiempo**")
                h3.caption("**Precio**")
                
                for i, row in df_ver.iterrows():
                    with st.container():
                        c_nom, c_t, c_pre, c_btn = st.columns([4, 1.5, 1.5, 1.2])
                        lugar = str(row.get('lugar_proceso',''))
                        badge_cls = "badge-int" if "santa fe" in lugar.lower() else "badge-ref"
                        badge_txt = "INT" if "santa fe" in lugar.lower() else f"REF"
                        c_nom.markdown(f"**{row['nombre_estudio']}** <span class='{badge_cls}'>{badge_txt}</span>", unsafe_allow_html=True)
                        
                        tiempo_mostrar = row.get('tiempo_entrega', row.get('tiempo_proceso', '-'))
                        if pd.isna(tiempo_mostrar) or tiempo_mostrar == 'nan': tiempo_mostrar = '-'
                        c_t.text(tiempo_mostrar)
                        
                        precio = row['precio_publico']
                        c_pre.markdown(f"<span class='precio-lista'>${precio:,.2f}</span>", unsafe_allow_html=True)
                        
                        sys_id = row.get('id', i)
                        col_add, col_edit = c_btn.columns(2)
                        if col_add.button("➕", key=f"add_{sys_id}"):
                            item = {"id": sys_id, "nombre_estudio": row['nombre_estudio'], "precio_publico": precio if pd.notna(precio) else 0}
                            agregar_item(item)
                        if col_edit.button("✏️", key=f"edit_st_{sys_id}", help="Editar estudio"):
                            editar_estudio_dialog(row)
                        st.markdown("---")

    with col_cotizador:
        with st.container(border=True):
            st.header("🧾 Nueva Cotización")
            paciente = st.text_input("👤 Paciente:", placeholder="Nombre completo")
            descuentos = {"Público General": 0, "👴 INAPAM (10%)": 0.10, "🤝 Convenio (15%)": 0.15, "💐 Promo (20%)": 0.20, "💎 Médico (25%)": 0.25}
            sel_desc = st.selectbox("Tarifa:", list(descuentos.keys()))
            tasa = descuentos[sel_desc]
            st.divider()
            
            # SCROLL CARRITO
            with st.container(height=300, border=False):
                if not st.session_state['carrito']: st.info("Agrega estudios.")
                else:
                    cart = pd.DataFrame(st.session_state['carrito'])
                    subtotal = cart['precio_publico'].sum()
                    total_desc = subtotal * tasa
                    total = subtotal - total_desc
                    for item in st.session_state['carrito']:
                        c1, c2, c3 = st.columns([3, 1, 0.5])
                        c1.text(item['nombre_estudio'][:20]+"..")
                        c2.text(f"${item['precio_publico']:,.0f}")
                        sys_id = item.get('id', item['nombre_estudio'])
                        if c3.button("x", key=f"del_{sys_id}"): borrar_item(sys_id)
            
            st.divider()
            if st.session_state['carrito']:
                st.metric("Total", f"${total:,.2f}")
                col_save, col_pdf = st.columns(2)
                if col_save.button("💾 Guardar", use_container_width=True):
                    guardar_en_supabase(paciente, float(total), sel_desc)
                pdf_data = generar_pdf(paciente or "Público", st.session_state['carrito'], subtotal, total_desc, total, sel_desc)
                col_pdf.download_button("📄 PDF", data=pdf_data, file_name=f"Cotizacion.pdf", mime="application/pdf", use_container_width=True)

# ---------------------------------------------------------
# VISTA 2: HISTORIAL
# ---------------------------------------------------------
elif menu_seleccionado == "🗄️ Historial Guardado":
    st.title("🗄️ Historial y Control de Estatus")
    if st.button("🔄 Actualizar Tabla"): st.rerun()
    historial = obtener_historial()
    if not historial: st.info("No hay cotizaciones.")
    else:
        search_hist = st.text_input("🔍 Buscar en historial:")
        c1, c2, c3, c4 = st.columns([1.5, 2.5, 1.5, 2.5])
        c1.markdown("**Fecha**")
        c2.markdown("**Paciente**")
        c3.markdown("**Estado**")
        c4.markdown("**Acciones**")
        st.divider()
        for cot in historial:
            if search_hist and normalizar_texto(search_hist) not in normalizar_texto(cot['nombre_paciente']): continue
            with st.container():
                c1, c2, c3, c4 = st.columns([1.5, 2.5, 1.5, 2.5])
                fecha_obj = datetime.fromisoformat(cot['created_at'].replace('Z', '+00:00'))
                c1.text(fecha_obj.strftime("%d/%m %H:%M"))
                c2.markdown(f"**{cot['nombre_paciente']}**")
                c2.caption(f"Total: ${cot['total']:,.2f}")
                if c2.button("✏️ Editar Completa", key=f"edit_cot_{cot['id']}"): editar_cotizacion_dialog(cot)
                estado_actual = cot.get('estado', 'Pendiente')
                opciones_estado = ["Pendiente", "Atendido", "Cancelada"]
                idx = opciones_estado.index(estado_actual) if estado_actual in opciones_estado else 0
                nuevo_estado = c3.selectbox("Estado", opciones_estado, key=f"st_{cot['id']}", index=idx, label_visibility="collapsed")
                if nuevo_estado != estado_actual:
                    actualizar_estado_cotizacion(cot['id'], nuevo_estado)
                    st.rerun()
                with c4:
                    col_ver, col_del = st.columns([3, 1])
                    with col_ver:
                        with st.expander("Ver / PDF"):
                            items = cot['items']
                            if items:
                                for i in items: st.text(f"• {i['nombre_estudio']}")
                                sub = sum([x.get('precio_publico', 0) for x in items])
                                pdf = generar_pdf(cot['nombre_paciente'], items, sub, sub - cot['total'], cot['total'], cot['tipo_descuento'], fecha_custom=fecha_obj.strftime("%d/%m/%Y %H:%M"))
                                st.download_button("📄 Imprimir", data=pdf, file_name=f"Nota_{cot['nombre_paciente']}.pdf", mime="application/pdf", key=f"pdf_{cot['id']}")
                    with col_del:
                         with st.popover("🗑️", help="Eliminar registro"):
                            st.markdown("¿Borrar permanentemente?")
                            if st.button("Sí, eliminar", key=f"confirm_del_{cot['id']}", type="primary"):
                                eliminar_cotizacion(cot['id'])
                                st.rerun()
                st.divider()

# ---------------------------------------------------------
# VISTA 3: ALTA
# ---------------------------------------------------------
elif menu_seleccionado == "➕ Alta de Estudios":
    st.title("➕ Alta de Nuevos Estudios")
    st.info("Formulario con Deduplicación Inteligente.")
    if df.empty: st.error("Error de conexión.")
    else:
        cols_sistema = ['id', 'created_at', 'uuid', 'search_index', 'id_interno', 'clave_interna']
        columnas_validas = [c for c in df.columns if c not in cols_sistema]
        with st.form("form_alta", clear_on_submit=True):
            st.subheader("Datos del Estudio")
            datos_a_insertar = {}
            cols_form = st.columns(2)
            for idx, col_nombre in enumerate(columnas_validas):
                col_tipo = df[col_nombre].dtype
                c_actual = cols_form[idx % 2]
                label = col_nombre.replace("_", " ").title()
                with c_actual:
                    if col_nombre in OPCIONES_BASE:
                        opciones_menu = list(OPCIONES_BASE[col_nombre])
                        opciones_base_norm = {normalizar_texto(x) for x in opciones_menu}
                        if not df[col_nombre].dropna().empty:
                            valores_bd = df[col_nombre].dropna().unique().tolist()
                            for val in valores_bd:
                                val_norm = normalizar_texto(str(val))
                                if val_norm not in opciones_base_norm:
                                    opciones_menu.append(val)
                                    opciones_base_norm.add(val_norm)
                        opciones_menu.sort(key=str)
                        opciones_menu.append("✏️ Otro (Escribir nuevo...)")
                        seleccion = st.selectbox(label, opciones_menu)
                        if seleccion == "✏️ Otro (Escribir nuevo...)": datos_a_insertar[col_nombre] = st.text_input(f"Escribe el nuevo {label}:")
                        else: datos_a_insertar[col_nombre] = seleccion
                    elif pd.api.types.is_numeric_dtype(col_tipo):
                        if pd.api.types.is_integer_dtype(col_tipo): datos_a_insertar[col_nombre] = st.number_input(label, step=1, value=0)
                        else: datos_a_insertar[col_nombre] = st.number_input(label, format="%.2f", value=0.0)
                    elif pd.api.types.is_bool_dtype(col_tipo): datos_a_insertar[col_nombre] = st.checkbox(label)
                    else: datos_a_insertar[col_nombre] = st.text_input(label)
            st.divider()
            submitted = st.form_submit_button("💾 Registrar Estudio")
            if submitted:
                datos_limpios = {}
                for k, v in datos_a_insertar.items():
                    if isinstance(v, str): datos_limpios[k] = v.strip()
                    else: datos_limpios[k] = v
                if registrar_estudio(datos_limpios):
                    st.success("✅ Estudio registrado.")
                    st.cache_data.clear()
                    st.rerun()

# ---------------------------------------------------------
# VISTA 4: SANITIZACIÓN
# ---------------------------------------------------------
elif menu_seleccionado == "🛠️ Sanitización de Datos":
    st.title("🛠️ Sanitización y Limpieza de Datos")
    st.warning("⚠️ Zona de Mantenimiento.")
    if df.empty: st.error("Base de datos vacía.")
    else:
        cols_limpiables = list(OPCIONES_BASE.keys())
        col_objetivo = st.selectbox("Selecciona la columna a limpiar:", cols_limpiables)
        if col_objetivo:
            st.markdown(f"### Analizando: `{col_objetivo}`...")
            lista_oficial = OPCIONES_BASE[col_objetivo]
            lista_oficial_norm = {normalizar_texto(x): x for x in lista_oficial}
            valores_unicos_bd = df[col_objetivo].dropna().unique().tolist()
            valores_sucios = []
            for val in valores_unicos_bd:
                if normalizar_texto(str(val)) not in lista_oficial_norm:
                    count = len(df[df[col_objetivo] == val])
                    valores_sucios.append({"valor": val, "conteo": count})
            if not valores_sucios: st.success(f"✨ ¡La columna '{col_objetivo}' está limpia!")
            else:
                st.info(f"Se encontraron {len(valores_sucios)} variaciones no estándar.")
                col1, col2, col3 = st.columns([2, 0.5, 2])
                col1.markdown("**Valor 'Sucio'**")
                col2.markdown("**Cant.**")
                col3.markdown("**Acción**")
                st.divider()
                for item in valores_sucios:
                    val_sucio = item['valor']
                    count = item['conteo']
                    c1, c2, c3 = st.columns([2, 0.5, 2])
                    c1.code(val_sucio)
                    c2.markdown(f"**{count}**")
                    opciones_fix = ["(Sin cambios)"] + lista_oficial
                    index_default = 0
                    for i, oficial in enumerate(lista_oficial):
                        if normalizar_texto(str(val_sucio)) == normalizar_texto(oficial):
                            index_default = i + 1
                            break
                    seleccion_fix = c3.selectbox("Corregir a:", opciones_fix, key=f"fix_{col_objetivo}_{val_sucio}", index=index_default, label_visibility="collapsed")
                    if seleccion_fix != "(Sin cambios)":
                        if c3.button(f"🔄 Corregir", key=f"btn_{val_sucio}"):
                            try:
                                supabase.table("catalogo_servicios").update({col_objetivo: seleccion_fix}).eq(col_objetivo, val_sucio).execute()
                                st.toast(f"Corregido: '{val_sucio}' -> '{seleccion_fix}'", icon="✅")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e: st.error(f"Error: {e}")
                    st.divider()