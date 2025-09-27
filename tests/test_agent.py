# import os
# import sys
# import pytest
# from unittest.mock import patch, MagicMock

# # --- CRITICAL FIX: Add the project's root directory to the Python path ---
# # This allows the 'src' directory to be available for imports.
# PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# sys.path.append(PROJECT_ROOT)
# # -----------------------------------------------------------------------

# # CORRECTED IMPORT: Since the project root is now in the path,
# # you should import from 'src.agent' which is the location of the module.
# from src.agent import IntelligentFormAgent

# # Define the data folder path
# DATA_DIR = os.path.join(PROJECT_ROOT, "data")


# # --- Fixture to create a temporary Agent instance for testing ---
# @pytest.fixture
# def agent_mocked(monkeypatch):
#     """
#     Creates an IntelligentFormAgent instance and mocks the API key retrieval
#     to prevent real API calls during initialization.
#     """

#     # Mock the get_gemini_api_key function to return a dummy key
#     def mock_get_key():
#         return "MOCKED_API_KEY_12345"

#     # --- FIX 1: Corrected path for mocking utils function ---
#     # The utils file is located at src/utils.py relative to the path.
#     monkeypatch.setattr("src.utils.get_gemini_api_key", mock_get_key)

#     # --- FIX 2: Corrected path for mocking requests.post ---
#     # The 'requests' module is used *inside* src.agent.
#     with patch("src.agent.requests.post"):
#         return IntelligentFormAgent()


# # --- Test Cases for File Processing (No changes needed here, logic is sound) ---


# def test_pdf_extraction_success(agent_mocked):
#     """Tests the agent's ability to extract text from a sample PDF."""
#     pdf_path = os.path.join(DATA_DIR, "sample_invoice.pdf")

#     # Ensure the sample file exists before running the test
#     if not os.path.exists(pdf_path):
#         pytest.skip(
#             f"Test skipped: Sample file not found at {pdf_path}. Please create one."
#         )

#     file_type = "pdf"

#     try:
#         # Open the file in binary mode and pass the file object
#         with open(pdf_path, "rb") as f:
#             extracted_text = agent_mocked.process_form(f, file_type)

#         # Assertions: Check if the text is not an error message and contains expected keywords
#         assert not extracted_text.startswith("Error")
#         assert len(extracted_text) > 50  # Check for reasonable length
#         assert any(
#             keyword in extracted_text.lower()
#             for keyword in ["invoice", "total", "date"]
#         )

#     except Exception as e:
#         pytest.fail(f"PDF Extraction failed with unexpected error: {e}")


# def test_unsupported_file_type(agent_mocked):
#     """Tests handling of an unsupported file type."""
#     unsupported_content = MagicMock()
#     file_type = "xlsx"

#     result = agent_mocked.process_form(unsupported_content, file_type)

#     assert result == "Unsupported file type."


# # --- Test Cases for LLM Functionality (MOCKED - Logic is sound) ---


# def test_answer_question_mocked_llm(agent_mocked):
#     """Tests the answer_question function using a mocked Gemini API call."""

#     mock_context = "The client's name is John Doe. Invoice number: INV-2024-55."
#     mock_question = "What is the client's name?"

#     # Mock the internal API call method (_call_gemini_api)
#     with patch.object(agent_mocked, "_call_gemini_api") as mock_api:
#         # Define what the mock should return when called
#         mock_api.return_value = "John Doe"

#         result = agent_mocked.answer_question(mock_context, mock_question)

#         # Check that the API was called exactly once
#         mock_api.assert_called_once()
#         # Check that the function returned the mocked result
#         assert result == "John Doe"
#         # Verify the prompt sent to the LLM contains the context and question
#         assert mock_question in mock_api.call_args[0][0]
#         assert mock_context in mock_api.call_args[0][0]


# def test_holistic_analysis_mocked_llm(agent_mocked):
#     """Tests the holistic_analysis function flow with a mocked Gemini API call."""

#     mock_contexts = ["Doc 1 details.", "Doc 2 details."]
#     mock_prompt = "Compare the dates."

#     # Mock the internal API call method (_call_gemini_api)
#     with patch.object(agent_mocked, "_call_gemini_api") as mock_api:

#         # Set return values for the intermediary QA calls (2 calls) and the final synthesis (1 call)
#         # Note: You should update your agent.py with the sleep fix if it's not present.
#         mock_api.side_effect = [
#             "1. Date is 2024-01-15",
#             "1. Date is 2024-03-20",
#             "Synthesis complete: Doc 1 is earlier.",
#         ]

#         result = agent_mocked.holistic_analysis(mock_contexts, mock_prompt)

#         # Check that the API was called exactly 3 times (2 QA + 1 Synthesis)
#         assert mock_api.call_count == 3
#         # Check that the final synthesis result is correct
#         assert result["final_synthesis"] == "Synthesis complete: Doc 1 is earlier."
#         # Check the intermediary results were captured
#         assert result["intermediary_results"][0]["answer"] == "1. Date is 2024-01-15"
