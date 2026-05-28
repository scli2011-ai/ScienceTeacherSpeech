# app.py
import streamlit as st
from database import init_supabase
from ai_services import get_genai_client, get_valid_gemini_model, get_valid_embedding_model
from components.auth import render_auth_tabs
from components.chat import render_chat

# --- SESSION STATE SETUP ---
if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_bot" not in st.session_state:
    st.session_state.active_bot = "facilitator"

# --- INITIALIZATION ---
supabase = init_supabase()
gemini_client = get_genai_client()

chat_model_name = get_valid_gemini_model(gemini_client) if gemini_client else None
embedding_model_name = get_valid_embedding_model(gemini_client) if gemini_client else None

# --- SIDEBAR ---
with st.sidebar:
    st.title("My AI RAG App")
    if st.session_state.user:
        st.success(f"Logged in as: {st.session_state.user.email}")
        st.info(f"Current Mode: {'👨‍🏫 Facilitator' if st.session_state.active_bot == 'facilitator' else '📝 Assessment'}")
        
        if st.button("Log Out"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.session_state.messages = []
            st.session_state.active_bot = "facilitator"
            st.rerun()
    else:
        st.warning("You are not logged in.")

# --- MAIN APP LOGIC ---
st.title("Welcome to the Future Science Classroom")

if not st.session_state.user:
    render_auth_tabs(supabase)
else:
    if not chat_model_name or not gemini_client:
        st.error("Cannot start chat because no compatible Gemini models were found for your API key.")
    else:
        render_chat(supabase, gemini_client, chat_model_name, embedding_model_name)

