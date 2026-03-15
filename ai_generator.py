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
    Falls back to a safe model if none found.
    """
    try:
        models = genai.list_models()
        for m in models:
            if getattr(m, "category", "").lower() == "text-out":
                if getattr(m, "capabilities", None) and "generateContent" in m.capabilities:
                    return m.name
        # If no supported model found, pick a known safe model in your project
        fallback_models = ["Gemini 2.5 Flash", "Gemini 3 Flash", "Gemini 3.1 Flash Lite"]
        for fb in fallback_models:
            try:
                genai.GenerativeModel(fb)  # check if available
                return fb
            except:
                continue
        return None
    except Exception as e:
        logging.error(f"Failed to list models: {e}")
        return None


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
    if not model_name:
        logging.error(f"No supported AI model available for topic '{topic}'")
        st.error("⚠️ AI lesson generation is not available at the moment. Please try later.")
        return None

    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        logging.error(f"AI generation failed for topic '{topic}' using model '{model_name}': {e}")
        st.error("⚠️ An error occurred while generating the lesson. Please try again later.")
        return None
