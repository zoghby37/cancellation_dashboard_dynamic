import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Cancellation Report Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stMetric > div {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Reasons that should NOT count as actual lost money
NON_LOST_MONEY_REASONS = [
    "Change as desired by the customer before processing",
    "Wrong transaction by waiter before processing",
    "Item not available"
]

# Data preprocessing function
def preprocess_data(df):
    """Clean and preprocess the cancellation data"""
    df['Modified Item'] = df['Modified Item'].str.strip()
    df['Modify Reason'] = df['Modify Reason'].str.strip()
    df['Order Entered By'] = df['Order Entered By'].str.strip()
    df['Who?'] = df['Who?'].str.strip()
    
    df = df.drop_duplicates(subset=['Order Number', 'Modified Item'], keep='first').copy()
    
    # Convert datetime - try multiple formats
    def parse_datetime(col):
        try:
            return pd.to_datetime(col, format='%d-%b-%Y %I:%M %p')
        except:
            pass
        try:
            return pd.to_datetime(col, format='%m/%d/%Y %H:%M')
        except:
            pass
        return pd.to_datetime(col, format='mixed', dayfirst=False)
    
    df['Order Time'] = parse_datetime(df['Order Time'])
    df['When?'] = parse_datetime(df['When?'])
    
    df['Cancel_Date'] = df['When?'].dt.date
    df['Cancel_Month'] = df['When?'].dt.strftime('%B %Y')
    df['Cancel_Hour'] = df['When?'].dt.hour
    df['Cancel_Day'] = df['When?'].dt.day_name()
    df['Time_Period'] = df['Cancel_Hour'].apply(lambda x: 
        'Morning (6-12)' if 6 <= x < 12 else
        'Afternoon (12-18)' if 12 <= x < 18 else
        'Evening (18-24)' if 18 <= x < 24 else
        'Late Night (0-6)')
    df['Time_to_Cancel_Min'] = (df['When?'] - df['Order Time']).dt.total_seconds() / 60
    
    df['Is_Actual_Loss'] = ~df['Modify Reason'].isin(NON_LOST_MONEY_REASONS)
    df['Actual_Lost_Amount'] = df.apply(
        lambda row: row['Reduced Amount'] if row['Is_Actual_Loss'] else 0, axis=1
    )
    
    return df

# Sidebar - File Upload & Filters
st.sidebar.header("📁 Upload Data")
uploaded_files = st.sidebar.file_uploader(
    "Upload CSV files",
    type=['csv'],
    accept_multiple_files=True,
    help="Upload one or more cancellation report CSV files"
)

if uploaded_files:
    st.sidebar.success(f"✅ {len(uploaded_files)} file(s) loaded")

st.sidebar.markdown("---")

# Main title
st.title("📊 Cancellation Report Dashboard")

# Process uploaded files
if uploaded_files:
    all_data = []
    for uploaded_file in uploaded_files:
        try:
            df_temp = pd.read_csv(uploaded_file)
            all_data.append(df_temp)
        except Exception as e:
            st.error(f"Error reading {uploaded_file.name}: {e}")
    
    if all_data:
        df_combined = pd.concat(all_data, ignore_index=True)
        df = preprocess_data(df_combined)
        
        # Sidebar filters
        st.sidebar.header("🔍 Filters")
        
        min_date = df['Cancel_Date'].min()
        max_date = df['Cancel_Date'].max()
        date_range = st.sidebar.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        all_months = ['All'] + sorted(df['Cancel_Month'].unique().tolist())
        selected_month = st.sidebar.selectbox("Month", all_months)
        
        all_reasons = ['All'] + sorted(df['Modify Reason'].unique().tolist())
        selected_reason = st.sidebar.selectbox("Modify Reason", all_reasons)
        
        all_staff = ['All'] + sorted(df['Order Entered By'].unique().tolist())
        selected_staff = st.sidebar.selectbox("Staff Member", all_staff)
        
        all_periods = ['All'] + df['Time_Period'].unique().tolist()
        selected_period = st.sidebar.selectbox("Time Period", all_periods)
        
        # Apply filters
        filtered_df = df.copy()
        
        if len(date_range) == 2:
            filtered_df = filtered_df[
                (filtered_df['Cancel_Date'] >= date_range[0]) & 
                (filtered_df['Cancel_Date'] <= date_range[1])
            ]
        
        if selected_month != 'All':
            filtered_df = filtered_df[filtered_df['Cancel_Month'] == selected_month]
        
        if selected_reason != 'All':
            filtered_df = filtered_df[filtered_df['Modify Reason'] == selected_reason]
        
        if selected_staff != 'All':
            filtered_df = filtered_df[filtered_df['Order Entered By'] == selected_staff]
        
        if selected_period != 'All':
            filtered_df = filtered_df[filtered_df['Time_Period'] == selected_period]
        
        st.markdown("---")
        
        # KPI Metrics Row
        st.subheader("📈 Key Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Total Cancellations",
                value=f"{len(filtered_df):,}"
            )
        
        with col2:
            total_amount = filtered_df['Reduced Amount'].sum()
            st.metric(
                label="Total Amount (SAR)",
                value=f"{total_amount:,.2f}",
                help="Sum of all reduced amounts"
            )
        
        with col3:
            actual_lost = filtered_df['Actual_Lost_Amount'].sum()
            st.metric(
                label="💰 Actual Lost Money (SAR)",
                value=f"{actual_lost:,.2f}",
                help="Excludes: Customer changes before processing, Waiter mistakes before processing, Item not available"
            )
        
        with col4:
            loss_percentage = (actual_lost / total_amount * 100) if total_amount > 0 else 0
            st.metric(
                label="Actual Loss %",
                value=f"{loss_percentage:.1f}%"
            )
        
        st.markdown("---")
        
        # Row 1: Reason Analysis
        st.subheader("📋 Cancellation Reasons Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            reason_data = filtered_df.groupby('Modify Reason').agg(
                Count=('Modify Reason', 'count'),
                Actual_Lost=('Actual_Lost_Amount', 'sum')
            ).reset_index().sort_values('Actual_Lost', ascending=True)
            
            fig_reason = px.bar(
                reason_data,
                x='Actual_Lost',
                y='Modify Reason',
                orientation='h',
                title='Actual Lost Money by Reason (SAR)',
                color='Actual_Lost',
                color_continuous_scale='Reds'
            )
            fig_reason.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_reason, use_container_width=True)
        
        with col2:
            reason_count = filtered_df.groupby('Modify Reason').size().reset_index(name='Count')
            fig_reason_pie = px.pie(
                reason_count,
                values='Count',
                names='Modify Reason',
                title='Cancellation Count Distribution',
                hole=0.4
            )
            fig_reason_pie.update_layout(height=400)
            st.plotly_chart(fig_reason_pie, use_container_width=True)
        
        st.markdown("---")
        
        # Row 2: Staff Analysis
        st.subheader("👥 Staff Performance Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            staff_data = filtered_df.groupby('Order Entered By').agg(
                Cancellations=('Order Number', 'count'),
                Actual_Lost=('Actual_Lost_Amount', 'sum')
            ).reset_index().sort_values('Cancellations', ascending=False)
            
            fig_staff = px.bar(
                staff_data,
                x='Order Entered By',
                y='Cancellations',
                title='Cancellations by Staff Member',
                color='Actual_Lost',
                color_continuous_scale='Blues'
            )
            fig_staff.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_staff, use_container_width=True)
        
        with col2:
            # Stacked bar chart - cleaner than grouped
            staff_reason_data = filtered_df.groupby(['Order Entered By', 'Modify Reason']).size().reset_index(name='Count')
            
            # Get top 5 reasons
            top_reasons = filtered_df['Modify Reason'].value_counts().head(5).index.tolist()
            staff_reason_filtered = staff_reason_data[staff_reason_data['Modify Reason'].isin(top_reasons)]
            
            # Shorten reason names for better display
            reason_short_names = {
                "Change as desired by the customer before processing": "Customer Change (Before)",
                "Wrong transaction by waiter before processing": "Waiter Error (Before)",
                "Change as desired by the customer after preparation": "Customer Change (After)",
                "Customer does not like the item": "Customer Dislike",
                "Item not available": "Item Unavailable",
                "Damage due external factors": "External Damage",
                "Wrong order by customer": "Wrong Order",
                "Wrong table order": "Wrong Table",
                "Wrong transaction by waiter after processing": "Waiter Error (After)",
                "Customer need to cancel as per his request": "Customer Request",
                "Item not meet quality pecifications": "Quality Issue",
                "Attempt request": "Attempt Request"
            }
            staff_reason_filtered['Reason_Short'] = staff_reason_filtered['Modify Reason'].map(reason_short_names).fillna(staff_reason_filtered['Modify Reason'])
            
            fig_stacked = px.bar(
                staff_reason_filtered,
                x='Order Entered By',
                y='Count',
                color='Reason_Short',
                title='Staff Cancellations by Reason (Top 5)',
                barmode='stack'
            )
            fig_stacked.update_layout(
                height=400,
                xaxis_tickangle=-45,
                legend=dict(
                    title="Reason",
                    orientation="h",
                    yanchor="bottom",
                    y=-0.55,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=10)
                ),
                margin=dict(b=120)
            )
            st.plotly_chart(fig_stacked, use_container_width=True)
        
        st.markdown("---")
        
        # Row 3: Time Analysis
        st.subheader("🕐 Time Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            hourly_data = filtered_df.groupby('Cancel_Hour').agg(
                Cancellations=('Order Number', 'count'),
                Actual_Lost=('Actual_Lost_Amount', 'sum')
            ).reset_index()
            
            fig_hourly = px.bar(
                hourly_data,
                x='Cancel_Hour',
                y='Cancellations',
                title='Cancellations by Hour of Day',
                color='Actual_Lost',
                color_continuous_scale='Viridis'
            )
            fig_hourly.update_layout(height=400, xaxis=dict(tickmode='linear', dtick=2))
            st.plotly_chart(fig_hourly, use_container_width=True)
        
        with col2:
            period_data = filtered_df.groupby('Time_Period').agg(
                Cancellations=('Order Number', 'count'),
                Actual_Lost=('Actual_Lost_Amount', 'sum')
            ).reset_index()
            
            fig_period = px.pie(
                period_data,
                values='Cancellations',
                names='Time_Period',
                title='Cancellations by Time Period',
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_period.update_layout(height=400)
            st.plotly_chart(fig_period, use_container_width=True)
        
        st.markdown("---")
        
        # Row 4: Daily Trend and Items
        st.subheader("📈 Trends & Top Items")
        col1, col2 = st.columns(2)
        
        with col1:
            daily_data = filtered_df.groupby('Cancel_Date').agg(
                Cancellations=('Order Number', 'count'),
                Actual_Lost=('Actual_Lost_Amount', 'sum')
            ).reset_index()
            
            fig_daily = go.Figure()
            fig_daily.add_trace(go.Scatter(
                x=daily_data['Cancel_Date'],
                y=daily_data['Cancellations'],
                mode='lines+markers',
                name='Cancellations',
                line=dict(color='#667eea', width=2),
                fill='tozeroy',
                fillcolor='rgba(102, 126, 234, 0.2)'
            ))
            fig_daily.update_layout(
                title='Daily Cancellation Trend',
                height=400,
                xaxis_title='Date',
                yaxis_title='Cancellations'
            )
            st.plotly_chart(fig_daily, use_container_width=True)
        
        with col2:
            item_data = filtered_df[filtered_df['Modified Item'] != '.'].groupby('Modified Item').agg(
                Times_Cancelled=('Modified Item', 'count'),
                Actual_Lost=('Actual_Lost_Amount', 'sum')
            ).reset_index().sort_values('Times_Cancelled', ascending=False).head(10)
            
            fig_items = px.bar(
                item_data,
                x='Times_Cancelled',
                y='Modified Item',
                orientation='h',
                title='Top 10 Most Cancelled Items',
                color='Actual_Lost',
                color_continuous_scale='Teal'
            )
            fig_items.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_items, use_container_width=True)
        
        st.markdown("---")
        
        # Monthly Comparison (if multiple months)
        if df['Cancel_Month'].nunique() > 1:
            st.subheader("📅 Monthly Comparison")
            
            monthly_data = filtered_df.groupby('Cancel_Month').agg(
                Cancellations=('Order Number', 'count'),
                Total_Amount=('Reduced Amount', 'sum'),
                Actual_Lost=('Actual_Lost_Amount', 'sum')
            ).reset_index()
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig_monthly = px.bar(
                    monthly_data,
                    x='Cancel_Month',
                    y='Cancellations',
                    title='Cancellations by Month',
                    color='Cancellations',
                    color_continuous_scale='Blues'
                )
                st.plotly_chart(fig_monthly, use_container_width=True)
            
            with col2:
                fig_monthly_amount = px.bar(
                    monthly_data,
                    x='Cancel_Month',
                    y=['Total_Amount', 'Actual_Lost'],
                    title='Amount Comparison by Month',
                    barmode='group'
                )
                st.plotly_chart(fig_monthly_amount, use_container_width=True)
            
            st.markdown("---")
        
        # Data Tables Section
        st.subheader("📋 Detailed Data")
        
        tab1, tab2, tab3 = st.tabs(["Reason Summary", "Staff Summary", "Raw Data"])
        
        with tab1:
            reason_summary = filtered_df.groupby('Modify Reason').agg(
                Count=('Modify Reason', 'count'),
                Total_Amount=('Reduced Amount', 'sum'),
                Actual_Lost=('Actual_Lost_Amount', 'sum')
            ).reset_index().sort_values('Count', ascending=False)
            reason_summary['Is_Actual_Loss'] = ~reason_summary['Modify Reason'].isin(NON_LOST_MONEY_REASONS)
            reason_summary['Loss_Type'] = reason_summary['Is_Actual_Loss'].apply(lambda x: '💰 Actual Loss' if x else '⚪ Not Counted')
            st.dataframe(reason_summary[['Modify Reason', 'Count', 'Total_Amount', 'Actual_Lost', 'Loss_Type']], 
                        use_container_width=True, hide_index=True)
        
        with tab2:
            staff_summary = filtered_df.groupby('Order Entered By').agg(
                Total_Cancellations=('Order Number', 'count'),
                Total_Amount=('Reduced Amount', 'sum'),
                Actual_Lost=('Actual_Lost_Amount', 'sum')
            ).reset_index().sort_values('Total_Cancellations', ascending=False)
            st.dataframe(staff_summary, use_container_width=True, hide_index=True)
        
        with tab3:
            display_cols = ['Order Number', 'Order Time', 'Order Entered By', 'Modified Item', 
                          'When?', 'Modify Reason', 'Reduced Amount', 'Actual_Lost_Amount', 'Cancel_Month']
            st.dataframe(filtered_df[display_cols], use_container_width=True, hide_index=True)
        
        # Download section
        st.markdown("---")
        st.subheader("📥 Download Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Filtered Data (CSV)",
                data=csv,
                file_name="filtered_cancellation_data.csv",
                mime="text/csv"
            )
        
        with col2:
            full_csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Full Clean Data (CSV)",
                data=full_csv,
                file_name="full_cancellation_data.csv",
                mime="text/csv"
            )

else:
    # Minimal welcome message when no file uploaded
    st.info("👈 Upload your cancellation report CSV files from the sidebar to get started.")
    st.markdown("""
    **Expected columns:** Order Number, Order Type, Order Time, Order Entered By, Modified Item, When?, What?, Who?, Modify Reason, Reduced Amount
    """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>Cancellation Analysis Dashboard</div>",
    unsafe_allow_html=True
)
