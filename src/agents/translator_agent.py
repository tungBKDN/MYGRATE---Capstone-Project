import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv

class TranslatorAgent:
    """
    Translator Agent responsible for performing Smart 1-to-1 Mapping 
    and code transformations.
    """
    def __init__(self, model_name: str = None):
        load_dotenv()
        if model_name is None:
            model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        api_key = os.getenv("GROQ_API_KEY")
        self.llm = ChatGroq(model_name=model_name, groq_api_key=api_key, temperature=0)

    def run(self, instruction: str) -> str:
        print(f"-> [TRANSLATOR] Migrating code: {instruction[:50]}...")
        # Simple implementation for now, will be expanded with AST tools
        response = self.llm.invoke([
            ("system", "You are an expert software engineer specialized in refactoring and migration."),
            ("user", instruction)
        ])
        return response.content
