import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()
LLM = ChatOpenAI (model="gpt-4o-mini")
print(LLM.invoke("Hello hello hey").content)