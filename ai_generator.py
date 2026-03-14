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
        model = genai.models.get("text-bison-001")
        response = model.generate(prompt=prompt)
        return response.content

    except Exception as e:
        # Friendly error handling for Streamlit users
        if "404" in str(e) or "model not found" in str(e).lower():
            st.error("Gemini model not found. Check your API key or model version.")
        elif "quota" in str(e).lower():
            st.warning("⚠️ AI usage limit reached. Please wait and try again.")
        else:
            st.error(f"AI generation error: {e}")
        return None