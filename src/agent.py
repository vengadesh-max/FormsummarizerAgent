import requests
import json
import pytesseract
from PIL import Image
import io
import pypdf

import time

# Assuming utils contains the correct get_gemini_api_key now
from utils import get_gemini_api_key

GEMINI_MODEL_NAME = "gemini-2.5-flash"


class IntelligentFormAgent:
    """
    An agent designed to process various form types (images, PDFs, text)
    using OCR/text extraction and leverage the Gemini API for advanced
    analysis, Q&A, summarization, and holistic comparison.
    """

    def __init__(self):
        """
        Initializes the agent by retrieving the Gemini API key and setting
        up the API endpoint configuration for the specified model.
        """
        try:
            # Retrieve the Gemini API key
            self.api_key = get_gemini_api_key()
        except Exception as e:
            raise RuntimeError(f"Gemini API key retrieval failed: {e}")

        # Use the current model name to avoid 404 errors
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_NAME}:generateContent?key={self.api_key}"
        self.headers = {"Content-Type": "application/json"}
        print(f"Agent initialized using model: {GEMINI_MODEL_NAME}")

    def _ocr_or_extract_text(self, file_path_or_content, file_type):
        """
        Performs OCR for image files (png, jpg, jpeg) or extracts text
        from PDF and plain text files.

        Args:
            file_path_or_content: File path or in-memory file object.
            file_type (str): The file extension (e.g., 'pdf', 'jpg', 'txt').

        Returns:
            str: The extracted text or an error message.
        """
        if file_type in ["png", "jpg", "jpeg"]:
            try:
                # Use Pillow to open the image content
                image = Image.open(file_path_or_content)
                # Apply OCR using pytesseract
                return pytesseract.image_to_string(image)
            except Exception as e:
                return f"Error during OCR: {e}"

        elif file_type == "pdf":
            text = ""
            try:
                # Use pypdf to read the PDF content
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
                # Read text from the in-memory file content (e.g., from Streamlit upload)
                return file_path_or_content.getvalue().decode("utf-8")
            except Exception as e:
                return f"Error reading TXT file: {e}"

        return "Unsupported file type."

    def process_form(self, file_content, file_type):
        """
        Public method to extract and clean text from the file content.

        Args:
            file_content: In-memory file content or path.
            file_type (str): The file type extension.

        Returns:
            str: Cleaned, extracted text or an error message.
        """
        # Extracts and cleans the text from the file content
        raw_text = self._ocr_or_extract_text(file_content, file_type)
        if raw_text.startswith("Error") or not raw_text.strip():
            return raw_text
        return raw_text.strip()

    def _call_gemini_api(self, prompt: str) -> str:
        """
        Handles the REST API call to the Gemini endpoint.

        Args:
            prompt (str): The text prompt to send to the model.

        Returns:
            str: The text response from the model or an error message.
        """
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            response = requests.post(self.endpoint, headers=self.headers, json=body)
            response.raise_for_status()
            data = response.json()
            # Safely parse the response text
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (requests.exceptions.RequestException, KeyError, IndexError) as e:
            # Catch network, HTTP error codes, and bad JSON structure
            print(f"API Call Error: {e}")
            return f"Error calling Gemini API: {e}"

    def answer_question(self, context: str, question: str) -> str:
        """
        Answers a specific question based on the provided document context
        using the Gemini model.

        Args:
            context (str): The extracted text from the document.
            question (str): The user's question.

        Returns:
            str: The answer or an error message.
        """
        if not context or context.startswith("Error"):
            return "Error: Invalid context for Q&A."

        # Optimized prompt for direct extraction
        prompt = (
            f"You are an expert document analyst. Use ONLY the provided document content to answer the question. "
            f"Document content: '''{context}'''\n"
            f"User question: {question}\n"
            "Extract the exact information asked. If the answer is not present, reply with 'No answer found'."
        )
        return self._call_gemini_api(prompt)

    def generate_summary(self, context: str, max_length: int = 150) -> str:
        """
        Generates a structured summary of the document context.

        Args:
            context (str): The extracted text from the document.
            max_length (int): A suggestion for maximum summary length (not strictly enforced by prompt).

        Returns:
            str: The generated summary or an error message.
        """
        if not context or context.startswith("Error"):
            return "Error: Invalid context for summarization."

        # Enhanced prompt for structured summarization
        prompt = (
            "Summarize this document. Start with a two-sentence introduction to the document's main topic, "
            "then provide a concise list of 3-5 key facts (names, dates, figures) in bullet points.\n"
            f"Document Text: '''{context}'''"
        )
        return self._call_gemini_api(prompt)

    def holistic_analysis(self, contexts: list[str], prompt: str) -> dict:
        """
        Analyzes and compares information across multiple documents (contexts)
        to answer a holistic question. It enforces a strict, 3-point comparison
        and summary format.

        Args:
            contexts (list[str]): A list of extracted text strings (one per document).
            prompt (str): The overall comparison question.

        Returns:
            dict: A dictionary containing intermediary results, the final synthesis,
                  and the original prompt.
        """
        if not contexts or any(c.startswith("Error") for c in contexts):
            return {"error": "Invalid contexts for holistic analysis."}

        intermediary_results = []
        form_names = [f"Document {i+1}" for i, _ in enumerate(contexts)]

        # 1. Intermediary Q&A (Sequential processing of each document)
        for i, c in enumerate(contexts):
            form_name = form_names[i]

            # UPDATED q_prompt for strict 3-point extraction
            q_prompt = (
                f"Document: '''{c}'''\n"
                f"Question: {prompt}\n"
                "Extract **EXACTLY THREE KEY FACTS** relevant to the question from this document. "
                "Format your response as a numbered list (1., 2., 3.) of facts. "
                "If the document is completely irrelevant or does not contain 3 distinct facts, reply ONLY with 'Document is irrelevant'."
            )
            answer = self._call_gemini_api(q_prompt)
            intermediary_results.append({"form": form_name, "answer": answer})

            # FIX: Add a sleep delay to prevent 429 "Too Many Requests" errors
            time.sleep(1)

        # 2. Final Synthesis (Combine all intermediary answers)

        combined_prompt = (
            "You are a comparison expert. Your task is to synthesize the extracted information from the documents. "
            f"The original question was: '{prompt}'.\n\n"
            # Provide all intermediary results clearly
            + "\n".join(
                [
                    f"{r['form']} Extracted Facts:\n{r['answer']}"
                    for r in intermediary_results
                ]
            )
            + "\n\n"
            # STRICT INSTRUCTIONS FOR THE FINAL OUTPUT
            "**FINAL ANSWER FORMAT IS CRITICAL.** Your entire response must be a direct comparison in the following format, with exactly 5 lines (3 comparison, 2 summary) and no extra text, preambles, or headings:"
            "\n\n"
            f"Comparison Point 1: [Short comparative statement about {form_names[0]} and {form_names[1]}]\n"
            f"Comparison Point 2: [Short comparative statement about {form_names[0]} and {form_names[1]}]\n"
            f"Comparison Point 3: [Short comparative statement about {form_names[0]} and {form_names[1]}]\n"
            f"{form_names[0]} Summary: [One-sentence summary of the 3 key facts extracted or 'Document was irrelevant']\n"
            f"{form_names[1]} Summary: [One-sentence summary of the 3 key facts extracted or 'Document was irrelevant']"
        )
        final_synthesis = self._call_gemini_api(combined_prompt)

        return {
            "holistic_prompt": prompt,
            "intermediary_results": intermediary_results,
            "final_synthesis": final_synthesis,
            "structured_data": {},
        }
