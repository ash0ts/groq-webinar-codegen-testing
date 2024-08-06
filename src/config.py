from dotenv import load_dotenv
import random

load_dotenv()

WEAVE_PROJECT = "groq-testing-generated-code-webinar"
MAX_RETRIES = 100
SEEDS = random.sample(range(1000001), MAX_RETRIES)
MODELS = [
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
    # "llama3-groq-70b-8192-tool-use-preview",
]
