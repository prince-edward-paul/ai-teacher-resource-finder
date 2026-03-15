# ai_generator.py
import google.generativeai as genai
import streamlit as st

# -------------------------
# Configure API
# -------------------------
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# -------------------------
# Supported model selection
# -------------------------
# You must use a currently supported model.
# Recommended: "gemini-2.1-large" or "gemini-2.1-mini"
MODEL_NAME = "gemini-2.1-large"

def generate_lesson(topic):
    """
    Generate a structured, student-centered lesson plan for the given topic.
    Includes objectives, activities, assessment, summary, and slide outline.
    User-friendly error messages only.
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
        # Initialize model
        model = genai.models.get(MODEL_NAME)

        # Generate content
        response = model.generate(
            prompt=prompt,
            temperature=0.7,
            max_output_tokens=1200
        )
        # Return text
        return response.candidates[0].content

    except Exception as e:
        # Generic user-friendly error
        err_msg = str(e).lower()
        if "quota" in err_msg or "429" in err_msg:
            st.warning("⚠️ AI usage limit reached. Please wait and try again later.")
        elif "not found" in err_msg or "404" in err_msg:
            st.error("⚠️ The requested AI model is currently unavailable. Please try again later.")
        else:
            st.error("⚠️ An error occurred while generating the lesson. Please try again.")
        return None
