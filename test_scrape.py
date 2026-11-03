import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}
urls = [
    'https://scholarship.odisha.gov.in/website/scholarship-details', 
    'https://scholarships.gov.in/All-Scholarships'
]

for url in urls:
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        print(f"--- {url} ---")
        print("Title:", soup.title.string if soup.title else "No title")
        print("Content length:", len(r.text))
        print("Snippet:", r.text[:200].replace('\n', ' '))
    except Exception as e:
        print(f"Failed {url}: {e}")
