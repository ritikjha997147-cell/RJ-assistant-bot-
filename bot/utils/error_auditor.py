import traceback
from google import genai
from bot.config import GEMINI_API_KEY  # सुनिश्चित करें कि आपके config में यह की मौजूद है

def analyze_and_fix_error(error: Exception, file_context: str = "Unknown File") -> str:
    """
    यह फंक्शन एरर ट्रेसबैक को जेमिनी एआई के पास भेजता है और सुधरा हुआ कोड मांगता है।
    """
    try:
        tb_lines = traceback.format_exception(type(error), error, error.__traceback__)
        tb_text = "".join(tb_lines)
        
        # Initialize Gemini Client
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""
        You are an expert Python developer auditing a Telegram bot. 
        An error occurred in the system.
        
        File Context: {file_context}
        Error Traceback:
        {tb_text}
        
        Please analyze this error and provide ONLY the corrected Python code that fixes this bug.
        Do not write any explanations, do not use markdown code blocks like ```python. 
        Just return the pure raw executable Python code.
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        
        return response.text.strip()
    except Exception as e:
        return f"AI Error Diagnostics Failed: {str(e)}"