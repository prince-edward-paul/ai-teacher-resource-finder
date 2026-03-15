# ai_generator.py
import google.generativeai as genai
import streamlit as st

# Configure Gemini API from Streamlit secrets
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

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
    try:
        # Use the latest supported text model
        model = genai.GenerativeModel("models/text-bison-001")  # Stable model
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        if "quota" in str(e).lower() or "429" in str(e):
            st.warning("⚠️ AI usage limit reached. Please wait and try again.")
        else:
            st.error(f"AI Error: {e}")
        return None