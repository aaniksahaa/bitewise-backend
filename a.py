from dotenv import load_dotenv
import os

load_dotenv()

# Get the raw value from os.getenv
raw_url = os.getenv("DATABASE_URL")
print("Raw URL from os.getenv:", raw_url)

# Replace \x3a escape sequences with :
decoded_url = raw_url.replace("\\x3a", ":") if raw_url else None
print("Decoded URL:", decoded_url)