# fresh_streamlit_app.py
# Career Advisor Streamlit App with Clarification Flow

import os
import streamlit as st
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to get API key from Streamlit secrets first (for cloud deployment)
# Fall back to environment variables for local development
try:
    API_KEY = st.secrets["OPENROUTER_API_KEY"]
except (KeyError, AttributeError):
    API_KEY = os.getenv("OPENROUTER_API_KEY")

if not API_KEY:
    st.error("Please set OPENROUTER_API_KEY in your Streamlit secrets or .env file")
    st.stop()

def get_career_advice(conversation):
    """Call OpenRouter API for career advice"""
    system_prompt = (
        "You are a career advisor assistant. "
        "Given a user conversation, perform these steps:\n"
        "1. Extract user interests and preferences.\n"
        "2. Map those interests to suitable career paths based on the interests provided.\n"
        "3. For each recommended path, generate a short explanation why it suits the user.\n"
        "If no clear interests are found, ask a clarifying question.\n"
        "Respond only in JSON with one of the following structures:\n"
        "- {\"interests\": [...], \"mapping\": {...}, \"explanations\": {...}}\n"
        "- {\"clarify\": \"<question>\"}\n"
    )
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "mistralai/devstral-small:free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Conversation: {conversation}"}
        ]
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload)
        )
        
        if response.status_code != 200:
            return {"error": f"Request failed ({response.status_code}): {response.text}"}
        
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
        
    except json.JSONDecodeError:
        # If response isn't JSON, treat as clarification
        return {"clarify": content.strip()}
    except Exception as e:
        return {"error": f"Error: {str(e)}"}

# Initialize Streamlit app
st.title("🎯 Career Advisor")
st.write("Enter your conversation below to get personalized career suggestions.")

# Initialize session state
if 'step' not in st.session_state:
    st.session_state.step = 'initial'  # 'initial', 'clarify', 'results'
if 'conversation' not in st.session_state:
    st.session_state.conversation = ''
if 'clarify_question' not in st.session_state:
    st.session_state.clarify_question = ''
if 'clarify_response' not in st.session_state:
    st.session_state.clarify_response = ''
if 'results' not in st.session_state:
    st.session_state.results = None

# Step 1: Initial conversation input
if st.session_state.step == 'initial':
    st.session_state.conversation = st.text_area(
        "Conversation:",
        value=st.session_state.conversation,
        placeholder="Tell me about your interests, hobbies, or activities you enjoy..."
    )
    
    if st.button("Get Advice", key="initial_button"):
        if st.session_state.conversation.strip():
            result = get_career_advice(st.session_state.conversation)
            
            if "error" in result:
                st.error(result["error"])
            elif "clarify" in result:
                st.session_state.clarify_question = result["clarify"]
                st.session_state.step = 'clarify'
                st.rerun()
            else:
                st.session_state.results = result
                st.session_state.step = 'results'
                st.rerun()
        else:
            st.warning("Please enter your conversation first.")

# Step 2: Clarification flow
elif st.session_state.step == 'clarify':
    # Show original conversation (read-only)
    st.text_area("Original Conversation:", value=st.session_state.conversation, disabled=True)
    
    # Show assistant's clarification question
    st.info(f"**Assistant:** {st.session_state.clarify_question}")
    
    # Input for clarification response
    st.session_state.clarify_response = st.text_input(
        "Your response:",
        value=st.session_state.clarify_response,
        placeholder="Please provide more details about your interests..."
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Get Advice", key="clarify_button"):
            if st.session_state.clarify_response.strip():
                result = get_career_advice(st.session_state.clarify_response)
                
                if "error" in result:
                    st.error(result["error"])
                elif "clarify" in result:
                    # Another clarification needed
                    st.session_state.clarify_question = result["clarify"]
                    st.session_state.clarify_response = ''
                    st.rerun()
                else:
                    st.session_state.results = result
                    st.session_state.step = 'results'
                    st.rerun()
            else:
                st.warning("Please provide your response first.")
    
    with col2:
        if st.button("Start Over", key="start_over"):
            st.session_state.step = 'initial'
            st.session_state.conversation = ''
            st.session_state.clarify_question = ''
            st.session_state.clarify_response = ''
            st.session_state.results = None
            st.rerun()

# Step 3: Display results
elif st.session_state.step == 'results':
    if st.session_state.results:
        results = st.session_state.results
        
        # Display results
        st.success("✅ Analysis Complete!")
        
        if "interests" in results:
            st.subheader("🎯 Extracted Interests")
            interests = results["interests"]
            if isinstance(interests, list):
                for i, interest in enumerate(interests, 1):
                    st.write(f"{i}. {interest}")
            else:
                st.write(interests)
        
        if "mapping" in results:
            st.subheader("🗺️ Career Path Mapping")
            mapping = results["mapping"]
            if isinstance(mapping, dict):
                for interest, path in mapping.items():
                    st.write(f"**{interest}** → {path}")
            else:
                st.json(mapping)
        
        if "explanations" in results:
            st.subheader("💡 Explanations")
            explanations = results["explanations"]
            if isinstance(explanations, dict):
                for path, explanation in explanations.items():
                    with st.expander(f"Why {path}?"):
                        st.write(explanation)
            else:
                st.json(explanations)
    
    # Option to start over
    if st.button("Start New Analysis", key="new_analysis"):
        st.session_state.step = 'initial'
        st.session_state.conversation = ''
        st.session_state.clarify_question = ''
        st.session_state.clarify_response = ''
        st.session_state.results = None
        st.rerun()

# Footer
st.markdown("---")
st.markdown("*Powered by AI Career Advisory*")
