import streamlit as st
import google.generativeai as genai
import json

# ==========================================
# 1. SYSTEM SETUP
# ==========================================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
    # Note: Using gemini-1.5-flash as it is the current stable version
    gemini_model = genai.GenerativeModel('gemini-2.5-flash-lite')
except Exception as e:
    st.error("API Key not found! Please check your secrets.toml file.")
    st.stop()

st.set_page_config(page_title="ThreadSense AI", page_icon="🧠", layout="wide")

# ==========================================
# 2. CUSTOM CSS
# ==========================================
st.markdown("""
    <style>
    div[data-testid="stSidebar"] .stButton > button {
        width: 100%; text-align: left; justify-content: flex-start;
        border: none; background-color: transparent; padding: 8px 10px;
        font-size: 15px; border-radius: 8px; transition: 0.2s;
        color: #FFFFFF;
    }
    div[data-testid="stSidebar"] .stButton > button:hover {
        background-color: rgba(255, 255, 255, 0.1); color: #4A90E2;
    }
    .metric-box {
        background-color: #1a1a1a; 
        border-left: 4px solid #4A90E2;
        padding: 10px; border-radius: 5px; margin-bottom: 10px;
        color: #FFFFFF;
    }
    .header-container {
        text-align: center;
        width: 100%;
        margin-top: -40px; 
        margin-bottom: 25px;
    }
    .main-title {
        font-weight: bold;
        font-size: 42px;
        color: #FFFFFF;
        margin-bottom: 5px;
    }
    .sub-title {
        font-size: 18px;
        color: #AAAAAA;
    }
    .stChatInput textarea {
        background-color: #1a1a1a !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. MAIN UI HEADERS
# ==========================================
st.markdown("""
    <div class="header-container">
        <div class="main-title">📍 THREADSENCE AI SYSTEM</div>
        <div class="sub-title">💫 ThreadSense is active. Type your first message to begin the analysis...</div>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 4. MEMORY & HISTORY LOGIC (FIXED)
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history_db" not in st.session_state:
    st.session_state.chat_history_db = {}
if "overall_intent" not in st.session_state:
    st.session_state.overall_intent = "AWAITING_INPUT"
if "overall_mood" not in st.session_state:
    st.session_state.overall_mood = "NEUTRAL"

def save_current_chat():
    """Puro conversation history database-e save kore"""
    if st.session_state.messages:
        # User-er prothom message theke title toiri kora
        user_msgs = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
        if user_msgs:
            first_msg = user_msgs[0]
            title = first_msg[:25] + "..." if len(first_msg) > 25 else first_msg
            # list() bebohar kore puro history-r ekta snapshot save kora
            st.session_state.chat_history_db[title] = list(st.session_state.messages)

# ==========================================
# 5. SIDEBAR MENU
# ==========================================
with st.sidebar:
    st.markdown("### ☰ Menu")
    
    if st.button("📝 New chat"):
        save_current_chat() 
        st.session_state.messages = []
        st.session_state.overall_intent = "AWAITING_INPUT"
        st.session_state.overall_mood = "NEUTRAL"
        st.rerun()
        
    st.divider()
    st.markdown("### 📊 Live Session Stats")
    st.markdown(f"""
        <div class="metric-box">
            <b>Overall Intent:</b><br>{st.session_state.overall_intent}<br><br>
            <b>Overall Mood:</b><br>{st.session_state.overall_mood}
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    st.markdown("**Recent Chats**")
    if not st.session_state.chat_history_db:
        st.caption("No chat history yet.")
    else:
        # Latest chat gulo upore dekhano hoyeche
        for title in list(st.session_state.chat_history_db.keys())[::-1]:
            # Unique key add kora hoyeche jate error na ase
            if st.button(f"💬 {title}", key=f"hist_{title}"):
                save_current_chat() 
                st.session_state.messages = list(st.session_state.chat_history_db[title])
                st.session_state.overall_intent = "HISTORY_LOADED"
                st.session_state.overall_mood = "HISTORY_LOADED"
                st.rerun()

# ==========================================
# 6. MAIN CHAT INTERFACE
# ==========================================
for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "✨"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and "curr_intent" in msg:
            st.caption(f"🎯 Msg Intent: **{msg['curr_intent']}** | 🎭 Msg Mood: **{msg['curr_mood']}**")

user_input = st.chat_input("Enter your message here...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    full_history_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages])

    master_prompt = f"""
    You are an advanced Enterprise Support Assistant.
    Analyze the entire conversation history.
    Transcript: {full_history_text}
    Reply ONLY with JSON (keys: current_intent, current_mood, overall_intent, overall_mood, response).
    """

    with st.spinner("Analyzing..."):
        try:
            response = gemini_model.generate_content(
                master_prompt,
                generation_config=genai.GenerationConfig(response_mime_type="application/json")
            )
            ai_data = json.loads(response.text)
            
            c_intent = ai_data.get("current_intent", "GREETING").upper()
            c_mood = ai_data.get("current_mood", "NEUTRAL").upper()
            o_intent = ai_data.get("overall_intent", "GREETING").upper()
            o_mood = ai_data.get("overall_mood", "NEUTRAL").upper()
            reply_val = ai_data.get("response", "I am here to help.")
        except Exception as e:
            c_intent, c_mood, o_intent, o_mood = "ERROR", "UNKNOWN", "ERROR", "UNKNOWN"
            reply_val = f"⚠️ SYSTEM ALERT: {str(e)}"

    st.session_state.overall_intent = o_intent
    st.session_state.overall_mood = o_mood

    st.session_state.messages.append({
        "role": "assistant", 
        "content": reply_val, 
        "curr_intent": c_intent, 
        "curr_mood": c_mood
    })
    
    st.rerun()