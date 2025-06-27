# app.py
import streamlit as st
from pipeline import build_pipeline

# Page config
st.set_page_config(page_title="PromptCraft AI", page_icon="🧠", layout="centered")

# Title
st.title("🧠 PromptCraft AI")
st.subheader("LLM Prompt Generator & Improver using LangGraph + Groq")

# Load Groq API key from Streamlit Secrets
# groq_api_key = st.secrets["groq"]["api_key"]
groq_api_key = st.secrets['GROQ_API_KEY']


# Build the LangGraph pipeline
pipeline = build_pipeline(groq_api_key)

# User selection
mode = st.radio("Choose Mode", ["🔁 Generate & Improve", "✍️ Improve Existing Prompt"])

# Form for mode 1: Full Generation Pipeline
if mode == "🔁 Generate & Improve":
    with st.form("generate_form"):
        task = st.text_area("Describe your task", placeholder="Explain relativity to a child...")
        submitted = st.form_submit_button("Generate Prompt")
        if submitted and task:
            with st.spinner("Generating and improving prompt..."):
                result = pipeline.invoke({
                    "mode": "generate",
                    "task_description": task
                })
                st.success("✅ Final Prompt")
                st.text_area("Generated Prompt", result.get("prompt"), height=150)

# Form for mode 2: Improve Existing Prompt
if mode == "✍️ Improve Existing Prompt":
    with st.form("improve_form"):
        prompt = st.text_area("Paste your prompt", placeholder="Explain relativity.")
        context = st.text_area("How do you want to improve it?", placeholder="Make it simple using a train and ball analogy")
        submitted = st.form_submit_button("Improve Prompt")
        if submitted and prompt and context:
            with st.spinner("Improving prompt..."):
                result = pipeline.invoke({
                    "mode": "improve",
                    "prompt": prompt,
                    "context": context
                })
                st.success("✅ Improved Prompt")
                st.text_area("Improved Prompt", result.get("improved_prompt"), height=150)
