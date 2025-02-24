import sqlite3
import nltk
from nltk.tokenize import sent_tokenize
import argparse
from tqdm import tqdm

# Initialize NLTK data
nltk.download('punkt')


def initialize_database(conn):
    """Create the training_data table if it doesn't exist."""
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS training_data
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      source TEXT,
                      type TEXT,
                      subtype TEXT,
                      prompt TEXT,
                      response TEXT)''')
    conn.commit()


def fetch_generative_chunks(conn):
    """Fetch chunks of type 'generative' from the database."""
    cursor = conn.cursor()
    cursor.execute('SELECT source, chunk FROM chunks WHERE type = "extraction" and chunks.source not in (select source from chunks where type = "generative") order by random() limit 500')
    return cursor.fetchall()


def split_chunk(chunk):
    """Split a chunk into prompt (60%) and response (40%) at sentence boundaries."""
    sentences = sent_tokenize(chunk)
    total_length = len(' '.join(sentences))

    # Calculate the approximate split point at 60% of total length
    split_point = int(0.6 * total_length)
    current_length = 0

    prompt_sentences = []
    for sentence in sentences:
        sentence_length = len(sentence) + 1  # Adding space
        if current_length + sentence_length <= split_point:
            prompt_sentences.append(sentence)
            current_length += sentence_length
        else:
            break

    prompt = ' '.join(prompt_sentences)
    response = ' '.join(sentences[len(prompt_sentences):])

    return prompt, response


def process_chunks(conn, chunks):
    """Process chunks and insert into training_data table."""
    cursor = conn.cursor()
    for source, chunk in tqdm(chunks, desc="Processing chunks", unit="chunk"):
        prompt, response = split_chunk(chunk)
        prompt = (f"#System: You are a writer's assistant.\n"
                  f"\n"
                  f"#Task: Read the story in the context, understand characters, motivations and continue it for a few sentences.\n"
                  f"\n"
                  f"#Context: \n{prompt}")
        cursor.execute('''INSERT INTO training_data
                         (source, type, subtype, prompt, response)
                         VALUES (?, 'generative', 'cc0-autocomplete', ?, ?)''',
                       (source, prompt, response))
    conn.commit()

def main():
    parser = argparse.ArgumentParser(description='Generate training data for autocomplete.')
    parser.add_argument('--database', type=str, required=False, default="text_chunks.db",
                        help='Path to the SQLite database file')
    args = parser.parse_args()

    with sqlite3.connect(args.database) as conn:
        initialize_database(conn)
        chunks = fetch_generative_chunks(conn)
        process_chunks(conn, chunks)


if __name__ == "__main__":
    main()