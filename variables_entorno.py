from dotenv import load_dotenv
import os

load_dotenv()
print(os.getenv("GEMINI_API_KEY") is not None)
# o el nombre de tu variable, si tu proveedor no es Gemini