# components/chat.py
import streamlit as st
from google.genai import types
from config import FACILITATOR_INSTRUCTION, ASSESSMENT_INSTRUCTION
from database import search_documents, log_study_interaction
from ai_services import get_embedding
from streamlit_mic_recorder import speech_to_text

def render_chat(supabase, gemini_client, chat_model_name, embedding_model_name):
    if st.session_state.active_bot == "facilitator":
        st.subheader("👨‍🏫 I am Einstein Junior, your science teacher!")
    else:
        st.subheader("📝 I am the Assessment Bot!")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- Custom Input Row ---
    # Create a container at the bottom for our custom input row
    input_container = st.container()
    
    with input_container:
        # Create columns: one for text input, one for the mic button
        col1, col2 = st.columns([5, 1])
        
        with col1:
            # We use standard text_input instead of chat_input to allow side-by-side layout
            text_prompt = st.text_input("Type your message...", key="text_input_box", label_visibility="collapsed")
        
        with col2:
            # The mic button will now appear right next to the text box
            voice_prompt = speech_to_text(
                language='en',
                start_prompt="🎙️ Speak",
                stop_prompt="🛑 Stop",
                just_once=True,
                key='voice_input'
            )

    # Combine inputs: Check if the user typed and pressed enter, OR if they spoke
    prompt = text_prompt or voice_prompt

    if prompt:
        # Clear the text input box safely if the user typed something
        if text_prompt and "text_input_box" in st.session_state:
            st.session_state["text_input_box"] = ""
            
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

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
                    # Hide both HANDOFF and HANDBACK tokens from the UI while streaming
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