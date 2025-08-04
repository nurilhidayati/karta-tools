import streamlit as st
import requests

# Page config
st.set_page_config(
    page_title="Karta Tools",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS for styling
st.markdown("""
    <style>
    /* Main app background */
    .stApp {
        background-color: #F3F6FB;
    }
    
    /* Navbar/header */
    .css-1rs6os, .css-17ziqus, header[data-testid="stHeader"] {
        background-color: #F3F6FB !important;
    }
    
    /* Sidebar */
    .css-1d391kg, .css-1lcbmhc, section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
    }
    
    /* Text color */
    .stApp, .stApp p, .stApp div, .stApp span, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        color: #000000 !important;
    }
    
    /* Button styling for primary buttons */
    .stButton > button[kind="primary"] {
        background-color: #085A3E !important;
        border: 1px solid #085A3E !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #064229 !important;
        border: 1px solid #064229 !important;
        color: #FFFFFF !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(8, 90, 62, 0.3) !important;
    }
    
    .stButton > button[kind="primary"]:active {
        background-color: #053822 !important;
        border: 1px solid #053822 !important;
    }
    
    /* Feature card styling */
    .feature-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border-left: 4px solid #085A3E;
    }
    
    .feature-title {
        color: #085A3E !important;
        font-weight: bold;
        margin-bottom: 10px;
    }
    
    /* Status indicator */
    .status-indicator {
        padding: 10px;
        border-radius: 8px;
        margin: 10px 0;
        text-align: center;
        font-weight: bold;
    }
    
    .status-healthy {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    
    .status-unhealthy {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
    
    /* Hero section */
    .hero-section {
        text-align: center;
        padding: 40px 20px;
        background: linear-gradient(135deg, #F3F6FB 0%, #E8F0FE 100%);
        border-radius: 15px;
        margin-bottom: 30px;
    }
    
    .hero-title {
        font-size: 3rem;
        font-weight: bold;
        color: #085A3E !important;
        margin-bottom: 10px;
    }
    
    .hero-subtitle {
        font-size: 1.2rem;
        color: #666666 !important;
        margin-bottom: 20px;
    }
    

    </style>
""", unsafe_allow_html=True)

# Check API health
def check_api_health():
    """Check if the API server is running"""
    try:
        response = requests.get("http://localhost:8000/api/v1/geospatial/health", timeout=5)
        return response.status_code == 200
    except:
        return False

# Hero Section
st.markdown("""
    <div class="hero-section">
        <div class="hero-title">🌍 Karta Tools</div>
        <div class="hero-subtitle">Geospatial Analysis and Management Platform</div>
        <p style="color: #888; margin-top: 10px;">
            Powerful tools for campaign planning, geospatial analysis, and data conversion
        </p>
    </div>
""", unsafe_allow_html=True)

# API Status Check
api_healthy = check_api_health()
if api_healthy:
    st.markdown("""
        <div class="status-indicator status-healthy">
            ✅ API Server is Running - All features available
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <div class="status-indicator status-unhealthy">
            ❌ API Server is not running - Some features may be limited
        </div>
    """, unsafe_allow_html=True)

# Main Navigation Section
st.markdown("## 🚀 Quick Access")

# Create navigation buttons using columns
col1, col2 = st.columns(2)

with col1:
    # Campaign Preparation Button
    st.markdown("""
        <div style="margin-bottom: 15px;">
            <div style="background: linear-gradient(135deg, #085A3E 0%, #0a6b47 100%); 
                        color: white; border-radius: 12px; padding: 25px; text-align: center;
                        box-shadow: 0 4px 15px rgba(8, 90, 62, 0.3); margin: 10px 0;">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">📋</div>
                <div style="font-size: 1.1rem; font-weight: bold; margin-bottom: 8px;">Campaign Preparation</div>
                <div style="font-size: 0.9rem; opacity: 0.9;">Complete geospatial workflow, budget forecasting, and campaign planning</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚀 Launch Campaign Preparation", key="nav_campaigns_prep", type="primary", use_container_width=True):
        st.switch_page("pages/1_Campaigns_Preparation.py")

with col2:
    # Campaign Evaluation Button
    st.markdown("""
        <div style="margin-bottom: 15px;">
            <div style="background: linear-gradient(135deg, #085A3E 0%, #0a6b47 100%); 
                        color: white; border-radius: 12px; padding: 25px; text-align: center;
                        box-shadow: 0 4px 15px rgba(8, 90, 62, 0.3); margin: 10px 0;">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">📊</div>
                <div style="font-size: 1.1rem; font-weight: bold; margin-bottom: 8px;">Campaign Evaluation</div>
                <div style="font-size: 0.9rem; opacity: 0.9;">Download geohash data, analyze regions, and evaluate campaigns</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("📥 Open Campaign Evaluation", key="nav_campaigns_eval", type="primary", use_container_width=True):
        st.switch_page("pages/2_Campaigns_Evaluation.py")

col3, col4 = st.columns(2)

with col3:
    # Tools Add-On Button
    st.markdown("""
        <div style="margin-bottom: 15px;">
            <div style="background: linear-gradient(135deg, #085A3E 0%, #0a6b47 100%); 
                        color: white; border-radius: 12px; padding: 25px; text-align: center;
                        box-shadow: 0 4px 15px rgba(8, 90, 62, 0.3); margin: 10px 0;">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">🛠️</div>
                <div style="font-size: 1.1rem; font-weight: bold; margin-bottom: 8px;">Tools Add-On</div>
                <div style="font-size: 0.9rem; opacity: 0.9;">File conversion, boundary to geohash, and data format tools</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔧 Access Tools Add-On", key="nav_tools_addon", type="primary", use_container_width=True):
        st.switch_page("pages/3_Tools_Add_On.py")

with col4:
    # About Us Button
    st.markdown("""
        <div style="margin-bottom: 15px;">
            <div style="background: linear-gradient(135deg, #085A3E 0%, #0a6b47 100%); 
                        color: white; border-radius: 12px; padding: 25px; text-align: center;
                        box-shadow: 0 4px 15px rgba(8, 90, 62, 0.3); margin: 10px 0;">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">👥</div>
                <div style="font-size: 1.1rem; font-weight: bold; margin-bottom: 8px;">About Us</div>
                <div style="font-size: 0.9rem; opacity: 0.9;">Team information, documentation, and project details</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("👋 Meet the Team", key="nav_about_us", type="primary", use_container_width=True):
        st.switch_page("pages/4_About_Us.py")

# Features Overview
st.markdown("---")
st.markdown("## 🎯 Key Features")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
        <div class="feature-card">
            <div class="feature-title">🗺️ Geospatial Workflow</div>
            <p>Complete automation from boundary selection to road network analysis with geohash precision.</p>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
        <div class="feature-card">
            <div class="feature-title">💰 Budget Forecasting</div>
            <p>Accurate cost estimation with multi-currency support and real-time calculations.</p>
        </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
        <div class="feature-card">
            <div class="feature-title">🔄 Data Conversion</div>
            <p>Seamless conversion between GeoJSON, CSV, KML, and Shapefile formats.</p>
        </div>
    """, unsafe_allow_html=True)

# Quick Start Guide
st.markdown("---")
st.markdown("## 🚀 Quick Start Guide")

with st.expander("🔍 How to get started", expanded=False):
    st.markdown("""
    ### Step 1: Campaign Preparation
    1. Click on **Campaign Preparation** above
    2. Select your country and region
    3. Configure analysis parameters
    4. Generate your complete campaign plan
    
    ### Step 2: Campaign Evaluation  
    1. Access **Campaign Evaluation** for data downloads
    2. Select regions for geohash generation
    3. Download GeoJSON and CSV files
    
    ### Step 3: Use Additional Tools
    1. Visit **Tools Add-On** for file conversions
    2. Convert between different geospatial formats
    3. Process boundary files to geohash
    
    ### Step 4: Learn More
    1. Check **About Us** for team information
    2. Access documentation and resources
    """)

# System Requirements
with st.expander("⚙️ System Requirements", expanded=False):
    st.markdown("""
    ### API Server Requirements
    - FastAPI backend running on `localhost:8000`
    - PostgreSQL database with geospatial extensions
    - Required API endpoints for geospatial processing
    
    ### Browser Compatibility
    - Modern web browsers (Chrome, Firefox, Safari, Edge)
    - JavaScript enabled for interactive maps
    - Stable internet connection for API calls
    """)

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
