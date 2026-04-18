# dashboard_app.py - Versión Profesional
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

# Paleta de colores corporativos
COLORS = {
    'primary': '#1E3A8A',      # Azul profundo
    'secondary': '#3B82F6',     # Azul brillante
    'success': '#10B981',       # Verde éxito
    'danger': '#EF4444',        # Rojo peligro
    'warning': '#F59E0B',       # Naranja advertencia
    'info': '#06B6D4',          # Cyan info
    'purple': '#8B5CF6',        # Púrpura
    'pink': '#EC4899',          # Rosa
    'gray': '#6B7280',          # Gris
    'light': '#F3F4F6',         # Gris claro
    'dark': '#1F2937',          # Gris oscuro
    'white': '#FFFFFF'          # Blanco
}

# CSS moderno y profesional
st.markdown(f"""
<style>
    /* Fuente moderna */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {{
        font-family: 'Inter', sans-serif;
    }}
    
    /* Ocultar elementos por defecto de Streamlit */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
    /* Header personalizado */
    .main-header {{
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
        padding: 2rem;
        border-radius: 1rem;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }}
    
    /* Tarjetas modernas */
    .card {{
        background: {COLORS['white']};
        border-radius: 1rem;
        padding: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: transform 0.2s, box-shadow 0.2s;
        margin-bottom: 1rem;
        border: 1px solid #E5E7EB;
    }}
    
    .card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }}
    
    /* Títulos de tarjetas */
    .card-title {{
        font-size: 0.875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: {COLORS['gray']};
        margin-bottom: 0.75rem;
    }}
    
    /* Valores principales */
    .card-value {{
        font-size: 2rem;
        font-weight: 700;
        color: {COLORS['dark']};
        margin-bottom: 0.5rem;
    }}
    
    /* Metas y objetivos */
    .card-meta {{
        font-size: 0.75rem;
        color: {COLORS['gray']};
        margin-top: 0.5rem;
    }}
    
    /* Barra de progreso */
    .progress-bar-container {{
        background-color: {COLORS['light']};
        border-radius: 9999px;
        height: 0.5rem;
        margin: 0.75rem 0;
        overflow: hidden;
    }}
    
    .progress-bar {{
        height: 100%;
        border-radius: 9999px;
        transition: width 0.3s ease;
    }}
    
    /* Indicadores de tendencia */
    .trend-up {{
        color: {COLORS['success']};
        font-weight: 600;
    }}
    
    .trend-down {{
        color: {COLORS['danger']};
        font-weight: 600;
    }}
    
    /* Badges */
    .badge {{
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }}
    
    .badge-success {{
        background-color: #D1FAE5;
        color: {COLORS['success']};
    }}
    
    .badge-warning {{
        background-color: #FEF3C7;
        color: {COLORS['warning']};
    }}
    
    .badge-danger {{
        background-color: #FEE2E2;
        color: {COLORS['danger']};
    }}
    
    /* Tablas */
    .dataframe {{
        border-radius: 0.5rem;
        overflow: hidden;
    }}
    
    /* Sidebar personalizada */
    .sidebar-content {{
        padding: 1rem;
    }}
    
    /* Separadores */
    .divider {{
        height: 1px;
        background: linear-gradient(90deg, transparent, {COLORS['secondary']}, transparent);
        margin: 2rem 0;
    }}
</style>
""", unsafe_allow_html=True)

# Header personalizado
st.markdown(f"""
<div class="main-header">
    <h1 style="margin: 0; font-size: 2rem;">📊 Panel de Control de Ventas</h1>
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
        st.error(f"Error: {str(e)}")
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
        st.error(f"Error: {str(e)}")
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

def crear_tarjeta_indicador(titulo, valor, meta=None, formato="{:,.0f}", sufijo="", color_hex=None):
    if meta and meta > 0:
        porcentaje = (valor / meta * 100)
        color_barra = COLORS['success'] if porcentaje >= 100 else COLORS['warning'] if porcentaje >= 80 else COLORS['danger']
    else:
        porcentaje = None
        color_barra = COLORS['secondary']
    
    if formato == "{:.1f}":
        valor_text = formato.format(valor)
    else:
        valor_text = formato.format(valor)
    
    html = f"""
    <div class="card">
        <div class="card-title">{titulo}</div>
        <div class="card-value" style="color: {color_hex or COLORS['dark']};">{valor_text}{sufijo}</div>
    """
    
    if meta:
        html += f"""
        <div class="card-meta">Meta: {formato.format(meta)}{sufijo}</div>
        <div class="progress-bar-container">
            <div class="progress-bar" style="width: {min(porcentaje, 100)}%; background-color: {color_barra};"></div>
        </div>
        <div class="card-meta">{porcentaje:.1f}% completado</div>
        """
    
    html += "</div>"
    return html

# Sidebar
with st.sidebar:
    st.markdown("### 📁 Datos")
    
    uploaded_file = st.file_uploader("Importar Excel", type=['xlsx', 'xls'], key="excel_uploader")
    
    if uploaded_file:
        if st.button("📤 Procesar archivo", type="primary", use_container_width=True):
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
    st.markdown("### 🎯 Objetivos")
    
    obj_ventas = st.number_input("Ventas", value=1277000000, step=1000000, format="%d")
    obj_conversion = st.number_input("Conversión %", value=37.0, step=1.0)
    obj_ticket = st.number_input("Ticket promedio", value=78000, step=1000)
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
            st.success("✅ Objetivos actualizados")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Inicializar
if not init_database():
    st.stop()

data = get_current_month_data()
if not data:
    st.warning("⚠️ No hay datos disponibles")
    st.stop()

comparison = get_comparison_data()

# KPIs Principales
st.markdown("### 📊 Indicadores Clave")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(crear_tarjeta_indicador(
        "Presupuesto Mensual",
        data['objetivo_ventas'],
        None,
        "${:,.0f}",
        "",
        COLORS['primary']
    ), unsafe_allow_html=True)

with col2:
    st.markdown(crear_tarjeta_indicador(
        "Ticket Promedio",
        data['ticket_promedio'],
        data['objetivo_ticket'],
        "${:,.0f}",
        ""
    ), unsafe_allow_html=True)

with col3:
    st.markdown(crear_tarjeta_indicador(
        "Artículos x Ticket",
        data['articulos_ticket'],
        data['objetivo_articulos'],
        "{:.1f}",
        ""
    ), unsafe_allow_html=True)

with col4:
    st.markdown(crear_tarjeta_indicador(
        "Conversión",
        data['conversion'],
        data['objetivo_conversion'],
        "{:.1f}",
        "%"
    ), unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# Comparativa Diaria
st.markdown("### 📈 Comparativa vs Día Anterior")

if comparison.get('tiene_datos', False):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        var_ventas = calcular_variacion(comparison['hoy']['ventas'], comparison['ayer']['ventas'])
        trend_class = "trend-up" if var_ventas >= 0 else "trend-down"
        trend_icon = "▲" if var_ventas >= 0 else "▼"
        
        st.markdown(f"""
        <div class="card">
            <div class="card-title">💰 Ventas</div>
            <div class="card-value">${comparison['hoy']['ventas']:,.0f}</div>
            <div class="{trend_class}">{trend_icon} {abs(var_ventas):.1f}% vs ayer</div>
            <div class="card-meta">Ayer: ${comparison['ayer']['ventas']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        var_tickets = calcular_variacion(comparison['hoy']['tickets'], comparison['ayer']['tickets'])
        trend_class = "trend-up" if var_tickets >= 0 else "trend-down"
        trend_icon = "▲" if var_tickets >= 0 else "▼"
        
        st.markdown(f"""
        <div class="card">
            <div class="card-title">🎫 Tickets</div>
            <div class="card-value">{comparison['hoy']['tickets']:,.0f}</div>
            <div class="{trend_class}">{trend_icon} {abs(var_tickets):.1f}% vs ayer</div>
            <div class="card-meta">Ayer: {comparison['ayer']['tickets']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        var_visitas = calcular_variacion(comparison['hoy']['visitas'], comparison['ayer']['visitas'])
        trend_class = "trend-up" if var_visitas >= 0 else "trend-down"
        trend_icon = "▲" if var_visitas >= 0 else "▼"
        
        st.markdown(f"""
        <div class="card">
            <div class="card-title">👥 Visitas</div>
            <div class="card-value">{comparison['hoy']['visitas']:,.0f}</div>
            <div class="{trend_class}">{trend_icon} {abs(var_visitas):.1f}% vs ayer</div>
            <div class="card-meta">Ayer: {comparison['ayer']['visitas']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        var_articulos = calcular_variacion(comparison['hoy']['articulos'], comparison['ayer']['articulos'])
        trend_class = "trend-up" if var_articulos >= 0 else "trend-down"
        trend_icon = "▲" if var_articulos >= 0 else "▼"
        
        st.markdown(f"""
        <div class="card">
            <div class="card-title">📦 Artículos x Ticket</div>
            <div class="card-value">{comparison['hoy']['articulos']:.1f}</div>
            <div class="{trend_class}">{trend_icon} {abs(var_articulos):.1f}% vs ayer</div>
            <div class="card-meta">Ayer: {comparison['ayer']['articulos']:.1f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        var_conversion = calcular_variacion(comparison['hoy']['conversion'], comparison['ayer']['conversion'])
        trend_class = "trend-up" if var_conversion >= 0 else "trend-down"
        trend_icon = "▲" if var_conversion >= 0 else "▼"
        
        st.markdown(f"""
        <div class="card">
            <div class="card-title">🔄 Conversión</div>
            <div class="card-value">{comparison['hoy']['conversion']:.1f}%</div>
            <div class="{trend_class}">{trend_icon} {abs(var_conversion):.1f}% vs ayer</div>
            <div class="card-meta">Ayer: {comparison['ayer']['conversion']:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        var_ticket = calcular_variacion(comparison['hoy']['ticket_promedio'], comparison['ayer']['ticket_promedio'])
        trend_class = "trend-up" if var_ticket >= 0 else "trend-down"
        trend_icon = "▲" if var_ticket >= 0 else "▼"
        
        st.markdown(f"""
        <div class="card">
            <div class="card-title">💵 Ticket Promedio</div>
            <div class="card-value">${comparison['hoy']['ticket_promedio']:,.0f}</div>
            <div class="{trend_class}">{trend_icon} {abs(var_ticket):.1f}% vs ayer</div>
            <div class="card-meta">Ayer: ${comparison['ayer']['ticket_promedio']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.caption(f"📅 Comparación: {comparison['fecha_hoy'].strftime('%d/%m/%Y')} vs {comparison['fecha_ayer'].strftime('%d/%m/%Y')}")
else:
    st.info("📊 Se necesitan al menos 2 días de datos para mostrar comparaciones")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# Desempeño General
st.markdown("### 📈 Desempeño General")

col1, col2 = st.columns(2)

with col1:
    promedio_diario = data['ventas_acumuladas'] / max(data['dias_operados'], 1)
    st.markdown(f"""
    <div class="card">
        <div class="card-title">💵 Última Venta</div>
        <div class="card-value">${data['ventas_hoy']:,.0f}</div>
        <div class="card-meta">Promedio diario: ${promedio_diario:,.0f}</div>
        <div class="card-meta">Días operados: {data['dias_operados']}/30</div>
    </div>
    """, unsafe_allow_html=True)

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
            trend_class = "trend-up" if crecimiento >= 0 else "trend-down"
            trend_icon = "▲" if crecimiento >= 0 else "▼"
            st.markdown(f"""
            <div class="card">
                <div class="card-title">📈 Crecimiento vs Mes Anterior</div>
                <div class="card-value {trend_class}">{trend_icon} {abs(crecimiento):.1f}%</div>
                <div class="card-meta">Mes anterior: ${ventas_anterior:,.0f}</div>
                <div class="card-meta">Mes actual: ${data['ventas_acumuladas']:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="card">
                <div class="card-title">📈 Crecimiento vs Mes Anterior</div>
                <div class="card-value">N/A</div>
                <div class="card-meta">Sin datos del mes anterior</div>
            </div>
            """, unsafe_allow_html=True)
    except:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">📈 Crecimiento vs Mes Anterior</div>
            <div class="card-value">N/A</div>
            <div class="card-meta">Sin datos disponibles</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# Gráfico de evolución
st.markdown("### 📈 Evolución Diaria")

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
                   name="Ventas", marker_color=COLORS['secondary'], opacity=0.8),
            row=1, col=1
        )
        
        meta_diaria = data['objetivo_ventas'] / 30
        fig.add_trace(
            go.Scatter(x=df_diario['fecha'], y=[meta_diaria] * len(df_diario), 
                      name="Meta diaria", line=dict(color=COLORS['danger'], dash='dash', width=2)),
            row=1, col=1
        )
        
        # Artículos
        fig.add_trace(
            go.Scatter(x=df_diario['fecha'], y=df_diario['articulos_ticket'], 
                      name="Artículos x Ticket", line=dict(color=COLORS['purple'], width=3),
                      mode='lines+markers', marker=dict(size=8, color=COLORS['purple'])),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(x=df_diario['fecha'], y=[data['objetivo_articulos']] * len(df_diario), 
                      name=f"Meta: {data['objetivo_articulos']}", 
                      line=dict(color=COLORS['warning'], dash='dash', width=2)),
            row=2, col=1
        )
        
        fig.update_layout(
            height=500,
            hovermode='x unified',
            showlegend=True,
            template='plotly_white',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            font=dict(family="Inter, sans-serif")
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