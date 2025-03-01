import streamlit as st
import pandas as pd
import re
import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

# Load API key
load_dotenv()
genai.configure(api_key=os.getenv('GENAI_API_KEY'))
model = genai.GenerativeModel("gemini-1.5-flash")

# Global session state for MCQ tracking
if "mcq_df" not in st.session_state:
    st.session_state.mcq_df = None
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "saved_answers" not in st.session_state:
    st.session_state.saved_answers = {}
if "selected_level" not in st.session_state:
    st.session_state.selected_level = None

# Function to generate MCQs
def generate_question_bank(topic: str, level: str) -> pd.DataFrame:
    prompt = f'''You are a tutor creating a multiple-choice question (MCQ) test for a student on the topic of "{topic}".
    The student's proficiency level is "{level}". The test must contain 10 well-structured and challenging MCQs.

    ### **Output Format**
    Return the question bank as a **Python list structure with each element as a separate dictionary** (not Python code) in the following format:

    [
        {{
            "question": "What is 2 + 2?",
            "options": ["1", "2", "4", "8"],
            "answer": "4",
            "language": false
        }},
        {{
            "question": "What does the following Python code output?",
            "options": ["Syntax Error", "[1, 2, 3]", "[3, 2, 1]", "None"],
            "answer": "[3, 2, 1]",
            "language": "Python"
        }}
    ]

    ### **Guidelines**
    - Ensure all questions match the specified topic and difficulty level.
    - Each question should have **four distinct options**.
    - The correct answer must be an **exact match to one of the options**.
    - If the question involves a programming language, specify `"language": "<Language>"`, else set `"language": false`.
    - Maintain **proper indentation, spacing, and formatting** for code-related questions.
    - Avoid unnecessary explanations, return only the structured JSON-like output.

    **Generate exactly 10 questions in this format.**
    '''

    response = model.generate_content(prompt)
    response_text = response.text.strip()

    if response_text.startswith("```json") or response_text.startswith("```"):
        response_text = response_text.strip("```json").strip("```").strip()

    try:
        mcq_list = json.loads(response_text)
        df = pd.DataFrame(mcq_list)  
        return df
    except json.JSONDecodeError as e:
        print("Error parsing JSON:", e)
        return None

def display_mcq():
    index = st.session_state.current_index
    mcq_df = st.session_state.mcq_df

    if mcq_df is None or mcq_df.empty:
        st.warning("No questions available. Please generate MCQs first.")
        return

    row = mcq_df.iloc[index]
    question_text = row["question"]
    language = row["language"]
    options = row.get("options", [])

    # Check if the question contains a code snippet
    code_match = re.search(r"```(\w+)?\n(.*?)```", question_text, re.DOTALL)

    if code_match:
        explanation_text = question_text[:code_match.start()].strip()
        code_language = code_match.group(1) if code_match.group(1) else "python"
        code_snippet = code_match.group(2).strip()

        if explanation_text:
            st.subheader(f"Q{index + 1}: {explanation_text}")
        st.code(code_snippet, language=code_language)
    else:
        st.subheader(f"Q{index + 1}: {question_text}")


    # Ensure all options have valid text
    options = [opt if opt.strip() else "Option not available" for opt in options]

    # Options inside the card
    for option in options:
        if st.button(option, key=f"option_{index}_{option}"):
            st.session_state.saved_answers[index] = option

    # Buttons for Save & Reset
    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Reset Answer", key=f"reset_{index}"):
            if index in st.session_state.saved_answers:
                del st.session_state.saved_answers[index]
    with col2:
        if st.button("✔ Save Answer", key=f"save_{index}"):
            pass  # No text output on UI

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.session_state.current_index > 0:
            if st.button("⬅ Previous"):
                st.session_state.current_index -= 1
                st.rerun()
    with col3:
        if st.session_state.current_index < len(mcq_df) - 1:
            if st.button("Next ➡"):
                st.session_state.current_index += 1
                st.rerun()

    st.markdown("---")  # Separator


# Function to calculate & show results
def submit_test():
    mcq_df = st.session_state.mcq_df
    saved_answers = st.session_state.saved_answers

    if mcq_df is None or mcq_df.empty:
        st.warning("No MCQs available. Please generate MCQs first.")
        return

    correct_count = sum(
        1 for i, row in mcq_df.iterrows() if i in saved_answers and saved_answers[i] == row["answer"]
    )

    # Clear the screen
    st.session_state.mcq_df = None
    st.session_state.current_index = 0
    st.session_state.saved_answers = {}

    st.success(f"🎉 Test Submitted! Your Score: **{correct_count} / {len(mcq_df)}**")

    # Display incorrectly answered questions
    st.markdown("## ❌ Incorrect Answers")
    for i, row in mcq_df.iterrows():
        if i in saved_answers and saved_answers[i] != row["answer"]:
            st.markdown(f"**Q{i + 1}: {row['question']}**")
            st.markdown(f"Your Answer: {saved_answers[i]}")
            st.markdown(f"Correct Answer: {row['answer']}")
            st.markdown("---")

# Streamlit UI
st.title("🧠 Quizify: AI-Powered MCQs")

col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    topic = st.text_input("📌 Enter Topic")
    diff_col1, diff_col2, diff_col3 = st.columns(3)
    
    st.markdown("### Select Difficulty")
    difficulty_levels = ["Beginner", "Intermediate", "Advanced"]

    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]

    for i, diff in enumerate(difficulty_levels):
        with cols[i]:
            key = f"btn_{diff.lower()}"
            if st.button(diff, key=key):
                st.session_state.selected_level = diff

# Button to generate MCQs
if st.button("🚀 Generate MCQs"):
    if topic and st.session_state.selected_level:
        st.write("Generating MCQs... Please wait.")
        mcq_df = generate_question_bank(topic, st.session_state.selected_level)
        if mcq_df is not None and not mcq_df.empty:
            st.session_state.mcq_df = mcq_df
            st.session_state.current_index = 0
            st.session_state.saved_answers = {}
            st.rerun()
        else:
            st.error("Error generating MCQs. Please try again.")
    else:
        st.warning("Please enter a topic and select a difficulty level.")

# Show MCQs if generated
if st.session_state.mcq_df is not None:
    display_mcq()

# Submit button
if st.button("✅ Submit Test"):
    submit_test()