# dashboard_app.py
import sqlite3
import pandas as pd
from datetime import datetime, date
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Ventas",
    page_icon="📊",
    layout="wide"
)

# Inicializar base de datos
def init_database():
    conn = sqlite3.connect('ventas_dashboard.db')
    cursor = conn.cursor()
    
    # Crear tabla de ventas diarias
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
    
    # Crear tabla para objetivos mensuales
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS objetivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mes INTEGER,
            año INTEGER,
            objetivo_ventas REAL,
            objetivo_conversion REAL,
            objetivo_ticket_promedio REAL,
            UNIQUE(mes, año)
        )
    ''')
    
    conn.commit()
    
    # Insertar objetivo por defecto si no existe
    cursor.execute("SELECT COUNT(*) FROM objetivos WHERE mes = ? AND año = ?", 
                   (date.today().month, date.today().year))
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO objetivos (mes, año, objetivo_ventas, objetivo_conversion, objetivo_ticket_promedio)
            VALUES (?, ?, ?, ?, ?)
        ''', (date.today().month, date.today().year, 1277000000, 37, 78000))
        conn.commit()
    
    conn.close()

# Función para importar desde Excel
def import_from_excel(uploaded_file):
    try:
        # Leer Excel
        df = pd.read_excel(uploaded_file)
        
        # Renombrar columnas esperadas
        columnas_esperadas = {
            'fecha': 'fecha',
            'ventas': 'ventas_dia',
            'tickets': 'tickets_dia',
            'visitas': 'visitas_dia'
        }
        
        # Verificar columnas
        df.columns = df.columns.str.lower().str.strip()
        
        conn = sqlite3.connect('ventas_dashboard.db')
        cursor = conn.cursor()
        
        registros_agregados = 0
        for _, row in df.iterrows():
            fecha = pd.to_datetime(row['fecha']).date()
            ventas_dia = float(row.get('ventas_dia', row.get('ventas', 0)))
            tickets_dia = int(row.get('tickets_dia', row.get('tickets', 0)))
            visitas_dia = int(row.get('visitas_dia', row.get('visitas', 0)))
            
            # Calcular métricas derivadas
            conversion = (tickets_dia / visitas_dia * 100) if visitas_dia > 0 else 0
            ticket_promedio = (ventas_dia / tickets_dia) if tickets_dia > 0 else 0
            articulos_ticket = float(row.get('articulos_ticket', 0))
            
            # Insertar o actualizar
            cursor.execute('''
                INSERT OR REPLACE INTO ventas_diarias 
                (fecha, ventas_dia, tickets_dia, visitas_dia, conversion, ticket_promedio, articulos_ticket)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (fecha, ventas_dia, tickets_dia, visitas_dia, conversion, ticket_promedio, articulos_ticket))
            registros_agregados += 1
        
        conn.commit()
        conn.close()
        return True, registros_agregados
    except Exception as e:
        return False, str(e)

# Obtener datos del mes actual
def get_current_month_data():
    conn = sqlite3.connect('ventas_dashboard.db')
    hoy = date.today()
    
    # Datos del mes actual
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
    
    # Ventas del día actual (último registro)
    df_hoy = pd.read_sql_query('''
        SELECT ventas_dia, conversion, ticket_promedio, articulos_ticket
        FROM ventas_diarias
        WHERE fecha = (SELECT MAX(fecha) FROM ventas_diarias)
    ''', conn)
    
    # Obtener objetivo del mes
    cursor = conn.cursor()
    cursor.execute('''
        SELECT objetivo_ventas, objetivo_conversion, objetivo_ticket_promedio
        FROM objetivos
        WHERE mes = ? AND año = ?
    ''', (hoy.month, hoy.year))
    objetivo = cursor.fetchone()
    
    conn.close()
    
    return {
        'ventas_acumuladas': df_mes['ventas_acumuladas'].iloc[0] if not df_mes['ventas_acumuladas'].isna().iloc[0] else 0,
        'conversion': df_mes['conversion_promedio'].iloc[0] if not df_mes['conversion_promedio'].isna().iloc[0] else 0,
        'ticket_promedio': df_mes['ticket_promedio'].iloc[0] if not df_mes['ticket_promedio'].isna().iloc[0] else 0,
        'articulos_ticket': df_mes['articulos_ticket'].iloc[0] if not df_mes['articulos_ticket'].isna().iloc[0] else 0,
        'ventas_hoy': df_hoy['ventas_dia'].iloc[0] if not df_hoy.empty else 0,
        'conversion_hoy': df_hoy['conversion'].iloc[0] if not df_hoy.empty else 0,
        'ticket_promedio_hoy': df_hoy['ticket_promedio'].iloc[0] if not df_hoy.empty else 0,
        'objetivo_ventas': objetivo[0] if objetivo else 1277000000,
        'objetivo_conversion': objetivo[1] if objetivo else 37,
        'objetivo_ticket': objetivo[2] if objetivo else 78000
    }

# Calcular crecimiento porcentual
def calcular_crecimiento(valor_actual, valor_anterior):
    if valor_anterior == 0:
        return 0
    return ((valor_actual - valor_anterior) / valor_anterior) * 100

# Mostrar métrica con color
def metric_card(title, value, target=None, suffix="", color_positive="#00ff00", color_negative="#ff0000"):
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.metric(title, f"{value:,.0f}{suffix}")
    if target:
        porcentaje = (value / target * 100) if target > 0 else 0
        color = color_positive if value >= target else color_negative
        with col2:
            st.markdown(f"<h4 style='color:{color}'>Meta: {target:,.0f}</h4>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<h4 style='color:{color}'>{porcentaje:.1f}%</h4>", unsafe_allow_html=True)

# Panel principal
def main():
    st.title("📊 Panel de Control de Ventas")
    st.markdown("---")
    
    # Inicializar DB
    init_database()
    
    # Sidebar para carga de datos
    with st.sidebar:
        st.header("📁 Carga de Datos")
        uploaded_file = st.file_uploader("Subir archivo Excel", type=['xlsx', 'xls'])
        
        if uploaded_file:
            if st.button("Importar Datos"):
                success, result = import_from_excel(uploaded_file)
                if success:
                    st.success(f"✅ {result} registros importados correctamente")
                    st.rerun()
                else:
                    st.error(f"❌ Error: {result}")
        
        st.markdown("---")
        st.header("📈 Formato Esperado del Excel")
        st.info("""
        Columnas necesarias:
        - **fecha** (YYYY-MM-DD)
        - **ventas** (número)
        - **tickets** (número)
        - **visitas** (número)
        - **articulos_ticket** (opcional)
        """)
        
        # Configurar objetivos
        st.header("🎯 Objetivos Mensuales")
        objetivo_ventas = st.number_input("Objetivo Ventas", value=1277000000, step=1000000, format="%d")
        objetivo_conversion = st.number_input("Objetivo Conversión (%)", value=37.0, step=1.0)
        objetivo_ticket = st.number_input("Objetivo Ticket Promedio ($)", value=78000, step=1000)
        
        if st.button("Actualizar Objetivos"):
            conn = sqlite3.connect('ventas_dashboard.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO objetivos (mes, año, objetivo_ventas, objetivo_conversion, objetivo_ticket_promedio)
                VALUES (?, ?, ?, ?, ?)
            ''', (date.today().month, date.today().year, objetivo_ventas, objetivo_conversion, objetivo_ticket))
            conn.commit()
            conn.close()
            st.success("✅ Objetivos actualizados")
            st.rerun()
    
    # Obtener datos
    data = get_current_month_data()
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("### 💰 Presupuesto Mensual")
        st.markdown(f"<h2 style='color:#FF6B6B'>${data['objetivo_ventas']:,.0f}</h2>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 🎫 Ticket Promedio")
        st.markdown(f"<h2 style='color:#4ECDC4'>${data['ticket_promedio']:,.0f}</h2>", unsafe_allow_html=True)
        crecimiento_ticket = calcular_crecimiento(data['ticket_promedio'], data['objetivo_ticket'])
        color_ticket = "🟢" if crecimiento_ticket >= 0 else "🔴"
        st.caption(f"{color_ticket} vs objetivo: {crecimiento_ticket:+.1f}%")
    
    with col3:
        st.markdown("### 📦 Artículos por ticket")
        st.markdown(f"<h2 style='color:#45B7D1'>{data['articulos_ticket']:.1f}</h2>", unsafe_allow_html=True)
    
    with col4:
        st.markdown("### 🔄 Conversión")
        st.markdown(f"<h2 style='color:#96CEB4'>{data['conversion']:.1f}%</h2>", unsafe_allow_html=True)
        crecimiento_conv = calcular_crecimiento(data['conversion'], data['objetivo_conversion'])
        color_conv = "🟢" if crecimiento_conv >= 0 else "🔴"
        st.caption(f"{color_conv} vs objetivo: {crecimiento_conv:+.1f}%")
    
    st.markdown("---")
    
    # Segunda fila de métricas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 💵 Venta Hoy")
        venta_hoy = data['ventas_hoy']
        st.markdown(f"<h2 style='color:{'#00ff00' if venta_hoy > data['ventas_acumuladas']/max(data['dias_operados'],1) else '#ff0000'}'>${venta_hoy:,.0f}</h2>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 📊 Acumulado mensual")
        acumulado = data['ventas_acumuladas']
        porcentaje_meta = (acumulado / data['objetivo_ventas'] * 100) if data['objetivo_ventas'] > 0 else 0
        color_acumulado = "#00ff00" if acumulado >= data['objetivo_ventas'] else "#ffa500"
        st.markdown(f"<h2 style='color:{color_acumulado}'>${acumulado:,.0f}</h2>", unsafe_allow_html=True)
        st.progress(min(porcentaje_meta/100, 1.0))
        st.caption(f"{porcentaje_meta:.1f}% de la meta mensual")
    
    with col3:
        st.markdown("### 📈 Crecimiento")
        # Calcular crecimiento vs mes anterior
        conn = sqlite3.connect('ventas_dashboard.db')
        query_anterior = '''
            SELECT SUM(ventas_dia) as ventas_anterior
            FROM ventas_diarias
            WHERE strftime('%Y-%m', fecha) = ?
        '''
        mes_anterior = date.today().replace(day=1) - pd.Timedelta(days=1)
        df_anterior = pd.read_sql_query(query_anterior, conn, params=[mes_anterior.strftime('%Y-%m')])
        conn.close()
        
        ventas_anterior = df_anterior['ventas_anterior'].iloc[0] if not df_anterior.empty else 0
        crecimiento = calcular_crecimiento(acumulado, ventas_anterior)
        color_crecimiento = "🟢" if crecimiento >= 0 else "🔴"
        st.markdown(f"<h2 style='color:{'#00ff00' if crecimiento >= 0 else '#ff0000'}'>{crecimiento:+.1f}%</h2>", unsafe_allow_html=True)
        st.caption(f"{color_crecimiento} vs mes anterior")
    
    st.markdown("---")
    
    # Gráfico de evolución diaria
    st.subheader("📈 Evolución Diaria de Ventas")
    conn = sqlite3.connect('ventas_dashboard.db')
    df_diario = pd.read_sql_query('''
        SELECT fecha, ventas_dia, conversion, ticket_promedio
        FROM ventas_diarias
        WHERE strftime('%Y-%m', fecha) = ?
        ORDER BY fecha
    ''', conn, params=[date.today().strftime('%Y-%m')])
    conn.close()
    
    if not df_diario.empty:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig.add_trace(
            go.Bar(x=df_diario['fecha'], y=df_diario['ventas_dia'], name="Ventas del día", marker_color='lightblue'),
            secondary_y=False,
        )
        
        fig.add_trace(
            go.Scatter(x=df_diario['fecha'], y=[data['objetivo_ventas']/30]*len(df_diario), 
                      name="Meta diaria", line=dict(color='red', dash='dash')),
            secondary_y=False,
        )
        
        fig.update_layout(
            title="Ventas Diarias",
            xaxis_title="Fecha",
            yaxis_title="Ventas ($)",
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabla de datos diarios
        with st.expander("📋 Ver detalle de ventas diarias"):
            st.dataframe(
                df_diario.style.format({
                    'ventas_dia': '${:,.0f}',
                    'conversion': '{:.1f}%',
                    'ticket_promedio': '${:,.0f}'
                }),
                use_container_width=True
            )
    else:
        st.warning("⚠️ No hay datos para el mes actual. Por favor, carga un archivo Excel con los datos.")

if __name__ == "__main__":
    main()