import os
import sys
import streamlit as st
from google import genai
from dotenv import load_dotenv

load_dotenv()

st.title("Diagnostic Mode")
st.write("### Python Path")
st.write(sys.path)

st.write("### Working Directory")
st.write(os.getcwd())

st.write("### Environment Variables")
api_key = os.getenv("GOOGLE_API_KEY")
st.write(f"API Key present: {bool(api_key)}")
if api_key:
    st.write(f"API Key start: {api_key[:5]}...")

st.write("### SDK Test")
try:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents="Say 'SDK OK'"
    )
    st.success(f"Gemini Response: {response.text}")
except Exception as e:
    st.error(f"SDK Error: {e}")
