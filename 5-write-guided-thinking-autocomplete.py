import argparse
import sqlite3
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import re

# Global lock for database updates
db_lock = threading.Lock()
BATCH_SIZE = 5  # Number of threads before updating the database

# Prompt template with placeholders for database content
PROMPT_TEMPLATE_TO_GENERATE_GUIDANCE = """### System: You are a Writer’s Assistant.

### Task: Read the beginning of a story, and the continuation. Very briefly and in a single sentence, summarize how the
story continues in the Continuation.

### Beginning:
{prompt}

### Continuation:
{response}
"""
# Prompt template with placeholders for database content
PROMPT_TEMPLATE_TO_GENERATE_THOUGHT_PROCESS = """### System: You are a Writer’s Assistant.

### Task: Read the beginning of a story, and the continuation. Understand how the story flows, what motivations the 
characters have and how they will interact with each other and the world. Reconstruct the internal monologue of the
Author, that resulted in the continuation of the story. The Author had guidance to help determine the direction of 
the story. Only respond with the internal monologue please. Think step by step within the monologue. Always keep in
mind what happens in the Continuation and if you can, include dialogue or event pieces from in it in the internal
monologue, if it was an idea. Repeat relevant parts of the guidance during the internal monologue when planning the 
next steps.

### Beginning:
{prompt}th

### Guidance: 
{guidance}

### Continuation:
{response}
"""

# Thought process prompt template
THOUGHT_PROCESS_TEMPLATE = """### Task: Understand how the story flows, what motivations the characters have and how 
they will interact with each other and the world as a step by step thought process before continuing the story. Keep
the guidance in mind when writing the story.

### Guidance: {guidance}

### Context:
{context}
"""

def call_openrouter(chunk, api_key):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [{
            "role": "user",
            "content": chunk
        }],
        "temperature": 0.5,
        "provider": {
            "allow_fallbacks": False,
            "order": ["DeepSeek", "DeepInfra", "Fireworks"]
        }
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content'].replace("```json", "").replace("```", "")
    except Exception as e:
        return f"Error: {str(e)}"


def call_ollama(chunk, api_key):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "qwen2.5:latest",
        "messages": [{
            "role": "user",
            "content": chunk
        }],
        "temperature": 0.5,
        "stream": False,
        "options": {
            "num_ctx": 16384
        }
    }

    try:
        response = requests.post(
            "http://127.0.0.1:11434/api/chat",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        return result['message']['content']
    except Exception as e:
        return f"Error: {str(e)}"


def create_database():
    conn = sqlite3.connect('text_chunks.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            chunk TEXT,
            response TEXT
        )
    ''')
    conn.commit()
    return conn


import re

def process_chunk(task, api_key, results):
    chunk_id, source, prompt, response = task

    # Extract the part of the prompt after '#Context:'
    match = re.search(r"#Context:(.*)", prompt, re.DOTALL)
    if match:
        prompt = match.group(1).strip()

    # Write guidance
    guidance_prompt = PROMPT_TEMPLATE_TO_GENERATE_GUIDANCE.format(prompt=prompt, response=response)
    guidance_response = call_ollama(guidance_prompt, '');

    filled_prompt = PROMPT_TEMPLATE_TO_GENERATE_THOUGHT_PROCESS.format(prompt=prompt, guidance=guidance_response, response=response)
    thought_prompt = THOUGHT_PROCESS_TEMPLATE.format(guidance=guidance_response, context=prompt)
    final_response = call_openrouter(filled_prompt, api_key)

    if "Error:" not in final_response:
        final_response = (f"<reasoning>{final_response}</reasoning>"
                          f"<answer>{response}</answer>")
        results.append((source, thought_prompt, final_response))
    else:
        print(f"Failed to process chunk ID {chunk_id}: {final_response}")

    return chunk_id




def update_database(results):
    if not results:
        return
    conn = sqlite3.connect('text_chunks.db')
    c = conn.cursor()
    with db_lock:
        c.executemany('''INSERT INTO training_data (source, type, subtype, prompt, response) 
                          VALUES (?, 'generative', 'thinking-guided-autocomplete', ?, ?)''',
                      [(source, thought_prompt, final_responsee) for source, thought_prompt, final_responsee in results])
    conn.commit()
    conn.close()
    results.clear()


def main():
    parser = argparse.ArgumentParser(
        description='Process text chunks from SQLite database and generate character extraction responses.')
    parser.add_argument('--api_key', type=str, required=True, help='OpenRouter API key')
    args = parser.parse_args()

    conn = sqlite3.connect('text_chunks.db')
    c = conn.cursor()
    c.execute("SELECT id, source, prompt, response FROM training_data WHERE type='generative' and (subtype='cc0-autocomplete' or subtype='autocomplete') order by random() limit 1500")
    chunks_to_process = c.fetchall()
    conn.close()

    results = []

    with tqdm(total=len(chunks_to_process), desc="Processing chunks") as pbar:
        with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
            futures = []
            for task in chunks_to_process:
                futures.append(executor.submit(process_chunk, task, args.api_key, results))
                if len(futures) >= BATCH_SIZE:
                    for future in as_completed(futures):
                        future.result()
                        pbar.update(1)
                    update_database(results)
                    futures.clear()

            for future in as_completed(futures):
                future.result()
                pbar.update(1)
            update_database(results)

    print(f"✅ Done. Processing of all chunks completed and results saved in the SQLite database.")


if __name__ == "__main__":
    main()