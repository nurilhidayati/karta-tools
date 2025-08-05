import streamlit as st
import json
import folium
from streamlit_folium import st_folium
import os
import numpy as np
from shapely.geometry import shape, GeometryCollection, box, Polygon
from shapely.validation import make_valid
import geohash2
import pandas as pd
import requests



# API Configuration
API_BASE_URL = "http://localhost:8000/api/v1"

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
    
    /* File uploader drag and drop area */
    .stFileUploader > div > div > div > div {
        background-color: #FFFFFF !important;
    }
    
    /* File uploader drag and drop zone */
    div[data-testid="stFileUploader"] > div > div > div {
        background-color: #FFFFFF !important;
    }
    
    /* File uploader section */
    section[data-testid="stFileUploader"] {
        background-color: #FFFFFF !important;
    }
    
    /* Upload area styling */
    .css-1cpxqw2, .css-1erivf3, .css-1v0mbdj {
        background-color: #FFFFFF !important;
    }
    
    /* Map container optimization - Force white background */
    .streamlit-folium {
        width: 100% !important;
        background-color: #FFFFFF !important;
    }
    
    /* Map iframe styling - Remove black background */
    iframe[title="streamlit_folium.st_folium"] {
        width: 100% !important;
        border-radius: 8px !important;
        border: 1px solid #E0E0E0 !important;
        background-color: #FFFFFF !important;
    }
    
    /* Force map container backgrounds to white */
    div[data-testid="stIFrame"] {
        background-color: #FFFFFF !important;
    }
    
    /* Remove any black backgrounds from map containers */
    .stApp iframe,
    .stApp iframe body,
    .stApp .leaflet-container {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
    }
    
    /* Force all map related elements to white background */
    .leaflet-container,
    .leaflet-tile-pane,
    .leaflet-map-pane {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
    }
    
    /* CRITICAL: Fix black space below map */
    /* Force iframe height to match content exactly */
    iframe[title="streamlit_folium.st_folium"] {
        height: 500px !important;
        max-height: 500px !important;
        min-height: 500px !important;
        overflow: hidden !important;
        background-color: #FFFFFF !important;
    }
    
    /* Remove any extra space below iframe */
    div[data-testid="stIFrame"] {
        height: auto !important;
        max-height: 520px !important;
        overflow: hidden !important;
        background-color: #FFFFFF !important;
    }
    
    /* Force container to not expand beyond content */
    .streamlit-folium {
        height: auto !important;
        max-height: 520px !important;
        overflow: hidden !important;
        background-color: #FFFFFF !important;
    }
    
    /* Remove margin/padding that might cause black space */
    .stApp iframe[title="streamlit_folium.st_folium"] {
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
        background-color: #FFFFFF !important;
    }
    
    /* Target any black backgrounds specifically */
    .stApp [style*="background: black"],
    .stApp [style*="background-color: black"], 
    .stApp [style*="background: #000"],
    .stApp [style*="background-color: #000000"] {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    /* Download button styling - GREEN THEME */
    .stDownloadButton > button {
        background-color: #085A3E !important;
        color: #FFFFFF !important;
        border: 1px solid #085A3E !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
    }
    
    .stDownloadButton > button:hover {
        background-color: #064229 !important;
        color: #FFFFFF !important;
        border: 1px solid #064229 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(8, 90, 62, 0.3) !important;
    }
    
    .stDownloadButton > button:active {
        background-color: #053822 !important;
        border: 1px solid #053822 !important;
    }
    
    /* Force download button text to be white */
    .stDownloadButton > button * {
        color: #FFFFFF !important;
    }
    
    .stDownloadButton > button span {
        color: #FFFFFF !important;
    }
    
    .stDownloadButton > button div {
        color: #FFFFFF !important;
    }
    
    .stDownloadButton > button p {
        color: #FFFFFF !important;
    }
    
    /* Alternative download button selectors */
    button[data-testid="baseButton-secondary"] {
        background-color: #085A3E !important;
        color: #FFFFFF !important;
        border: 1px solid #085A3E !important;
        font-weight: 600 !important;
    }
    
    button[data-testid="baseButton-secondary"]:hover {
        background-color: #064229 !important;
        color: #FFFFFF !important;
        border: 1px solid #064229 !important;
    }
    
    button[data-testid="baseButton-secondary"] * {
        color: #FFFFFF !important;
    }
    
    /* Force all download-related buttons */
    .stApp button[kind="secondary"] {
        background-color: #085A3E !important;
        color: #FFFFFF !important;
        border: 1px solid #085A3E !important;
    }
    
    .stApp button[kind="secondary"]:hover {
        background-color: #064229 !important;
        color: #FFFFFF !important;
    }
    
    .stApp button[kind="secondary"] * {
        color: #FFFFFF !important;
    }
    </style>
""", unsafe_allow_html=True)



# Setup
st.set_page_config(layout="wide")

# Navigation header
st.markdown("<h1 style='text-align: center; color: #000000;'>Campaign Evaluation</h1>", unsafe_allow_html=True)


