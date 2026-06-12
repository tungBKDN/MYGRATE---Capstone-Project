import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

load_dotenv()

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

print("Testing ChatOllama connection...")
base_url = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
api_key = os.getenv("OLLAMA_KEY", "")
model_name = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")

print(f"Base URL: {base_url}")
print(f"Model: {model_name}")
print(f"API Key present: {bool(api_key)}")

try:
    kwargs = {
        "model": model_name,
        "base_url": base_url,
        "temperature": 0,
    }
    if api_key:
        kwargs["client_kwargs"] = {"headers": {"Authorization": f"Bearer {api_key}"}}
        kwargs["async_client_kwargs"] = {"headers": {"Authorization": f"Bearer {api_key}"}}
        
    llm = ChatOllama(**kwargs)
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="Hello! Respond with exactly the word 'OK' if you can hear me.")
    ]
    print("Invoking LLM...")
    response = llm.invoke(messages)
    print("Success!")
    print(f"Response: {response}")
except Exception as e:
    print(f"ERROR: {e}")
