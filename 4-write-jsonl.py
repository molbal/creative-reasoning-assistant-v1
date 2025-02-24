import sqlite3
import json
from tqdm import tqdm


def main():
    # Connect to the SQLite database
    try:
        conn = sqlite3.connect('../text_chunks.db')
        cursor = conn.cursor()

        # Query the training_data table for all records
        cursor.execute("""
            SELECT type, subtype, prompt, response
            FROM main.training_data
        """)

        # Fetch all the records
        records = cursor.fetchall()

        # Create a dictionary to hold entries grouped by (type, subtype)
        grouped_entries = {}

        for record in records:
            type_, subtype, prompt, response = record

            # Initialize the dictionary for the (type, subtype) if it doesn't exist
            if (type_, subtype) not in grouped_entries:
                grouped_entries[(type_, subtype)] = []

            # Create the message structure
            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response}
            ]
            grouped_entries[(type_, subtype)].append({"messages": messages})

        # Write the JSONL files
        for (type_, subtype), entries in grouped_entries.items():
            filename = f'dataset-{type_}-{subtype}.jsonl'
            with open(filename, 'w', encoding='utf-8') as jsonl_file:
                # Use tqdm for progress bar during writing
                for entry in tqdm(entries, desc=f'Writing to {filename}', unit='entry'):
                    json_line = json.dumps(entry, ensure_ascii=False)
                    jsonl_file.write(json_line + '\n')
            print(f"JSONL file '{filename}' has been created successfully.")

    except sqlite3.OperationalError as e:
        print(f"Error connecting to database: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the database connection
        if conn:
            conn.close()


if __name__ == "__main__":
    main()