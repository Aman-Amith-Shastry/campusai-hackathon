import requests
from bs4 import BeautifulSoup
import re

def scrape_and_save(url, major):
    # Check if URL is a Google Docs link and convert to export URL
    if "docs.google.com/document/d/" in url:
        match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', url)
        if match:
            doc_id = match.group(1)
            url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"

    response = requests.get(url)
    response.raise_for_status()

    if "docs.google.com/document/d/" in url and url.endswith("format=txt"):
        text = response.text
    else:
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(separator='\n')

    with open(f"{major}.txt", "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Extracted {len(text)} characters.")

# Example usage:
scrape_and_save("https://docs.google.com/document/d/1pd9-kPsnGRNls8Aa_1YFrjOUIPdSWtSO3IYLWwd7fHY/edit", "data_science_coe")
# scrape_and_save("https://example.com/page", "some_major")
