# dashboard_app.py - Versión simplificada y corregida
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
    page_title="Dashboard de Ventas - Indicadores Restrepo",
    page_icon="📊",
    layout="wide"
)

# CSS simplificado
st.markdown("""
<style>
    /* Estilos para tarjetas */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 20px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .metric-card-blue {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }
    .metric-card-green {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
    }
    .metric-card-pink {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    .metric-card-orange {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
    }
    .metric-title {
        font-size: 14px;
        opacity: 0.9;
        margin-bottom: 10px;
    }
    .metric-value {
        font-size: 32px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .metric-target {
        font-size: 12px;
        opacity: 0.8;
    }
    .metric-progress {
        background-color: rgba(255,255,255,0.2);
        border-radius: 10px;
        height: 6px;
        margin: 10px 0;
    }
    .metric-progress-bar {
        background-color: white;
        height: 6px;
        border-radius: 10px;
        transition: width 0.5s ease;
    }
    .comparison-card {
        background: white;
        border-radius: 10px;
        padding: 15px;
        border-left: 4px solid;
        margin: 8px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .comparison-label {
        font-size: 13px;
        font-weight: bold;
        color: #666;
        margin-bottom: 8px;
    }
    .comparison-today {
        font-size: 20px;
        font-weight: bold;
    }
    .trend-up {
        color: #00ff00;
    }
    .trend-down {
        color: #ff0000;
    }
</style>
""", unsafe_allow_html=True)

# Título
st.title("📊 Panel de Control de Ventas")
st.caption("Indicadores Restrepo")
st.markdown("---")

# Funciones de base de datos
def init_database():
    try:
        conn = sqlite3.connect('ventas_dashboard.db')
        cursor = conn.cursor()
        
        # Crear tablas
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
        
        # Insertar objetivos por defecto
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
        
        conn.commit()
        conn.close()
        return True, len(df)
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
        
        # Última venta
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
    except Exception as e:
        return {'tiene_datos': False}

def calcular_variacion(valor_actual, valor_anterior):
    if valor_anterior == 0:
        return 0
    return ((valor_actual - valor_anterior) / valor_anterior) * 100

# Sidebar
with st.sidebar:
    st.header("📁 Carga de Datos")
    uploaded_file = st.file_uploader("Subir archivo Excel", type=['xlsx', 'xls'])
    
    if uploaded_file:
        if st.button("📤 Importar Datos", type="primary"):
            with st.spinner("Procesando..."):
                success, result = import_from_excel(uploaded_file)
                if success:
                    st.success(f"✅ {result} registros importados")
                    st.rerun()
                else:
                    st.error(f"❌ Error: {result}")
    
    st.markdown("---")
    st.header("📈 Formato del Excel")
    st.info("""
    Columnas requeridas:
    - fecha (YYYY-MM-DD)
    - ventas
    - tickets
    - visitas
    - articulos_ticket (opcional)
    """)
    
    st.markdown("---")
    st.header("🎯 Configurar Metas")
    
    objetivo_ventas = st.number_input("Meta Ventas ($)", value=1277000000, step=1000000, format="%d")
    objetivo_conversion = st.number_input("Meta Conversión (%)", value=37.0, step=1.0)
    objetivo_ticket = st.number_input("Meta Ticket Promedio ($)", value=78000, step=1000)
    objetivo_articulos = st.number_input("Meta Artículos x Ticket", value=3.5, step=0.1)
    
    if st.button("💾 Guardar Metas", type="primary"):
        try:
            conn = sqlite3.connect('ventas_dashboard.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO objetivos (mes, año, objetivo_ventas, objetivo_conversion, objetivo_ticket_promedio, objetivo_articulos_ticket)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (date.today().month, date.today().year, objetivo_ventas, objetivo_conversion, objetivo_ticket, objetivo_articulos))
            conn.commit()
            conn.close()
            st.success("✅ Metas actualizadas")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Inicializar
if not init_database():
    st.stop()

# Obtener datos
data = get_current_month_data()
if not data:
    st.warning("⚠️ No se pudieron cargar los datos")
    st.stop()

comparison = get_comparison_data()

# SECCIÓN 1: Indicadores Clave
st.subheader("📊 Indicadores Clave del Mes")

col1, col2, col3, col4 = st.columns(4)

with col1:
    porcentaje = (data['ventas_acumuladas'] / data['objetivo_ventas'] * 100) if data['objetivo_ventas'] > 0 else 0
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">💰 PRESUPUESTO MENSUAL</div>
        <div class="metric-value">${data['objetivo_ventas']:,.0f}</div>
        <div class="metric-target">Acumulado: ${data['ventas_acumuladas']:,.0f}</div>
        <div class="metric-progress">
            <div class="metric-progress-bar" style="width: {min(porcentaje, 100)}%;"></div>
        </div>
        <div class="metric-target">{porcentaje:.1f}% completado</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    porcentaje_ticket = (data['ticket_promedio'] / data['objetivo_ticket'] * 100) if data['objetivo_ticket'] > 0 else 0
    color_ticket = "#00ff00" if data['ticket_promedio'] >= data['objetivo_ticket'] else "#ffa500"
    st.markdown(f"""
    <div class="metric-card metric-card-pink">
        <div class="metric-title">🎫 TICKET PROMEDIO</div>
        <div class="metric-value" style="color: {color_ticket};">${data['ticket_promedio']:,.0f}</div>
        <div class="metric-target">Meta: ${data['objetivo_ticket']:,.0f}</div>
        <div class="metric-progress">
            <div class="metric-progress-bar" style="width: {min(porcentaje_ticket, 100)}%;"></div>
        </div>
        <div class="metric-target">{porcentaje_ticket:.1f}% de la meta</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    porcentaje_articulos = (data['articulos_ticket'] / data['objetivo_articulos'] * 100) if data['objetivo_articulos'] > 0 else 0
    color_art = "#00ff00" if data['articulos_ticket'] >= data['objetivo_articulos'] else "#ffa500"
    st.markdown(f"""
    <div class="metric-card metric-card-blue">
        <div class="metric-title">📦 ARTÍCULOS x TICKET</div>
        <div class="metric-value" style="color: {color_art};">{data['articulos_ticket']:.1f}</div>
        <div class="metric-target">Meta: {data['objetivo_articulos']:.1f}</div>
        <div class="metric-progress">
            <div class="metric-progress-bar" style="width: {min(porcentaje_articulos, 100)}%;"></div>
        </div>
        <div class="metric-target">{porcentaje_articulos:.1f}% de la meta</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    porcentaje_conv = (data['conversion'] / data['objetivo_conversion'] * 100) if data['objetivo_conversion'] > 0 else 0
    color_conv = "#00ff00" if data['conversion'] >= data['objetivo_conversion'] else "#ffa500"
    st.markdown(f"""
    <div class="metric-card metric-card-green">
        <div class="metric-title">🔄 CONVERSIÓN</div>
        <div class="metric-value" style="color: {color_conv};">{data['conversion']:.1f}%</div>
        <div class="metric-target">Meta: {data['objetivo_conversion']:.1f}%</div>
        <div class="metric-progress">
            <div class="metric-progress-bar" style="width: {min(porcentaje_conv, 100)}%;"></div>
        </div>
        <div class="metric-target">{porcentaje_conv:.1f}% de la meta</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# SECCIÓN 2: Comparación Diaria
st.subheader("📈 Comparación Diaria")

if comparison.get('tiene_datos', False):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        variacion_ventas = calcular_variacion(comparison['hoy']['ventas'], comparison['ayer']['ventas'])
        color_ventas = "trend-up" if variacion_ventas >= 0 else "trend-down"
        st.markdown(f"""
        <div class="comparison-card" style="border-left-color: {'#00ff00' if variacion_ventas >= 0 else '#ff0000'}">
            <div class="comparison-label">💰 Ventas</div>
            <div class="comparison-today">${comparison['hoy']['ventas']:,.0f}</div>
            <div class="{color_ventas}">{variacion_ventas:+.1f}% vs ayer</div>
            <div style="font-size: 11px; color: #888;">Ayer: ${comparison['ayer']['ventas']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        variacion_tickets = calcular_variacion(comparison['hoy']['tickets'], comparison['ayer']['tickets'])
        color_tickets = "trend-up" if variacion_tickets >= 0 else "trend-down"
        st.markdown(f"""
        <div class="comparison-card" style="border-left-color: {'#00ff00' if variacion_tickets >= 0 else '#ff0000'}">
            <div class="comparison-label">🎫 Tickets</div>
            <div class="comparison-today">{comparison['hoy']['tickets']:,.0f}</div>
            <div class="{color_tickets}">{variacion_tickets:+.1f}% vs ayer</div>
            <div style="font-size: 11px; color: #888;">Ayer: {comparison['ayer']['tickets']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        variacion_visitas = calcular_variacion(comparison['hoy']['visitas'], comparison['ayer']['visitas'])
        color_visitas = "trend-up" if variacion_visitas >= 0 else "trend-down"
        st.markdown(f"""
        <div class="comparison-card" style="border-left-color: {'#00ff00' if variacion_visitas >= 0 else '#ff0000'}">
            <div class="comparison-label">👥 Visitas</div>
            <div class="comparison-today">{comparison['hoy']['visitas']:,.0f}</div>
            <div class="{color_visitas}">{variacion_visitas:+.1f}% vs ayer</div>
            <div style="font-size: 11px; color: #888;">Ayer: {comparison['ayer']['visitas']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        variacion_articulos = calcular_variacion(comparison['hoy']['articulos'], comparison['ayer']['articulos'])
        color_arts = "trend-up" if variacion_articulos >= 0 else "trend-down"
        st.markdown(f"""
        <div class="comparison-card" style="border-left-color: {'#00ff00' if variacion_articulos >= 0 else '#ff0000'}">
            <div class="comparison-label">📦 Artículos x Ticket</div>
            <div class="comparison-today">{comparison['hoy']['articulos']:.1f}</div>
            <div class="{color_arts}">{variacion_articulos:+.1f}% vs ayer</div>
            <div style="font-size: 11px; color: #888;">Ayer: {comparison['ayer']['articulos']:.1f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        variacion_conversion = calcular_variacion(comparison['hoy']['conversion'], comparison['ayer']['conversion'])
        color_conv = "trend-up" if variacion_conversion >= 0 else "trend-down"
        st.markdown(f"""
        <div class="comparison-card" style="border-left-color: {'#00ff00' if variacion_conversion >= 0 else '#ff0000'}">
            <div class="comparison-label">🔄 Conversión</div>
            <div class="comparison-today">{comparison['hoy']['conversion']:.1f}%</div>
            <div class="{color_conv}">{variacion_conversion:+.1f}% vs ayer</div>
            <div style="font-size: 11px; color: #888;">Ayer: {comparison['ayer']['conversion']:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        variacion_ticket = calcular_variacion(comparison['hoy']['ticket_promedio'], comparison['ayer']['ticket_promedio'])
        color_ticket = "trend-up" if variacion_ticket >= 0 else "trend-down"
        st.markdown(f"""
        <div class="comparison-card" style="border-left-color: {'#00ff00' if variacion_ticket >= 0 else '#ff0000'}">
            <div class="comparison-label">💵 Ticket Promedio</div>
            <div class="comparison-today">${comparison['hoy']['ticket_promedio']:,.0f}</div>
            <div class="{color_ticket}">{variacion_ticket:+.1f}% vs ayer</div>
            <div style="font-size: 11px; color: #888;">Ayer: ${comparison['ayer']['ticket_promedio']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.caption(f"📅 Comparación: {comparison['fecha_hoy'].strftime('%d/%m/%Y')} vs {comparison['fecha_ayer'].strftime('%d/%m/%Y')}")
else:
    st.info("📊 Carga más datos para ver comparación entre días")

st.markdown("---")

# SECCIÓN 3: Desempeño General
st.subheader("📈 Desempeño General")

col1, col2, col3 = st.columns(3)

with col1:
    promedio_diario = data['ventas_acumuladas'] / max(data['dias_operados'], 1)
    st.markdown(f"""
    <div class="metric-card metric-card-orange">
        <div class="metric-title">💵 ÚLTIMA VENTA</div>
        <div class="metric-value">${data['ventas_hoy']:,.0f}</div>
        <div class="metric-target">Promedio diario: ${promedio_diario:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card metric-card-blue">
        <div class="metric-title">📊 ACUMULADO MENSUAL</div>
        <div class="metric-value">${data['ventas_acumuladas']:,.0f}</div>
        <div class="metric-target">Días operados: {data['dias_operados']}/30</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    # Calcular crecimiento
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
            color_crec = "#00ff00" if crecimiento >= 0 else "#ff0000"
            st.markdown(f"""
            <div class="metric-card metric-card-green">
                <div class="metric-title">📈 CRECIMIENTO</div>
                <div class="metric-value" style="color: {color_crec};">{crecimiento:+.1f}%</div>
                <div class="metric-target">vs mes anterior</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="metric-card metric-card-green">
                <div class="metric-title">📈 CRECIMIENTO</div>
                <div class="metric-value">N/A</div>
                <div class="metric-target">Sin datos del mes anterior</div>
            </div>
            """, unsafe_allow_html=True)
    except:
        st.markdown(f"""
        <div class="metric-card metric-card-green">
            <div class="metric-title">📈 CRECIMIENTO</div>
            <div class="metric-value">N/A</div>
            <div class="metric-target">Sin datos disponibles</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# SECCIÓN 4: Gráfico
st.subheader("📈 Evolución Diaria")

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
        fig = make_subplots(rows=2, cols=1, 
                           subplot_titles=("Ventas Diarias", "Artículos por Ticket"),
                           vertical_spacing=0.15,
                           row_heights=[0.6, 0.4])
        
        # Ventas
        fig.add_trace(go.Bar(x=df_diario['fecha'], y=df_diario['ventas_dia'], 
                            name="Ventas", marker_color='#4CAF50', opacity=0.7), row=1, col=1)
        
        meta_diaria = data['objetivo_ventas'] / 30
        fig.add_trace(go.Scatter(x=df_diario['fecha'], y=[meta_diaria] * len(df_diario), 
                                name="Meta diaria", line=dict(color='#FF6B6B', dash='dash')), row=1, col=1)
        
        # Artículos
        fig.add_trace(go.Scatter(x=df_diario['fecha'], y=df_diario['articulos_ticket'], 
                                name="Artículos x Ticket", line=dict(color='#2196F3', width=3),
                                mode='lines+markers'), row=2, col=1)
        
        fig.add_trace(go.Scatter(x=df_diario['fecha'], y=[data['objetivo_articulos']] * len(df_diario), 
                                name=f"Meta: {data['objetivo_articulos']}", 
                                line=dict(color='#FF9800', dash='dash')), row=2, col=1)
        
        fig.update_layout(height=550, hovermode='x unified', template='plotly_white')
        fig.update_yaxes(title_text="Ventas ($)", tickformat='$,.0f', row=1, col=1)
        fig.update_yaxes(title_text="Artículos", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("📋 Ver detalle diario"):
            df_display = df_diario.copy()
            df_display['ventas_dia'] = df_display['ventas_dia'].apply(lambda x: f"${x:,.0f}")
            df_display['articulos_ticket'] = df_display['articulos_ticket'].apply(lambda x: f"{x:.1f}")
            df_display.columns = ['Fecha', 'Ventas', 'Artículos x Ticket']
            st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("📭 No hay datos para el mes actual")
        
except Exception as e:
    st.error(f"Error: {str(e)}")