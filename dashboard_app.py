# dashboard_app.py
import sqlite3
import pandas as pd
from datetime import datetime, date
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

# Título principal
st.title("📊 Panel de Control de Ventas - Indicadores Restrepo")
st.markdown("---")

# Función para migrar base de datos existente
def migrar_base_datos():
    try:
        conn = sqlite3.connect('ventas_dashboard.db')
        cursor = conn.cursor()
        
        # Verificar si la tabla objetivos existe y tiene la columna objetivo_articulos_ticket
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='objetivos'")
        if cursor.fetchone():
            # Verificar columnas existentes
            cursor.execute("PRAGMA table_info(objetivos)")
            columnas = [columna[1] for columna in cursor.fetchall()]
            
            if 'objetivo_articulos_ticket' not in columnas:
                st.info("🔄 Migrando base de datos: agregando columna objetivo_articulos_ticket...")
                # Crear tabla temporal con nueva estructura
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
                
                # Copiar datos existentes
                cursor.execute('''
                    INSERT INTO objetivos_nueva (id, mes, año, objetivo_ventas, objetivo_conversion, objetivo_ticket_promedio, objetivo_articulos_ticket)
                    SELECT id, mes, año, objetivo_ventas, objetivo_conversion, objetivo_ticket_promedio, 3.5
                    FROM objetivos
                ''')
                
                # Reemplazar tabla
                cursor.execute("DROP TABLE objetivos")
                cursor.execute("ALTER TABLE objetivos_nueva RENAME TO objetivos")
                
                conn.commit()
                st.success("✅ Base de datos migrada correctamente")
        
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error en migración: {str(e)}")
        return False

# Inicializar base de datos
def init_database():
    try:
        # Primero migrar si es necesario
        migrar_base_datos()
        
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
        
        # Crear tabla para objetivos mensuales (actualizada con articulos_por_ticket)
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
        
        # Insertar objetivo por defecto si no existe para el mes actual
        cursor.execute("SELECT COUNT(*) FROM objetivos WHERE mes = ? AND año = ?", 
                       (date.today().month, date.today().year))
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO objetivos (mes, año, objetivo_ventas, objetivo_conversion, objetivo_ticket_promedio, objetivo_articulos_ticket)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (date.today().month, date.today().year, 1277000000, 37.0, 78000, 3.5))
            conn.commit()
            st.info("📝 Objetivos por defecto creados para el mes actual")
        
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error inicializando base de datos: {str(e)}")
        return False

# Función para importar desde Excel
def import_from_excel(uploaded_file):
    try:
        # Leer Excel con manejo de errores
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        
        # Normalizar nombres de columnas
        df.columns = df.columns.str.lower().str.strip()
        
        conn = sqlite3.connect('ventas_dashboard.db')
        cursor = conn.cursor()
        
        registros_agregados = 0
        errores = []
        
        for idx, row in df.iterrows():
            try:
                # Convertir fecha
                if 'fecha' not in row:
                    errores.append(f"Fila {idx+2}: Columna 'fecha' no encontrada")
                    continue
                    
                fecha = pd.to_datetime(row['fecha']).date()
                
                # Obtener valores con manejo de columnas flexibles
                ventas_dia = float(row.get('ventas', row.get('ventas_dia', 0)))
                tickets_dia = int(row.get('tickets', row.get('tickets_dia', 0)))
                visitas_dia = int(row.get('visitas', row.get('visitas_dia', 0)))
                articulos_ticket = float(row.get('articulos_ticket', row.get('articulos', 0)))
                
                # Calcular métricas derivadas
                conversion = (tickets_dia / visitas_dia * 100) if visitas_dia > 0 else 0
                ticket_promedio = (ventas_dia / tickets_dia) if tickets_dia > 0 else 0
                
                # Insertar o actualizar
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
            with st.expander("Ver detalles de errores"):
                for error in errores[:10]:
                    st.write(f"- {error}")
        else:
            st.success(f"✅ {registros_agregados} registros importados correctamente")
        
        return True, registros_agregados
    except Exception as e:
        return False, str(e)

# Obtener datos del mes actual
def get_current_month_data():
    try:
        conn = sqlite3.connect('ventas_dashboard.db')
        hoy = date.today()
        
        # Datos del mes actual
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
        
        # Ventas del día más reciente
        if not df_mes.empty and df_mes['ultima_fecha'].iloc[0]:
            ultima_fecha = df_mes['ultima_fecha'].iloc[0]
            df_hoy = pd.read_sql_query('''
                SELECT ventas_dia, conversion, ticket_promedio, articulos_ticket
                FROM ventas_diarias
                WHERE fecha = ?
            ''', conn, params=[ultima_fecha])
            ventas_hoy = df_hoy['ventas_dia'].iloc[0] if not df_hoy.empty else 0
            conversion_hoy = df_hoy['conversion'].iloc[0] if not df_hoy.empty else 0
            ticket_hoy = df_hoy['ticket_promedio'].iloc[0] if not df_hoy.empty else 0
            articulos_hoy = df_hoy['articulos_ticket'].iloc[0] if not df_hoy.empty else 0
        else:
            ventas_hoy = 0
            conversion_hoy = 0
            ticket_hoy = 0
            articulos_hoy = 0
        
        # Obtener objetivo del mes
        cursor = conn.cursor()
        cursor.execute('''
            SELECT objetivo_ventas, objetivo_conversion, objetivo_ticket_promedio, objetivo_articulos_ticket
            FROM objetivos
            WHERE mes = ? AND año = ?
        ''', (hoy.month, hoy.year))
        objetivo = cursor.fetchone()
        
        conn.close()
        
        # Manejar caso cuando no hay objetivos
        if not objetivo:
            objetivo = (1277000000, 37.0, 78000, 3.5)
        
        return {
            'ventas_acumuladas': float(df_mes['ventas_acumuladas'].iloc[0]) if not df_mes.empty and pd.notna(df_mes['ventas_acumuladas'].iloc[0]) else 0,
            'conversion': float(df_mes['conversion_promedio'].iloc[0]) if not df_mes.empty and pd.notna(df_mes['conversion_promedio'].iloc[0]) else 0,
            'ticket_promedio': float(df_mes['ticket_promedio'].iloc[0]) if not df_mes.empty and pd.notna(df_mes['ticket_promedio'].iloc[0]) else 0,
            'articulos_ticket': float(df_mes['articulos_ticket'].iloc[0]) if not df_mes.empty and pd.notna(df_mes['articulos_ticket'].iloc[0]) else 0,
            'dias_operados': int(df_mes['dias_operados'].iloc[0]) if not df_mes.empty and pd.notna(df_mes['dias_operados'].iloc[0]) else 0,
            'ventas_hoy': ventas_hoy,
            'conversion_hoy': conversion_hoy,
            'ticket_promedio_hoy': ticket_hoy,
            'articulos_hoy': articulos_hoy,
            'objetivo_ventas': objetivo[0],
            'objetivo_conversion': objetivo[1],
            'objetivo_ticket': objetivo[2],
            'objetivo_articulos': objetivo[3]
        }
    except Exception as e:
        st.error(f"Error obteniendo datos: {str(e)}")
        return None

# Calcular crecimiento porcentual
def calcular_crecimiento(valor_actual, valor_anterior):
    if valor_anterior == 0:
        return 0
    return ((valor_actual - valor_anterior) / valor_anterior) * 100

# Mostrar tarjeta de métrica con indicador de meta
def metric_card_with_target(title, value, target, suffix="", precision=0):
    if value == 0 and target == 0:
        color = "#ffa500"
        display_value = "N/A"
        porcentaje = 0
    else:
        color = "#00ff00" if value >= target else "#ff0000"
        display_value = f"{value:,.{precision}f}{suffix}" if precision == 0 else f"{value:.{precision}f}{suffix}"
        porcentaje = (value / target * 100) if target > 0 else 0
    
    col1, col2, col3 = st.columns([3, 1.5, 1])
    with col1:
        st.markdown(f"### {title}\n<h2 style='color:{color};'>{display_value}</h2>", unsafe_allow_html=True)
    with col2:
        if target > 0:
            st.markdown(f"<p style='margin-top: 30px;'><strong>Meta:</strong> {target:,.{precision}f}{suffix}</p>", unsafe_allow_html=True)
        else:
            st.markdown(f"<p style='margin-top: 30px;'><strong>Meta:</strong> No definida</p>", unsafe_allow_html=True)
    with col3:
        if target > 0:
            st.markdown(f"<p style='margin-top: 30px; color:{color};'><strong>{porcentaje:.1f}%</strong></p>", unsafe_allow_html=True)

# Panel principal
def main():
    # Inicializar DB
    if not init_database():
        st.stop()
    
    # Sidebar para carga de datos
    with st.sidebar:
        st.header("📁 Carga de Datos")
        st.markdown("### Subir archivo Excel")
        uploaded_file = st.file_uploader("Seleccionar archivo Excel", type=['xlsx', 'xls'])
        
        if uploaded_file:
            if st.button("📤 Importar Datos", type="primary"):
                with st.spinner("Procesando archivo..."):
                    success, result = import_from_excel(uploaded_file)
                    if success:
                        st.rerun()
                    else:
                        st.error(f"❌ Error: {result}")
        
        st.markdown("---")
        st.header("📈 Formato Esperado del Excel")
        st.info("""
        **Columnas necesarias:**
        - `fecha` (YYYY-MM-DD)
        - `ventas` (número)
        - `tickets` (número)
        - `visitas` (número)
        - `articulos_ticket` (opcional, promedio de artículos por ticket)
        
        **Ejemplo:**
        | fecha | ventas | tickets | visitas | articulos_ticket |
        |-------|--------|---------|---------|------------------|
        | 2026-04-01 | 32990000 | 423 | 1143 | 3.2 |
        """)
        
        st.markdown("---")
        st.header("🎯 Configurar Objetivos Mensuales")
        
        objetivo_ventas = st.number_input("💰 Objetivo Ventas ($)", value=1277000000, step=1000000, format="%d")
        objetivo_conversion = st.number_input("📊 Objetivo Conversión (%)", value=37.0, step=1.0, format="%.1f")
        objetivo_ticket = st.number_input("🎫 Objetivo Ticket Promedio ($)", value=78000, step=1000, format="%d")
        objetivo_articulos = st.number_input("📦 Objetivo Artículos por Ticket", value=3.5, step=0.1, format="%.1f")
        
        if st.button("💾 Actualizar Objetivos", type="primary"):
            try:
                conn = sqlite3.connect('ventas_dashboard.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO objetivos (mes, año, objetivo_ventas, objetivo_conversion, objetivo_ticket_promedio, objetivo_articulos_ticket)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (date.today().month, date.today().year, objetivo_ventas, objetivo_conversion, objetivo_ticket, objetivo_articulos))
                conn.commit()
                conn.close()
                st.success("✅ Objetivos actualizados correctamente")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Obtener datos
    data = get_current_month_data()
    if not data:
        st.warning("⚠️ No se pudieron cargar los datos. Por favor, verifica la base de datos.")
        return
    
    # Métricas principales
    st.subheader("📊 Indicadores Clave del Mes")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("### 💰 Presupuesto Mensual")
        st.markdown(f"<h2 style='color:#FF6B6B;'>${data['objetivo_ventas']:,.0f}</h2>", unsafe_allow_html=True)
    
    with col2:
        metric_card_with_target("🎫 Ticket Promedio", data['ticket_promedio'], data['objetivo_ticket'], "$", 0)
    
    with col3:
        metric_card_with_target("📦 Artículos x Ticket", data['articulos_ticket'], data['objetivo_articulos'], "", 1)
    
    with col4:
        metric_card_with_target("🔄 Conversión", data['conversion'], data['objetivo_conversion'], "%", 1)
    
    st.markdown("---")
    
    # Segunda fila de métricas
    st.subheader("📈 Desempeño Diario y Acumulado")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 💵 Última Venta Registrada")
        venta_hoy = data['ventas_hoy']
        if data['dias_operados'] > 0:
            promedio_diario = data['ventas_acumuladas'] / data['dias_operados']
            color_venta = "#00ff00" if venta_hoy > promedio_diario else "#ff0000"
            st.markdown(f"<h2 style='color:{color_venta};'>${venta_hoy:,.0f}</h2>", unsafe_allow_html=True)
            st.caption(f"📊 Promedio diario: ${promedio_diario:,.0f}")
        else:
            st.markdown("<h2 style='color:#ffa500;'>$0</h2>", unsafe_allow_html=True)
            st.caption("📊 Sin datos aún")
        
        # Mostrar artículos del último día
        if data['articulos_hoy'] > 0:
            color_arts = "#00ff00" if data['articulos_hoy'] >= data['objetivo_articulos'] else "#ff0000"
            st.caption(f"📦 Artículos hoy: {data['articulos_hoy']:.1f} (Meta: {data['objetivo_articulos']:.1f})")
    
    with col2:
        st.markdown("### 📊 Acumulado Mensual")
        acumulado = data['ventas_acumuladas']
        porcentaje_meta = (acumulado / data['objetivo_ventas'] * 100) if data['objetivo_ventas'] > 0 else 0
        color_acumulado = "#00ff00" if acumulado >= data['objetivo_ventas'] else "#ffa500"
        st.markdown(f"<h2 style='color:{color_acumulado};'>${acumulado:,.0f}</h2>", unsafe_allow_html=True)
        if data['objetivo_ventas'] > 0:
            st.progress(min(porcentaje_meta/100, 1.0))
            st.caption(f"🎯 {porcentaje_meta:.1f}% de la meta mensual")
        
        # Mostrar días operados
        st.caption(f"📅 Días con datos: {data['dias_operados']}/30")
    
    with col3:
        st.markdown("### 📈 Crecimiento vs Mes Anterior")
        # Calcular crecimiento vs mes anterior
        try:
            conn = sqlite3.connect('ventas_dashboard.db')
            hoy = date.today()
            query_anterior = '''
                SELECT 
                    SUM(ventas_dia) as ventas_anterior,
                    AVG(articulos_ticket) as articulos_anterior
                FROM ventas_diarias
                WHERE strftime('%Y-%m', fecha) = ?
            '''
            mes_anterior = date(hoy.year, hoy.month, 1) - pd.Timedelta(days=1)
            df_anterior = pd.read_sql_query(query_anterior, conn, params=[mes_anterior.strftime('%Y-%m')])
            conn.close()
            
            ventas_anterior = float(df_anterior['ventas_anterior'].iloc[0]) if not df_anterior.empty and pd.notna(df_anterior['ventas_anterior'].iloc[0]) else 0
            articulos_anterior = float(df_anterior['articulos_anterior'].iloc[0]) if not df_anterior.empty and pd.notna(df_anterior['articulos_anterior'].iloc[0]) else 0
            
            if ventas_anterior > 0:
                crecimiento_ventas = calcular_crecimiento(acumulado, ventas_anterior)
                crecimiento_articulos = calcular_crecimiento(data['articulos_ticket'], articulos_anterior)
                
                color_crecimiento = "#00ff00" if crecimiento_ventas >= 0 else "#ff0000"
                st.markdown(f"<h2 style='color:{color_crecimiento};'>{crecimiento_ventas:+.1f}%</h2>", unsafe_allow_html=True)
                st.caption(f"{'🟢' if crecimiento_ventas >= 0 else '🔴'} en ventas")
                
                color_arts_crec = "#00ff00" if crecimiento_articulos >= 0 else "#ff0000"
                st.caption(f"📦 Artículos x ticket: <span style='color:{color_arts_crec};'>{crecimiento_articulos:+.1f}%</span>", unsafe_allow_html=True)
            else:
                st.markdown("<h2 style='color:#ffa500;'>N/A</h2>", unsafe_allow_html=True)
                st.caption("No hay datos del mes anterior")
        except Exception as e:
            st.markdown("<h2 style='color:#ffa500;'>N/A</h2>", unsafe_allow_html=True)
            st.caption("No hay datos del mes anterior")
    
    st.markdown("---")
    
    # Gráfico de evolución diaria
    st.subheader("📈 Evolución Diaria de Ventas")
    try:
        conn = sqlite3.connect('ventas_dashboard.db')
        df_diario = pd.read_sql_query('''
            SELECT fecha, ventas_dia, conversion, ticket_promedio, articulos_ticket
            FROM ventas_diarias
            WHERE strftime('%Y-%m', fecha) = ?
            ORDER BY fecha
        ''', conn, params=[date.today().strftime('%Y-%m')])
        conn.close()
        
        if not df_diario.empty:
            # Gráfico de ventas diarias
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=("Ventas Diarias", "Artículos por Ticket Diario"),
                vertical_spacing=0.12,
                row_heights=[0.6, 0.4]
            )
            
            # Gráfico de ventas
            fig.add_trace(
                go.Bar(x=df_diario['fecha'], y=df_diario['ventas_dia'], name="Ventas del día", marker_color='lightblue'),
                row=1, col=1
            )
            
            if data['objetivo_ventas'] > 0:
                meta_diaria = data['objetivo_ventas'] / 30
                fig.add_trace(
                    go.Scatter(x=df_diario['fecha'], y=[meta_diaria] * len(df_diario), 
                              name="Meta diaria", line=dict(color='red', dash='dash', width=2)),
                    row=1, col=1
                )
            
            # Gráfico de artículos por ticket
            fig.add_trace(
                go.Scatter(x=df_diario['fecha'], y=df_diario['articulos_ticket'], 
                          name="Artículos x Ticket", line=dict(color='green', width=2),
                          mode='lines+markers'),
                row=2, col=1
            )
            
            # Línea de meta de artículos
            if data['objetivo_articulos'] > 0:
                fig.add_trace(
                    go.Scatter(x=df_diario['fecha'], y=[data['objetivo_articulos']] * len(df_diario), 
                              name=f"Meta: {data['objetivo_articulos']} artículos", 
                              line=dict(color='orange', dash='dash', width=2)),
                    row=2, col=1
                )
            
            fig.update_layout(
                title="Evolución Diaria - Ventas y Artículos por Ticket",
                height=600,
                hovermode='x unified',
                showlegend=True,
                template='plotly_white'
            )
            
            fig.update_yaxes(title_text="Ventas ($)", tickformat='$,.0f', row=1, col=1)
            fig.update_yaxes(title_text="Artículos por Ticket", row=2, col=1)
            fig.update_xaxes(title_text="Fecha", row=2, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabla de datos diarios
            with st.expander("📋 Ver detalle de ventas diarias"):
                df_display = df_diario.copy()
                df_display['ventas_dia'] = df_display['ventas_dia'].apply(lambda x: f"${x:,.0f}")
                df_display['conversion'] = df_display['conversion'].apply(lambda x: f"{x:.1f}%")
                df_display['ticket_promedio'] = df_display['ticket_promedio'].apply(lambda x: f"${x:,.0f}")
                df_display['articulos_ticket'] = df_display['articulos_ticket'].apply(lambda x: f"{x:.1f}")
                
                # Agregar indicador de cumplimiento
                if data['objetivo_articulos'] > 0:
                    df_display['Cumple Meta Artículos'] = df_diario['articulos_ticket'].apply(
                        lambda x: '✅' if x >= data['objetivo_articulos'] else '❌'
                    )
                    df_display.columns = ['Fecha', 'Ventas', 'Conversión', 'Ticket Promedio', 'Artículos x Ticket', 'Meta Artículos']
                else:
                    df_display.columns = ['Fecha', 'Ventas', 'Conversión', 'Ticket Promedio', 'Artículos x Ticket']
                
                st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("📭 No hay datos para el mes actual. Por favor, carga un archivo Excel con los datos.")
    except Exception as e:
        st.error(f"Error al cargar el gráfico: {str(e)}")

if __name__ == "__main__":
    main()