# components/chat.py
import streamlit as st
from google.genai import types
from config import FACILITATOR_INSTRUCTION, ASSESSMENT_INSTRUCTION
from database import search_documents, log_study_interaction
from ai_services import get_embedding
from streamlit_mic_recorder import speech_to_text

# --- Callback function to handle text submission and clear the box ---
def submit_message():
    if st.session_state.text_input_box:
        # Save the typed message to a separate state variable
        st.session_state.submitted_prompt = st.session_state.text_input_box
        # Clear the input box safely
        st.session_state.text_input_box = ""

def render_chat(supabase, gemini_client, chat_model_name, embedding_model_name):
    # --- Custom CSS for the Text Input Border ---
    st.markdown("""
        <style>
        /* Target the Streamlit text input box to add a custom border */
        div[data-testid="stTextInput"] div[data-baseweb="input"] {
            border: 2px solid #4A90E2 !important; /* Change color here (currently a nice blue) */
            border-radius: 8px !important; /* Rounded corners */
            transition: border-color 0.3s ease-in-out;
        }
        /* Make the border change color slightly when clicked/focused */
        div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {
            border: 2px solid #2C3E50 !important; 
        }
        </style>
    """, unsafe_allow_html=True)

    # Initialize the submitted_prompt state if it doesn't exist
    if "submitted_prompt" not in st.session_state:
        st.session_state.submitted_prompt = ""

    if st.session_state.active_bot == "facilitator":
        st.subheader("👨‍🏫 I am Einstein Junior, your science teacher!")
    else:
        st.subheader("📝 I am the Assessment Bot!")
        
    # --- 1. Voice Input Language Selector (Moved to Sidebar) ---
    supported_languages = {
        "Cantonese (廣東話)": "yue-Hant-HK",
        "English": "en",
        "Mandarin (普通話)": "zh-CN",
        "Spanish": "es-ES"
    }
    
    st.sidebar.markdown("### ⚙️ Voice Input Settings")
    selected_lang_name = st.sidebar.selectbox(
        "Select your preferred language:",
        list(supported_languages.keys()),
        index=0
    )
    selected_lang_code = supported_languages[selected_lang_name]
    
    # --- 2. Scrollable Chat Container ---
    chat_container = st.container(height=500)
    
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # --- 3. Custom Input Row (Locked below the chat) ---
    input_container = st.container()
    
    with input_container:
        col1, col2 = st.columns([5, 1])
        
        with col1:
            # Added on_change callback to handle submission and clearing
            st.text_input(
                "Type your message...", 
                key="text_input_box", 
                label_visibility="collapsed",
                on_change=submit_message
            )
        
        with col2:
            voice_prompt = speech_to_text(
                language=selected_lang_code,
                start_prompt="🎙️ Speak",
                stop_prompt="🛑 Stop",
                just_once=True,
                key=f'voice_input_{selected_lang_code}'
            )

    # --- 4. Determine the prompt ---
    prompt = None
    # Check if a text message was submitted via the callback
    if st.session_state.submitted_prompt:
        prompt = st.session_state.submitted_prompt
        st.session_state.submitted_prompt = "" # Reset it after capturing
    # Otherwise, check if a voice message was recorded
    elif voice_prompt:
        prompt = voice_prompt

    # --- 5. Process the prompt ---
    if prompt:
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with chat_container:
            with st.spinner("Thinking..."):
                query_embedding = get_embedding(gemini_client, prompt, embedding_model_name)
                retrieved_chunks = search_documents(supabase, query_embedding) if query_embedding else []
                
                if retrieved_chunks:
                    context_texts = [chunk['content'] for chunk in retrieved_chunks]
                    current_rag_context = "\n\n---\n\n".join(context_texts)
                else:
                    current_rag_context = "No specific context found in the Knowledge Base."

        gemini_history = [
            types.Content(role="user" if msg["role"] == "user" else "model", parts=[types.Part.from_text(text=msg["content"])])
            for msg in st.session_state.messages[:-1]
        ]

        current_instruction = FACILITATOR_INSTRUCTION if st.session_state.active_bot == "facilitator" else ASSESSMENT_INSTRUCTION
        bot_name_context = "Einstein Junior (Facilitator)" if st.session_state.active_bot == "facilitator" else "Assessment Bot"

        augmented_prompt = f"You are {bot_name_context}. Use the following Knowledge Base to inform your response.\n\nKnowledge Base Context:\n{current_rag_context}\n\nStudent's Query:\n{prompt}"

        with chat_container:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                try:
                    chat_session = gemini_client.chats.create(
                        model=chat_model_name,
                        config=types.GenerateContentConfig(system_instruction=current_instruction),
                        history=gemini_history
                    )
                    
                    response_stream = chat_session.send_message_stream(augmented_prompt)
                    full_response = ""
                    for chunk in response_stream:
                        full_response += chunk.text
                        display_text = full_response.replace("[HANDOFF]", "").replace("[HANDBACK]", "")
                        message_placeholder.markdown(display_text + "▌")
                    
                    if "[HANDOFF]" in full_response:
                        clean_response = full_response.replace("[HANDOFF]", "").strip()
                        message_placeholder.markdown(clean_response)
                        st.session_state.messages.append({"role": "assistant", "content": clean_response})
                        
                        st.session_state.active_bot = "assessment"
                        handoff_greeting = "Hello! I am the Assessment Bot. Einstein Junior tells me you have a great understanding of aerodynamics! Would you like to take a 5-question quiz to test your knowledge?"
                        st.session_state.messages.append({"role": "assistant", "content": handoff_greeting})
                        st.rerun()
                        
                    elif "[HANDBACK]" in full_response:
                        clean_response = full_response.replace("[HANDBACK]", "").strip()
                        message_placeholder.markdown(clean_response)
                        st.session_state.messages.append({"role": "assistant", "content": clean_response})
                        
                        st.session_state.active_bot = "facilitator"
                        handback_greeting = "Hello again! I am Einstein Junior. I heard you just finished your assessment. How did you do? Are you ready to learn more about science?"
                        st.session_state.messages.append({"role": "assistant", "content": handback_greeting})
                        st.rerun()
                        
                    else:
                        message_placeholder.markdown(full_response)
                        st.session_state.messages.append({"role": "assistant", "content": full_response})
                    
                    log_study_interaction(supabase, st.session_state.user.id, prompt, full_response)
                    
                except Exception as e:
                    st.error(f"Error communicating with Gemini: {e}")