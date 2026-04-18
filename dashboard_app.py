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

# Inicializar base de datos
def init_database():
    try:
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
            ''', (date.today().month, date.today().year, 1277000000, 37.0, 78000))
            conn.commit()
        
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
        else:
            ventas_hoy = 0
            conversion_hoy = 0
            ticket_hoy = 0
        
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
            'ventas_acumuladas': float(df_mes['ventas_acumuladas'].iloc[0]) if not df_mes.empty and pd.notna(df_mes['ventas_acumuladas'].iloc[0]) else 0,
            'conversion': float(df_mes['conversion_promedio'].iloc[0]) if not df_mes.empty and pd.notna(df_mes['conversion_promedio'].iloc[0]) else 0,
            'ticket_promedio': float(df_mes['ticket_promedio'].iloc[0]) if not df_mes.empty and pd.notna(df_mes['ticket_promedio'].iloc[0]) else 0,
            'articulos_ticket': float(df_mes['articulos_ticket'].iloc[0]) if not df_mes.empty and pd.notna(df_mes['articulos_ticket'].iloc[0]) else 0,
            'dias_operados': int(df_mes['dias_operados'].iloc[0]) if not df_mes.empty and pd.notna(df_mes['dias_operados'].iloc[0]) else 0,
            'ventas_hoy': ventas_hoy,
            'conversion_hoy': conversion_hoy,
            'ticket_promedio_hoy': ticket_hoy,
            'objetivo_ventas': objetivo[0] if objetivo else 1277000000,
            'objetivo_conversion': objetivo[1] if objetivo else 37.0,
            'objetivo_ticket': objetivo[2] if objetivo else 78000
        }
    except Exception as e:
        st.error(f"Error obteniendo datos: {str(e)}")
        return None

# Calcular crecimiento porcentual
def calcular_crecimiento(valor_actual, valor_anterior):
    if valor_anterior == 0:
        return 0
    return ((valor_actual - valor_anterior) / valor_anterior) * 100

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
        - `articulos_ticket` (opcional)
        
        **Ejemplo:**
        | fecha | ventas | tickets | visitas |
        |-------|--------|---------|---------|
        | 2026-04-01 | 32990000 | 423 | 1143 |
        """)
        
        st.markdown("---")
        st.header("🎯 Configurar Objetivos")
        objetivo_ventas = st.number_input("💰 Objetivo Ventas", value=1277000000, step=1000000, format="%d")
        objetivo_conversion = st.number_input("📊 Objetivo Conversión (%)", value=37.0, step=1.0)
        objetivo_ticket = st.number_input("🎫 Objetivo Ticket Promedio ($)", value=78000, step=1000)
        
        if st.button("💾 Actualizar Objetivos", type="primary"):
            try:
                conn = sqlite3.connect('ventas_dashboard.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO objetivos (mes, año, objetivo_ventas, objetivo_conversion, objetivo_ticket_promedio)
                    VALUES (?, ?, ?, ?, ?)
                ''', (date.today().month, date.today().year, objetivo_ventas, objetivo_conversion, objetivo_ticket))
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
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("### 💰 Presupuesto Mensual")
        st.markdown(f"<h2 style='color:#FF6B6B;'>${data['objetivo_ventas']:,.0f}</h2>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 🎫 Ticket Promedio")
        valor_ticket = data['ticket_promedio']
        meta_ticket = data['objetivo_ticket']
        color_ticket = "#00ff00" if valor_ticket >= meta_ticket else "#ff0000"
        st.markdown(f"<h2 style='color:{color_ticket};'>${valor_ticket:,.0f}</h2>", unsafe_allow_html=True)
        crecimiento_ticket = calcular_crecimiento(valor_ticket, meta_ticket)
        st.caption(f"{'🟢' if crecimiento_ticket >= 0 else '🔴'} vs objetivo: {crecimiento_ticket:+.1f}%")
    
    with col3:
        st.markdown("### 📦 Artículos por ticket")
        st.markdown(f"<h2 style='color:#45B7D1;'>{data['articulos_ticket']:.1f}</h2>", unsafe_allow_html=True)
    
    with col4:
        st.markdown("### 🔄 Conversión")
        valor_conv = data['conversion']
        meta_conv = data['objetivo_conversion']
        color_conv = "#00ff00" if valor_conv >= meta_conv else "#ff0000"
        st.markdown(f"<h2 style='color:{color_conv};'>{valor_conv:.1f}%</h2>", unsafe_allow_html=True)
        crecimiento_conv = calcular_crecimiento(valor_conv, meta_conv)
        st.caption(f"{'🟢' if crecimiento_conv >= 0 else '🔴'} vs objetivo: {crecimiento_conv:+.1f}%")
    
    st.markdown("---")
    
    # Segunda fila de métricas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 💵 Última Venta")
        venta_hoy = data['ventas_hoy']
        promedio_diario = data['ventas_acumuladas'] / max(data['dias_operados'], 1)
        color_venta = "#00ff00" if venta_hoy > promedio_diario else "#ff0000"
        st.markdown(f"<h2 style='color:{color_venta};'>${venta_hoy:,.0f}</h2>", unsafe_allow_html=True)
        st.caption(f"Promedio diario: ${promedio_diario:,.0f}")
    
    with col2:
        st.markdown("### 📊 Acumulado mensual")
        acumulado = data['ventas_acumuladas']
        porcentaje_meta = (acumulado / data['objetivo_ventas'] * 100) if data['objetivo_ventas'] > 0 else 0
        color_acumulado = "#00ff00" if acumulado >= data['objetivo_ventas'] else "#ffa500"
        st.markdown(f"<h2 style='color:{color_acumulado};'>${acumulado:,.0f}</h2>", unsafe_allow_html=True)
        st.progress(min(porcentaje_meta/100, 1.0))
        st.caption(f"{porcentaje_meta:.1f}% de la meta mensual")
    
    with col3:
        st.markdown("### 📈 Crecimiento Mensual")
        # Calcular crecimiento vs mes anterior
        try:
            conn = sqlite3.connect('ventas_dashboard.db')
            hoy = date.today()
            query_anterior = '''
                SELECT SUM(ventas_dia) as ventas_anterior
                FROM ventas_diarias
                WHERE strftime('%Y-%m', fecha) = ?
            '''
            mes_anterior = date(hoy.year, hoy.month, 1) - pd.Timedelta(days=1)
            df_anterior = pd.read_sql_query(query_anterior, conn, params=[mes_anterior.strftime('%Y-%m')])
            conn.close()
            
            ventas_anterior = float(df_anterior['ventas_anterior'].iloc[0]) if not df_anterior.empty and pd.notna(df_anterior['ventas_anterior'].iloc[0]) else 0
            crecimiento = calcular_crecimiento(acumulado, ventas_anterior)
            color_crecimiento = "#00ff00" if crecimiento >= 0 else "#ff0000"
            st.markdown(f"<h2 style='color:{color_crecimiento};'>{crecimiento:+.1f}%</h2>", unsafe_allow_html=True)
            st.caption(f"{'🟢' if crecimiento >= 0 else '🔴'} vs mes anterior")
        except:
            st.markdown("<h2 style='color:#ffa500;'>N/A</h2>", unsafe_allow_html=True)
            st.caption("No hay datos del mes anterior")
    
    st.markdown("---")
    
    # Gráfico de evolución diaria
    st.subheader("📈 Evolución Diaria de Ventas")
    try:
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
            
            meta_diaria = data['objetivo_ventas'] / 30
            fig.add_trace(
                go.Scatter(x=df_diario['fecha'], y=[meta_diaria] * len(df_diario), 
                          name="Meta diaria", line=dict(color='red', dash='dash', width=2)),
                secondary_y=False,
            )
            
            fig.update_layout(
                title="Ventas Diarias del Mes Actual",
                xaxis_title="Fecha",
                yaxis_title="Ventas ($)",
                height=450,
                hovermode='x unified',
                showlegend=True,
                template='plotly_white'
            )
            
            fig.update_yaxis(tickformat='$,.0f')
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabla de datos diarios
            with st.expander("📋 Ver detalle de ventas diarias"):
                df_display = df_diario.copy()
                df_display['ventas_dia'] = df_display['ventas_dia'].apply(lambda x: f"${x:,.0f}")
                df_display['conversion'] = df_display['conversion'].apply(lambda x: f"{x:.1f}%")
                df_display['ticket_promedio'] = df_display['ticket_promedio'].apply(lambda x: f"${x:,.0f}")
                df_display.columns = ['Fecha', 'Ventas', 'Conversión', 'Ticket Promedio']
                st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("📭 No hay datos para el mes actual. Por favor, carga un archivo Excel con los datos.")
    except Exception as e:
        st.error(f"Error al cargar el gráfico: {str(e)}")

if __name__ == "__main__":
    main()