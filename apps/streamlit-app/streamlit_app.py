import os
import httpx
import streamlit as st
from pydantic import BaseModel, EmailStr, ValidationError

# ---------- Config ----------
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")

# ---------- Models ----------
class ChatResponse(BaseModel):
    reply: str

class User(BaseModel):
    id: int
    email: EmailStr

# ---------- Tiny API client ----------
def api_post(path: str, payload: dict):
    url = f"{API_BASE}{path}"
    with httpx.Client(timeout=30.0) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        return r.json()

# ---------- Streamlit UI ----------
st.set_page_config(page_title="AI Support Bot", page_icon="🤖")
st.title("🤖 AI Customer Support (Streamlit + FastAPI)")

# Session bootstrap
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user" not in st.session_state:
    st.session_state.user = None  # will hold {"id": ..., "email": ...}

# --- Sidebar: Auth controls ---
with st.sidebar:
    st.subheader("Account")

    # If logged in, show profile + logout; else show tabs for login/register
    if st.session_state.user:
        st.success(f"Logged in as **{st.session_state.user['email']}**")
        if st.button("🔒 Logout", use_container_width=True):
            st.session_state.user = None
            st.session_state.messages = []
            st.toast("Logged out", icon="✅")
            st.rerun()
    else:
        tabs = st.tabs(["Login", "Register"])

        with tabs[0]:
            with st.form("login_form", clear_on_submit=False):
                login_email = st.text_input("Email", key="login_email")
                login_password = st.text_input("Password", type="password", key="login_password")
                login_submitted = st.form_submit_button("Sign in")
            if login_submitted:
                try:
                    # _ = EmailStr(login_email)  # quick local validation
                    data = api_post("/auth/login", {"email": login_email, "password": login_password})
                    # backend returns: {"message": "...", "user": {"id": ..., "email": ...}}
                    st.session_state.user = data["user"]
                    st.toast("Login successful", icon="✅")
                    st.rerun()
                except ValidationError as ve:
                    st.error(f"Invalid email: {ve}")
                except httpx.HTTPStatusError as he:
                    # 401 from backend -> invalid creds
                    detail = he.response.json().get("detail", str(he))
                    st.error(f"Login failed: {detail}")
                except Exception as e:
                    st.error(f"Login error: {e}")

        with tabs[1]:
            with st.form("register_form", clear_on_submit=False):
                reg_email = st.text_input("Email", key="reg_email")
                reg_password = st.text_input("Password", type="password", key="reg_password")
                reg_confirm = st.text_input("Confirm password", type="password", key="reg_confirm")
                reg_submitted = st.form_submit_button("Create account")
            if reg_submitted:
                if reg_password != reg_confirm:
                    st.error("Passwords do not match.")
                else:
                    try:
                        _ = EmailStr(reg_email)
                        # backend 201 -> returns UserOut: {"id": ..., "email": ...}
                        user = api_post("/auth/register", {"email": reg_email, "password": reg_password})
                        st.success("Registration successful. You can log in now.")
                        # Optional: auto-login after register:
                        # st.session_state.user = user
                        # st.rerun()
                    except httpx.HTTPStatusError as he:
                        detail = he.response.json().get("detail", str(he))
                        st.error(f"Registration failed: {detail}")
                    except Exception as e:
                        st.error(f"Registration error: {e}")

st.divider()

# --- Main area: Chat (requires login) ---
if not st.session_state.user:
    st.info("Please log in to start chatting.")
    st.stop()

# Show who is logged in
st.caption(f"Signed in as **{st.session_state.user['email']}**")

# Render chat history
for role, content in st.session_state.messages:
    with st.chat_message(role):
        st.markdown(content)

# Chat input
if prompt := st.chat_input("Ask a question..."):
    st.session_state.messages.append(("user", prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    # call backend
    try:
        # If your /chat later needs user info, pass it here:
        # payload = {"message": prompt, "user_id": st.session_state.user["id"]}
        payload = {"message": prompt}
        data = api_post("/chat", payload)
        bot_reply = ChatResponse(**data).reply
    except Exception as e:
        bot_reply = f"Error contacting API: {e}"

    st.session_state.messages.append(("assistant", bot_reply))
    with st.chat_message("assistant"):
        st.markdown(bot_reply)
