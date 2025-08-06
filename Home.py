import streamlit as st
import requests

# Page config
st.set_page_config(
    page_title="SMOOTH",
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
    
    .stButton > button[kind="primary"] * {
        color: #FFFFFF !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #064229 !important;
        border: 1px solid #064229 !important;
        color: #FFFFFF !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(8, 90, 62, 0.3) !important;
    }
    
    .stButton > button[kind="primary"]:hover * {
        color: #FFFFFF !important;
    }
    
    .stButton > button[kind="primary"]:active {
        background-color: #053822 !important;
        border: 1px solid #053822 !important;
        color: #FFFFFF !important;
    }
    
    .stButton > button[kind="primary"]:active * {
        color: #FFFFFF !important;
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



st.markdown("<h1 style='text-align: center; color: #000000;'>SMOOTH</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #666666; font-weight: normal; margin-top: -10px;'>(Smart Map Operations Tool Hub)</h3>", unsafe_allow_html=True)

# Create navigation buttons using columns
col1, col2 = st.columns(2)

with col1:
    # Campaign Preparation Button
    st.markdown("""
        <div style="margin-bottom: 15px;">
            <div style="background: white; 
                        color: #000000; border-radius: 12px; padding: 25px; text-align: center;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin: 10px 0;
                        border-left: 4px solid #085A3E;">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">📋</div>
                <div style="font-size: 1.1rem; font-weight: bold; margin-bottom: 8px; color: #085A3E;">Campaign Preparation</div>
                <div style="font-size: 0.9rem; opacity: 0.8;">Generate Geohash → Smart Define Targets → Calculate Target UKM → Forecast Budget</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("Campaign Preparation", key="nav_campaigns_prep", type="primary", use_container_width=True):
        st.switch_page("pages/1_Campaigns_Preparation.py")

with col2:
    # Campaign Evaluation Button
    st.markdown("""
        <div style="margin-bottom: 15px;">
            <div style="background: white; 
                        color: #000000; border-radius: 12px; padding: 25px; text-align: center;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin: 10px 0;
                        border-left: 4px solid #085A3E;">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">📊</div>
                <div style="font-size: 1.1rem; font-weight: bold; margin-bottom: 8px; color: #085A3E;">Campaign Evaluation</div>
                <div style="font-size: 0.9rem; opacity: 0.8;">Compare Targeted UKM Plan vs Actual UKM → Gap Analysis → Smarter Decisions</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("Campaign Evaluation", key="nav_campaigns_eval", type="primary", use_container_width=True):
        st.switch_page("pages/2_Campaigns_Evaluation.py")

col3, col4 = st.columns(2)

with col3:
    # Tools Add-On Button
    st.markdown("""
        <div style="margin-bottom: 15px;">
            <div style="background: white; 
                        color: #000000; border-radius: 12px; padding: 25px; text-align: center;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin: 10px 0;
                        border-left: 4px solid #085A3E;">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">🛠️</div>
                <div style="font-size: 1.1rem; font-weight: bold; margin-bottom: 8px; color: #085A3E;">Tools Add-On</div>
                <div style="font-size: 0.9rem; opacity: 0.8;">All-in-One Converter Tool from Area to Geohash, Geohash to CSV, and CSV to Geohash</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("Tools Add-On", key="nav_tools_addon", type="primary", use_container_width=True):
        st.switch_page("pages/3_Tools_Add_On.py")

with col4:
    # About Us Button
    st.markdown("""
        <div style="margin-bottom: 15px;">
            <div style="background: white; 
                        color: #000000; border-radius: 12px; padding: 25px; text-align: center;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin: 10px 0;
                        border-left: 4px solid #085A3E;">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">👥</div>
                <div style="font-size: 1.1rem; font-weight: bold; margin-bottom: 8px; color: #085A3E;">About Us</div>
                <div style="font-size: 0.9rem; opacity: 0.8;">Meet the team, read docs, and explore the project</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("Meet the Team", key="nav_about_us", type="primary", use_container_width=True):
        st.switch_page("pages/4_About_Us.py")


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
