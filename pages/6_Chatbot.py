import json
import os

import streamlit as st
import requests

API_BASE_URL = "http://localhost:8000/api/v1"

st.write("# Welcome to SQLChat Assistant! 👋")

st.write(
    "Greetings! I'm your sql assistant.\n Together we can craft any sql query you want.")

# Check chatbot health first
try:
    health_response = requests.get(f"{API_BASE_URL}/chat/health", timeout=5)
    health_data = health_response.json()
    
    if not health_data.get("openai_configured", False):
        st.error("🔑 **OpenAI API Key Not Configured**")
        st.write("The chatbot functionality requires an OpenAI API key to work.")
        st.info("📖 Please check the **CHATBOT_SETUP.md** file for setup instructions.")
        
        with st.expander("Quick Setup Guide"):
            st.write("""
            **Option 1: Set Environment Variable (Windows PowerShell)**
            ```powershell
            $env:OPENAI_API_KEY="your_openai_api_key_here"
            ```
            
            **Option 2: Create .env file in project root**
            ```
            OPENAI_API_KEY=your_openai_api_key_here
            ```
            
            **Then restart both the API server and Streamlit app.**
            """)
        st.stop()
    
    elif health_data.get("status") == "healthy":
        st.success("✅ Chatbot is ready to use!")
    else:
        st.warning(f"⚠️ Chatbot status: {health_data.get('message', 'Unknown issue')}")
        
except Exception as e:
    st.error("❌ Cannot connect to chatbot API. Please ensure the API server is running.")
    st.stop()

session_name = st.text_input("Provide a name for your chat session")

streaming = st.sidebar.selectbox("Streaming", [True, False])

if session_name:
    messages = requests.get(f"{API_BASE_URL}/chat/history/{session_name}").json()
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["message"])

    prompt = st.chat_input("Type a message...")
    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)
        if streaming:
            res = requests.post(f"{API_BASE_URL}/chat/submit/{session_name}/streaming",
                                params={"request": prompt},
                                stream=True)
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""

                buffer = ""
                for chunk in res:
                    decoded_chunk = chunk.decode('utf-8')
                    buffer += decoded_chunk

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        parsed_chunk = json.loads(line.strip())
                        try:
                            full_response += parsed_chunk["raw_response"]["choices"][0]["delta"]["content"]
                            message_placeholder.markdown(full_response + "▌")
                        except KeyError:
                            pass

                message_placeholder.markdown(full_response)
        else:
            with st.spinner("..."):
                res = requests.post(f"{API_BASE_URL}/chat/submit/{session_name}",
                                    params={"request": prompt}).json()
                with st.chat_message("assistant"):
                    st.markdown(res)

        messages = requests.get(
            f"{API_BASE_URL}/chat/history/{session_name}").json()