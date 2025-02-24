import argparse
import os
import time
import requests
import re


def clean_filename(input_string):
    allowed_chars = r'[a-zA-Z .-]'
    output_string = re.sub(r'[^' + allowed_chars + ']', '', input_string)
    return output_string


def extract_gutenberg_book_content(text):
    """
    Extracts the main book content from a Project Gutenberg text, removing the header,
    license, title, and table of contents.
    Args:
        text: The text content of the ebook
    Returns:
        A string containing only the book content.
    """
    # General start and end markers for any Project Gutenberg book
    start_marker_pattern = r'\*\*\* START OF [^\*]+ \*\*\*'
    end_marker_pattern = r'\*\*\* END OF [^\*]+ \*\*\*'
    # Find the start and end of the actual book content
    start_match = re.search(start_marker_pattern, text)
    end_match = re.search(end_marker_pattern, text)
    if not start_match or not end_match:
        return text
    content_start = start_match.end()
    content_end = end_match.start()
    book_content = text[content_start:content_end].strip()
    # Remove common patterns for title and table of contents
    book_content = re.sub(r'^\s*[-\w\s]+by[-\w\s]+\n+', '', book_content, flags=re.IGNORECASE)
    book_content = re.sub(r'\s*Table of Contents\s*[\s\S]+?([IVXLCDM]+[\.\s])', r'\1', book_content,
                          flags=re.IGNORECASE)
    return book_content.strip()


def download_book(book_url, output_dir, filename):
    # Clean filename
    filename = clean_filename(filename)
    # Skip if it already exists
    output_file = os.path.join(output_dir, f"{filename}.txt")
    if os.path.exists(output_file):
        print(f"File {output_file} already exists, skipping")
        return

    # Download the book content
    response = requests.get(book_url)
    response.raise_for_status()
    time.sleep(1)  # Let's not hammer the API

    # Decode content for cleaning
    book_text = response.content.decode('utf-8')
    # Clean the book content
    cleaned_book_text = extract_gutenberg_book_content(book_text)

    # Save the cleaned book content to a TXT file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(cleaned_book_text)

    print(f"Downloaded and cleaned {output_dir}/{filename}.txt")


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Query and save books from Project Gutenberg')
    parser.add_argument('--output_dir', required=True, help='Output directory to save books')
    parser.add_argument('--topic', required=True, help='Topic of books e.g. horror')
    parser.add_argument('--num_records', type=int, required=True, help='Number of records to retrieve')
    args = parser.parse_args()

    print(f"Querying '{args.topic}' topic books for download into {args.output_dir}")

    # Create the output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    # Base URL for querying Project Gutenberg
    base_url = "https://gutendex.com/books/"

    # Query parameters
    params = {
        "languages": "en",
        "copyright": "false",
        "topic": args.topic,
        "mime-type": "text/plain",
    }

    already_downloaded = 0
    while already_downloaded < args.num_records:
        # Send the request and get the response
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        # Parse the response JSON
        data = response.json()

        if data['count'] == 0:
            print(f"⚠️ Got no results for {args.topic}. Unable to download {args.num_records} files.")
            break

        for book in data['results']:
            try:
                book_url = book['formats']['text/plain; charset=us-ascii']
                if len(book['authors']) == 0:
                    author = "Unknown Author"
                else:
                    author = book['authors'][0]['name']

                filename = f"{author} - {book['title']}"
                download_book(book_url, args.output_dir, filename)
                already_downloaded += 1
                if already_downloaded >= args.num_records:
                    break
            except KeyError:
                print(f"Skipping book {book['title']} due to error (Probably TXT format is not available.)")
            except Exception as e:
                print(f"Skipping book {book['title']} due to an unexpected error: {e}")

        if already_downloaded < args.num_records and data['next'] is not None:
            print(f"Navigating to next page ({data['next']}).")
            params = None  # Remove params now
            base_url = data['next']
        else:
            break  # No more pages found
    print(f"✅ Done. Downloaded {already_downloaded} books.")


if __name__ == '__main__':
    main()