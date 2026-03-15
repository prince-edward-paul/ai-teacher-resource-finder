# ai_generator.py
import google.generativeai as genai
import streamlit as st
import logging
import time

# Configure Gemini API from Streamlit secrets
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Set up logging for errors
logging.basicConfig(
    filename="ai_errors.log",
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_supported_models():
    """
    Returns a list of available Gemini text-out models that support generateContent.
    Prioritizes Gemini 3 Flash, then Gemini 2.5 Flash.
    """
    try:
        models = genai.list_models()
        supported = []
        for m in models:
            if getattr(m, "category", "").lower() == "text-out":
                if getattr(m, "capabilities", None) and "generateContent" in m.capabilities:
                    supported.append(m.name)
        # Sort: Gemini 3 Flash first, then Gemini 2.5 Flash, then others
        preferred_order = ["Gemini 3 Flash", "Gemini 2.5 Flash"]
        sorted_models = sorted(supported, key=lambda x: preferred_order.index(x) if x in preferred_order else 99)
        return sorted_models
    except Exception as e:
        logging.error(f"Failed to list models: {e}")
        return []

def generate_lesson(topic, retries=2):
    """
    Generate a structured, student-centered lesson plan for the given topic.
    Retries with fallback models if the first one fails.
    """
    prompt = f"""
Create a student-centered, 21st century teaching lesson plan for: {topic}

Include:
1. Learning objectives
2. Starter activity / engagement
3. Key teaching points
4. Classroom activities (interactive, collaborative)
5. Assessment ideas (formative and summative)
6. Summary / recap
7. Slide-by-slide outline with suggested images or visuals (mention sources if possible)

Format each section clearly, separate by double line breaks.
"""

    models_to_try = get_supported_models()
    if not models_to_try:
        logging.error(f"No supported AI model available for topic '{topic}'")
        st.error("⚠️ AI lesson generation is not available at the moment. Please try later.")
        return None

    for attempt, model_name in enumerate(models_to_try[:retries], start=1):
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response and hasattr(response, "text") and response.text.strip():
                return response.text
            else:
                logging.error(f"Attempt {attempt}: AI response empty or invalid for topic '{topic}' with model '{model_name}'")
        except Exception as e:
            logging.error(f"Attempt {attempt}: AI generation failed for topic '{topic}' using model '{model_name}': {e}")
            time.sleep(1)  # slight pause before retry

    st.error("⚠️ An error occurred while generating the lesson. Please try again later.")
    return None

