# ai_generator.py
import google.generativeai as genai
import streamlit as st
import logging

# Configure Gemini API from Streamlit secrets
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Set up logging for errors
logging.basicConfig(filename="ai_errors.log", level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def get_supported_model():
    """
    Returns the first available generative text model from Gemini that supports generate_content.
    """
    try:
        models = genai.list_models()
        for m in models:
            if getattr(m, "capabilities", None):
                if "generateContent" in m.capabilities:
                    return m.name
        # fallback
        return "models/text-bison-001"
    except Exception as e:
        logging.error(f"Failed to list models: {e}")
        # fallback model
        return "models/text-bison-001"


def generate_lesson(topic):
    """
    Generate a structured, student-centered lesson plan for the given topic.
    Includes objectives, activities, assessment, summary, and slide outline.
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

    model_name = get_supported_model()
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        # Log the full error for debugging
        logging.error(f"AI generation failed for topic '{topic}': {e}")
        # Show friendly message to user
        st.error("⚠️ An error occurred while generating the lesson. Please try again later.")
        return None
