import google.generativeai as genai
import streamlit as st

# Gemini key from Streamlit secrets
API_KEY = st.secrets["GEMINI_API_KEY"]

genai.configure(api_key=API_KEY)


def get_model():
    return genai.GenerativeModel("gemini-1.5-flash")


@st.cache_data
def generate_lesson(topic):

    model = get_model()

    prompt = f"""
Create a structured lesson plan.

Topic: {topic}

Include:

1. Lesson objectives
2. Starter activity
3. Teaching explanation
4. Class activities
5. Assessment questions
6. Summary
7. Homework

Also create slide outline using this format:

SLIDE: Title
Content

SLIDE: Objectives
• bullet
• bullet

SLIDE: Key concept
Explanation

SLIDE: Activity
Activity description

SLIDE: Assessment
3 questions

SLIDE: Summary
Lesson summary
"""

    try:
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:

        if "quota" in str(e).lower():
            return "⚠️ AI is busy. Try again later."

        if "429" in str(e):
            return "⚠️ Too many requests. Wait and try again."

        return f"AI error: {e}"


@st.cache_data
def generate_worksheet(topic):

    model = get_model()

    prompt = f"""
Create a student worksheet.

Topic: {topic}

Include:

5 short questions
5 multiple choice questions
2 critical thinking questions
Answer key
"""

    try:
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"Worksheet error: {e}"


@st.cache_data
def generate_quiz(topic):

    model = get_model()

    prompt = f"""
Create a quiz.

Topic: {topic}

10 multiple choice questions with answers.
"""

    try:
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"Quiz error: {e}"