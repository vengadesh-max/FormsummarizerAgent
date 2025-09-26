import requests
import json
import pytesseract
from PIL import Image
import io
import pypdf

from utils import (
    get_gemini_api_key,
)  # Ensure this method exists to retrieve your API key


class IntelligentFormAgent:
    def __init__(self):
        try:
            self.api_key = get_gemini_api_key()
        except Exception as e:
            raise RuntimeError(f"Gemini API key retrieval failed: {e}")

        # Updated Gemini API endpoint with your api_key as query param
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.0:generateContent?key={self.api_key}"
        self.headers = {"Content-Type": "application/json"}

    def _ocr_or_extract_text(self, file_path_or_content, file_type):
        if file_type in ["png", "jpg", "jpeg"]:
            try:
                image = Image.open(file_path_or_content)
                return pytesseract.image_to_string(image)
            except Exception as e:
                return f"Error during OCR: {e}"

        elif file_type == "pdf":
            text = ""
            try:
                reader = pypdf.PdfReader(file_path_or_content)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            except Exception as e:
                return f"Error extracting text from PDF: {e}"
            if not text.strip():
                return "Error: No usable text extracted from PDF."
            return text

        elif file_type == "txt":
            try:
                return file_path_or_content.getvalue().decode("utf-8")
            except Exception as e:
                return f"Error reading TXT file: {e}"

        return "Unsupported file type."

    def process_form(self, file_content, file_type):
        raw_text = self._ocr_or_extract_text(file_content, file_type)
        if raw_text.startswith("Error") or not raw_text.strip():
            return raw_text
        return raw_text.strip()

    def _call_gemini_api(self, prompt: str) -> str:
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            response = requests.post(self.endpoint, headers=self.headers, json=body)
            response.raise_for_status()
            data = response.json()
            # Response parsing per Gemini API spec
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            return f"Error calling Gemini API: {e}"

    def answer_question(self, context: str, question: str) -> str:
        if not context or context.startswith("Error"):
            return "Error: Invalid context for Q&A."
        prompt = (
            f"Document content: '''{context}'''\n"
            f"User question: {question}\n"
            "Extract the exact information asked or reply 'No answer found' if unavailable."
        )
        return self._call_gemini_api(prompt)

    def generate_summary(self, context: str, max_length: int = 150) -> str:
        if not context or context.startswith("Error"):
            return "Error: Invalid context for summarization."
        prompt = (
            "Summarize this document with a two-line introduction followed by bullet points with key information "
            f"(dates, names, topics):\nDocument Text: '''{context}'''"
        )
        return self._call_gemini_api(prompt)

    def holistic_analysis(self, contexts: list[str], prompt: str) -> dict:
        if not contexts or any(c.startswith("Error") for c in contexts):
            return {"error": "Invalid contexts for holistic analysis."}
        intermediary_results = []
        for i, c in enumerate(contexts):
            form_name = f"Form {i+1}"
            q_prompt = f"Document: '''{c}'''\nQuestion: {prompt}\nAnswer based on the document."
            answer = self._call_gemini_api(q_prompt)
            intermediary_results.append({"form": form_name, "answer": answer})

        combined_prompt = (
            "Answers from multiple documents:\n"
            + "\n".join([f"{r['form']}: {r['answer']}" for r in intermediary_results])
            + f"\nSynthesize a concise final answer to: {prompt}."
        )
        final_synthesis = self._call_gemini_api(combined_prompt)

        return {
            "holistic_prompt": prompt,
            "intermediary_results": intermediary_results,
            "final_synthesis": final_synthesis,
            "structured_data": {},
        }
