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

# CSS personalizado para mejorar la apariencia
st.markdown("""
<style>
    /* Estilo para las tarjetas de métricas */
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .metric-title {
        font-size: 14px;
        color: #666;
        margin-bottom: 10px;
    }
    .metric-value {
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .metric-target {
        font-size: 12px;
        color: #888;
    }
    .metric-percentage {
        font-size: 14px;
        font-weight: bold;
    }
    .green {
        color: #00ff00;
    }
    .red {
        color: #ff0000;
    }
    .orange {
        color: #ffa500;
    }
    /* Separador */
    hr {
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

# Título principal
st.title("📊 Panel de Control de Ventas")
st.caption("Indicadores Restrepo")
st.markdown("---")

# Función para migrar base de datos existente
def migrar_base_datos():
    try:
        conn = sqlite3.connect('ventas_dashboard.db')
        cursor = conn.cursor()
        
        # Verificar si la tabla objetivos existe y tiene la columna objetivo_articulos_ticket
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
            conversion_hoy = df_hoy['conversion'].iloc[0] if not df_hoy.empty else 0
            ticket_hoy = df_hoy['ticket_promedio'].iloc[0] if not df_hoy.empty else 0
            articulos_hoy = df_hoy['articulos_ticket'].iloc[0] if not df_hoy.empty else 0
        else:
            ventas_hoy = conversion_hoy = ticket_hoy = articulos_hoy = 0
        
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

# Calcular porcentaje de cumplimiento
def get_percentage_color(value, target):
    if target == 0:
        return "#ffa500", "0%"
    percentage = (value / target * 100)
    if percentage >= 100:
        return "#00ff00", f"{percentage:.1f}%"
    elif percentage >= 80:
        return "#ffa500", f"{percentage:.1f}%"
    else:
        return "#ff0000", f"{percentage:.1f}%"

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
    
    # Fila 1: Métricas principales
    st.subheader("📊 Indicadores Clave")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Tarjeta 1: Presupuesto Mensual
    with col1:
        st.markdown("""
        <div style='background-color:#f8f9fa; border-radius:10px; padding:20px; text-align:center;'>
            <div style='font-size:14px; color:#666;'>💰 PRESUPUESTO MENSUAL</div>
            <div style='font-size:32px; font-weight:bold; color:#FF6B6B;'>${:,.0f}</div>
        </div>
        """.format(data['objetivo_ventas']), unsafe_allow_html=True)
    
    # Tarjeta 2: Ticket Promedio
    with col2:
        color_ticket, pct_ticket = get_percentage_color(data['ticket_promedio'], data['objetivo_ticket'])
        st.markdown(f"""
        <div style='background-color:#f8f9fa; border-radius:10px; padding:20px; text-align:center;'>
            <div style='font-size:14px; color:#666;'>🎫 TICKET PROMEDIO</div>
            <div style='font-size:32px; font-weight:bold; color:{color_ticket};'>${data['ticket_promedio']:,.0f}</div>
            <div style='font-size:12px; color:#888;'>Meta: ${data['objetivo_ticket']:,.0f}</div>
            <div style='font-size:14px; font-weight:bold; color:{color_ticket};'>{pct_ticket}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Tarjeta 3: Artículos por Ticket
    with col3:
        color_art, pct_art = get_percentage_color(data['articulos_ticket'], data['objetivo_articulos'])
        st.markdown(f"""
        <div style='background-color:#f8f9fa; border-radius:10px; padding:20px; text-align:center;'>
            <div style='font-size:14px; color:#666;'>📦 ARTÍCULOS x TICKET</div>
            <div style='font-size:32px; font-weight:bold; color:{color_art};'>{data['articulos_ticket']:.1f}</div>
            <div style='font-size:12px; color:#888;'>Meta: {data['objetivo_articulos']:.1f}</div>
            <div style='font-size:14px; font-weight:bold; color:{color_art};'>{pct_art}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Tarjeta 4: Conversión
    with col4:
        color_conv, pct_conv = get_percentage_color(data['conversion'], data['objetivo_conversion'])
        st.markdown(f"""
        <div style='background-color:#f8f9fa; border-radius:10px; padding:20px; text-align:center;'>
            <div style='font-size:14px; color:#666;'>🔄 CONVERSIÓN</div>
            <div style='font-size:32px; font-weight:bold; color:{color_conv};'>{data['conversion']:.1f}%</div>
            <div style='font-size:12px; color:#888;'>Meta: {data['objetivo_conversion']:.1f}%</div>
            <div style='font-size:14px; font-weight:bold; color:{color_conv};'>{pct_conv}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Fila 2: Desempeño
    st.subheader("📈 Desempeño")
    
    col1, col2, col3 = st.columns(3)
    
    # Última Venta
    with col1:
        promedio_diario = data['ventas_acumuladas'] / max(data['dias_operados'], 1)
        color_venta = "#00ff00" if data['ventas_hoy'] > promedio_diario else "#ff0000"
        st.markdown(f"""
        <div style='background-color:#f8f9fa; border-radius:10px; padding:20px;'>
            <div style='font-size:14px; color:#666;'>💵 ÚLTIMA VENTA</div>
            <div style='font-size:28px; font-weight:bold; color:{color_venta};'>${data['ventas_hoy']:,.0f}</div>
            <div style='font-size:12px; color:#888;'>Promedio diario: ${promedio_diario:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Acumulado Mensual
    with col2:
        porcentaje_meta = (data['ventas_acumuladas'] / data['objetivo_ventas'] * 100) if data['objetivo_ventas'] > 0 else 0
        color_acum = "#00ff00" if data['ventas_acumuladas'] >= data['objetivo_ventas'] else "#ffa500"
        st.markdown(f"""
        <div style='background-color:#f8f9fa; border-radius:10px; padding:20px;'>
            <div style='font-size:14px; color:#666;'>📊 ACUMULADO MENSUAL</div>
            <div style='font-size:28px; font-weight:bold; color:{color_acum};'>${data['ventas_acumuladas']:,.0f}</div>
            <div style='font-size:12px; color:#888;'>{porcentaje_meta:.1f}% de la meta</div>
            <div style='margin-top:10px; background-color:#e0e0e0; border-radius:5px; height:8px;'>
                <div style='background-color:{color_acum}; width:{min(porcentaje_meta, 100)}%; height:8px; border-radius:5px;'></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Crecimiento
    with col3:
        try:
            conn = sqlite3.connect('ventas_dashboard.db')
            hoy = date.today()
            mes_anterior = date(hoy.year, hoy.month, 1) - pd.Timedelta(days=1)
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
                <div style='background-color:#f8f9fa; border-radius:10px; padding:20px; text-align:center;'>
                    <div style='font-size:14px; color:#666;'>📈 CRECIMIENTO vs MES ANTERIOR</div>
                    <div style='font-size:32px; font-weight:bold; color:{color_crec};'>{crecimiento:+.1f}%</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style='background-color:#f8f9fa; border-radius:10px; padding:20px; text-align:center;'>
                    <div style='font-size:14px; color:#666;'>📈 CRECIMIENTO vs MES ANTERIOR</div>
                    <div style='font-size:32px; font-weight:bold; color:#ffa500;'>N/A</div>
                </div>
                """, unsafe_allow_html=True)
        except:
            st.markdown("""
            <div style='background-color:#f8f9fa; border-radius:10px; padding:20px; text-align:center;'>
                <div style='font-size:14px; color:#666;'>📈 CRECIMIENTO vs MES ANTERIOR</div>
                <div style='font-size:32px; font-weight:bold; color:#ffa500;'>N/A</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Gráfico
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
            
            # Ventas
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
            
            # Artículos
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
            
            # Tabla resumen
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