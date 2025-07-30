import streamlit as st
import requests
import pandas as pd
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
from io import BytesIO
from config import settings
import math


# === PAGE CONFIG ===
st.set_page_config(page_title="💱 Forecast & Currency Converter", layout="centered")

# === CSS STYLING ===
st.markdown("""
    <style>
    .title {
        text-align: center;
        font-size: 36px;
        font-weight: bold;
        color: #f1c40f;
    }
    .result-box {
        background-color: #1e1e2f;
        border: 1px solid #444;
        border-radius: 10px;
        padding: 15px;
        margin-top: 10px;
        color: white;
    }
    .country-info {
        background-color: #e8f4fd;
        border-left: 5px solid #2196F3;
        padding: 10px;
        margin: 10px 0;
        border-radius: 5px;
    }
    .stButton button {
        background-color: #f1c40f;
        color: black;
        font-weight: bold;
        border-radius: 8px;
    }
    .stButton button:hover {
        background-color: #f39c12;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# === COUNTRY DATA FUNCTIONS ===
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_countries_pricing():
    """Get all countries with their pricing information from API"""
    try:
        api_url = f"http://{settings.API_HOST}:{settings.API_PORT}/api/v1/country/pricing"
        response = requests.get(api_url, timeout=30)
        
        if response.status_code == 200:
            countries = response.json()
            if countries and len(countries) > 0:
                # Map API field names to simplified names
                mapped_countries = []
                for country in countries:
                    mapped_country = {
                        "id": country.get("id"),
                        "name": country.get("name"),
                        "currency": country.get("currency"),
                        "currency_symbol": country.get("currency_symbol"),
                        "ukm_price": country.get("ukm_price"),
                        "insurance": country.get("insurance_per_dax_per_month", country.get("insurance", 0)),
                        "dataplan": country.get("dataplan_per_dax_per_month", country.get("dataplan", 0)),
                        "exchange_rate_to_usd": country.get("exchange_rate_to_usd")
                    }
                    mapped_countries.append(mapped_country)
                return mapped_countries
            else:
                return get_fallback_countries()
        else:
            return get_fallback_countries()
            
    except:
        return get_fallback_countries()

def get_fallback_countries():
    """Fallback country data when API is unavailable"""
    return [
        {
            "id": 1,
            "name": "Indonesia",
            "currency": "IDR",
            "currency_symbol": "Rp",
            "ukm_price": 8000.0,
            "insurance": 132200.0,
            "dataplan": 450000.0,
            "exchange_rate_to_usd": 0.000063
        },
        {
            "id": 2,
            "name": "Malaysia", 
            "currency": "MYR",
            "currency_symbol": "RM",
            "ukm_price": 2.0,
            "insurance": 35.0,
            "dataplan": 120.0,
            "exchange_rate_to_usd": 0.22
        },
        {
            "id": 3,
            "name": "Thailand",
            "currency": "THB", 
            "currency_symbol": "฿",
            "ukm_price": 90.0,
            "insurance": 1200.0,
            "dataplan": 4000.0,
            "exchange_rate_to_usd": 0.029
        },
        {
            "id": 4,
            "name": "United States",
            "currency": "USD",
            "currency_symbol": "$", 
            "ukm_price": 0.25,
            "insurance": 8.5,
            "dataplan": 30.0,
            "exchange_rate_to_usd": 1.0
        }
    ]

@st.cache_data(ttl=3600)
def get_exchange_rates():
    """Get real-time exchange rates"""
    try:
        response = requests.get("https://api.exchangerate-api.com/v4/latest/USD")
        response.raise_for_status()
        data = response.json()
        return {
            "rates": data.get("rates", {}),
            "last_updated": data.get("date", "Unknown"),
            "success": True
        }
    except Exception as e:
        st.warning(f"Failed to get real-time exchange rates. Using fallback. Error: {str(e)}")
        return {
            "rates": {"IDR": 15800, "MYR": 4.5, "THB": 34.5, "USD": 1.0},
            "last_updated": "Fallback",
            "success": False
        }

def format_currency(amount, currency="USD", symbol="$"):
    """Format currency with proper symbol and decimal places"""
    if currency in ["IDR"]:
        return f"{symbol} {amount:,.0f}"
    else:
        return f"{symbol} {amount:,.2f}"

def convert_currency(amount, from_rate, to_rate):
    """Convert between currencies using exchange rates"""
    # Convert to USD first, then to target currency
    usd_amount = amount * from_rate
    return usd_amount / to_rate

# === APP HEADER ===
st.markdown('<div class="title">💱 Multi-Country Forecast & Currency Converter</div>', unsafe_allow_html=True)

# === LOAD COUNTRY DATA ===
countries_data = get_countries_pricing()
exchange_rates = get_exchange_rates()

if not countries_data:
    st.error("❌ Unable to load country data. Please check API connection.")
    st.stop()

# Create country lookup dictionaries
country_dict = {country['name']: country for country in countries_data}
country_names = list(country_dict.keys())

# === COUNTRY SELECTION ===
st.subheader("🌍 Select Country")

selected_country_name = st.selectbox(
    "Choose Country:",
    options=country_names,
    index=0 if country_names else None,
    key="country_selector"
)

if selected_country_name:
    selected_country = country_dict[selected_country_name]
    currency = selected_country['currency']
    symbol = selected_country['currency_symbol']
    
    # Get exchange rate
    real_time_rate = exchange_rates['rates'].get(currency)
    if real_time_rate:
        usd_to_local = real_time_rate
    else:
        stored_rate = selected_country['exchange_rate_to_usd']
        usd_to_local = 1 / stored_rate if stored_rate > 0 else 1
    
    # === USD CONVERSION DISPLAY ===
    st.subheader("💱 Exchange Rate")
    
    if currency == "USD":
        st.info("💵 **1 USD = $1.00 USD** (Base currency)")
    else:
        st.success(f"💰 **1 USD = {format_currency(usd_to_local, currency, symbol)}**")

# === FORECAST FUNCTION ===
def forecast_budget_simple(target_km, dax_number, country_data):
    """Calculate forecast budget using country pricing with automatic week to month calculation"""
    # First calculate week estimation using formula: target_km / (dax_count * 100)
    week_estimation = target_km / (dax_number * 100)
    
    # Then convert to months using ceiling (always round up any fraction)
    month_estimation = math.ceil(week_estimation / 4)
    
    # Ensure minimum 1 month
    if month_estimation < 1:
        month_estimation = 1
    
    ukm_price = country_data['ukm_price']
    insurance_rate = country_data['insurance']
    dataplan_rate = country_data['dataplan']
    currency = country_data['currency']
    currency_symbol = country_data['currency_symbol']
    stored_rate = country_data['exchange_rate_to_usd']
    
    # Get real-time exchange rate if available
    real_time_rate = exchange_rates['rates'].get(currency)
    if real_time_rate:
        local_to_usd = 1 / real_time_rate
    else:
        local_to_usd = stored_rate
    
    basic_incentive = target_km * ukm_price
    bonus_coverage = basic_incentive
    insurance = insurance_rate * dax_number * month_estimation
    dataplan = dataplan_rate * dax_number * month_estimation
    
    total_before_misc = basic_incentive + bonus_coverage + insurance + dataplan
    miscellaneous = total_before_misc * 0.05
    total_forecast = total_before_misc + miscellaneous
    total_forecast_usd = total_forecast * local_to_usd
    
    return {
        "Week Estimation": round(week_estimation, 2),
        "Month Estimation": month_estimation,
        "Basic Incentive": round(basic_incentive),
        ">95% Bonus Coverage": round(bonus_coverage),
        "Insurance": round(insurance),
        "Dataplan": round(dataplan),
        "Miscellaneous (5%)": round(miscellaneous),
        "Total Forecast Budget": round(total_forecast),
        "Total Forecast Budget (USD)": round(total_forecast_usd, 2),
        "Currency": currency,
        "Symbol": currency_symbol,
        "Country": country_data['name']
    }

# === BULK FORECAST ===
st.subheader("📂 Bulk Forecast from CSV")
st.info("📋 CSV should contain: city, target_km, dax_number, country_name")

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
if uploaded_file and selected_country_name:
    df = pd.read_csv(uploaded_file)
    required_cols = {'city', 'target_km', 'dax_number'}
    
    if required_cols.issubset(df.columns):
        st.success("✅ File loaded.")

        # List untuk menyimpan hasil forecast
        forecast_results = []
        for idx, row in df.iterrows():
            # Use country from CSV if available, otherwise use selected country
            if 'country_name' in df.columns and pd.notna(row['country_name']):
                country_name = row['country_name']
                if country_name in country_dict:
                    country_data = country_dict[country_name]
                else:
                    st.warning(f"⚠️ Country '{country_name}' not found for {row['city']}. Using {selected_country_name}.")
                    country_data = selected_country
            else:
                country_data = selected_country
            
            # Calculate forecast (month automatically calculated)
            result = forecast_budget_simple(
                target_km=row['target_km'],
                dax_number=int(row['dax_number']),
                country_data=country_data
            )
            
            forecast_results.append({
                "City": row['city'],
                "Country": result["Country"],
                "Currency": result["Currency"],
                "UKM Target": row['target_km'],
                "DAX Count": row['dax_number'],
                "Week Estimation": result["Week Estimation"],
                "Duration (Months)": result["Month Estimation"],
                "Basic Incentive": result["Basic Incentive"],
                ">95% Bonus Coverage": result[">95% Bonus Coverage"],
                "Insurance": result["Insurance"],
                "Data Plan": result["Dataplan"],
                "Miscellaneous (5%)": result["Miscellaneous (5%)"],
                f"Estimation Incentive ({result['Currency']})": result["Total Forecast Budget"],
                "Estimation Incentive (USD)": result["Total Forecast Budget (USD)"]
            })

        df_forecast = pd.DataFrame(forecast_results)

        # === Export Files ===
        output_excel = BytesIO()
        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
            df_forecast.to_excel(writer, index=False, sheet_name="Forecast")
        output_excel.seek(0)

        csv_data = df_forecast.to_csv(index=False)

        # === Download Buttons ===
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Download Forecast Excel",
                data=output_excel,
                file_name=f"forecast_budget_{selected_country_name.lower()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with col2:
            st.download_button(
                label="📥 Download Forecast CSV",
                data=csv_data,
                file_name=f"forecast_budget_{selected_country_name.lower()}.csv",
                mime="text/csv"
            )

    else:
        st.error("⚠️ CSV must contain columns: city, target_km, dax_number")

# === MANUAL INPUT FORECAST ===
if selected_country_name:
    st.subheader("🧮 Manual Forecast Calculator")
    col1, col2 = st.columns([1, 1.2])

    with col1:
        with st.form("manual_forecast"):
            st.markdown("#### 🔧 Input Parameters")
            target_km = st.number_input("📏 Target KM", min_value=0.0, step=100.0)
            dax_number = st.number_input("👷 DAX count", min_value=1, step=1)
            
            # Show calculated duration
            if target_km > 0 and dax_number > 0:
                calculated_weeks = target_km / (dax_number * 100)
                calculated_months = math.ceil(calculated_weeks / 4)
                # Ensure minimum 1 month
                if calculated_months < 1:
                    calculated_months = 1
                st.info(f"📅 Week estimation: {calculated_weeks:.2f} weeks")
                st.info(f"📅 Duration (round up): {calculated_months} months")
            
            submitted = st.form_submit_button("🧮 Calculate")

    with col2:
        if submitted:
            result = forecast_budget_simple(target_km, dax_number, selected_country)
                
            st.markdown("#### 📈 Forecast Result")
            
            # Bullet list
            bullets = ""
            for k, v in result.items():
                if "Total Forecast Budget" in k or "USD" in k or k in ["Currency", "Symbol", "Country"]:
                    continue
                elif "Week" in k:
                    bullets += f"- **{k}**: {v} weeks\n"
                elif "Month" in k:
                    bullets += f"- **{k}**: {v} months\n"
                else:
                    bullets += f"- **{k}**: {format_currency(v, result['Currency'], result['Symbol'])}\n"
            st.markdown(bullets)
            
            # Highlight Total
            st.markdown(f"""
                <div class="result-box">
                <strong>Total Forecast Budget ({result['Country']}):</strong> {format_currency(result['Total Forecast Budget'], result['Currency'], result['Symbol'])} &nbsp;&nbsp;|&nbsp;&nbsp;
                <strong>USD:</strong> ${result['Total Forecast Budget (USD)']:,.2f}
                </div>
            """, unsafe_allow_html=True)

# Footer
st.markdown(
    """
    <hr style="margin-top: 2rem; margin-bottom: 1rem;">
    <div style='text-align: center; color: grey; font-size: 0.9rem;'>
        © 2025 ID Karta IoT Team 
    </div>
    """,
    unsafe_allow_html=True
) 