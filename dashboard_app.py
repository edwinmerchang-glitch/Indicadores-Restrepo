# dashboard_app.py - Versión corregida con mejor formato de números
import sqlite3
import pandas as pd
from datetime import datetime, date, timedelta
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Ventas | Restrepo",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS minimalista
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .info-box {
        background-color: #EFF6FF;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3B82F6;
        margin: 1rem 0;
    }
    /* Mejorar visibilidad de números grandes */
    .stMetric label {
        font-size: 0.9rem !important;
    }
    .stMetric .metric-value {
        font-size: 1.8rem !important;
        word-break: break-word !important;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1 style="margin: 0; font-size: 1.8rem;">📊 Panel de Control de Ventas</h1>
    <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Sistema de Monitoreo y Análisis | Restrepo</p>
</div>
""", unsafe_allow_html=True)

# Funciones de base de datos
def init_database():
    try:
        conn = sqlite3.connect('ventas_dashboard.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ventas_diarias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha DATE UNIQUE NOT NULL,
                ventas_dia REAL NOT NULL,
                tickets_dia INTEGER,
                visitas_dia INTEGER,
                conversion REAL,
                ticket_promedio REAL,
                articulos_ticket REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS objetivos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mes INTEGER,
                año INTEGER,
                objetivo_ventas REAL,
                objetivo_conversion REAL,
                objetivo_ticket_promedio REAL,
                objetivo_articulos_ticket REAL,
                UNIQUE(mes, año)
            )
        ''')
        
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM objetivos WHERE mes = ? AND año = ?", 
                       (date.today().month, date.today().year))
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO objetivos (mes, año, objetivo_ventas, objetivo_conversion, objetivo_ticket_promedio, objetivo_articulos_ticket)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (date.today().month, date.today().year, 1277000000, 37.0, 78000, 3.5))
            conn.commit()
        
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error inicializando: {str(e)}")
        return False

def import_from_excel(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        df.columns = df.columns.str.lower().str.strip()
        
        conn = sqlite3.connect('ventas_dashboard.db')
        cursor = conn.cursor()
        
        registros = 0
        for _, row in df.iterrows():
            fecha = pd.to_datetime(row['fecha']).date()
            ventas_dia = float(row.get('ventas', 0))
            tickets_dia = int(row.get('tickets', 0))
            visitas_dia = int(row.get('visitas', 0))
            articulos_ticket = float(row.get('articulos_ticket', 0))
            
            conversion = (tickets_dia / visitas_dia * 100) if visitas_dia > 0 else 0
            ticket_promedio = (ventas_dia / tickets_dia) if tickets_dia > 0 else 0
            
            cursor.execute('''
                INSERT OR REPLACE INTO ventas_diarias 
                (fecha, ventas_dia, tickets_dia, visitas_dia, conversion, ticket_promedio, articulos_ticket)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (fecha, ventas_dia, tickets_dia, visitas_dia, conversion, ticket_promedio, articulos_ticket))
            registros += 1
        
        conn.commit()
        conn.close()
        return True, registros
    except Exception as e:
        return False, str(e)

def get_current_month_data():
    try:
        conn = sqlite3.connect('ventas_dashboard.db')
        hoy = date.today()
        
        query = '''
            SELECT 
                SUM(ventas_dia) as ventas_acumuladas,
                AVG(conversion) as conversion_promedio,
                AVG(ticket_promedio) as ticket_promedio,
                AVG(articulos_ticket) as articulos_ticket,
                COUNT(DISTINCT fecha) as dias_operados
            FROM ventas_diarias
            WHERE strftime('%Y-%m', fecha) = ?
        '''
        df_mes = pd.read_sql_query(query, conn, params=[hoy.strftime('%Y-%m')])
        
        df_ultima = pd.read_sql_query('''
            SELECT ventas_dia
            FROM ventas_diarias
            WHERE strftime('%Y-%m', fecha) = ?
            ORDER BY fecha DESC
            LIMIT 1
        ''', conn, params=[hoy.strftime('%Y-%m')])
        
        cursor = conn.cursor()
        cursor.execute('''
            SELECT objetivo_ventas, objetivo_conversion, objetivo_ticket_promedio, objetivo_articulos_ticket
            FROM objetivos
            WHERE mes = ? AND año = ?
        ''', (hoy.month, hoy.year))
        objetivo = cursor.fetchone()
        
        conn.close()
        
        if not objetivo:
            objetivo = (1277000000, 37.0, 78000, 3.5)
        
        return {
            'ventas_acumuladas': float(df_mes['ventas_acumuladas'].iloc[0]) if not df_mes.empty and pd.notna(df_mes['ventas_acumuladas'].iloc[0]) else 0,
            'conversion': float(df_mes['conversion_promedio'].iloc[0]) if not df_mes.empty and pd.notna(df_mes['conversion_promedio'].iloc[0]) else 0,
            'ticket_promedio': float(df_mes['ticket_promedio'].iloc[0]) if not df_mes.empty and pd.notna(df_mes['ticket_promedio'].iloc[0]) else 0,
            'articulos_ticket': float(df_mes['articulos_ticket'].iloc[0]) if not df_mes.empty and pd.notna(df_mes['articulos_ticket'].iloc[0]) else 0,
            'dias_operados': int(df_mes['dias_operados'].iloc[0]) if not df_mes.empty and pd.notna(df_mes['dias_operados'].iloc[0]) else 0,
            'ventas_hoy': float(df_ultima['ventas_dia'].iloc[0]) if not df_ultima.empty else 0,
            'objetivo_ventas': objetivo[0],
            'objetivo_conversion': objetivo[1],
            'objetivo_ticket': objetivo[2],
            'objetivo_articulos': objetivo[3]
        }
    except Exception as e:
        st.error(f"Error obteniendo datos: {str(e)}")
        return None

def get_comparison_data():
    try:
        conn = sqlite3.connect('ventas_dashboard.db')
        df_ultimas = pd.read_sql_query('''
            SELECT fecha, ventas_dia, tickets_dia, visitas_dia, conversion, ticket_promedio, articulos_ticket
            FROM ventas_diarias
            ORDER BY fecha DESC
            LIMIT 2
        ''', conn)
        conn.close()
        
        if len(df_ultimas) >= 2:
            hoy_data = df_ultimas.iloc[0]
            ayer_data = df_ultimas.iloc[1]
            return {
                'tiene_datos': True,
                'fecha_hoy': pd.to_datetime(hoy_data['fecha']).date(),
                'fecha_ayer': pd.to_datetime(ayer_data['fecha']).date(),
                'hoy': {
                    'ventas': float(hoy_data['ventas_dia']),
                    'tickets': int(hoy_data['tickets_dia']),
                    'visitas': int(hoy_data['visitas_dia']),
                    'conversion': float(hoy_data['conversion']),
                    'ticket_promedio': float(hoy_data['ticket_promedio']),
                    'articulos': float(hoy_data['articulos_ticket'])
                },
                'ayer': {
                    'ventas': float(ayer_data['ventas_dia']),
                    'tickets': int(ayer_data['tickets_dia']),
                    'visitas': int(ayer_data['visitas_dia']),
                    'conversion': float(ayer_data['conversion']),
                    'ticket_promedio': float(ayer_data['ticket_promedio']),
                    'articulos': float(ayer_data['articulos_ticket'])
                }
            }
        return {'tiene_datos': False}
    except Exception:
        return {'tiene_datos': False}

def calcular_variacion(valor_actual, valor_anterior):
    if valor_anterior == 0:
        return 0
    return ((valor_actual - valor_anterior) / valor_anterior) * 100

def formatear_numero(valor):
    """Formatea números grandes de manera legible"""
    if valor >= 1_000_000_000:
        return f"${valor/1_000_000_000:.1f}B"
    elif valor >= 1_000_000:
        return f"${valor/1_000_000:.1f}M"
    elif valor >= 1_000:
        return f"${valor/1_000:.1f}K"
    else:
        return f"${valor:,.0f}"

# Sidebar
with st.sidebar:
    st.markdown("## 📁 Datos")
    
    uploaded_file = st.file_uploader("Importar Excel", type=['xlsx', 'xls'])
    
    if uploaded_file:
        if st.button("📤 Procesar", type="primary", use_container_width=True):
            with st.spinner("Procesando..."):
                success, result = import_from_excel(uploaded_file)
                if success:
                    st.success(f"✅ {result} registros importados")
                    st.rerun()
                else:
                    st.error(f"❌ Error: {result}")
    
    st.markdown("---")
    
    with st.expander("📋 Formato requerido"):
        st.markdown("""
        - `fecha` (YYYY-MM-DD)
        - `ventas`
        - `tickets`
        - `visitas`
        - `articulos_ticket` (opcional)
        """)
    
    st.markdown("---")
    st.markdown("## 🎯 Objetivos")
    
    obj_ventas = st.number_input("Ventas ($)", value=1277000000, step=1000000, format="%d")
    obj_conversion = st.number_input("Conversión (%)", value=37.0, step=1.0)
    obj_ticket = st.number_input("Ticket promedio ($)", value=78000, step=1000)
    obj_articulos = st.number_input("Artículos/ticket", value=3.5, step=0.1)
    
    if st.button("💾 Guardar", type="primary", use_container_width=True):
        try:
            conn = sqlite3.connect('ventas_dashboard.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO objetivos (mes, año, objetivo_ventas, objetivo_conversion, objetivo_ticket_promedio, objetivo_articulos_ticket)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (date.today().month, date.today().year, obj_ventas, obj_conversion, obj_ticket, obj_articulos))
            conn.commit()
            conn.close()
            st.success("✅ Objetivos guardados")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Inicializar
if not init_database():
    st.stop()

data = get_current_month_data()
if not data:
    st.warning("⚠️ No hay datos disponibles. Importa un archivo Excel para comenzar.")
    st.stop()

comparison = get_comparison_data()

# ==================== SECCIÓN 1: KPIs PRINCIPALES ====================
st.markdown("## 📊 Indicadores Clave del Mes")

col1, col2, col3, col4 = st.columns(4)

with col1:
    porcentaje_meta = (data['ventas_acumuladas'] / data['objetivo_ventas'] * 100) if data['objetivo_ventas'] > 0 else 0
    # Usar formato compacto para números grandes
    st.metric(
        label="💰 Presupuesto Mensual",
        value=formatear_numero(data['objetivo_ventas']),
        delta=f"{porcentaje_meta:.1f}% completado"
    )
    st.progress(min(porcentaje_meta / 100, 1.0))
    st.caption(f"📊 Acumulado: ${data['ventas_acumuladas']:,.0f}")

with col2:
    porcentaje_ticket = (data['ticket_promedio'] / data['objetivo_ticket'] * 100) if data['objetivo_ticket'] > 0 else 0
    diferencia_ticket = data['ticket_promedio'] - data['objetivo_ticket']
    delta_ticket = f"{diferencia_ticket:+,.0f} vs meta"
    st.metric(
        label="🎫 Ticket Promedio",
        value=f"${data['ticket_promedio']:,.0f}",
        delta=delta_ticket,
        delta_color="normal" if data['ticket_promedio'] >= data['objetivo_ticket'] else "inverse"
    )
    st.progress(min(porcentaje_ticket / 100, 1.0))
    st.caption(f"🎯 Meta: ${data['objetivo_ticket']:,.0f}")

with col3:
    porcentaje_art = (data['articulos_ticket'] / data['objetivo_articulos'] * 100) if data['objetivo_articulos'] > 0 else 0
    diferencia_art = data['articulos_ticket'] - data['objetivo_articulos']
    delta_art = f"{diferencia_art:+.1f} vs meta"
    st.metric(
        label="📦 Artículos por Ticket",
        value=f"{data['articulos_ticket']:.1f}",
        delta=delta_art,
        delta_color="normal" if data['articulos_ticket'] >= data['objetivo_articulos'] else "inverse"
    )
    st.progress(min(porcentaje_art / 100, 1.0))
    st.caption(f"🎯 Meta: {data['objetivo_articulos']:.1f}")

with col4:
    porcentaje_conv = (data['conversion'] / data['objetivo_conversion'] * 100) if data['objetivo_conversion'] > 0 else 0
    diferencia_conv = data['conversion'] - data['objetivo_conversion']
    delta_conv = f"{diferencia_conv:+.1f}pp vs meta"
    st.metric(
        label="🔄 Conversión",
        value=f"{data['conversion']:.1f}%",
        delta=delta_conv,
        delta_color="normal" if data['conversion'] >= data['objetivo_conversion'] else "inverse"
    )
    st.progress(min(porcentaje_conv / 100, 1.0))
    st.caption(f"🎯 Meta: {data['objetivo_conversion']:.1f}%")

st.markdown("---")

# ==================== SECCIÓN 2: COMPARACIÓN DIARIA ====================
st.markdown("## 📈 Comparación vs Día Anterior")

if comparison.get('tiene_datos', False):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        var_ventas = calcular_variacion(comparison['hoy']['ventas'], comparison['ayer']['ventas'])
        st.metric(
            label="💰 Ventas",
            value=f"${comparison['hoy']['ventas']:,.0f}",
            delta=f"{var_ventas:+.1f}% vs ayer",
            delta_color="normal" if var_ventas >= 0 else "inverse"
        )
        st.caption(f"📅 Ayer: ${comparison['ayer']['ventas']:,.0f}")
    
    with col2:
        var_tickets = calcular_variacion(comparison['hoy']['tickets'], comparison['ayer']['tickets'])
        st.metric(
            label="🎫 Tickets",
            value=f"{comparison['hoy']['tickets']:,.0f}",
            delta=f"{var_tickets:+.1f}% vs ayer",
            delta_color="normal" if var_tickets >= 0 else "inverse"
        )
        st.caption(f"📅 Ayer: {comparison['ayer']['tickets']:,.0f}")
    
    with col3:
        var_visitas = calcular_variacion(comparison['hoy']['visitas'], comparison['ayer']['visitas'])
        st.metric(
            label="👥 Visitas",
            value=f"{comparison['hoy']['visitas']:,.0f}",
            delta=f"{var_visitas:+.1f}% vs ayer",
            delta_color="normal" if var_visitas >= 0 else "inverse"
        )
        st.caption(f"📅 Ayer: {comparison['ayer']['visitas']:,.0f}")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        var_articulos = calcular_variacion(comparison['hoy']['articulos'], comparison['ayer']['articulos'])
        st.metric(
            label="📦 Artículos x Ticket",
            value=f"{comparison['hoy']['articulos']:.1f}",
            delta=f"{var_articulos:+.1f}% vs ayer",
            delta_color="normal" if var_articulos >= 0 else "inverse"
        )
        st.caption(f"📅 Ayer: {comparison['ayer']['articulos']:.1f}")
    
    with col2:
        var_conversion = calcular_variacion(comparison['hoy']['conversion'], comparison['ayer']['conversion'])
        st.metric(
            label="🔄 Conversión",
            value=f"{comparison['hoy']['conversion']:.1f}%",
            delta=f"{var_conversion:+.1f}% vs ayer",
            delta_color="normal" if var_conversion >= 0 else "inverse"
        )
        st.caption(f"📅 Ayer: {comparison['ayer']['conversion']:.1f}%")
    
    with col3:
        var_ticket = calcular_variacion(comparison['hoy']['ticket_promedio'], comparison['ayer']['ticket_promedio'])
        st.metric(
            label="💵 Ticket Promedio",
            value=f"${comparison['hoy']['ticket_promedio']:,.0f}",
            delta=f"{var_ticket:+.1f}% vs ayer",
            delta_color="normal" if var_ticket >= 0 else "inverse"
        )
        st.caption(f"📅 Ayer: ${comparison['ayer']['ticket_promedio']:,.0f}")
    
    st.info(f"📅 Comparación: {comparison['fecha_hoy'].strftime('%d/%m/%Y')} vs {comparison['fecha_ayer'].strftime('%d/%m/%Y')}")
else:
    st.info("📊 Se necesitan al menos 2 días de datos para mostrar comparaciones")

st.markdown("---")

# ==================== SECCIÓN 3: DESEMPEÑO GENERAL ====================
st.markdown("## 📈 Desempeño General")

col1, col2 = st.columns(2)

with col1:
    promedio_diario = data['ventas_acumuladas'] / max(data['dias_operados'], 1)
    st.metric(
        label="💵 Última Venta Registrada",
        value=f"${data['ventas_hoy']:,.0f}",
        delta=f"Promedio diario: ${promedio_diario:,.0f}"
    )
    st.caption(f"📅 Días operados en el mes: {data['dias_operados']}/30")

with col2:
    try:
        conn = sqlite3.connect('ventas_dashboard.db')
        hoy = date.today()
        mes_anterior = date(hoy.year, hoy.month, 1) - timedelta(days=1)
        df_anterior = pd.read_sql_query('''
            SELECT SUM(ventas_dia) as ventas_anterior
            FROM ventas_diarias
            WHERE strftime('%Y-%m', fecha) = ?
        ''', conn, params=[mes_anterior.strftime('%Y-%m')])
        conn.close()
        
        ventas_anterior = float(df_anterior['ventas_anterior'].iloc[0]) if not df_anterior.empty and pd.notna(df_anterior['ventas_anterior'].iloc[0]) else 0
        
        if ventas_anterior > 0:
            crecimiento = ((data['ventas_acumuladas'] - ventas_anterior) / ventas_anterior * 100)
            st.metric(
                label="📈 Crecimiento vs Mes Anterior",
                value=f"{crecimiento:+.1f}%",
                delta=f"Mes anterior: ${ventas_anterior:,.0f}"
            )
        else:
            st.metric(
                label="📈 Crecimiento vs Mes Anterior",
                value="N/A",
                delta="Sin datos del mes anterior"
            )
    except Exception as e:
        st.metric(
            label="📈 Crecimiento vs Mes Anterior",
            value="N/A",
            delta="Sin datos disponibles"
        )

st.markdown("---")

# ==================== SECCIÓN 4: GRÁFICO DE EVOLUCIÓN ====================
st.markdown("## 📈 Evolución Diaria")

try:
    conn = sqlite3.connect('ventas_dashboard.db')
    df_diario = pd.read_sql_query('''
        SELECT fecha, ventas_dia, articulos_ticket
        FROM ventas_diarias
        WHERE strftime('%Y-%m', fecha) = ?
        ORDER BY fecha
    ''', conn, params=[date.today().strftime('%Y-%m')])
    conn.close()
    
    if not df_diario.empty:
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=("Ventas Diarias", "Artículos por Ticket"),
            vertical_spacing=0.12,
            row_heights=[0.6, 0.4]
        )
        
        # Ventas
        fig.add_trace(
            go.Bar(x=df_diario['fecha'], y=df_diario['ventas_dia'], 
                   name="Ventas", marker_color='#3B82F6', opacity=0.8),
            row=1, col=1
        )
        
        meta_diaria = data['objetivo_ventas'] / 30
        fig.add_trace(
            go.Scatter(x=df_diario['fecha'], y=[meta_diaria] * len(df_diario), 
                      name="Meta diaria", line=dict(color='#EF4444', dash='dash', width=2)),
            row=1, col=1
        )
        
        # Artículos
        fig.add_trace(
            go.Scatter(x=df_diario['fecha'], y=df_diario['articulos_ticket'], 
                      name="Artículos x Ticket", line=dict(color='#8B5CF6', width=3),
                      mode='lines+markers', marker=dict(size=8, color='#8B5CF6')),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(x=df_diario['fecha'], y=[data['objetivo_articulos']] * len(df_diario), 
                      name=f"Meta: {data['objetivo_articulos']}", 
                      line=dict(color='#F59E0B', dash='dash', width=2)),
            row=2, col=1
        )
        
        fig.update_layout(
            height=500,
            hovermode='x unified',
            showlegend=True,
            template='plotly_white',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        fig.update_yaxes(title_text="Ventas ($)", tickformat='$,.0f', row=1, col=1)
        fig.update_yaxes(title_text="Artículos", row=2, col=1)
        fig.update_xaxes(title_text="Fecha", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("📋 Ver detalle completo"):
            df_display = df_diario.copy()
            df_display['ventas_dia'] = df_display['ventas_dia'].apply(lambda x: f"${x:,.0f}")
            df_display['articulos_ticket'] = df_display['articulos_ticket'].apply(lambda x: f"{x:.1f}")
            df_display.columns = ['Fecha', 'Ventas', 'Artículos x Ticket']
            st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("📭 No hay datos para el mes actual. Importa un archivo Excel para comenzar.")
        
except Exception as e:
    st.error(f"Error al cargar el gráfico: {str(e)}")