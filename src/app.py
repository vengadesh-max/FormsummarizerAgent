import streamlit as st
import io
import os
import sys
import json


# This block ensures that the Python interpreter can find modules
# (like 'agent.py') when running the script from a Streamlit environment.
current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.append(current_dir)


from agent import IntelligentFormAgent


# --- Configuration and Initialization ---
st.set_page_config(
    page_title="Intelligent Form Agent", layout="wide", initial_sidebar_state="expanded"
)


@st.cache_resource
def get_agent():
    """
    Initializes the IntelligentFormAgent. This function is cached
    to prevent re-initialization on every rerun.
    """
    try:
        return IntelligentFormAgent()
    except Exception as e:
        st.error(
            f"❌ Application Error: Failed to initialize Intelligent Form Agent."
            f"\n\n**Please check your .env file** and ensure your API key is valid. "
            f"\n\nSpecific Error: {e}"
        )
        return None


agent = get_agent()


# State initialization with caching dicts for each feature
if "forms_data" not in st.session_state:
    st.session_state.forms_data = {}
if "qa_cache" not in st.session_state:
    st.session_state.qa_cache = {}
if "summary_cache" not in st.session_state:
    st.session_state.summary_cache = {}
if "holistic_cache" not in st.session_state:
    st.session_state.holistic_cache = {}

if "qa_result" not in st.session_state:
    st.session_state.qa_result = {"question": "", "answer": "", "form": ""}
if "current_summary" not in st.session_state:
    st.session_state.current_summary = ""
if "current_summary_form" not in st.session_state:
    st.session_state.current_summary_form = ""
if "holistic_result" not in st.session_state:
    st.session_state.holistic_result = {}


st.title("📄 Intelligent Form Agent")
st.markdown(
    "Upload forms (PDF/TXT/DOCX) to enable automatic extraction, QA, and summarization using large language models."
)


if not agent:
    st.markdown("---")
    st.error(
        "Application functionality is **disabled** because the Agent failed to initialize."
    )
    st.stop()


st.header("1. Upload Forms")
supported_file_types = ["pdf", "txt", "doc", "docx"]
uploaded_files = st.file_uploader(
    f"Choose form files ({'/'.join([t.upper() for t in supported_file_types])}). Uploading multiple files enables Holistic Analysis.",
    type=supported_file_types,
    accept_multiple_files=True,
)


if uploaded_files:
    for uploaded_file in uploaded_files:
        file_id = uploaded_file.name
        if file_id not in st.session_state.forms_data:
            with st.spinner(f"Processing {file_id}... (OCR/PDF/Text extraction)"):
                file_type = uploaded_file.name.split(".")[-1].lower()

                if file_type in ["doc", "docx"]:
                    # DOC/DOCX files require special libraries and are explicitly unsupported here
                    raw_text = f"Error: File type .{file_type} not supported for automated extraction."
                else:
                    file_content = io.BytesIO(uploaded_file.read())
                    raw_text = agent.process_form(file_content, file_type)

                if raw_text.startswith("Error"):
                    st.error(f"Error processing {file_id}: {raw_text}")
                    if file_id in st.session_state.forms_data:
                        del st.session_state.forms_data[file_id]
                    continue

                st.session_state.forms_data[file_id] = {
                    "text": raw_text,
                    "name": file_id,
                    "type": file_type,
                }
            st.success(
                f"Successfully processed **{file_id}**. Extracted {len(raw_text)} characters."
            )


# Sidebar Content and Download Report
holistic_data = st.session_state.holistic_result
if isinstance(holistic_data, dict) and "error" in holistic_data:
    holistic_analysis_result = f"Error: {holistic_data['error']}"
elif isinstance(holistic_data, dict):
    holistic_analysis_result = {
        "final_synthesis": holistic_data.get("final_synthesis", "No result generated."),
        "structured_data": holistic_data.get("structured_data", {}),
    }
else:
    holistic_analysis_result = "No result generated."

full_report_data = {
    "forms_data": {
        name: {
            "text_length": len(data["text"]) if data.get("text") else 0,
            "status": (
                "Processed" if not data.get("text", "").startswith("Error") else "Error"
            ),
            "file_type": data["type"],
        }
        for name, data in st.session_state.forms_data.items()
    },
    "single_form_qa_result": st.session_state.qa_result,
    "form_summary_result": {
        "form": st.session_state.current_summary_form,
        "summary": st.session_state.current_summary,
    },
    "holistic_analysis_result": holistic_analysis_result,
}

report_filename = "intelligent_form_report.json"

st.sidebar.header("📝 Processed Forms")
if st.session_state.forms_data:
    st.sidebar.info(f"Total forms loaded: {len(st.session_state.forms_data)}")
    for file_id, data in st.session_state.forms_data.items():
        st.sidebar.markdown(f"- **{data['name']}**")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Download Report")

    st.sidebar.download_button(
        label="Download Full JSON Report",
        data=json.dumps(full_report_data, indent=4),
        file_name=report_filename,
        mime="application/json",
        help="Downloads all extracted data, QA results, and analysis results in JSON format.",
    )
else:
    st.sidebar.info("No forms uploaded yet.")


st.markdown("---")

tab_qa, tab_summary, tab_holistic = st.tabs(
    ["2. Single Form QA", "3. Form Summary", "4. Holistic Analysis"]
)

with tab_qa:
    st.subheader("Answering a Question from a Single Form")
    if st.session_state.forms_data:
        form_names = list(st.session_state.forms_data.keys())
        with st.form("qa_form"):
            selected_form_qa = st.selectbox(
                "Select Form for QA:", form_names, key="qa_select"
            )
            qa_question = st.text_input(
                "Enter your question (e.g., 'What is the total amount due?', 'What is the patient's date of birth?'):",
                key="qa_input_text",
            )
            submit_qa = st.form_submit_button("Get Answer")

            if submit_qa and qa_question and selected_form_qa:
                cache_key = f"{selected_form_qa}_{qa_question}"
                if cache_key in st.session_state.qa_cache:
                    answer = st.session_state.qa_cache[cache_key]
                else:
                    context = st.session_state.forms_data[selected_form_qa]["text"]
                    if not context or context.startswith("Error"):
                        answer = (
                            f"Error: No usable text extracted from {selected_form_qa}."
                        )
                    else:
                        with st.spinner("Finding the answer..."):
                            answer = agent.answer_question(context, qa_question)
                    st.session_state.qa_cache[cache_key] = answer

                st.session_state.qa_result = {
                    "question": qa_question,
                    "answer": answer,
                    "form": selected_form_qa,
                }
                st.success("Query Complete")

        if st.session_state.qa_result["answer"]:
            st.markdown(f"**Question:** {st.session_state.qa_result['question']}")
            if st.session_state.qa_result["answer"].startswith("Error"):
                st.error(
                    f"**Answer from {st.session_state.qa_result['form']}:** {st.session_state.qa_result['answer']}"
                )
            else:
                st.markdown(
                    f"**Answer from {st.session_state.qa_result['form']}:** :green[{st.session_state.qa_result['answer']}]"
                )
    else:
        st.warning("Please upload a form first to use the QA feature.")

with tab_summary:
    st.subheader("Generating a Concise Summary")
    if st.session_state.forms_data:
        form_names = list(st.session_state.forms_data.keys())
        selected_form_summary = st.selectbox(
            "Select Form for Summary:", form_names, key="summary_select"
        )
        if st.button("Generate Summary", key="run_summary") and selected_form_summary:
            cache_key = f"summary_{selected_form_summary}"
            if cache_key in st.session_state.summary_cache:
                summary = st.session_state.summary_cache[cache_key]
            else:
                context = st.session_state.forms_data[selected_form_summary]["text"]
                if not context or context.startswith("Error"):
                    summary = (
                        f"Error: No usable text extracted from {selected_form_summary}."
                    )
                else:
                    with st.spinner("Generating summary..."):
                        summary = agent.generate_summary(context)
                st.session_state.summary_cache[cache_key] = summary

            st.session_state.current_summary = summary
            st.session_state.current_summary_form = selected_form_summary

            if summary.startswith("Error"):
                st.error("Summary Generation Failed.")
            else:
                st.success("Summary Complete")

        if (
            st.session_state.current_summary
            and st.session_state.current_summary_form == selected_form_summary
        ):
            st.markdown(f"**Summary of {selected_form_summary}:**")
            if st.session_state.current_summary.startswith("Error"):
                st.error(st.session_state.current_summary)
            else:
                st.info(st.session_state.current_summary)
    else:
        st.warning("Please upload a form first to use the Summarization feature.")

with tab_holistic:
    st.subheader("Holistic Analysis Across Multiple Forms")
    st.markdown(
        "💡 For structured data extraction (e.g., fields, tables), use a prompt like: **'List the name and date for each form.'**"
    )
    form_names = list(st.session_state.forms_data.keys())
    selected_forms_holistic = st.multiselect(
        "Select Forms for Holistic Analysis (min 2 required):",
        form_names,
        default=form_names,
        key="holistic_multiselect",
    )
    holistic_prompt = st.text_input(
        "Enter the question for holistic insight (e.g., 'Compare the payment deadlines and report the earliest date.'):",
        key="holistic_input",
    )
    is_holistic_ready = (
        len(selected_forms_holistic) >= 2 and holistic_prompt.strip() != ""
    )
    if st.button(
        "Run Holistic Analysis",
        key="run_holistic_final",
        disabled=not is_holistic_ready,
    ):
        if len(selected_forms_holistic) < 2:
            st.warning(
                "Please select at least two forms to perform a Holistic Analysis."
            )
        else:
            cache_key = (
                f"holistic_{'_'.join(selected_forms_holistic)}_{holistic_prompt}"
            )
            if cache_key in st.session_state.holistic_cache:
                holistic_result = st.session_state.holistic_cache[cache_key]
            else:
                contexts = [
                    st.session_state.forms_data[name]["text"]
                    for name in selected_forms_holistic
                ]
                with st.spinner("Analyzing and synthesizing data across forms..."):
                    holistic_result = agent.holistic_analysis(contexts, holistic_prompt)
                st.session_state.holistic_cache[cache_key] = holistic_result

            st.session_state.holistic_result = holistic_result

            if "error" in holistic_result:
                st.error("Holistic Analysis Failed.")
            else:
                st.success("Holistic Analysis Complete")

    if st.session_state.holistic_result:
        st.markdown("---")
        st.markdown("**Holistic Analysis Result:**")
        result = st.session_state.holistic_result
        if "error" in result:
            st.error(f"Analysis Error: {result['error']}")
        else:
            st.markdown("### Structured Data Extraction")
            structured_data = result.get("structured_data", {})
            if (
                structured_data.get("structured_output")
                == "Not applicable - prompt does not require structured extraction."
            ):
                st.info(
                    "Structured extraction was skipped because the prompt did not ask for a list or comparison."
                )
            elif "Error" in str(structured_data.get("structured_output")):
                st.error(
                    f"Structured Data Error: {structured_data.get('structured_output', 'Unknown error.')}"
                )
                if "raw_text" in structured_data:
                    st.caption("Raw output from model:")
                    st.code(structured_data["raw_text"])
            else:
                st.json(structured_data.get("structured_output", {}))
            st.markdown("---")
            st.markdown(
                f"### Final Synthesis (Answer to: *{result.get('holistic_prompt')}*)"
            )
            st.success(result.get("final_synthesis", "No conclusive answer found."))
            st.markdown("### Intermediary QA Results per Document")
            for res in result.get("intermediary_results", []):
                if res["answer"].startswith("Error"):
                    st.error(f"**{res['form']}**:")
                    st.text(res["answer"])
                else:
                    st.markdown(f"**{res['form']}**")
                    st.info(f"{res['answer']}")
    elif len(st.session_state.forms_data) < 2:
        st.warning("Please upload at least two forms to perform a Holistic Analysis.")
