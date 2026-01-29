import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(
    page_title="Restaurant Sales Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stMetric > div { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    .main-header { font-size: 2.5rem; font-weight: bold; color: #1f77b4; margin-bottom: 0; }
    .sub-header { font-size: 1.1rem; color: #666; margin-top: 0; }
</style>
""", unsafe_allow_html=True)

# Business day starts at 5:00 AM
BUSINESS_DAY_START_HOUR = 5

# Event colors and icons mapping
EVENT_STYLES = {
    'holiday': {'color': '#ff6b6b', 'fill': 'rgba(255, 107, 107, 0.2)', 'icon': '🎉'},
    'ramadan': {'color': '#4ecdc4', 'fill': 'rgba(78, 205, 196, 0.2)', 'icon': '🌙'},
    'campaign': {'color': '#ffe66d', 'fill': 'rgba(255, 230, 109, 0.2)', 'icon': '📢'},
    'offer': {'color': '#a855f7', 'fill': 'rgba(168, 85, 247, 0.2)', 'icon': '🏷️'}
}

def parse_datetime_flexible(series):
    """Parse datetime with multiple format support"""
    formats_to_try = [
        '%d-%b-%Y %I:%M %p',
        '%m/%d/%Y %H:%M',
        '%Y-%m-%d %H:%M:%S',
        '%d/%m/%Y %H:%M',
        '%Y-%m-%d %H:%M',
        '%m/%d/%Y %H:%M:%S',
    ]
    
    for fmt in formats_to_try:
        try:
            return pd.to_datetime(series, format=fmt)
        except:
            continue
    
    return pd.to_datetime(series, format='mixed', dayfirst=False)

def get_business_date(dt):
    """Get business date (day starts at 5 AM)"""
    if dt.hour < BUSINESS_DAY_START_HOUR:
        return (dt - timedelta(days=1)).date()
    return dt.date()

def preprocess_sales_orders(df):
    """Preprocess sales orders file (aggregated orders level)"""
    df.columns = df.columns.str.strip()
    
    if 'Order Time' in df.columns:
        df['Order Time'] = parse_datetime_flexible(df['Order Time'])
    
    df['Business_Date'] = df['Order Time'].apply(get_business_date)
    df['Order_Month'] = df['Order Time'].dt.to_period('M').astype(str)
    df['Order_Hour'] = df['Order Time'].dt.hour
    df['Order_Day'] = df['Order Time'].dt.day_name()
    
    if 'Order Amount' in df.columns:
        df['Order Amount'] = pd.to_numeric(df['Order Amount'], errors='coerce').fillna(0)
    
    if 'Payments' in df.columns:
        def extract_payment_total(payment_str):
            if pd.isna(payment_str) or payment_str == '':
                return 0
            try:
                total = 0
                parts = str(payment_str).split(',')
                for part in parts:
                    if '-' in part:
                        amount_part = part.split('-')[-1].strip()
                        total += float(amount_part)
                return total
            except:
                return 0
        
        df['Payment_Total'] = df['Payments'].apply(extract_payment_total)
    
    return df

def preprocess_sales_items(df):
    """Preprocess sales items file (item level details)"""
    df.columns = df.columns.str.strip()
    
    if 'Order Time' in df.columns:
        df['Order Time'] = parse_datetime_flexible(df['Order Time'])
    
    df['Business_Date'] = df['Order Time'].apply(get_business_date)
    df['Order_Month'] = df['Order Time'].dt.to_period('M').astype(str)
    df['Order_Hour'] = df['Order Time'].dt.hour
    df['Order_Day'] = df['Order Time'].dt.day_name()
    
    if 'Quantity' in df.columns:
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0).astype(int)
    if 'Price' in df.columns:
        df['Price'] = pd.to_numeric(df['Price'], errors='coerce').fillna(0)
    
    df['Item_Revenue'] = df['Quantity'] * df['Price']
    
    if 'Item name' in df.columns:
        df['Item name'] = df['Item name'].str.strip()
    
    return df

def preprocess_events(df):
    """Preprocess events/marketing data"""
    df.columns = df.columns.str.strip()
    
    df['Start_Date'] = pd.to_datetime(df['Start_Date'], format='mixed', dayfirst=False).dt.date
    df['End_Date'] = pd.to_datetime(df['End_Date'], format='mixed', dayfirst=False).dt.date
    
    df['Event_Name'] = df['Event_Name'].str.strip()
    df['Event_Type'] = df['Event_Type'].str.strip().str.lower()
    if 'Description' in df.columns:
        df['Description'] = df['Description'].fillna('').str.strip()
    else:
        df['Description'] = ''
    
    return df

def create_revenue_chart_with_events(daily_data, df_events, date_col='Business_Date', value_col='Revenue'):
    """Create revenue line chart with event markers and shaded regions"""
    
    fig = go.Figure()
    
    y_min = daily_data[value_col].min()
    y_max = daily_data[value_col].max()
    y_range = y_max - y_min if y_max != y_min else 1
    marker_y = y_min - y_range * 0.12
    
    # Add shaded regions for multi-day events
    if len(df_events) > 0:
        for _, event in df_events.iterrows():
            if event['Start_Date'] != event['End_Date']:
                event_type = event['Event_Type']
                style = EVENT_STYLES.get(event_type, EVENT_STYLES['campaign'])
                
                fig.add_vrect(
                    x0=event['Start_Date'],
                    x1=event['End_Date'],
                    fillcolor=style['fill'],
                    line=dict(color=style['color'], width=1, dash='dash'),
                    layer='below',
                    annotation_text=None
                )
    
    # Add main revenue line
    fig.add_trace(go.Scatter(
        x=daily_data[date_col],
        y=daily_data[value_col],
        mode='lines+markers',
        name='Revenue',
        line=dict(color='#00d4ff', width=2.5),
        marker=dict(size=5, color='#00d4ff'),
        hovertemplate='<b>%{x|%b %d, %Y}</b><br>Revenue: SAR %{y:,.0f}<extra></extra>'
    ))
    
    # Add event markers below x-axis
    if len(df_events) > 0:
        for _, event in df_events.iterrows():
            event_type = event['Event_Type']
            style = EVENT_STYLES.get(event_type, EVENT_STYLES['campaign'])
            
            period_text = str(event['Start_Date'])
            if event['Start_Date'] != event['End_Date']:
                period_text = f"{event['Start_Date']} → {event['End_Date']}"
            
            hover_text = (
                f"<b>{style['icon']} {event['Event_Name']}</b><br>"
                f"<b>Period:</b> {period_text}<br>"
                f"<b>Type:</b> {event_type.title()}<br>"
                f"<b>Details:</b> {event.get('Description', 'N/A')}"
            )
            
            # Event marker
            fig.add_trace(go.Scatter(
                x=[event['Start_Date']],
                y=[marker_y],
                mode='markers+text',
                marker=dict(
                    size=24,
                    color=style['color'],
                    line=dict(color='white', width=2),
                    symbol='circle'
                ),
                text=[style['icon']],
                textposition='middle center',
                textfont=dict(size=12),
                hovertemplate=hover_text + '<extra></extra>',
                showlegend=False,
                name=event['Event_Name']
            ))
            
            # Vertical dashed line from marker to x-axis
            fig.add_shape(
                type='line',
                x0=event['Start_Date'],
                x1=event['Start_Date'],
                y0=marker_y + y_range * 0.04,
                y1=y_min,
                line=dict(color=style['color'], width=1.5, dash='dot'),
                layer='below'
            )
    
    # Update layout
    fig.update_layout(
        title='Daily Revenue Trend with Events',
        xaxis_title='Date',
        yaxis_title='Revenue (SAR)',
        hovermode='closest',
        showlegend=False,
        yaxis=dict(
            range=[marker_y - y_range * 0.08, y_max + y_range * 0.05] if len(df_events) > 0 else None
        ),
        margin=dict(b=100),
        height=500
    )
    
    # Add "Events" label on y-axis at marker level
    if len(df_events) > 0:
        fig.add_annotation(
            x=daily_data[date_col].min(),
            y=marker_y,
            text="Events →",
            showarrow=False,
            xanchor='right',
            xshift=-10,
            font=dict(size=10, color='gray')
        )
    
    return fig


# ===========================================
# SIDEBAR - File Uploads
# ===========================================

st.sidebar.markdown("## 📂 Data Upload")

# Sales Orders Upload
st.sidebar.markdown("### 📋 Sales Orders Files")
sales_orders_files = st.sidebar.file_uploader(
    "Upload Sales Orders CSV files",
    type=['csv'],
    accept_multiple_files=True,
    key="sales_orders",
    help="Upload one or more sales orders files (aggregated order data)"
)

# Sales Items Upload
st.sidebar.markdown("### 🍽️ Sales Items Files")
sales_items_files = st.sidebar.file_uploader(
    "Upload Sales Items CSV files",
    type=['csv'],
    accept_multiple_files=True,
    key="sales_items",
    help="Upload one or more sales items files (item-level data)"
)

# Events Upload
st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 Events & Marketing")
events_file = st.sidebar.file_uploader(
    "Upload Events CSV",
    type=['csv'],
    key="events",
    help="Upload marketing events, holidays, campaigns (optional)"
)

# Download events template
events_template = """Event_Name,Start_Date,End_Date,Event_Type,Description
Eid Al-Adha,2025-06-06,2025-06-09,holiday,Eid celebration - Extended hours
Summer Campaign,2025-05-15,2025-05-15,campaign,20% off all beverages
Buy 1 Get 1 Offer,2025-05-25,2025-05-27,offer,BOGO on selected items
Ramadan,2025-03-01,2025-03-30,ramadan,Holy month of Ramadan
National Day,2025-09-23,2025-09-23,holiday,Saudi National Day"""

st.sidebar.download_button(
    label="📥 Download Events Template",
    data=events_template,
    file_name="events_template.csv",
    mime="text/csv",
    key="download_events_template"
)

st.sidebar.markdown("""
<small style='color: #808495;'>
Event Types: holiday, ramadan, campaign, offer
</small>
""", unsafe_allow_html=True)


# ===========================================
# MAIN CONTENT
# ===========================================

st.markdown('<p class="main-header">🍽️ Restaurant Sales Analytics</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Multi-period sales analysis with item-level insights</p>', unsafe_allow_html=True)
st.markdown("---")

# Initialize dataframes
df_orders = pd.DataFrame()
df_items = pd.DataFrame()
df_events = pd.DataFrame()

# Process Sales Orders
if sales_orders_files:
    orders_list = []
    for file in sales_orders_files:
        try:
            temp_df = pd.read_csv(file)
            temp_df['Source_File'] = file.name
            orders_list.append(temp_df)
            st.sidebar.success(f"✅ {file.name}")
        except Exception as e:
            st.sidebar.error(f"❌ {file.name}: {str(e)}")
    
    if orders_list:
        df_orders = pd.concat(orders_list, ignore_index=True)
        df_orders = preprocess_sales_orders(df_orders)

# Process Sales Items
if sales_items_files:
    items_list = []
    for file in sales_items_files:
        try:
            temp_df = pd.read_csv(file)
            temp_df['Source_File'] = file.name
            items_list.append(temp_df)
            st.sidebar.success(f"✅ {file.name}")
        except Exception as e:
            st.sidebar.error(f"❌ {file.name}: {str(e)}")
    
    if items_list:
        df_items = pd.concat(items_list, ignore_index=True)
        df_items = preprocess_sales_items(df_items)

# Process Events
if events_file:
    try:
        df_events = pd.read_csv(events_file)
        df_events = preprocess_events(df_events)
        st.sidebar.success(f"✅ Events: {len(df_events)} loaded")
    except Exception as e:
        st.sidebar.error(f"❌ Events error: {str(e)}")

# Check if we have data
has_orders = len(df_orders) > 0
has_items = len(df_items) > 0
has_events = len(df_events) > 0

if not has_orders and not has_items:
    st.info("👆 Please upload your sales data files using the sidebar to begin analysis.")
    st.markdown("""
    ### 📁 Expected File Formats:
    
    **Sales Orders Files** (aggregated order data):
    - Columns: Order No, Order Time, Order Type, Order Taken By, Order Amount, Payments, Status, etc.
    
    **Sales Items Files** (item-level data):
    - Columns: Order No, Order Time, Item name, Quantity, Price, Item Type, etc.
    
    **Events File** (optional):
    - Columns: Event_Name, Start_Date, End_Date, Event_Type, Description
    """)
    st.stop()

# Create tabs
tabs = st.tabs(["📊 Sales Overview", "📈 Revenue Trends", "🍽️ Items Analysis"])

# ==================== TAB 1: SALES OVERVIEW ====================
with tabs[0]:
    if has_orders:
        st.subheader("📊 Sales Overview")
        
        col1, col2 = st.columns(2)
        min_date = df_orders['Business_Date'].min()
        max_date = df_orders['Business_Date'].max()
        
        with col1:
            start_date = st.date_input("Start Date", min_date, key="orders_start")
        with col2:
            end_date = st.date_input("End Date", max_date, key="orders_end")
        
        filtered_orders = df_orders[
            (df_orders['Business_Date'] >= start_date) & 
            (df_orders['Business_Date'] <= end_date)
        ]
        
        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        
        total_orders = filtered_orders['Order No'].nunique()
        total_revenue = filtered_orders['Order Amount'].sum() if 'Order Amount' in filtered_orders.columns else 0
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        total_days = (end_date - start_date).days + 1
        
        col1.metric("Total Orders", f"{total_orders:,}")
        col2.metric("Total Revenue", f"SAR {total_revenue:,.0f}")
        col3.metric("Avg Order Value", f"SAR {avg_order_value:,.2f}")
        col4.metric("Period Days", f"{total_days}")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if 'Order Type' in filtered_orders.columns:
                type_summary = filtered_orders.groupby('Order Type').agg(
                    Orders=('Order No', 'nunique'),
                    Revenue=('Order Amount', 'sum')
                ).reset_index().sort_values('Revenue', ascending=False)
                
                fig = px.bar(type_summary, x='Order Type', y='Revenue',
                            title='Revenue by Order Type',
                            color='Order Type')
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if 'Order Taken By' in filtered_orders.columns:
                staff_summary = filtered_orders.groupby('Order Taken By').agg(
                    Orders=('Order No', 'nunique'),
                    Revenue=('Order Amount', 'sum')
                ).reset_index().sort_values('Revenue', ascending=False).head(10)
                
                fig = px.bar(staff_summary, x='Order Taken By', y='Revenue',
                            title='Top 10 Staff by Revenue',
                            color='Revenue',
                            color_continuous_scale='Blues')
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📋 Upload Sales Orders files to see sales overview.")

# ==================== TAB 2: REVENUE TRENDS ====================
with tabs[1]:
    if has_orders:
        st.subheader("📈 Revenue Trends Analysis")
        
        time_view = st.radio(
            "View Revenue By:",
            ["Monthly", "Daily", "Hourly Distribution"],
            horizontal=True,
            key="revenue_time_view"
        )
        
        col1, col2 = st.columns(2)
        min_date = df_orders['Business_Date'].min()
        max_date = df_orders['Business_Date'].max()
        
        with col1:
            trend_start = st.date_input("Start Date", min_date, key="trend_start")
        with col2:
            trend_end = st.date_input("End Date", max_date, key="trend_end")
        
        filtered_trend = df_orders[
            (df_orders['Business_Date'] >= trend_start) & 
            (df_orders['Business_Date'] <= trend_end)
        ]
        
        if time_view == "Monthly":
            monthly_data = filtered_trend.groupby('Order_Month').agg(
                Revenue=('Order Amount', 'sum'),
                Orders=('Order No', 'nunique')
            ).reset_index()
            monthly_data = monthly_data.sort_values('Order_Month')
            
            # Convert period to readable month labels (e.g., "May 2025")
            monthly_data['Month_Label'] = monthly_data['Order_Month'].apply(
                lambda x: pd.to_datetime(x).strftime('%b %Y')
            )
            
            fig = px.bar(monthly_data, x='Month_Label', y='Revenue',
                        title='Monthly Revenue',
                        text='Revenue')
            fig.update_traces(texttemplate='SAR %{text:,.0f}', textposition='outside')
            fig.update_layout(
                xaxis_title='Month', 
                yaxis_title='Revenue (SAR)',
                xaxis={'categoryorder': 'array', 'categoryarray': monthly_data['Month_Label'].tolist()}
            )
            st.plotly_chart(fig, use_container_width=True)
            
            display_df = monthly_data[['Month_Label', 'Revenue', 'Orders']].copy()
            display_df.columns = ['Month', 'Revenue', 'Orders']
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        elif time_view == "Daily":
            daily_data = filtered_trend.groupby('Business_Date').agg(
                Revenue=('Order Amount', 'sum'),
                Orders=('Order No', 'nunique')
            ).reset_index()
            daily_data = daily_data.sort_values('Business_Date')
            
            # Filter events to selected date range
            filtered_events = pd.DataFrame()
            if has_events:
                filtered_events = df_events[
                    (df_events['Start_Date'] >= trend_start) & 
                    (df_events['Start_Date'] <= trend_end)
                ]
            
            # Show events toggle if events exist
            show_events = False
            if has_events and len(filtered_events) > 0:
                show_events = st.checkbox("📅 Show Events on Chart", value=True, key="show_events_daily")
            
            # Create chart
            if show_events and len(filtered_events) > 0:
                fig = create_revenue_chart_with_events(daily_data, filtered_events)
                st.plotly_chart(fig, use_container_width=True)
                
                # Events legend
                st.markdown("#### 📌 Events in Period")
                legend_cols = st.columns(4)
                for i, (etype, style) in enumerate(EVENT_STYLES.items()):
                    with legend_cols[i]:
                        count = len(filtered_events[filtered_events['Event_Type'] == etype])
                        st.markdown(f"{style['icon']} **{etype.title()}**: {count}")
                
                # Events table
                with st.expander("📋 View Events Details"):
                    st.dataframe(
                        filtered_events[['Event_Name', 'Start_Date', 'End_Date', 'Event_Type', 'Description']], 
                        use_container_width=True, 
                        hide_index=True
                    )
            else:
                fig = px.line(daily_data, x='Business_Date', y='Revenue',
                             title='Daily Revenue Trend', markers=True)
                fig.update_layout(xaxis_title='Date', yaxis_title='Revenue (SAR)')
                st.plotly_chart(fig, use_container_width=True)
            
            # Month filter for detailed view
            if len(filtered_trend['Order_Month'].unique()) > 1:
                selected_month = st.selectbox(
                    "Filter by Month (for detailed view):",
                    ['All'] + sorted(filtered_trend['Order_Month'].unique().tolist()),
                    key="month_filter"
                )
                if selected_month != 'All':
                    month_daily = daily_data[
                        pd.to_datetime(daily_data['Business_Date']).dt.to_period('M').astype(str) == selected_month
                    ]
                    
                    if show_events and len(filtered_events) > 0:
                        month_events = filtered_events[
                            pd.to_datetime(filtered_events['Start_Date']).dt.to_period('M').astype(str) == selected_month
                        ]
                        if len(month_events) > 0:
                            fig2 = create_revenue_chart_with_events(month_daily, month_events)
                            fig2.update_layout(title=f'Daily Revenue - {selected_month}')
                            st.plotly_chart(fig2, use_container_width=True)
                        else:
                            fig2 = px.bar(month_daily, x='Business_Date', y='Revenue',
                                         title=f'Daily Revenue - {selected_month}')
                            st.plotly_chart(fig2, use_container_width=True)
                    else:
                        fig2 = px.bar(month_daily, x='Business_Date', y='Revenue',
                                     title=f'Daily Revenue - {selected_month}')
                        st.plotly_chart(fig2, use_container_width=True)
        
        else:  # Hourly Distribution
            st.markdown("*Hours displayed starting from 5:00 AM (business day start)*")
            
            hourly_monthly = filtered_trend.groupby(['Order_Hour', 'Order_Month']).agg(
                Revenue=('Order Amount', 'sum')
            ).reset_index()
            
            # Create hour order starting from 5 AM: 5, 6, 7, ..., 23, 0, 1, 2, 3, 4
            business_hour_order = list(range(BUSINESS_DAY_START_HOUR, 24)) + list(range(0, BUSINESS_DAY_START_HOUR))
            
            # Create hour labels
            def format_hour_label(h):
                if h == 0: return "12 AM"
                elif h < 12: return f"{h} AM"
                elif h == 12: return "12 PM"
                else: return f"{h-12} PM"
            
            hour_labels = {h: format_hour_label(h) for h in range(24)}
            hourly_monthly['Hour_Label'] = hourly_monthly['Order_Hour'].map(hour_labels)
            
            # Convert month to readable label
            hourly_monthly['Month_Label'] = hourly_monthly['Order_Month'].apply(
                lambda x: pd.to_datetime(x).strftime('%b %Y')
            )
            
            # Create ordered category for x-axis
            hour_label_order = [format_hour_label(h) for h in business_hour_order]
            hourly_monthly['Hour_Label'] = pd.Categorical(
                hourly_monthly['Hour_Label'], 
                categories=hour_label_order, 
                ordered=True
            )
            hourly_monthly = hourly_monthly.sort_values('Hour_Label')
            
            # Use grouped bars (barmode='group') so each month starts from 0
            fig = px.bar(hourly_monthly, x='Hour_Label', y='Revenue',
                        color='Month_Label',
                        title='Hourly Revenue Distribution by Month',
                        barmode='group',
                        labels={'Hour_Label': 'Hour of Day', 'Revenue': 'Revenue (SAR)', 'Month_Label': 'Month'})
            
            fig.update_layout(
                xaxis=dict(title='Hour of Day (Starting 5 AM)', tickangle=-45),
                xaxis_categoryorder='array',
                xaxis_categoryarray=hour_label_order
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Orders distribution
            hourly_orders = filtered_trend.groupby(['Order_Hour', 'Order_Month']).agg(
                Orders=('Order No', 'nunique')
            ).reset_index()
            
            hourly_orders['Hour_Label'] = hourly_orders['Order_Hour'].map(hour_labels)
            hourly_orders['Month_Label'] = hourly_orders['Order_Month'].apply(
                lambda x: pd.to_datetime(x).strftime('%b %Y')
            )
            hourly_orders['Hour_Label'] = pd.Categorical(
                hourly_orders['Hour_Label'], 
                categories=hour_label_order, 
                ordered=True
            )
            hourly_orders = hourly_orders.sort_values('Hour_Label')
            
            fig2 = px.bar(hourly_orders, x='Hour_Label', y='Orders',
                         color='Month_Label',
                         title='Hourly Orders Distribution by Month',
                         barmode='group')
            fig2.update_layout(
                xaxis=dict(title='Hour of Day (Starting 5 AM)', tickangle=-45),
                xaxis_categoryorder='array',
                xaxis_categoryarray=hour_label_order
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            hourly_summary = filtered_trend.groupby('Order_Hour').agg(
                Total_Revenue=('Order Amount', 'sum'),
                Total_Orders=('Order No', 'nunique'),
                Avg_Order_Value=('Order Amount', 'mean')
            ).reset_index()
            hourly_summary['Hour_Label'] = hourly_summary['Order_Hour'].map(hour_labels)
            hourly_summary['Hour_Label'] = pd.Categorical(
                hourly_summary['Hour_Label'], 
                categories=hour_label_order, 
                ordered=True
            )
            hourly_summary = hourly_summary.sort_values('Hour_Label')
            
            st.markdown("### Hourly Summary")
            display_summary = hourly_summary[['Hour_Label', 'Total_Revenue', 'Total_Orders', 'Avg_Order_Value']].copy()
            display_summary.columns = ['Hour', 'Total Revenue', 'Total Orders', 'Avg Order Value']
            st.dataframe(display_summary, use_container_width=True, hide_index=True)
    else:
        st.info("📋 Upload Sales Orders files to see revenue trends.")

# ==================== TAB 3: ITEMS ANALYSIS ====================
with tabs[2]:
    if has_items:
        st.subheader("🍽️ Items Analysis")
        
        if 'Item Type' in df_items.columns:
            main_items = df_items[df_items['Item Type'] == 'Regular Item'].copy()
        else:
            main_items = df_items.copy()
        
        col1, col2 = st.columns(2)
        min_date_items = main_items['Business_Date'].min()
        max_date_items = main_items['Business_Date'].max()
        
        with col1:
            items_start = st.date_input("Start Date", min_date_items, key="items_start")
        with col2:
            items_end = st.date_input("End Date", max_date_items, key="items_end")
        
        filtered_items = main_items[
            (main_items['Business_Date'] >= items_start) & 
            (main_items['Business_Date'] <= items_end)
        ]
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        items_summary = filtered_items.groupby('Item name').agg(
            Total_Quantity=('Quantity', 'sum'),
            Total_Revenue=('Item_Revenue', 'sum'),
            Order_Count=('Order No', 'nunique')
        ).reset_index()
        
        with col1:
            st.markdown("### 🔥 Most Popular Items")
            n_top = st.slider("Number of top items", 5, 30, 15, key="top_items")
            
            top_items = items_summary.nlargest(n_top, 'Total_Quantity')
            
            fig = px.bar(top_items, y='Item name', x='Total_Quantity',
                        orientation='h',
                        title=f'Top {n_top} Items by Quantity',
                        color='Total_Quantity',
                        color_continuous_scale='Greens')
            fig.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### ❄️ Least Popular Items")
            n_bottom = st.slider("Number of bottom items", 5, 30, 15, key="bottom_items")
            
            bottom_items = items_summary[items_summary['Total_Quantity'] > 0].nsmallest(n_bottom, 'Total_Quantity')
            
            fig = px.bar(bottom_items, y='Item name', x='Total_Quantity',
                        orientation='h',
                        title=f'Bottom {n_bottom} Items by Quantity',
                        color='Total_Quantity',
                        color_continuous_scale='Reds_r')
            fig.update_layout(yaxis={'categoryorder': 'total descending'}, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Item Consumption Trends
        st.markdown("### 📈 Item Consumption Trends")
        st.markdown("Select items to track their consumption pattern over time")
        
        all_items_list = sorted(items_summary['Item name'].unique().tolist())
        default_items = items_summary.nlargest(5, 'Total_Quantity')['Item name'].tolist()
        
        selected_items = st.multiselect(
            "Select Items to Track:",
            all_items_list,
            default=default_items[:3] if len(default_items) >= 3 else default_items,
            key="track_items"
        )
        
        if selected_items:
            track_granularity = st.radio(
                "View By:",
                ["Monthly", "Daily"],
                horizontal=True,
                key="track_granularity"
            )
            
            tracked_items = filtered_items[filtered_items['Item name'].isin(selected_items)]
            
            if track_granularity == "Monthly":
                monthly_items = tracked_items.groupby(['Order_Month', 'Item name']).agg(
                    Quantity=('Quantity', 'sum')
                ).reset_index()
                
                fig = px.line(monthly_items, x='Order_Month', y='Quantity',
                             color='Item name',
                             title='Monthly Item Consumption Trends',
                             markers=True)
                fig.update_layout(
                    xaxis_title='Month',
                    yaxis_title='Quantity Sold',
                    legend_title='Item'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                fig2 = px.bar(monthly_items, x='Order_Month', y='Quantity',
                             color='Item name',
                             title='Monthly Item Consumption (Stacked)',
                             barmode='stack')
                st.plotly_chart(fig2, use_container_width=True)
            
            else:
                daily_items = tracked_items.groupby(['Business_Date', 'Item name']).agg(
                    Quantity=('Quantity', 'sum')
                ).reset_index()
                
                fig = px.line(daily_items, x='Business_Date', y='Quantity',
                             color='Item name',
                             title='Daily Item Consumption Trends',
                             markers=True)
                fig.update_layout(
                    xaxis_title='Date',
                    yaxis_title='Quantity Sold',
                    legend_title='Item'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("### Selected Items Summary")
            selected_summary = items_summary[items_summary['Item name'].isin(selected_items)].sort_values(
                'Total_Quantity', ascending=False
            )
            st.dataframe(selected_summary, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        st.markdown("### 📋 Complete Items Summary")
        st.dataframe(
            items_summary.sort_values('Total_Quantity', ascending=False),
            use_container_width=True,
            hide_index=True
        )
        
        csv = items_summary.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Items Summary (CSV)",
            csv,
            "items_summary.csv",
            "text/csv"
        )
    
    elif has_orders:
        st.info("🍽️ Upload Sales Items files for detailed item-level analysis.")
    else:
        st.info("📋 Upload data files to see analysis.")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Restaurant Sales Analytics Dashboard | Business Day: 5:00 AM - 4:59 AM"
    "</div>",
    unsafe_allow_html=True
)
