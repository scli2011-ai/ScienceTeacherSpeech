# components/auth.py
import streamlit as st

def render_auth_tabs(supabase):
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        st.header("Login")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password", autocomplete="off")
        
        if st.button("Login"):
            try:
                response = supabase.auth.sign_in_with_password({
                    "email": login_email, 
                    "password": login_password
                })
                if response.user:
                    st.session_state.user = response.user
                    st.success("Login successful!")
                    st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")

    with tab2:
        st.header("Create an Account")
        signup_name = st.text_input("Full Name", key="signup_name")
        signup_age = st.number_input("Age", min_value=1, max_value=120, step=1, value=18, key="signup_age")
        signup_gender = st.selectbox("Gender", ["Select...", "Male", "Female", "Non-binary", "Prefer not to say"], key="signup_gender")
        signup_email = st.text_input("Email", key="signup_email")
        signup_password = st.text_input("Password", type="password", key="signup_password", autocomplete="off")
        
        if st.button("Sign Up"):
            if not signup_name.strip() or signup_gender == "Select..." or not signup_email or not signup_password:
                st.error("Please fill out all fields correctly.")
            else:
                try:
                    response = supabase.auth.sign_up({"email": signup_email, "password": signup_password})
                    if response.user:
                        try:
                            supabase.table("participants").insert({
                                "participant_id": response.user.id,
                                "email": signup_email,
                                "name": signup_name,
                                "age": int(signup_age),
                                "gender": signup_gender
                            }).execute()
                            st.success("Account created successfully! You can now log in.")
                        except Exception as db_error:
                            st.error(f"Database Error: {db_error}")
                except Exception as auth_error:
                    st.error(f"Auth Error: {auth_error}")