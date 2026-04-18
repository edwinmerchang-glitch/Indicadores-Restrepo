# dashboard_app.py - Versión completa con diseño premium uniforme
import sqlite3
import pandas as pd
from datetime import datetime, date, timedelta
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import warnings
warnings.filterwarnings('ignore')

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Ventas - Indicadores Restrepo",
    page_icon="📊",
    layout="wide"
)

# CSS personalizado con estilos premium para todas las tarjetas
st.markdown("""
<style>
    /* Estilos generales */
    .stApp {
        background-color: #f5f7fb;
    }
    
    /* Tarjeta premium base */
    .premium-card {
        border-radius: 15px;
        padding: 20px;
        color: white;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        position: relative;
        overflow: hidden;
        margin: 10px 0;
        transition: transform 0.3s ease;
    }
    .premium-card:hover {
        transform: translateY(-5px);
    }
    .premium-card::before {
        position: absolute;
        font-size: 80px;
        opacity: 0.1;
        bottom: -10px;
        right: -10px;
        transform: rotate(-10deg);
    }
    
    /* Colores específicos para cada tipo de tarjeta */
    .card-budget { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .card-budget::before { content: "💰"; }
    
    .card-ticket { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .card-ticket::before { content: "🎫"; }
    
    .card-articles { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    .card-articles::before { content: "📦"; }
    
    .card-conversion { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
    .card-conversion::before { content: "🔄"; }
    
    .card-sales { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
    .card-sales::before { content: "💵"; }
    
    .card-accumulated { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); }
    .card-accumulated::before { content: "📊"; }
    
    .card-growth { background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); }
    .card-growth::before { content: "📈"; }
    
    /* Estilos comunes para todas las tarjetas */
    .card-title {
        font-size: 14px;
        opacity: 0.9;
        letter-spacing: 2px;
        margin-bottom: 10px;
        text-transform: uppercase;
    }
    .card-value {
        font-size: 36px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .card-target {
        font-size: 12px;
        opacity: 0.8;
        margin-bottom: 5px;
    }
    .card-percentage {
        font-size: 14px;
        font-weight: bold;
        margin-top: 5px;
    }
    .card-progress {
        background-color: rgba(255,255,255,0.2);
        border-radius: 10px;
        height: 6px;
        margin: 10px 0;
        overflow: hidden;
    }
    .card-progress-bar {
        background: linear-gradient(90deg, #ffffff, rgba(255,255,255,0.5));
        width: 0%;
        height: 100%;
        border-radius: 10px;
        transition: width 1s ease;
    }
    .card-stats {
        display: flex;
        justify-content: space-between;
        margin-top: 10px;
        font-size: 11px;
        opacity: 0.8;
    }
    .card-stat {
        text-align: center;
    }
    .card-stat-value {
        font-size: 16px;
        font-weight: bold;
    }
    
    /* Tarjeta de comparación */
    .comparison-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 12px;
        padding: 15px;
        border-left: 4px solid;
        margin: 8px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: transform 0.2s ease;
    }
    .comparison-card:hover {
        transform: translateX(5px);
    }
    .comparison-label {
        font-size: 13px;
        font-weight: bold;
        color: #666;
        margin-bottom: 8px;
    }
    .comparison-values {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-top: 10px;
    }
    .comparison-today {
        font-size: 22px;
        font-weight: bold;
    }
    .comparison-variation {
        font-size: 16px;
        font-weight: bold;
    }
    .comparison-yesterday {
        font-size: 11px;
        color: #888;
        margin-top: 5px;
    }
    .trend-up { color: #00ff00; }
    .trend-down { color: #ff0000; }
    .trend-neutral { color: #ffa500; }
    
    /* Separador */
    .section-divider {
        margin: 30px 0 20px 0;
        border-top: 2px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# Título principal
st.title("📊 Panel de Control de Ventas")
st.caption("Indicadores Restrepo")
st.markdown("---")

# Función para migrar base de datos
def migrar_base_datos():
    try:
        conn = sqlite3.connect('ventas_dashboard.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='objetivos'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(objetivos)")
            columnas = [columna[1] for columna in cursor.fetchall()]
            
            if 'objetivo_articulos_ticket' not in columnas:
                st.info("🔄 Migrando base de datos...")
                cursor.execute('''
                    CREATE TABLE objetivos_nueva (
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
                
                cursor.execute('''
                    INSERT INTO objetivos_nueva (id, mes, año, objetivo_ventas, objetivo_conversion, objetivo_ticket_promedio, objetivo_articulos_ticket)
                    SELECT id, mes, año, objetivo_ventas, objetivo_conversion, objetivo_ticket_promedio, 3.5
                    FROM objetivos
                ''')
                
                cursor.execute("DROP TABLE objetivos")
                cursor.execute("ALTER TABLE objetivos_nueva RENAME TO objetivos")
                conn.commit()
                st.success("✅ Base de datos migrada")
        
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error en migración: {str(e)}")
        return False

# Inicializar base de datos
def init_database():
    try:
        migrar_base_datos()
        
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
        st.error(f"Error inicializando base de datos: {str(e)}")
        return False

# Función para importar desde Excel
def import_from_excel(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        df.columns = df.columns.str.lower().str.strip()
        
        conn = sqlite3.connect('ventas_dashboard.db')
        cursor = conn.cursor()
        
        registros_agregados = 0
        errores = []
        
        for idx, row in df.iterrows():
            try:
                if 'fecha' not in row:
                    errores.append(f"Fila {idx+2}: Columna 'fecha' no encontrada")
                    continue
                    
                fecha = pd.to_datetime(row['fecha']).date()
                ventas_dia = float(row.get('ventas', row.get('ventas_dia', 0)))
                tickets_dia = int(row.get('tickets', row.get('tickets_dia', 0)))
                visitas_dia = int(row.get('visitas', row.get('visitas_dia', 0)))
                articulos_ticket = float(row.get('articulos_ticket', row.get('articulos', 0)))
                
                conversion = (tickets_dia / visitas_dia * 100) if visitas_dia > 0 else 0
                ticket_promedio = (ventas_dia / tickets_dia) if tickets_dia > 0 else 0
                
                cursor.execute('''
                    INSERT OR REPLACE INTO ventas_diarias 
                    (fecha, ventas_dia, tickets_dia, visitas_dia, conversion, ticket_promedio, articulos_ticket)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (fecha, ventas_dia, tickets_dia, visitas_dia, conversion, ticket_promedio, articulos_ticket))
                registros_agregados += 1
                
            except Exception as e:
                errores.append(f"Fila {idx+2}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        if errores:
            st.warning(f"Se procesaron {registros_agregados} registros con {len(errores)} advertencias")
        else:
            st.success(f"✅ {registros_agregados} registros importados correctamente")
        
        return True, registros_agregados
    except Exception as e:
        return False, str(e)

# Obtener datos del día actual y anterior
def get_comparison_data():
    try:
        conn = sqlite3.connect('ventas_dashboard.db')
        
        df_ultima = pd.read_sql_query('''
            SELECT MAX(fecha) as ultima_fecha
            FROM ventas_diarias
        ''', conn)
        
        if df_ultima['ultima_fecha'].iloc[0] is None:
            conn.close()
            return None
        
        ultima_fecha = pd.to_datetime(df_ultima['ultima_fecha'].iloc[0]).date()
        fecha_anterior = ultima_fecha - timedelta(days=1)
        
        df_hoy = pd.read_sql_query('''
            SELECT fecha, ventas_dia, tickets_dia, visitas_dia, conversion, ticket_promedio, articulos_ticket
            FROM ventas_diarias
            WHERE fecha = ?
        ''', conn, params=[ultima_fecha])
        
        df_ayer = pd.read_sql_query('''
            SELECT fecha, ventas_dia, tickets_dia, visitas_dia, conversion, ticket_promedio, articulos_ticket
            FROM ventas_diarias
            WHERE fecha = ?
        ''', conn, params=[fecha_anterior])
        
        conn.close()
        
        if df_hoy.empty:
            return None
        
        resultado = {
            'fecha_hoy': ultima_fecha,
            'fecha_ayer': fecha_anterior if not df_ayer.empty else None,
            'tiene_ayer': not df_ayer.empty
        }
        
        resultado['hoy'] = {
            'ventas': float(df_hoy['ventas_dia'].iloc[0]),
            'tickets': int(df_hoy['tickets_dia'].iloc[0]),
            'visitas': int(df_hoy['visitas_dia'].iloc[0]),
            'conversion': float(df_hoy['conversion'].iloc[0]),
            'ticket_promedio': float(df_hoy['ticket_promedio'].iloc[0]),
            'articulos': float(df_hoy['articulos_ticket'].iloc[0])
        }
        
        if not df_ayer.empty:
            resultado['ayer'] = {
                'ventas': float(df_ayer['ventas_dia'].iloc[0]),
                'tickets': int(df_ayer['tickets_dia'].iloc[0]),
                'visitas': int(df_ayer['visitas_dia'].iloc[0]),
                'conversion': float(df_ayer['conversion'].iloc[0]),
                'ticket_promedio': float(df_ayer['ticket_promedio'].iloc[0]),
                'articulos': float(df_ayer['articulos_ticket'].iloc[0])
            }
        
        return resultado
    except Exception as e:
        st.error(f"Error obteniendo comparación: {str(e)}")
        return None

# Obtener datos del mes actual
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
                COUNT(DISTINCT fecha) as dias_operados,
                MAX(fecha) as ultima_fecha
            FROM ventas_diarias
            WHERE strftime('%Y-%m', fecha) = ?
        '''
        df_mes = pd.read_sql_query(query, conn, params=[hoy.strftime('%Y-%m')])
        
        if not df_mes.empty and df_mes['ultima_fecha'].iloc[0]:
            ultima_fecha = df_mes['ultima_fecha'].iloc[0]
            df_hoy = pd.read_sql_query('''
                SELECT ventas_dia, conversion, ticket_promedio, articulos_ticket
                FROM ventas_diarias
                WHERE fecha = ?
            ''', conn, params=[ultima_fecha])
            ventas_hoy = df_hoy['ventas_dia'].iloc[0] if not df_hoy.empty else 0
        else:
            ventas_hoy = 0
        
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
            'ventas_hoy': ventas_hoy,
            'objetivo_ventas': objetivo[0],
            'objetivo_conversion': objetivo[1],
            'objetivo_ticket': objetivo[2],
            'objetivo_articulos': objetivo[3]
        }
    except Exception as e:
        st.error(f"Error obteniendo datos: {str(e)}")
        return None

# Función para crear tarjeta premium
def crear_tarjeta_premium(card_class, title, value, target=None, suffix="", precision=0, show_progress=False, extra_stats=None):
    if target:
        percentage = (value / target * 100) if target > 0 else 0
        percentage_text = f"{percentage:.1f}%"
        color = "#ffffff"
        
        if precision == 0:
            value_text = f"{value:,.0f}{suffix}"
            target_text = f"{target:,.0f}{suffix}"
        else:
            value_text = f"{value:.{precision}f}{suffix}"
            target_text = f"{target:.{precision}f}{suffix}"
    else:
        percentage_text = ""
        if precision == 0:
            value_text = f"{value:,.0f}{suffix}"
        else:
            value_text = f"{value:.{precision}f}{suffix}"
        target_text = ""
    
    html = f"""
    <div class='premium-card {card_class}'>
        <div class='card-title'>{title}</div>
        <div class='card-value'>{value_text}</div>
    """
    
    if target:
        html += f"""
        <div class='card-target'>Meta: {target_text}</div>
        <div class='card-percentage'>{percentage_text}</div>
        """
        
        if show_progress:
            html += f"""
            <div class='card-progress'>
                <div class='card-progress-bar' style='width: {min(percentage, 100)}%;'></div>
            </div>
            """
    
    if extra_stats:
        html += f"""
        <div class='card-stats'>
            {extra_stats}
        </div>
        """
    
    html += "</div>"
    return html

# Calcular variación
def calcular_variacion(valor_actual, valor_anterior):
    if valor_anterior == 0:
        return 0
    return ((valor_actual - valor_anterior) / valor_anterior) * 100

# Mostrar tarjeta de comparación
def mostrar_comparacion(label, valor_hoy, valor_ayer, formato="{:,.0f}", sufijo=""):
    variacion = calcular_variacion(valor_hoy, valor_ayer)
    color = "trend-up" if variacion >= 0 else "trend-down"
    signo = "+" if variacion >= 0 else ""
    
    if formato == "{:.1f}":
        valor_hoy_str = formato.format(valor_hoy)
        valor_ayer_str = formato.format(valor_ayer)
    else:
        valor_hoy_str = formato.format(valor_hoy)
        valor_ayer_str = formato.format(valor_ayer)
    
    st.markdown(f"""
    <div class='comparison-card' style='border-left-color: {"#00ff00" if variacion >= 0 else "#ff0000"};'>
        <div class='comparison-label'>{label}</div>
        <div class='comparison-values'>
            <div>
                <span class='comparison-today'>{valor_hoy_str}{sufijo}</span>
                <span style='font-size:11px; color:#888; margin-left:8px;'>Hoy</span>
            </div>
            <div class='comparison-variation {color}'>
                {signo}{variacion:.1f}%
            </div>
        </div>
        <div class='comparison-yesterday'>
            Ayer: {valor_ayer_str}{sufijo}
        </div>
    </div>
    """, unsafe_allow_html=True)

# Panel principal
def main():
    if not init_database():
        st.stop()
    
    # Sidebar
    with st.sidebar:
        st.header("📁 Carga de Datos")
        uploaded_file = st.file_uploader("Subir archivo Excel", type=['xlsx', 'xls'])
        
        if uploaded_file:
            if st.button("📤 Importar Datos", type="primary"):
                with st.spinner("Procesando..."):
                    success, result = import_from_excel(uploaded_file)
                    if success:
                        st.rerun()
                    else:
                        st.error(f"❌ Error: {result}")
        
        st.markdown("---")
        st.header("📈 Formato del Excel")
        st.info("""
        **Columnas requeridas:**
        - fecha (YYYY-MM-DD)
        - ventas
        - tickets
        - visitas
        - articulos_ticket (opcional)
        """)
        
        st.markdown("---")
        st.header("🎯 Configurar Metas")
        
        objetivo_ventas = st.number_input("Meta Ventas ($)", value=1277000000, step=1000000, format="%d")
        objetivo_conversion = st.number_input("Meta Conversión (%)", value=37.0, step=1.0, format="%.1f")
        objetivo_ticket = st.number_input("Meta Ticket Promedio ($)", value=78000, step=1000, format="%d")
        objetivo_articulos = st.number_input("Meta Artículos x Ticket", value=3.5, step=0.1, format="%.1f")
        
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
    
    # Obtener datos
    data = get_current_month_data()
    if not data:
        st.warning("⚠️ No se pudieron cargar los datos")
        return
    
    comparison = get_comparison_data()
    
    # SECCIÓN 1: Indicadores Clave del Mes (Tarjetas Premium)
    st.subheader("📊 Indicadores Clave del Mes")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        porcentaje_meta = (data['ventas_acumuladas'] / data['objetivo_ventas'] * 100) if data['objetivo_ventas'] > 0 else 0
        dias_restantes = max(0, 30 - data['dias_operados'])
        ritmo_actual = data['ventas_acumuladas'] / data['dias_operados'] if data['dias_operados'] > 0 else 0
        venta_promedio_necesaria = max(0, (data['objetivo_ventas'] - data['ventas_acumuladas']) / dias_restantes) if dias_restantes > 0 else 0
        
        extra_stats = f"""
            <div class='card-stat'>
                <div class='card-stat-value'>${data['ventas_acumuladas']:,.0f}</div>
                <div>Acumulado</div>
            </div>
            <div class='card-stat'>
                <div class='card-stat-value'>{porcentaje_meta:.1f}%</div>
                <div>Progreso</div>
            </div>
            <div class='card-stat'>
                <div class='card-stat-value'>${ritmo_actual:,.0f}</div>
                <div>Ritmo diario</div>
            </div>
        """
        
        st.markdown(crear_tarjeta_premium(
            "card-budget", 
            "PRESUPUESTO MENSUAL", 
            data['objetivo_ventas'], 
            None, 
            "$", 
            0, 
            True,
            extra_stats
        ), unsafe_allow_html=True)
        
        st.caption(f"📅 {data['dias_operados']} días operados | {dias_restantes} días restantes")
        st.caption(f"🎯 Meta diaria necesaria: ${venta_promedio_necesaria:,.0f}")
    
    with col2:
        st.markdown(crear_tarjeta_premium(
            "card-ticket", 
            "TICKET PROMEDIO", 
            data['ticket_promedio'], 
            data['objetivo_ticket'], 
            "$", 
            0, 
            True
        ), unsafe_allow_html=True)
    
    with col3:
        st.markdown(crear_tarjeta_premium(
            "card-articles", 
            "ARTÍCULOS x TICKET", 
            data['articulos_ticket'], 
            data['objetivo_articulos'], 
            "", 
            1, 
            True
        ), unsafe_allow_html=True)
    
    with col4:
        st.markdown(crear_tarjeta_premium(
            "card-conversion", 
            "CONVERSIÓN", 
            data['conversion'], 
            data['objetivo_conversion'], 
            "%", 
            1, 
            True
        ), unsafe_allow_html=True)
    
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    
    # SECCIÓN 2: Comparación Día Actual vs Día Anterior
    st.subheader("📈 Comparación Diaria")
    
    if comparison and comparison['tiene_ayer']:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            mostrar_comparacion("💰 Ventas", 
                              comparison['hoy']['ventas'], 
                              comparison['ayer']['ventas'], 
                              "${:,.0f}", "")
        
        with col2:
            mostrar_comparacion("🎫 Tickets", 
                              comparison['hoy']['tickets'], 
                              comparison['ayer']['tickets'], 
                              "{:,.0f}", "")
        
        with col3:
            mostrar_comparacion("👥 Visitas", 
                              comparison['hoy']['visitas'], 
                              comparison['ayer']['visitas'], 
                              "{:,.0f}", "")
        
        with col4:
            mostrar_comparacion("📦 Artículos x Ticket", 
                              comparison['hoy']['articulos'], 
                              comparison['ayer']['articulos'], 
                              "{:.1f}", "")
        
        col1, col2 = st.columns(2)
        
        with col1:
            mostrar_comparacion("🔄 Conversión", 
                              comparison['hoy']['conversion'], 
                              comparison['ayer']['conversion'], 
                              "{:.1f}", "%")
        
        with col2:
            mostrar_comparacion("💵 Ticket Promedio", 
                              comparison['hoy']['ticket_promedio'], 
                              comparison['ayer']['ticket_promedio'], 
                              "${:,.0f}", "")
        
        st.caption(f"📅 Comparación entre {comparison['fecha_hoy'].strftime('%d/%m/%Y')} (hoy) y {comparison['fecha_ayer'].strftime('%d/%m/%Y')} (ayer)")
    else:
        if comparison and not comparison['tiene_ayer']:
            st.info(f"📊 Solo hay datos para {comparison['fecha_hoy'].strftime('%d/%m/%Y')}. Carga más días para ver comparaciones.")
        else:
            st.info("📊 Carga datos para ver comparación entre días")
    
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    
    # SECCIÓN 3: Desempeño General (Tarjetas Premium)
    st.subheader("📈 Desempeño General")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        promedio_diario = data['ventas_acumuladas'] / max(data['dias_operados'], 1)
        variacion_vs_promedio = calcular_variacion(data['ventas_hoy'], promedio_diario)
        
        extra_stats = f"""
            <div class='card-stat'>
                <div class='card-stat-value'>${promedio_diario:,.0f}</div>
                <div>Promedio diario</div>
            </div>
            <div class='card-stat'>
                <div class='card-stat-value' style='color: {"#00ff00" if variacion_vs_promedio >= 0 else "#ff0000"}'>
                    {variacion_vs_promedio:+.1f}%
                </div>
                <div>vs promedio</div>
            </div>
        """
        
        st.markdown(crear_tarjeta_premium(
            "card-sales", 
            "ÚLTIMA VENTA", 
            data['ventas_hoy'], 
            None, 
            "$", 
            0, 
            False,
            extra_stats
        ), unsafe_allow_html=True)
    
    with col2:
        porcentaje_meta = (data['ventas_acumuladas'] / data['objetivo_ventas'] * 100) if data['objetivo_ventas'] > 0 else 0
        
        extra_stats = f"""
            <div class='card-stat'>
                <div class='card-stat-value'>{data['dias_operados']}/30</div>
                <div>Días operados</div>
            </div>
            <div class='card-stat'>
                <div class='card-stat-value'>{porcentaje_meta:.1f}%</div>
                <div>Meta alcanzada</div>
            </div>
        """
        
        st.markdown(crear_tarjeta_premium(
            "card-accumulated", 
            "ACUMULADO MENSUAL", 
            data['ventas_acumuladas'], 
            data['objetivo_ventas'], 
            "$", 
            0, 
            True,
            extra_stats
        ), unsafe_allow_html=True)
    
    with col3:
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
                extra_stats = f"""
                    <div class='card-stat'>
                        <div class='card-stat-value'>${ventas_anterior:,.0f}</div>
                        <div>Mes anterior</div>
                    </div>
                    <div class='card-stat'>
                        <div class='card-stat-value' style='color: {"#00ff00" if crecimiento >= 0 else "#ff0000"}'>
                            {crecimiento:+.1f}%
                        </div>
                        <div>Variación</div>
                    </div>
                """
                
                st.markdown(crear_tarjeta_premium(
                    "card-growth", 
                    "CRECIMIENTO", 
                    data['ventas_acumuladas'], 
                    None, 
                    "$", 
                    0, 
                    False,
                    extra_stats
                ), unsafe_allow_html=True)
            else:
                st.markdown(crear_tarjeta_premium(
                    "card-growth", 
                    "CRECIMIENTO", 
                    0, 
                    None, 
                    "$", 
                    0, 
                    False,
                    "<div class='card-stat'>Sin datos del mes anterior</div>"
                ), unsafe_allow_html=True)
        except:
            st.markdown(crear_tarjeta_premium(
                "card-growth", 
                "CRECIMIENTO", 
                0, 
                None, 
                "$", 
                0, 
                False,
                "<div class='card-stat'>Sin datos disponibles</div>"
            ), unsafe_allow_html=True)
    
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    
    # SECCIÓN 4: Evolución Diaria
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
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=("Ventas Diarias", "Artículos por Ticket"),
                vertical_spacing=0.15,
                row_heights=[0.6, 0.4]
            )
            
            fig.add_trace(
                go.Bar(x=df_diario['fecha'], y=df_diario['ventas_dia'], 
                       name="Ventas", marker_color='#4CAF50', opacity=0.7),
                row=1, col=1
            )
            
            meta_diaria = data['objetivo_ventas'] / 30
            fig.add_trace(
                go.Scatter(x=df_diario['fecha'], y=[meta_diaria] * len(df_diario), 
                          name=f"Meta diaria", line=dict(color='#FF6B6B', dash='dash', width=2)),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(x=df_diario['fecha'], y=df_diario['articulos_ticket'], 
                          name="Artículos x Ticket", line=dict(color='#2196F3', width=3),
                          mode='lines+markers', marker=dict(size=8)),
                row=2, col=1
            )
            
            fig.add_trace(
                go.Scatter(x=df_diario['fecha'], y=[data['objetivo_articulos']] * len(df_diario), 
                          name=f"Meta: {data['objetivo_articulos']} artículos", 
                          line=dict(color='#FF9800', dash='dash', width=2)),
                row=2, col=1
            )
            
            fig.update_layout(
                height=550,
                hovermode='x unified',
                showlegend=True,
                template='plotly_white',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            fig.update_yaxes(title_text="Ventas ($)", tickformat='$,.0f', row=1, col=1)
            fig.update_yaxes(title_text="Artículos", row=2, col=1)
            fig.update_xaxes(title_text="Fecha", row=2, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("📋 Ver detalle diario"):
                df_display = df_diario.copy()
                df_display['ventas_dia'] = df_display['ventas_dia'].apply(lambda x: f"${x:,.0f}")
                df_display['articulos_ticket'] = df_display['articulos_ticket'].apply(lambda x: f"{x:.1f}")
                df_display.columns = ['Fecha', 'Ventas', 'Artículos x Ticket']
                st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("📭 No hay datos para el mes actual. Carga un archivo Excel para comenzar.")
            
    except Exception as e:
        st.error(f"Error al cargar el gráfico: {str(e)}")

if __name__ == "__main__":
    main()