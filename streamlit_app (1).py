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

# Business day starts at 5:00 AM (changed from 6:00 AM)
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
        '%d-%b-%Y %I:%M %p',  # 01-May-2025 06:59 AM
        '%m/%d/%Y %H:%M',      # 6/1/2025 7:07
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
    """
    Get business date (day starts at 5:00 AM).
    Orders before 5:00 AM belong to the previous business day.
    Example: May 2nd business day = May 2nd 5:00 AM to May 3rd 4:59 AM
    """
    if pd.isna(dt):
        return None
    if dt.hour < BUSINESS_DAY_START_HOUR:
        return (dt - timedelta(days=1)).date()
    return dt.date()

def get_business_hour(dt):
    """
    Get business hour (0-23) where 0 = 5:00 AM, 1 = 6:00 AM, ..., 23 = 4:00 AM
    This shifts the hours so the business day starts at 5 AM
    """
    if pd.isna(dt):
        return None
    return (dt.hour - BUSINESS_DAY_START_HOUR) % 24

def get_clock_hour_from_business_hour(business_hour):
    """Convert business hour back to clock hour"""
    return (business_hour + BUSINESS_DAY_START_HOUR) % 24

def format_hour_label(clock_hour):
    """Format clock hour as readable label (e.g., '5 AM', '10 PM')"""
    if clock_hour == 0:
        return "12 AM"
    elif clock_hour < 12:
        return f"{clock_hour} AM"
    elif clock_hour == 12:
        return "12 PM"
    else:
        return f"{clock_hour - 12} PM"

def preprocess_sales_orders(df):
    """Preprocess sales orders file (aggregated orders level)"""
    df.columns = df.columns.str.strip()
    
    # Parse Order Time
    if 'Order Time' in df.columns:
        df['Order Time'] = parse_datetime_flexible(df['Order Time'])
    
    # Extract business date (based on 5 AM start)
    df['Business_Date'] = df['Order Time'].apply(get_business_date)
    df['Order_Month'] = df['Order Time'].dt.to_period('M').astype(str)
    df['Order_Hour'] = df['Order Time'].dt.hour  # Clock hour for hourly distribution
    df['Business_Hour'] = df['Order Time'].apply(get_business_hour)  # For ordering
    df['Order_Day'] = df['Order Time'].dt.day_name()
    
    # Clean amount columns
    if 'Order Amount' in df.columns:
        df['Order Amount'] = pd.to_numeric(df['Order Amount'], errors='coerce').fillna(0)
    
    # Parse payments for payment method extraction
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
    
    # Parse Order Time
    if 'Order Time' in df.columns:
        df['Order Time'] = parse_datetime_flexible(df['Order Time'])
    
    # Extract business date (based on 5 AM start)
    df['Business_Date'] = df['Order Time'].apply(get_business_date)
    df['Order_Month'] = df['Order Time'].dt.to_period('M').astype(str)
    df['Order_Hour'] = df['Order Time'].dt.hour
    df['Business_Hour'] = df['Order Time'].apply(get_business_hour)
    df['Order_Day'] = df['Order Time'].dt.day_name()
    
    # Clean numeric columns
    if 'Quantity' in df.columns:
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0).astype(int)
    if 'Price' in df.columns:
        df['Price'] = pd.to_numeric(df['Price'], errors='coerce').fillna(0)
    
    # Calculate item revenue
    df['Item_Revenue'] = df['Quantity'] * df['Price']
    
    # Clean item names
    if 'Item name' in df.columns:
        df['Item name'] = df['Item name'].str.strip()
    
    return df

def preprocess_events(df):
    """Preprocess events/marketing CSV"""
    df.columns = df.columns.str.strip()
    
    # Parse dates
    df['Start_Date'] = pd.to_datetime(df['Start_Date'], errors='coerce')
    df['End_Date'] = pd.to_datetime(df['End_Date'], errors='coerce')
    
    # Fill missing end dates with start date (single-day events)
    df['End_Date'] = df['End_Date'].fillna(df['Start_Date'])
    
    # Normalize event type
    df['Event_Type'] = df['Event_Type'].str.lower().str.strip()
    
    return df

def get_month_label(period_str):
    """Convert period string (2025-05) to readable month label (May 2025)"""
    try:
        dt = pd.to_datetime(period_str)
        return dt.strftime('%b %Y')
    except:
        return period_str

# ==================== SIDEBAR ====================
st.sidebar.title("📊 Sales Analytics")
st.sidebar.markdown("---")

# File uploaders
st.sidebar.subheader("📁 Upload Data Files")

# Sales Orders upload
sales_orders_files = st.sidebar.file_uploader(
    "Sales Orders (Aggregated)",
    type=['csv'],
    accept_multiple_files=True,
    key="orders_upload",
    help="Upload one or more CSV files with Order No, Order Time, Order Amount, etc."
)

# Sales Items upload
sales_items_files = st.sidebar.file_uploader(
    "Sales Items (Item Level)",
    type=['csv'],
    accept_multiple_files=True,
    key="items_upload",
    help="Upload one or more CSV files with Item name, Quantity, Price, etc."
)

# Events upload
st.sidebar.markdown("---")
st.sidebar.subheader("📅 Events & Marketing")

events_file = st.sidebar.file_uploader(
    "Events CSV (Optional)",
    type=['csv'],
    key="events_upload",
    help="Upload events/marketing calendar"
)

# Events template download
events_template = """Event_Name,Start_Date,End_Date,Event_Type,Description
Eid Al-Adha,2025-06-06,2025-06-09,holiday,Eid celebration
Summer Promo,2025-05-15,2025-05-15,campaign,20% off beverages
New Menu Launch,2025-05-25,2025-05-27,offer,Buy 1 Get 1 Free
Ramadan Start,2025-03-01,2025-03-30,ramadan,Holy month"""

st.sidebar.download_button(
    "📥 Download Events Template",
    events_template,
    "events_template.csv",
    "text/csv",
    key="download_template"
)

# ==================== LOAD DATA ====================
df_orders = pd.DataFrame()
df_items = pd.DataFrame()
df_events = pd.DataFrame()

# Load Sales Orders
if sales_orders_files:
    orders_list = []
    for file in sales_orders_files:
        try:
            temp_df = pd.read_csv(file)
            temp_df = preprocess_sales_orders(temp_df)
            orders_list.append(temp_df)
        except Exception as e:
            st.sidebar.error(f"Error loading {file.name}: {e}")
    
    if orders_list:
        df_orders = pd.concat(orders_list, ignore_index=True)
        # Remove duplicates by Order No
        if 'Order No' in df_orders.columns:
            df_orders = df_orders.drop_duplicates(subset=['Order No'], keep='first')

# Load Sales Items
if sales_items_files:
    items_list = []
    for file in sales_items_files:
        try:
            temp_df = pd.read_csv(file)
            temp_df = preprocess_sales_items(temp_df)
            items_list.append(temp_df)
        except Exception as e:
            st.sidebar.error(f"Error loading {file.name}: {e}")
    
    if items_list:
        df_items = pd.concat(items_list, ignore_index=True)

# Load Events
if events_file:
    try:
        df_events = pd.read_csv(events_file)
        df_events = preprocess_events(df_events)
    except Exception as e:
        st.sidebar.error(f"Error loading events: {e}")

has_orders = len(df_orders) > 0
has_items = len(df_items) > 0
has_events = len(df_events) > 0

# ==================== MAIN CONTENT ====================
st.title("📊 Restaurant Sales Analytics Dashboard")
st.markdown(f"*Business day starts at {BUSINESS_DAY_START_HOUR}:00 AM*")

# Display data summary
if has_orders or has_items:
    col1, col2, col3 = st.columns(3)
    with col1:
        if has_orders:
            st.metric("📋 Orders Loaded", f"{len(df_orders):,}")
    with col2:
        if has_items:
            st.metric("🍽️ Item Records", f"{len(df_items):,}")
    with col3:
        if has_events:
            st.metric("📅 Events", f"{len(df_events):,}")

# Create tabs
tabs = st.tabs(["🏪 Sales Overview", "📈 Revenue Trends", "🍽️ Items Analysis"])

# ==================== TAB 1: SALES OVERVIEW ====================
with tabs[0]:
    if has_orders:
        st.subheader("📊 Sales Overview")
        
        # Date filter
        col1, col2 = st.columns(2)
        min_date = df_orders['Business_Date'].min()
        max_date = df_orders['Business_Date'].max()
        
        with col1:
            start_date = st.date_input("Start Date", min_date, key="overview_start")
        with col2:
            end_date = st.date_input("End Date", max_date, key="overview_end")
        
        # Filter data
        filtered_orders = df_orders[
            (df_orders['Business_Date'] >= start_date) & 
            (df_orders['Business_Date'] <= end_date)
        ]
        
        # KPIs
        total_revenue = filtered_orders['Order Amount'].sum() if 'Order Amount' in filtered_orders.columns else 0
        total_orders = filtered_orders['Order No'].nunique() if 'Order No' in filtered_orders.columns else len(filtered_orders)
        avg_order = total_revenue / total_orders if total_orders > 0 else 0
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1:
            st.metric("💰 Total Revenue", f"SAR {total_revenue:,.0f}")
        with kpi2:
            st.metric("📋 Total Orders", f"{total_orders:,}")
        with kpi3:
            st.metric("📊 Avg Order Value", f"SAR {avg_order:,.2f}")
        with kpi4:
            days_count = (end_date - start_date).days + 1
            st.metric("📅 Days", f"{days_count}")
        
        st.markdown("---")
        
        # Charts row
        col1, col2 = st.columns(2)
        
        with col1:
            if 'Order Type' in filtered_orders.columns:
                order_type_summary = filtered_orders.groupby('Order Type').agg(
                    Orders=('Order No', 'nunique'),
                    Revenue=('Order Amount', 'sum')
                ).reset_index().sort_values('Revenue', ascending=False)
                
                fig = px.bar(order_type_summary, x='Order Type', y='Revenue',
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
        
        # Time granularity selector
        time_view = st.radio(
            "View Revenue By:",
            ["Monthly", "Daily", "Hourly Distribution"],
            horizontal=True,
            key="revenue_time_view"
        )
        
        # Date filter for trends
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
            # Monthly revenue bar chart with proper month labels
            monthly_data = filtered_trend.groupby('Order_Month').agg(
                Revenue=('Order Amount', 'sum'),
                Orders=('Order No', 'nunique')
            ).reset_index()
            monthly_data = monthly_data.sort_values('Order_Month')
            
            # Convert period to readable month labels
            monthly_data['Month_Label'] = monthly_data['Order_Month'].apply(get_month_label)
            
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
            
            # Show table
            display_df = monthly_data[['Month_Label', 'Revenue', 'Orders']].copy()
            display_df.columns = ['Month', 'Revenue (SAR)', 'Orders']
            display_df['Revenue (SAR)'] = display_df['Revenue (SAR)'].apply(lambda x: f"SAR {x:,.0f}")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        elif time_view == "Daily":
            # Daily revenue line chart
            daily_data = filtered_trend.groupby('Business_Date').agg(
                Revenue=('Order Amount', 'sum'),
                Orders=('Order No', 'nunique')
            ).reset_index()
            daily_data = daily_data.sort_values('Business_Date')
            
            # Events toggle
            show_events = False
            if has_events:
                show_events = st.checkbox("📅 Show Events on Chart", value=True, key="show_events_daily")
            
            fig = go.Figure()
            
            # Revenue line
            fig.add_trace(go.Scatter(
                x=daily_data['Business_Date'],
                y=daily_data['Revenue'],
                mode='lines+markers',
                name='Revenue',
                line=dict(color='#1f77b4', width=2),
                hovertemplate='Date: %{x}<br>Revenue: SAR %{y:,.0f}<extra></extra>'
            ))
            
            # Add events if enabled
            if show_events and has_events:
                for _, event in df_events.iterrows():
                    event_type = event['Event_Type']
                    style = EVENT_STYLES.get(event_type, EVENT_STYLES['campaign'])
                    
                    # Shaded region for multi-day events
                    if event['Start_Date'] != event['End_Date']:
                        fig.add_vrect(
                            x0=event['Start_Date'],
                            x1=event['End_Date'],
                            fillcolor=style['fill'],
                            layer='below',
                            line_width=0
                        )
                    
                    # Marker for start date
                    fig.add_vline(
                        x=event['Start_Date'],
                        line_dash='dash',
                        line_color=style['color'],
                        annotation_text=f"{style['icon']} {event['Event_Name']}",
                        annotation_position='top'
                    )
            
            fig.update_layout(
                title='Daily Revenue',
                xaxis_title='Date',
                yaxis_title='Revenue (SAR)',
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Events legend
            if show_events and has_events:
                st.markdown("**Events Legend:**")
                legend_cols = st.columns(4)
                for i, (etype, style) in enumerate(EVENT_STYLES.items()):
                    count = len(df_events[df_events['Event_Type'] == etype])
                    if count > 0:
                        legend_cols[i % 4].markdown(f"{style['icon']} {etype.title()}: {count}")
        
        elif time_view == "Hourly Distribution":
            # Hourly distribution by month - STARTING FROM 5 AM
            st.markdown("*Hours are displayed starting from 5:00 AM (business day start)*")
            
            # Create hourly data with business hour ordering
            hourly_data = filtered_trend.groupby(['Order_Month', 'Order_Hour']).agg(
                Revenue=('Order Amount', 'sum')
            ).reset_index()
            
            # Get all months and create pivot table
            months = sorted(hourly_data['Order_Month'].unique())
            
            # Create business hour order (starting from 5 AM)
            # Business hour order: 5, 6, 7, ..., 23, 0, 1, 2, 3, 4
            business_hour_order = list(range(BUSINESS_DAY_START_HOUR, 24)) + list(range(0, BUSINESS_DAY_START_HOUR))
            
            # Create labels for x-axis
            hour_labels = [format_hour_label(h) for h in business_hour_order]
            
            # Pivot data to get months as columns
            pivot_data = hourly_data.pivot(index='Order_Hour', columns='Order_Month', values='Revenue').fillna(0)
            
            # Reorder rows according to business hour order
            pivot_data = pivot_data.reindex(business_hour_order)
            
            # Calculate total revenue per month to determine stacking order (largest at bottom)
            month_totals = pivot_data.sum().sort_values(ascending=False)
            ordered_months = month_totals.index.tolist()
            
            # Create stacked bar chart with largest values at bottom
            fig = go.Figure()
            
            # Add bars in order (largest total first = bottom of stack)
            colors = px.colors.qualitative.Pastel
            for i, month in enumerate(ordered_months):
                month_label = get_month_label(month)
                fig.add_trace(go.Bar(
                    name=month_label,
                    x=hour_labels,
                    y=pivot_data[month].values,
                    marker_color=colors[i % len(colors)],
                    hovertemplate=f'{month_label}<br>Hour: %{{x}}<br>Revenue: SAR %{{y:,.0f}}<extra></extra>'
                ))
            
            fig.update_layout(
                barmode='stack',
                title='Hourly Revenue Distribution by Month',
                xaxis_title='Hour of Day (Starting 5 AM)',
                yaxis_title='Revenue (SAR)',
                legend_title='Month',
                xaxis={'tickangle': -45}
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Summary table
            summary_df = pivot_data.copy()
            summary_df.index = hour_labels
            summary_df.columns = [get_month_label(m) for m in summary_df.columns]
            summary_df['Total'] = summary_df.sum(axis=1)
            
            with st.expander("📊 Hourly Revenue Data Table"):
                st.dataframe(summary_df.style.format("{:,.0f}"), use_container_width=True)
    
    else:
        st.info("📋 Upload Sales Orders files to see revenue trends.")

# ==================== TAB 3: ITEMS ANALYSIS ====================
with tabs[2]:
    if has_items:
        st.subheader("🍽️ Items Analysis")
        
        # Date filter
        col1, col2 = st.columns(2)
        min_date = df_items['Business_Date'].min()
        max_date = df_items['Business_Date'].max()
        
        with col1:
            items_start = st.date_input("Start Date", min_date, key="items_start")
        with col2:
            items_end = st.date_input("End Date", max_date, key="items_end")
        
        filtered_items = df_items[
            (df_items['Business_Date'] >= items_start) & 
            (df_items['Business_Date'] <= items_end)
        ]
        
        # Top/Bottom items
        st.markdown("### 📊 Item Performance")
        
        item_summary = filtered_items.groupby('Item name').agg(
            Quantity=('Quantity', 'sum'),
            Revenue=('Item_Revenue', 'sum'),
            Orders=('Order No', 'nunique')
        ).reset_index().sort_values('Quantity', ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🔝 Top 15 Items (by Quantity)**")
            top_items = item_summary.head(15)
            fig = px.bar(top_items, x='Quantity', y='Item name',
                        orientation='h',
                        title='Most Popular Items',
                        color='Quantity',
                        color_continuous_scale='Greens')
            fig.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("**📉 Bottom 15 Items (by Quantity)**")
            bottom_items = item_summary[item_summary['Quantity'] > 0].tail(15)
            fig = px.bar(bottom_items, x='Quantity', y='Item name',
                        orientation='h',
                        title='Least Popular Items',
                        color='Quantity',
                        color_continuous_scale='Reds_r')
            fig.update_layout(yaxis={'categoryorder': 'total descending'}, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        # Item consumption trends
        st.markdown("---")
        st.markdown("### 📈 Item Consumption Trends")
        
        # Multi-select for items
        all_items = sorted(filtered_items['Item name'].unique())
        
        # Get top 5 items as default selection
        default_items = item_summary.head(5)['Item name'].tolist()
        
        selected_items = st.multiselect(
            "Select items to track:",
            options=all_items,
            default=default_items[:3] if len(default_items) >= 3 else default_items,
            key="item_trend_select"
        )
        
        if selected_items:
            # Monthly consumption for selected items
            item_trend = filtered_items[filtered_items['Item name'].isin(selected_items)].groupby(
                ['Order_Month', 'Item name']
            ).agg(
                Quantity=('Quantity', 'sum')
            ).reset_index()
            
            # Convert month to label
            item_trend['Month_Label'] = item_trend['Order_Month'].apply(get_month_label)
            
            fig = px.line(item_trend, x='Month_Label', y='Quantity',
                         color='Item name',
                         markers=True,
                         title='Item Consumption Over Time')
            fig.update_layout(
                xaxis_title='Month',
                yaxis_title='Quantity Sold',
                legend_title='Item'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Full item table
        with st.expander("📋 Full Item Performance Table"):
            display_summary = item_summary.copy()
            display_summary['Revenue'] = display_summary['Revenue'].apply(lambda x: f"SAR {x:,.2f}")
            st.dataframe(display_summary, use_container_width=True, hide_index=True)
    
    else:
        st.info("📋 Upload Sales Items files to see items analysis.")

# Footer
st.markdown("---")
st.markdown(
    f"<div style='text-align: center; color: gray;'>"
    f"Restaurant Sales Analytics Dashboard | Business Day: {BUSINESS_DAY_START_HOUR}:00 AM - {BUSINESS_DAY_START_HOUR-1 if BUSINESS_DAY_START_HOUR > 0 else 23}:59 AM"
    f"</div>",
    unsafe_allow_html=True
)
