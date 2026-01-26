# Tesh Lounge - Sales Orders Analysis

A comprehensive sales analysis dashboard for Tesh Lounge, built with Streamlit.

## 🕐 Business Day Logic

- **Business day starts at 6:00 AM**
- Orders from 12:00 AM - 5:59 AM belong to the **previous business day**
- 24-hour operation support

## 📁 Project Structure

```
tesh_sales_analysis/
├── app.py              # Main Streamlit application
├── preprocessing.py    # Data preprocessing module
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## 🚀 Features

### 1. Data Preprocessing
- Automatic column name cleaning
- Duplicate order removal
- Data type conversion
- Business date/hour calculation
- Payment method parsing

### 2. Orders Insights
- Total orders, revenue, average order value
- Order type distribution (Dine-In, Walk-In)
- Rush hours analysis (24-hour cycle starting 6 AM)
- Daily and weekly patterns
- Zero amount orders tracking

### 3. Payment Analysis
- Revenue by payment method (MADA, Visa, Cash, etc.)
- Transaction counts
- Multi-payment order analysis
- Detailed payment summary

### 4. Staff Performance
- Orders and revenue per staff
- Performance matrix (scatter plot)
- Hourly activity heatmap
- Staff contribution percentages

## 📊 Expected CSV Format

| Column | Description |
|--------|-------------|
| Order No | Unique order identifier |
| Order Time | DD-Mon-YYYY HH:MM AM/PM |
| Order Type | Dine-In, Walk-In, etc. |
| Order Taken By | Staff member name |
| Order Amount | Total value (tax included) |
| Payments | Method - Amount (e.g., "MADA - 123.0") |
| Notes | Additional notes |

## 🖥️ Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## ☁️ Streamlit Cloud Deployment

1. Push this code to a GitHub repository
2. Go to [Streamlit Cloud](https://streamlit.io/cloud)
3. Create a new app and connect your GitHub repo
4. Set the main file path to `app.py`
5. Deploy!

## 📝 License

Internal use only - Tesh Lounge
