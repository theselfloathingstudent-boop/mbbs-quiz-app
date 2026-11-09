import streamlit as st
import pdfplumber
import re
import random
from io import BytesIO

st.set_page_config(page_title="MBBS PDF Quiz Generator", page_icon="📚", layout="wide")

st.title("📚 MBBS PDF Question Generator")
st.markdown("Upload your lecture notes, textbooks, or past papers (PDF) and generate practice questions from them.")

# Sidebar
with st.sidebar:
    st.header("Settings")
    num_questions = st.slider("Number of questions to generate", 3, 20, 8)
    question_type = st.selectbox("Question style", ["Multiple Choice", "Short Answer / Flashcards", "Both"])
    st.markdown("---")
    st.info("Tip: Upload clear, text-based PDFs (not scanned images) for best results.")

# File upload
uploaded_files = st.file_uploader(
    "Upload one or more PDFs",
    type=["pdf"],
    accept_multiple_files=True,
    help="Lecture notes, textbooks, or study materials"
)

def extract_text_from_pdf(file):
    text = ""
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
    return text.strip()

def clean_text(text):
    # Basic cleaning
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\s+', ' ', text)
    return text

def split_into_sentences(text):
    # Simple sentence splitter
    sentences = re.split(r'(?<=[.!?])\s+', text)
    # Filter out very short or very long sentences
    good_sentences = [s.strip() for s in sentences if 40 < len(s.strip()) < 300]
    return good_sentences

def generate_mcq(sentence, all_sentences):
    """Generate a simple multiple-choice question from a sentence"""
    words = sentence.split()
    if len(words) < 8:
        return None
    
    # Try to find a key term (capitalized words or medical-looking terms)
    key_candidates = [w for w in words if w[0].isupper() and len(w) > 4 and w not in ["The", "This", "That", "These", "Those", "Which", "What"]]
    
    if key_candidates:
        answer = random.choice(key_candidates)
    else:
        # Pick a random important word
        candidates = [w.strip('.,;:') for w in words if len(w) > 6]
        if not candidates:
            return None
        answer = random.choice(candidates)
    
    # Create question by blanking the answer
    question_text = sentence.replace(answer, "______", 1)
    
    # Generate wrong options from other sentences
    wrong_options = set()
    for s in random.sample(all_sentences, min(10, len(all_sentences))):
        other_words = [w.strip('.,;:') for w in s.split() if len(w) > 5 and w != answer]
        if other_words:
            wrong_options.add(random.choice(other_words))
        if len(wrong_options) >= 3:
            break
    
    options = list(wrong_options)[:3]
    options.append(answer)
    random.shuffle(options)
    
    return {
        "question": question_text,
        "options": options,
        "answer": answer,
        "type": "mcq"
    }

def generate_short_answer(sentence):
    """Turn a sentence into a short-answer question"""
    # Simple transformation
    if sentence.lower().startswith(("the ", "a ", "an ")):
        q = "What is described by the following: " + sentence
    else:
        q = "Explain or complete: " + sentence[:100] + "..."
    
    return {
        "question": q,
        "answer": sentence,
        "type": "short"
    }

# Main logic
if uploaded_files:
    all_text = ""
    with st.spinner("Extracting text from PDFs..."):
        for uploaded_file in uploaded_files:
            text = extract_text_from_pdf(uploaded_file)
            if text:
                all_text += f"\n\n--- From: {uploaded_file.name} ---\n\n" + text
    
    if not all_text.strip():
        st.warning("Could not extract text from the uploaded PDF(s). They might be scanned images. Try a text-based PDF.")
    else:
        cleaned = clean_text(all_text)
        sentences = split_into_sentences(cleaned)
        
        st.success(f"Extracted text from {len(uploaded_files)} file(s). Found {len(sentences)} usable sentences.")
        
        if len(sentences) < 5:
            st.warning("Not enough text found to generate good questions. Try a longer or clearer PDF.")
        else:
            if st.button("Generate Questions", type="primary"):
                with st.spinner("Generating questions..."):
                    questions = []
                    used_sentences = random.sample(sentences, min(num_questions * 2, len(sentences)))
                    
                    for sent in used_sentences:
                        if len(questions) >= num_questions:
                            break
                        
                        if question_type in ["Multiple Choice", "Both"]:
                            mcq = generate_mcq(sent, sentences)
                            if mcq:
                                questions.append(mcq)
                        
                        if question_type in ["Short Answer / Flashcards", "Both"] and len(questions) < num_questions:
                            sa = generate_short_answer(sent)
                            questions.append(sa)
                    
                    # Store in session
                    st.session_state.questions = questions[:num_questions]
                    st.session_state.current_q = 0
                    st.session_state.score = 0
                    st.session_state.answered = set()
            
            # Display questions if generated
            if "questions" in st.session_state and st.session_state.questions:
                questions = st.session_state.questions
                st.markdown("---")
                st.subheader(f"Practice Questions ({len(questions)})")
                
                # Navigation
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    q_num = st.session_state.current_q + 1
                    st.markdown(f"**Question {q_num} of {len(questions)}**")
                
                current = questions[st.session_state.current_q]
                
                if current["type"] == "mcq":
                    st.markdown(f"**{current['question']}**")
                    choice = st.radio("Choose the correct answer:", current["options"], key=f"q{st.session_state.current_q}")
                    
                    if st.button("Check Answer", key=f"check{st.session_state.current_q}"):
                        if choice == current["answer"]:
                            st.success("✅ Correct!")
                            if st.session_state.current_q not in st.session_state.answered:
                                st.session_state.score += 1
                                st.session_state.answered.add(st.session_state.current_q)
                        else:
                            st.error(f"❌ Incorrect. The correct answer is: **{current['answer']}**")
                            st.session_state.answered.add(st.session_state.current_q)
                
                else:  # Short answer
                    st.markdown(f"**{current['question']}**")
                    user_answer = st.text_area("Your answer:", key=f"sa{st.session_state.current_q}")
                    if st.button("Show Answer", key=f"show{st.session_state.current_q}"):
                        st.info(f"**Model answer:** {current['answer']}")
                
                # Navigation buttons
                nav1, nav2, nav3 = st.columns(3)
                with nav1:
                    if st.session_state.current_q > 0:
                        if st.button("← Previous"):
                            st.session_state.current_q -= 1
                            st.rerun()
                with nav3:
                    if st.session_state.current_q < len(questions) - 1:
                        if st.button("Next →"):
                            st.session_state.current_q += 1
                            st.rerun()
                
                # Score
                if st.session_state.answered:
                    st.sidebar.markdown(f"**Score:** {st.session_state.score} / {len(st.session_state.answered)}")
                
                # Export option
                if st.button("Download Questions as Text"):
                    export_text = ""
                    for i, q in enumerate(questions, 1):
                        export_text += f"Q{i}: {q['question']}\n"
                        if q["type"] == "mcq":
                            for opt in q["options"]:
                                export_text += f"  - {opt}\n"
                            export_text += f"Answer: {q['answer']}\n\n"
                        else:
                            export_text += f"Answer: {q['answer']}\n\n"
                    
                    st.download_button(
                        label="Download .txt",
                        data=export_text,
                        file_name="mbbs_practice_questions.txt",
                        mime="text/plain"
                    )

else:
    st.info("👆 Upload one or more PDF files to get started.")
    st.markdown("""
    ### How it works
    1. Upload your medical notes or textbook chapters (PDF)
    2. The app extracts the text
    3. It generates practice questions (MCQs and short-answer)
    4. Practice and check your answers
    
    **Best results** come from clean, text-based PDFs (not scanned documents).
    """)

st.markdown("---")
st.caption("Built for MBBS students • Extract text from PDFs and practice with generated questions")
