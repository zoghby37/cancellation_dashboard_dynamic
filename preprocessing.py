"""
Tesh Lounge - Sales Orders Preprocessing Module
Business day starts at 6:00 AM (orders before 6 AM belong to previous business day)
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime, timedelta


# ==================== BUSINESS DAY LOGIC ====================

def get_business_date(order_time):
    """
    Convert order time to business date.
    Business day starts at 6:00 AM.
    Orders from 00:00-05:59 belong to the previous business day.
    """
    if pd.isna(order_time):
        return None
    
    hour = order_time.hour
    
    # If order is between midnight and 5:59 AM, it belongs to previous day
    if hour < 6:
        return (order_time - timedelta(days=1)).date()
    else:
        return order_time.date()


def get_business_hour(order_time):
    """
    Convert clock hour to business hour (0-23 where 0 = 6AM, 23 = 5AM next day)
    This helps visualize the full business day cycle starting from 6 AM.
    """
    if pd.isna(order_time):
        return None
    
    hour = order_time.hour
    # Shift hours so 6 AM = 0, 7 AM = 1, ..., 5 AM = 23
    business_hour = (hour - 6) % 24
    return business_hour


def get_business_hour_label(business_hour):
    """
    Convert business hour (0-23) back to clock time label.
    Business hour 0 = 6 AM, Business hour 23 = 5 AM
    """
    if pd.isna(business_hour):
        return None
    
    clock_hour = (int(business_hour) + 6) % 24
    if clock_hour == 0:
        return "12 AM"
    elif clock_hour < 12:
        return f"{clock_hour} AM"
    elif clock_hour == 12:
        return "12 PM"
    else:
        return f"{clock_hour - 12} PM"


# ==================== PREPROCESSING FUNCTIONS ====================

def preprocess_data(df):
    """
    Comprehensive preprocessing pipeline for sales orders data.
    
    Steps:
    1. Remove extra spaces from column names
    2. Drop columns with all null values
    3. Remove duplicates by 'Order No'
    4. Convert data types (dates, amounts)
    5. Add business date and business hour columns
    
    Returns:
        df: Processed DataFrame
        preprocessing_log: List of preprocessing steps performed
    """
    preprocessing_log = []
    
    # 1. Remove extra spaces from column names
    original_cols = df.columns.tolist()
    df.columns = df.columns.str.strip()
    renamed_cols = df.columns.tolist()
    if original_cols != renamed_cols:
        preprocessing_log.append("✅ Cleaned column names (removed extra spaces)")
    
    # 2. Drop columns where all values are null
    cols_before = len(df.columns)
    null_cols = df.columns[df.isnull().all()].tolist()
    df = df.dropna(axis=1, how='all')
    cols_after = len(df.columns)
    if cols_before != cols_after:
        preprocessing_log.append(f"✅ Dropped {cols_before - cols_after} columns with all null values")
    
    # 3. Check and remove duplicates by 'Order No'
    if 'Order No' in df.columns:
        dups_before = len(df)
        df = df.drop_duplicates(subset=['Order No'], keep='first')
        dups_after = len(df)
        dups_removed = dups_before - dups_after
        if dups_removed > 0:
            preprocessing_log.append(f"✅ Removed {dups_removed} duplicate orders")
        else:
            preprocessing_log.append("✅ No duplicate orders found")
    
    # 4. Convert data types
    # Convert Order Time to datetime
    if 'Order Time' in df.columns:
        df['Order Time'] = pd.to_datetime(df['Order Time'], format='%d-%b-%Y %I:%M %p', errors='coerce')
        valid_dates = df['Order Time'].notna().sum()
        preprocessing_log.append(f"✅ Converted 'Order Time' to datetime ({valid_dates} valid dates)")
    
    # Convert numeric columns
    numeric_columns = ['Order Amount', 'Tax', 'Amount Received', 'Amount Returned']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            preprocessing_log.append(f"✅ Converted '{col}' to numeric")
    
    # 5. Add business date and business hour columns
    if 'Order Time' in df.columns:
        df['Business Date'] = df['Order Time'].apply(get_business_date)
        df['Business Hour'] = df['Order Time'].apply(get_business_hour)
        df['Clock Hour'] = df['Order Time'].dt.hour
        df['Day of Week'] = df['Order Time'].dt.day_name()
        preprocessing_log.append("✅ Added Business Date column (day starts at 6 AM)")
        preprocessing_log.append("✅ Added Business Hour column (0=6AM, 23=5AM)")
    
    return df, preprocessing_log


# ==================== PAYMENT PROCESSING ====================

def parse_payments(payment_str):
    """
    Parse payment string to extract methods and amounts.
    
    Handles formats like:
    - 'MADA - 123.0'
    - 'Visa - 100.01, MADA - 199.0'
    - 'Cash - 75.02, Visa - 9.0, Mastercard - 115.0, MADA - 40.0'
    
    Returns:
        list of tuples: [(method, amount), ...]
    """
    if pd.isna(payment_str) or payment_str == '':
        return []
    
    payment_str = str(payment_str)
    payments = []
    
    # Split by comma
    parts = re.split(r',\s*', payment_str)
    
    for part in parts:
        part = part.strip().strip('"')
        # Match pattern: Method - Amount
        match = re.match(r'(.+?)\s*-\s*([\d.]+)', part)
        if match:
            method = match.group(1).strip()
            try:
                amount = float(match.group(2))
                payments.append((method, amount))
            except ValueError:
                continue
    
    return payments


def process_payments_column(df):
    """
    Process the Payments column to extract:
    - Number of payment methods used per order
    - Total amount per method
    - List of methods used
    
    Returns:
        DataFrame with payment details for each order
    """
    payment_details = []
    
    for idx, row in df.iterrows():
        payments = parse_payments(row.get('Payments', ''))
        num_methods = len(payments)
        total_paid = sum(amt for _, amt in payments)
        methods_used = list(set(method for method, _ in payments))
        
        payment_details.append({
            'Order No': row['Order No'],
            'Num_Payment_Methods': num_methods,
            'Total_Paid': total_paid,
            'Payment_Methods_Used': ', '.join(methods_used),
            'Payment_Details': payments
        })
    
    return pd.DataFrame(payment_details)


def get_payment_method_summary(df):
    """
    Get summary statistics for all payment methods.
    
    Returns:
        DataFrame with columns: Payment Method, Total Amount, Transaction Count
    """
    method_totals = {}
    method_counts = {}
    
    for idx, row in df.iterrows():
        payments = parse_payments(row.get('Payments', ''))
        for method, amount in payments:
            method_totals[method] = method_totals.get(method, 0) + amount
            method_counts[method] = method_counts.get(method, 0) + 1
    
    summary = pd.DataFrame({
        'Payment Method': list(method_totals.keys()),
        'Total Amount': list(method_totals.values()),
        'Transaction Count': [method_counts[m] for m in method_totals.keys()]
    })
    summary = summary.sort_values('Total Amount', ascending=False)
    return summary


# ==================== COMPLETE PREPROCESSING PIPELINE ====================

def run_full_preprocessing(df):
    """
    Run the complete preprocessing pipeline.
    
    Steps:
    1. Basic preprocessing (cleaning, type conversion)
    2. Payment column processing
    3. Merge payment details back to main dataframe
    
    Returns:
        df: Fully processed DataFrame
        payment_df: Payment details DataFrame
        preprocessing_log: List of steps performed
    """
    # Run basic preprocessing
    df, preprocessing_log = preprocess_data(df.copy())
    
    # Process payments
    payment_df = process_payments_column(df)
    preprocessing_log.append(f"✅ Processed payments for {len(payment_df)} orders")
    
    # Merge payment details
    df = df.merge(
        payment_df[['Order No', 'Num_Payment_Methods', 'Total_Paid', 'Payment_Methods_Used']], 
        on='Order No', 
        how='left'
    )
    
    # Count multi-payment orders
    multi_payment_count = (payment_df['Num_Payment_Methods'] > 1).sum()
    preprocessing_log.append(f"✅ Identified {multi_payment_count} orders with multiple payment methods")
    
    return df, payment_df, preprocessing_log


# ==================== DATA SPLITTING ====================

def split_orders_by_amount(df):
    """
    Split orders into paid orders (amount > 0) and zero-amount orders.
    
    Returns:
        paid_orders: DataFrame with Order Amount > 0
        zero_orders: DataFrame with Order Amount == 0
    """
    zero_orders = df[df['Order Amount'] == 0].copy()
    paid_orders = df[df['Order Amount'] > 0].copy()
    
    return paid_orders, zero_orders


# ==================== UTILITY FUNCTIONS ====================

def get_hour_labels_for_business_day():
    """
    Get ordered hour labels for a business day starting at 6 AM.
    Returns list of 24 labels from '6 AM' to '5 AM'
    """
    labels = []
    for i in range(24):
        clock_hour = (i + 6) % 24
        if clock_hour == 0:
            labels.append("12 AM")
        elif clock_hour < 12:
            labels.append(f"{clock_hour} AM")
        elif clock_hour == 12:
            labels.append("12 PM")
        else:
            labels.append(f"{clock_hour - 12} PM")
    return labels


def format_currency(value, currency="SAR"):
    """Format a number as currency."""
    return f"{currency} {value:,.2f}"


def format_percentage(value):
    """Format a number as percentage."""
    return f"{value:.1f}%"
