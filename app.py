"""
Tesh Lounge - Sales Orders Analysis Dashboard
Business day starts at 6:00 AM
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from preprocessing import (
    run_full_preprocessing,
    split_orders_by_amount,
    get_payment_method_summary,
    get_business_hour_label,
    get_hour_labels_for_business_day,
    format_currency,
    format_percentage
)

# Tesh Brand Colors (used for UI elements like tabs, headers)
TESH_TEAL = '#2B6A6C'
TESH_GOLD = '#C9A227'

# Page configuration
st.set_page_config(
    page_title="Tesh Lounge - Sales Analysis",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - Fixed for dark mode compatibility
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #C9A227;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #888;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #C9A227;
        border-bottom: 3px solid #2B6A6C;
        padding-bottom: 0.5rem;
        margin: 2rem 0 1rem 0;
    }
    .insight-box {
        background-color: rgba(43, 106, 108, 0.2);
        border-left: 4px solid #2B6A6C;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 8px 8px 0;
        color: inherit;
    }
    .warning-box {
        background-color: rgba(201, 162, 39, 0.2);
        border-left: 4px solid #C9A227;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 8px 8px 0;
        color: inherit;
    }
    .info-box {
        background-color: rgba(43, 106, 108, 0.15);
        border-left: 4px solid #2B6A6C;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 8px 8px 0;
        color: inherit;
    }
    /* Fixed Tabs for Dark Mode */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #2B6A6C;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: white !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #3d8a8c;
        color: white !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #C9A227 !important;
        color: #1a1a1a !important;
    }
    /* Ensure tab text is always visible */
    .stTabs [data-baseweb="tab"] span {
        color: white !important;
    }
    .stTabs [aria-selected="true"] span {
        color: #1a1a1a !important;
    }
    /* Logo styling */
    .logo-container {
        display: flex;
        justify-content: center;
        margin-bottom: 1rem;
    }
    .logo-container img {
        max-width: 120px;
        height: auto;
    }
</style>
""", unsafe_allow_html=True)


def main():
    # Header with Logo
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Check if logo exists in the same directory
        import os
        logo_path = os.path.join(os.path.dirname(__file__), 'tesh_logo.png')
        if os.path.exists(logo_path):
            st.image(logo_path, width=90)
        
        st.markdown('<div class="main-header">Tesh Lounge - Sales Analysis</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">Business day starts at 6:00 AM | 24-Hour Operation</div>', unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("📁 Data Upload")
    st.sidebar.markdown("---")
    
    uploaded_file = st.sidebar.file_uploader(
        "Upload Sales Orders CSV",
        type=['csv'],
        help="Upload your sales orders CSV file"
    )
    
    if uploaded_file is not None:
        # Load data
        try:
            raw_df = pd.read_csv(uploaded_file)
            st.sidebar.success(f"✅ Loaded {len(raw_df)} orders")
        except Exception as e:
            st.error(f"Error loading file: {e}")
            return
        
        # Run preprocessing
        df, payment_df, preprocessing_log = run_full_preprocessing(raw_df)
        
        # Split orders
        paid_orders, zero_orders = split_orders_by_amount(df)
        
        # Sidebar filters
        st.sidebar.markdown("---")
        st.sidebar.title("🔍 Filters")
        
        # Date range filter
        if 'Business Date' in paid_orders.columns and paid_orders['Business Date'].notna().any():
            min_date = pd.to_datetime(paid_orders['Business Date'].min())
            max_date = pd.to_datetime(paid_orders['Business Date'].max())
            
            date_range = st.sidebar.date_input(
                "Business Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            
            if len(date_range) == 2:
                paid_orders = paid_orders[
                    (pd.to_datetime(paid_orders['Business Date']) >= pd.to_datetime(date_range[0])) &
                    (pd.to_datetime(paid_orders['Business Date']) <= pd.to_datetime(date_range[1]))
                ]
        
        # Order type filter
        if 'Order Type' in paid_orders.columns:
            order_types = ['All'] + paid_orders['Order Type'].dropna().unique().tolist()
            selected_type = st.sidebar.selectbox("Order Type", order_types)
            if selected_type != 'All':
                paid_orders = paid_orders[paid_orders['Order Type'] == selected_type]
        
        # Staff filter
        if 'Order Taken By' in paid_orders.columns:
            staff_list = ['All'] + sorted(paid_orders['Order Taken By'].dropna().unique().tolist())
            selected_staff = st.sidebar.selectbox("Staff Member", staff_list)
            if selected_staff != 'All':
                paid_orders = paid_orders[paid_orders['Order Taken By'] == selected_staff]
        
        st.sidebar.markdown("---")
        st.sidebar.info(f"📊 Showing {len(paid_orders)} orders after filters")
        
        # Tabs - Preprocessing tab commented out
        # tab1, tab2, tab3, tab4 = st.tabs([
        #     "🔧 Preprocessing", 
        #     "📈 Orders Insights", 
        #     "💳 Payment Analysis",
        #     "👥 Staff Performance"
        # ])
        
        tab2, tab3, tab4 = st.tabs([
            "📈 Orders Insights", 
            "💳 Payment Analysis",
            "👥 Staff Performance"
        ])
        
        # ==================== TAB 1: PREPROCESSING (COMMENTED OUT) ====================
        # with tab1:
        #     st.markdown('<div class="section-header">Data Preprocessing</div>', unsafe_allow_html=True)
        #     
        #     col1, col2 = st.columns(2)
        #     
        #     with col1:
        #         st.markdown("**📋 Original Data Summary**")
        #         st.write(f"- Total Rows: {len(raw_df)}")
        #         st.write(f"- Total Columns: {len(raw_df.columns)}")
        #         st.write(f"- Memory Usage: {raw_df.memory_usage(deep=True).sum() / 1024:.2f} KB")
        #     
        #     with col2:
        #         st.markdown("**✨ Preprocessing Steps**")
        #         for log in preprocessing_log:
        #             st.write(log)
        #     
        #     st.markdown("---")
        #     
        #     # Business day explanation
        #     st.markdown("""
        #     <div class="info-box">
        #         <strong>📅 Business Day Logic:</strong><br>
        #         • Business day starts at <strong>6:00 AM</strong><br>
        #         • Orders from 12:00 AM - 5:59 AM are counted as the <strong>previous business day</strong><br>
        #         • Example: An order at 2:00 AM on May 15th belongs to the May 14th business day
        #     </div>
        #     """, unsafe_allow_html=True)
        #     
        #     st.markdown("---")
        #     
        #     # Show sample of processed data
        #     st.markdown("**📊 Sample of Processed Data (Key Columns)**")
        #     key_cols = ['Order No', 'Order Time', 'Business Date', 'Business Hour', 'Order Type', 
        #                'Order Taken By', 'Order Amount', 'Num_Payment_Methods', 'Payment_Methods_Used', 'Notes']
        #     key_cols = [c for c in key_cols if c in df.columns]
        #     st.dataframe(df[key_cols].head(10), use_container_width=True)
        
        # ==================== TAB 2: ORDERS INSIGHTS ====================
        with tab2:
            st.markdown('<div class="section-header">Orders Insights</div>', unsafe_allow_html=True)
            
            # Key Metrics
            col1, col2, col3, col4 = st.columns(4)
            
            total_orders = len(paid_orders)
            total_revenue = paid_orders['Order Amount'].sum()
            avg_order_value = paid_orders['Order Amount'].mean() if total_orders > 0 else 0
            
            with col1:
                st.metric("Total Paid Orders", f"{total_orders:,}")
            with col2:
                st.metric("Total Revenue", f"SAR {total_revenue:,.2f}")
            with col3:
                st.metric("Average Order Value", f"SAR {avg_order_value:,.2f}")
            with col4:
                st.metric("Zero Amount Orders", f"{len(zero_orders)}")
            
            st.markdown("---")
            
            # Order Type Distribution
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📊 Orders by Type**")
                if len(paid_orders) > 0:
                    order_type_counts = paid_orders['Order Type'].value_counts()
                    fig_type = px.pie(
                        values=order_type_counts.values,
                        names=order_type_counts.index,
                        title="Order Count by Type",
                        color_discrete_sequence=px.colors.qualitative.Set2
                    )
                    fig_type.update_traces(textposition='inside', textinfo='percent+label+value')
                    st.plotly_chart(fig_type, use_container_width=True)
            
            with col2:
                st.markdown("**💰 Revenue by Order Type**")
                if len(paid_orders) > 0:
                    order_type_revenue = paid_orders.groupby('Order Type')['Order Amount'].sum()
                    fig_revenue = px.pie(
                        values=order_type_revenue.values,
                        names=order_type_revenue.index,
                        title="Revenue Distribution by Type",
                        color_discrete_sequence=px.colors.qualitative.Set2
                    )
                    fig_revenue.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_revenue, use_container_width=True)
            
            st.markdown("---")
            
            # Rush Hours Analysis (Business Hours)
            st.markdown("**⏰ Rush Hours Analysis (Business Day: 6 AM - 5 AM)**")
            
            if 'Business Hour' in paid_orders.columns and paid_orders['Business Hour'].notna().any():
                # Orders by Business Hour
                hourly_orders = paid_orders.groupby('Business Hour').agg({
                    'Order No': 'count',
                    'Order Amount': 'sum'
                }).reset_index()
                hourly_orders.columns = ['Business Hour', 'Order Count', 'Total Revenue']
                
                # Create full 24-hour range
                full_hours = pd.DataFrame({'Business Hour': range(24)})
                hourly_orders = full_hours.merge(hourly_orders, on='Business Hour', how='left').fillna(0)
                
                # Add clock time labels
                hourly_orders['Hour Label'] = hourly_orders['Business Hour'].apply(get_business_hour_label)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_hourly_count = px.bar(
                        hourly_orders,
                        x='Hour Label',
                        y='Order Count',
                        title="Number of Orders by Hour (Starting 6 AM)",
                        color='Order Count',
                        color_continuous_scale='Blues'
                    )
                    fig_hourly_count.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig_hourly_count, use_container_width=True)
                
                with col2:
                    fig_hourly_revenue = px.bar(
                        hourly_orders,
                        x='Hour Label',
                        y='Total Revenue',
                        title="Revenue by Hour (SAR)",
                        color='Total Revenue',
                        color_continuous_scale='Greens'
                    )
                    fig_hourly_revenue.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig_hourly_revenue, use_container_width=True)
                
                # Peak hours insight
                peak_hour_orders = hourly_orders.loc[hourly_orders['Order Count'].idxmax()]
                peak_hour_revenue = hourly_orders.loc[hourly_orders['Total Revenue'].idxmax()]
                
                st.markdown(f"""
                <div class="insight-box">
                    <strong>📌 Key Insights:</strong><br>
                    • Peak orders time: <strong>{peak_hour_orders['Hour Label']}</strong> with {int(peak_hour_orders['Order Count'])} orders<br>
                    • Peak revenue time: <strong>{peak_hour_revenue['Hour Label']}</strong> with SAR {peak_hour_revenue['Total Revenue']:,.2f}
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Daily Pattern (Business Dates)
            st.markdown("**📅 Daily Pattern (Business Dates)**")
            
            if 'Business Date' in paid_orders.columns and paid_orders['Business Date'].notna().any():
                daily_stats = paid_orders.groupby('Business Date').agg({
                    'Order No': 'count',
                    'Order Amount': 'sum'
                }).reset_index()
                daily_stats.columns = ['Business Date', 'Order Count', 'Total Revenue']
                daily_stats = daily_stats.sort_values('Business Date')
                
                fig_daily = make_subplots(specs=[[{"secondary_y": True}]])
                fig_daily.add_trace(
                    go.Bar(x=daily_stats['Business Date'], y=daily_stats['Order Count'], 
                           name="Orders", marker_color='#667eea'),
                    secondary_y=False
                )
                fig_daily.add_trace(
                    go.Scatter(x=daily_stats['Business Date'], y=daily_stats['Total Revenue'], 
                               name="Revenue", line=dict(color='#2ecc71', width=3)),
                    secondary_y=True
                )
                fig_daily.update_layout(title="Daily Orders and Revenue Trend (Business Dates)")
                fig_daily.update_yaxes(title_text="Order Count", secondary_y=False)
                fig_daily.update_yaxes(title_text="Revenue (SAR)", secondary_y=True)
                st.plotly_chart(fig_daily, use_container_width=True)
                
                # Day of week analysis
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                if 'Day of Week' in paid_orders.columns:
                    dow_stats = paid_orders.groupby('Day of Week').agg({
                        'Order No': 'count',
                        'Order Amount': ['sum', 'mean']
                    }).reset_index()
                    dow_stats.columns = ['Day', 'Order Count', 'Total Revenue', 'Avg Order Value']
                    dow_stats['Day'] = pd.Categorical(dow_stats['Day'], categories=day_order, ordered=True)
                    dow_stats = dow_stats.sort_values('Day')
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig_dow = px.bar(
                            dow_stats,
                            x='Day',
                            y='Order Count',
                            title="Orders by Day of Week",
                            color='Order Count',
                            color_continuous_scale='Purples'
                        )
                        st.plotly_chart(fig_dow, use_container_width=True)
                    
                    with col2:
                        fig_dow_rev = px.bar(
                            dow_stats,
                            x='Day',
                            y='Total Revenue',
                            title="Revenue by Day of Week",
                            color='Total Revenue',
                            color_continuous_scale='Oranges'
                        )
                        st.plotly_chart(fig_dow_rev, use_container_width=True)
            
            # Zero Amount Orders Section
            st.markdown("---")
            st.markdown('<div class="section-header">⚠️ Zero Amount Orders</div>', unsafe_allow_html=True)
            
            if len(zero_orders) > 0:
                st.warning(f"Found **{len(zero_orders)}** orders with zero amount")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**📋 Zero Orders by Staff**")
                    zero_by_staff = zero_orders['Order Taken By'].value_counts().head(10)
                    fig_zero_staff = px.bar(
                        x=zero_by_staff.values,
                        y=zero_by_staff.index,
                        orientation='h',
                        title="Zero Amount Orders by Staff",
                        labels={'x': 'Count', 'y': 'Staff'}
                    )
                    st.plotly_chart(fig_zero_staff, use_container_width=True)
                
                with col2:
                    st.markdown("**📝 Notes/Reasons**")
                    notes_analysis = zero_orders[zero_orders['Notes'].notna() & (zero_orders['Notes'] != '')]
                    if len(notes_analysis) > 0:
                        st.dataframe(
                            notes_analysis[['Order No', 'Order Time', 'Order Taken By', 'Notes']].head(20),
                            use_container_width=True
                        )
                    else:
                        st.info("No notes provided for zero amount orders")
            else:
                st.success("No zero amount orders found!")
        
        # ==================== TAB 3: PAYMENT ANALYSIS ====================
        with tab3:
            st.markdown('<div class="section-header">Payment Analysis</div>', unsafe_allow_html=True)
            
            # Recalculate payment summary for filtered data
            payment_summary = get_payment_method_summary(paid_orders)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Payment Methods Used", len(payment_summary))
            with col2:
                top_method = payment_summary.iloc[0]['Payment Method'] if len(payment_summary) > 0 else "N/A"
                st.metric("Top Payment Method", top_method)
            with col3:
                multi_payment_orders = (paid_orders['Num_Payment_Methods'] > 1).sum()
                st.metric("Multi-Payment Orders", multi_payment_orders)
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**💳 Revenue by Payment Method**")
                if len(payment_summary) > 0:
                    fig_payment = px.pie(
                        payment_summary,
                        values='Total Amount',
                        names='Payment Method',
                        title="Revenue Distribution by Payment Method",
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    fig_payment.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_payment, use_container_width=True)
            
            with col2:
                st.markdown("**📊 Transaction Count by Method**")
                if len(payment_summary) > 0:
                    fig_trans = px.bar(
                        payment_summary,
                        x='Payment Method',
                        y='Transaction Count',
                        title="Number of Transactions by Payment Method",
                        color='Transaction Count',
                        color_continuous_scale='Viridis'
                    )
                    fig_trans.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_trans, use_container_width=True)
            
            st.markdown("---")
            
            # Payment Method Details Table
            st.markdown("**📋 Payment Methods Summary Table**")
            if len(payment_summary) > 0:
                payment_summary['Avg Transaction'] = payment_summary['Total Amount'] / payment_summary['Transaction Count']
                payment_summary['% of Revenue'] = (payment_summary['Total Amount'] / payment_summary['Total Amount'].sum() * 100).round(2)
                
                display_summary = payment_summary.copy()
                display_summary['Total Amount'] = display_summary['Total Amount'].apply(lambda x: f"SAR {x:,.2f}")
                display_summary['Avg Transaction'] = display_summary['Avg Transaction'].apply(lambda x: f"SAR {x:,.2f}")
                display_summary['% of Revenue'] = display_summary['% of Revenue'].apply(lambda x: f"{x}%")
                
                st.dataframe(display_summary, use_container_width=True)
            
            st.markdown("---")
            
            # Multi-Payment Analysis
            st.markdown("**🔄 Multi-Payment Method Orders**")
            
            multi_payment_df = paid_orders[paid_orders['Num_Payment_Methods'] > 1].copy()
            
            if len(multi_payment_df) > 0:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"Total multi-payment orders: **{len(multi_payment_df)}**")
                    st.write(f"Percentage of all orders: **{len(multi_payment_df)/len(paid_orders)*100:.1f}%**")
                    
                    method_dist = multi_payment_df['Num_Payment_Methods'].value_counts().sort_index()
                    fig_dist = px.bar(
                        x=method_dist.index,
                        y=method_dist.values,
                        title="Distribution of Payment Methods per Order",
                        labels={'x': 'Number of Payment Methods', 'y': 'Order Count'}
                    )
                    st.plotly_chart(fig_dist, use_container_width=True)
                
                with col2:
                    st.markdown("**Sample Multi-Payment Orders**")
                    sample_cols = ['Order No', 'Order Amount', 'Num_Payment_Methods', 'Payment_Methods_Used']
                    st.dataframe(
                        multi_payment_df[sample_cols].head(15),
                        use_container_width=True
                    )
            else:
                st.info("No orders with multiple payment methods found")
        
        # ==================== TAB 4: STAFF PERFORMANCE ====================
        with tab4:
            st.markdown('<div class="section-header">Staff Performance</div>', unsafe_allow_html=True)
            
            if len(paid_orders) > 0:
                # Staff Performance Metrics
                staff_stats = paid_orders.groupby('Order Taken By').agg({
                    'Order No': 'count',
                    'Order Amount': ['sum', 'mean', 'max', 'min']
                }).reset_index()
                staff_stats.columns = ['Staff', 'Total Orders', 'Total Revenue', 'Avg Order Value', 'Max Order', 'Min Order']
                staff_stats = staff_stats.sort_values('Total Revenue', ascending=False)
                
                # Top performers
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    top_orders = staff_stats.iloc[0]['Staff'] if len(staff_stats) > 0 else "N/A"
                    top_orders_count = staff_stats.iloc[0]['Total Orders'] if len(staff_stats) > 0 else 0
                    st.metric("Most Orders", f"{top_orders}", f"{top_orders_count} orders")
                
                with col2:
                    top_revenue = staff_stats.iloc[0]['Staff'] if len(staff_stats) > 0 else "N/A"
                    top_revenue_amt = staff_stats.iloc[0]['Total Revenue'] if len(staff_stats) > 0 else 0
                    st.metric("Highest Revenue", f"{top_revenue}", f"SAR {top_revenue_amt:,.0f}")
                
                with col3:
                    if len(staff_stats) > 0:
                        best_avg = staff_stats.loc[staff_stats['Avg Order Value'].idxmax()]
                        st.metric("Best Avg Order", f"{best_avg['Staff']}", f"SAR {best_avg['Avg Order Value']:,.2f}")
                
                st.markdown("---")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**📊 Orders by Staff**")
                    fig_staff_orders = px.bar(
                        staff_stats.head(15),
                        x='Staff',
                        y='Total Orders',
                        title="Total Orders by Staff Member",
                        color='Total Orders',
                        color_continuous_scale='Blues'
                    )
                    fig_staff_orders.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_staff_orders, use_container_width=True)
                
                with col2:
                    st.markdown("**💰 Revenue by Staff**")
                    fig_staff_revenue = px.bar(
                        staff_stats.head(15),
                        x='Staff',
                        y='Total Revenue',
                        title="Total Revenue by Staff Member (SAR)",
                        color='Total Revenue',
                        color_continuous_scale='Greens'
                    )
                    fig_staff_revenue.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_staff_revenue, use_container_width=True)
                
                st.markdown("---")
                
                # Staff Performance Scatter
                st.markdown("**🎯 Staff Performance Matrix**")
                
                fig_scatter = px.scatter(
                    staff_stats,
                    x='Total Orders',
                    y='Avg Order Value',
                    size='Total Revenue',
                    color='Total Revenue',
                    hover_name='Staff',
                    title="Staff Performance: Orders vs Average Value (size = Total Revenue)",
                    color_continuous_scale='Viridis'
                )
                fig_scatter.update_layout(height=500)
                st.plotly_chart(fig_scatter, use_container_width=True)
                
                st.markdown("---")
                
                # Detailed Staff Table
                st.markdown("**📋 Complete Staff Performance Table**")
                
                display_staff = staff_stats.copy()
                display_staff['Total Revenue'] = display_staff['Total Revenue'].apply(lambda x: f"SAR {x:,.2f}")
                display_staff['Avg Order Value'] = display_staff['Avg Order Value'].apply(lambda x: f"SAR {x:,.2f}")
                display_staff['Max Order'] = display_staff['Max Order'].apply(lambda x: f"SAR {x:,.2f}")
                display_staff['Min Order'] = display_staff['Min Order'].apply(lambda x: f"SAR {x:,.2f}")
                display_staff['% of Total Orders'] = (staff_stats['Total Orders'] / staff_stats['Total Orders'].sum() * 100).apply(lambda x: f"{x:.1f}%")
                
                st.dataframe(display_staff, use_container_width=True)
                
                st.markdown("---")
                
                # Staff Hourly Performance
                # if 'Business Hour' in paid_orders.columns and paid_orders['Business Hour'].notna().any():
                #     st.markdown("**⏰ Staff Activity by Hour (Business Day)**")
                    
                #     top_5_staff = staff_stats.head(5)['Staff'].tolist()
                #     top_staff_orders = paid_orders[paid_orders['Order Taken By'].isin(top_5_staff)]
                    
                #     staff_hourly = top_staff_orders.groupby(['Business Hour', 'Order Taken By']).size().reset_index(name='Orders')
                #     staff_hourly['Hour Label'] = staff_hourly['Business Hour'].apply(get_business_hour_label)
                    
                #     fig_heatmap = px.density_heatmap(
                #         staff_hourly,
                #         x='Hour Label',
                #         y='Order Taken By',
                #         z='Orders',
                #         title="Staff Activity Heatmap (Top 5 Staff by Revenue)",
                #         color_continuous_scale='YlOrRd'
                #     )
                #     fig_heatmap.update_layout(xaxis_tickangle=-45)
                #     st.plotly_chart(fig_heatmap, use_container_width=True)
                
                # Additional Staff Insights
                st.markdown("---")
                st.markdown("**💡 Staff Insights**")
                
                total_staff = len(staff_stats)
                avg_orders_per_staff = staff_stats['Total Orders'].mean()
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"""
                    <div class="insight-box">
                        <strong>Team Size:</strong> {total_staff} staff members<br>
                        <strong>Avg Orders/Staff:</strong> {avg_orders_per_staff:.1f}
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    top_performer_pct = (staff_stats.iloc[0]['Total Orders'] / staff_stats['Total Orders'].sum() * 100)
                    st.markdown(f"""
                    <div class="insight-box">
                        <strong>Top Performer:</strong> {staff_stats.iloc[0]['Staff']}<br>
                        <strong>Contribution:</strong> {top_performer_pct:.1f}% of orders
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    top_rev_pct = (staff_stats.iloc[0]['Total Revenue'] / staff_stats['Total Revenue'].sum() * 100)
                    st.markdown(f"""
                    <div class="insight-box">
                        <strong>Revenue Leader:</strong> {staff_stats.iloc[0]['Staff']}<br>
                        <strong>Revenue Share:</strong> {top_rev_pct:.1f}%
                    </div>
                    """, unsafe_allow_html=True)
    
    else:
        # No file uploaded - show instructions
        st.info("👈 Please upload a Sales Orders CSV file to begin analysis")
        
        st.markdown("""
        ### Expected CSV Format
        
        The file should contain the following key columns:
        - **Order No**: Unique order identifier
        - **Order Time**: Date and time of order (format: DD-Mon-YYYY HH:MM AM/PM)
        - **Order Type**: Type of order (Dine-In, Walk-In, etc.)
        - **Order Taken By**: Staff member who took the order
        - **Order Amount**: Total order value (tax included)
        - **Payments**: Payment method(s) and amount(s)
        - **Notes**: Any additional notes
        
        ### Business Day Logic
        
        🕐 **Business day starts at 6:00 AM**
        - Orders from 6:00 AM to 11:59 PM → Current business day
        - Orders from 12:00 AM to 5:59 AM → Previous business day
        
        ### Features
        
        1. **Preprocessing**: Automatic data cleaning and transformation
        2. **Orders Insights**: Overall metrics, rush hours, daily patterns
        3. **Payment Analysis**: Payment methods distribution and multi-payment handling
        4. **Staff Performance**: Individual staff metrics and comparisons
        """)


if __name__ == "__main__":
    main()
