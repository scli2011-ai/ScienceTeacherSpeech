# database.py
import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def search_documents(supabase: Client, query_embedding: list[float], match_threshold=0.7, match_count=2):
    try:
        response = supabase.rpc(
            'match_document_chunks',
            {
                'query_embedding': query_embedding,
                'match_threshold': match_threshold,
                'match_count': match_count
            }
        ).execute()
        return response.data
    except Exception as e:
        st.error(f"Error searching documents: {e}")
        return []

def log_study_interaction(supabase: Client, user_id: str, query: str, response: str):
    try:
        supabase.table("study_logs").insert({
            "participant_id": user_id,
            "user_query": query,
            "bot_response": response,
        }).execute()
    except Exception as db_log_error:
        st.error(f"Failed to save log to database: {db_log_error}")