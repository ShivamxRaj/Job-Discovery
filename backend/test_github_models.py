import asyncio
import os
import openai
from dotenv import load_dotenv

# Load env variables
load_dotenv(dotenv_path="d:\\ai\\.env")

async def test():
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = "https://models.inference.ai.azure.com"
    client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
    
    print("\n1. Testing short model name 'text-embedding-3-small'...")
    try:
        response = await client.embeddings.create(
            input="Hello world",
            model="text-embedding-3-small"
        )
        print(f"-> Success! Embedding length: {len(response.data[0].embedding)}")
    except Exception as e:
        print(f"-> Failed: {e}")
        
    print("\n2. Testing short model name 'gpt-4o-mini'...")
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello! Reply with 'OK'"}]
        )
        print(f"-> Success! Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"-> Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test())
