# ai_services.py
import streamlit as st
from google import genai
from google.genai import types
from config import PREFERRED_CHAT_MODELS

@st.cache_resource
def get_genai_client():
    try:
        return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except Exception as e:
        st.error(f"Failed to initialize Gemini client: {e}")
        return None

@st.cache_resource
def get_valid_gemini_model(_client):
    if not _client:
        return None
        
    available_models = []
    for m in _client.models.list():
        if m.supported_actions and 'generateContent' in m.supported_actions:
            name = m.name.replace('models/', '')
            available_models.append(name)
            
    if not available_models:
        raise ValueError("Your API key does not have access to any text generation models.")
        
    selected_model_name = available_models[0]
    for pref in PREFERRED_CHAT_MODELS:
        if pref in available_models:
            selected_model_name = pref
            break
            
    return selected_model_name

@st.cache_resource
def get_valid_embedding_model(_client):
    if not _client:
        return None
        
    available_embedding_models = []
    for m in _client.models.list():
        if m.supported_actions and 'embedContent' in m.supported_actions:
            name = m.name.replace('models/', '')
            available_embedding_models.append(name)
            
    if not available_embedding_models:
        available_embedding_models = ['text-embedding-004']
        
    working_models = [m for m in available_embedding_models if "text-embedding-004" not in m]
    
    return working_models[-1] if working_models else available_embedding_models[0]

def get_embedding(client, text: str, model_name: str) -> list[float]:
    if not client:
        return []
    try:
        response = client.models.embed_content(
            model=model_name, 
            contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
        )
        return response.embeddings[0].values
    except Exception as e:
        st.error(f"Error generating embedding: {e}")
        return []