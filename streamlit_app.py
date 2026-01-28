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

# Business day starts at 6:00 AM
BUSINESS_DAY_START_HOUR = 6

def parse_datetime_flexible(series):
    """Parse datetime with multiple format support"""
    formats_to_try = [
        '%d-%b-%Y %I:%M %p',  # 01-May-2025 06:59 AM
        '%m/%d/%Y %H:%M',      # 7/1/2025 5:32
        '%Y-%m-%d %H:%M:%S',   # 2025-05-01 06:59:00
        '%d/%m/%Y %H:%M',      # 01/05/2025 06:59
        '%Y-%m-%d %H:%M',      # 2025-05-01 06:59
    ]
    
    for fmt in formats_to_try:
        try:
            return pd.to_datetime(series, format=fmt)
        except:
            continue
    
    # Fallback to pandas inference
    return pd.to_datetime(series, format='mixed', dayfirst=False)

def get_business_date(dt):
    """Get business date (day starts at 6 AM)"""
    if dt.hour < BUSINESS_DAY_START_HOUR:
        return (dt - timedelta(days=1)).date()
    return dt.date()

def preprocess_sales_orders(df):
    """Preprocess sales orders file (aggregated orders level)"""
    df.columns = df.columns.str.strip()
    
    # Parse Order Time
    if 'Order Time' in df.columns:
        df['Order Time'] = parse_datetime_flexible(df['Order Time'])
    
    # Extract business date
    df['Business_Date'] = df['Order Time'].apply(get_business_date)
    df['Order_Month'] = df['Order Time'].dt.to_period('M').astype(str)
    df['Order_Hour'] = df['Order Time'].dt.hour
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
    
    # Extract time components
    df['Business_Date'] = df['Order Time'].apply(get_business_date)
    df['Order_Month'] = df['Order Time'].dt.to_period('M').astype(str)
    df['Order_Hour'] = df['Order Time'].dt.hour
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

# Sidebar for file uploads
st.sidebar.markdown("## 📂 Data Upload")

# Sales Orders Upload (multiple files)
st.sidebar.markdown("### 📋 Sales Orders Files")
sales_orders_files = st.sidebar.file_uploader(
    "Upload Sales Orders CSV files",
    type=['csv'],
    accept_multiple_files=True,
    key="sales_orders",
    help="Upload one or more sales orders files (aggregated order data)"
)

# Sales Items Upload (multiple files)
st.sidebar.markdown("### 🍽️ Sales Items Files")
sales_items_files = st.sidebar.file_uploader(
    "Upload Sales Items CSV files",
    type=['csv'],
    accept_multiple_files=True,
    key="sales_items",
    help="Upload one or more sales items files (item-level data)"
)

# Main content
st.markdown('<p class="main-header">🍽️ Restaurant Sales Analytics</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Multi-period sales analysis with item-level insights</p>', unsafe_allow_html=True)
st.markdown("---")

# Initialize dataframes
df_orders = pd.DataFrame()
df_items = pd.DataFrame()

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

# Check if we have data
has_orders = len(df_orders) > 0
has_items = len(df_items) > 0

if not has_orders and not has_items:
    st.info("👆 Please upload your sales data files using the sidebar to begin analysis.")
    st.markdown("""
    ### 📁 Expected File Formats:
    
    **Sales Orders Files** (aggregated order data):
    - Columns: Order No, Order Time, Order Type, Order Taken By, Order Amount, Payments, Status, etc.
    
    **Sales Items Files** (item-level data):
    - Columns: Order No, Order Time, Item name, Quantity, Price, Item Type, etc.
    """)
    st.stop()

# Create tabs for different analyses
tabs = st.tabs(["📊 Sales Overview", "📈 Revenue Trends", "🍽️ Items Analysis"])

# ==================== TAB 1: SALES OVERVIEW ====================
with tabs[0]:
    if has_orders:
        st.subheader("📊 Sales Overview")
        
        # Date filter
        col1, col2 = st.columns(2)
        min_date = df_orders['Business_Date'].min()
        max_date = df_orders['Business_Date'].max()
        
        with col1:
            start_date = st.date_input("Start Date", min_date, key="orders_start")
        with col2:
            end_date = st.date_input("End Date", max_date, key="orders_end")
        
        # Filter data
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
        
        # Orders by type and staff
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
            # Monthly revenue bar chart
            monthly_data = filtered_trend.groupby('Order_Month').agg(
                Revenue=('Order Amount', 'sum'),
                Orders=('Order No', 'nunique')
            ).reset_index()
            monthly_data = monthly_data.sort_values('Order_Month')
            
            fig = px.bar(monthly_data, x='Order_Month', y='Revenue',
                        title='Monthly Revenue',
                        text='Revenue')
            fig.update_traces(texttemplate='SAR %{text:,.0f}', textposition='outside')
            fig.update_layout(xaxis_title='Month', yaxis_title='Revenue (SAR)')
            st.plotly_chart(fig, use_container_width=True)
            
            # Show table
            st.dataframe(monthly_data.rename(columns={'Order_Month': 'Month'}), 
                        use_container_width=True, hide_index=True)
        
        elif time_view == "Daily":
            # Daily revenue line chart
            daily_data = filtered_trend.groupby('Business_Date').agg(
                Revenue=('Order Amount', 'sum'),
                Orders=('Order No', 'nunique')
            ).reset_index()
            daily_data = daily_data.sort_values('Business_Date')
            
            fig = px.line(daily_data, x='Business_Date', y='Revenue',
                         title='Daily Revenue Trend',
                         markers=True)
            fig.update_layout(xaxis_title='Date', yaxis_title='Revenue (SAR)')
            st.plotly_chart(fig, use_container_width=True)
            
            # Add month filter for daily view
            if len(filtered_trend['Order_Month'].unique()) > 1:
                selected_month = st.selectbox(
                    "Filter by Month (for detailed view):",
                    ['All'] + sorted(filtered_trend['Order_Month'].unique().tolist())
                )
                if selected_month != 'All':
                    month_daily = daily_data[
                        pd.to_datetime(daily_data['Business_Date']).dt.to_period('M').astype(str) == selected_month
                    ]
                    fig2 = px.bar(month_daily, x='Business_Date', y='Revenue',
                                 title=f'Daily Revenue - {selected_month}')
                    st.plotly_chart(fig2, use_container_width=True)
        
        else:  # Hourly Distribution
            # Stacked bar chart by hour with months as colors
            hourly_monthly = filtered_trend.groupby(['Order_Hour', 'Order_Month']).agg(
                Revenue=('Order Amount', 'sum')
            ).reset_index()
            
            # Create stacked bar chart
            fig = px.bar(hourly_monthly, x='Order_Hour', y='Revenue',
                        color='Order_Month',
                        title='Hourly Revenue Distribution by Month',
                        barmode='stack',
                        labels={'Order_Hour': 'Hour of Day', 'Revenue': 'Revenue (SAR)', 'Order_Month': 'Month'})
            
            # Customize x-axis to show all 24 hours
            fig.update_layout(
                xaxis=dict(
                    tickmode='linear',
                    tick0=0,
                    dtick=1,
                    title='Hour of Day (0-23)'
                )
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Also show orders count by hour
            hourly_orders = filtered_trend.groupby(['Order_Hour', 'Order_Month']).agg(
                Orders=('Order No', 'nunique')
            ).reset_index()
            
            fig2 = px.bar(hourly_orders, x='Order_Hour', y='Orders',
                         color='Order_Month',
                         title='Hourly Orders Distribution by Month',
                         barmode='stack')
            fig2.update_layout(
                xaxis=dict(tickmode='linear', tick0=0, dtick=1, title='Hour of Day (0-23)')
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            # Summary table
            hourly_summary = filtered_trend.groupby('Order_Hour').agg(
                Total_Revenue=('Order Amount', 'sum'),
                Total_Orders=('Order No', 'nunique'),
                Avg_Order_Value=('Order Amount', 'mean')
            ).reset_index().sort_values('Order_Hour')
            
            st.markdown("### Hourly Summary")
            st.dataframe(hourly_summary, use_container_width=True, hide_index=True)
    else:
        st.info("📋 Upload Sales Orders files to see revenue trends.")

# ==================== TAB 3: ITEMS ANALYSIS ====================
with tabs[2]:
    if has_items:
        st.subheader("🍽️ Items Analysis")
        
        # Filter out modifiers for main analysis
        if 'Item Type' in df_items.columns:
            main_items = df_items[df_items['Item Type'] == 'Regular Item'].copy()
        else:
            main_items = df_items.copy()
        
        # Date filter
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
        
        # Top/Bottom items analysis
        col1, col2 = st.columns(2)
        
        # Aggregate items
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
        
        # Multi-select for items
        all_items_list = sorted(items_summary['Item name'].unique().tolist())
        
        # Default selection - top 5 items
        default_items = items_summary.nlargest(5, 'Total_Quantity')['Item name'].tolist()
        
        selected_items = st.multiselect(
            "Select Items to Track:",
            all_items_list,
            default=default_items[:3] if len(default_items) >= 3 else default_items,
            key="track_items"
        )
        
        if selected_items:
            # Time granularity for tracking
            track_granularity = st.radio(
                "View By:",
                ["Monthly", "Daily"],
                horizontal=True,
                key="track_granularity"
            )
            
            # Filter for selected items
            tracked_items = filtered_items[filtered_items['Item name'].isin(selected_items)]
            
            if track_granularity == "Monthly":
                # Monthly consumption
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
                
                # Stacked bar version
                fig2 = px.bar(monthly_items, x='Order_Month', y='Quantity',
                             color='Item name',
                             title='Monthly Item Consumption (Stacked)',
                             barmode='stack')
                st.plotly_chart(fig2, use_container_width=True)
            
            else:
                # Daily consumption
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
            
            # Summary table for selected items
            st.markdown("### Selected Items Summary")
            selected_summary = items_summary[items_summary['Item name'].isin(selected_items)].sort_values(
                'Total_Quantity', ascending=False
            )
            st.dataframe(selected_summary, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Full items table
        st.markdown("### 📋 Complete Items Summary")
        st.dataframe(
            items_summary.sort_values('Total_Quantity', ascending=False),
            use_container_width=True,
            hide_index=True
        )
        
        # Download
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
    "Restaurant Sales Analytics Dashboard | Business Day: 6:00 AM - 5:59 AM"
    "</div>",
    unsafe_allow_html=True
)
