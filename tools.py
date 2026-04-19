import os
import requests
from dotenv import load_dotenv
import base64
load_dotenv()


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "rashadmin")  
BASE_URL = "https://api.github.com"
HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}","Accept": "application/vnd.github.v3+json",}

def get_readme_content(repo_url: str) -> str | None:
    """Fetch the decoded README for a single repo. Returns None if absent."""
    readme_url = f"{repo_url}/readme"
    resp = requests.get(readme_url, headers=HEADERS, timeout=10)
    if resp.status_code != 200:
        return None
    data = resp.json()
    try:
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        content = content.replace('\n',' ').replace('#','').replace('>','').replace('|','').replace('-','')
        return content
    except Exception:
        return None


def owner() -> str:
    """Return the authenticated GitHub username."""
    r = requests.get(f"{BASE_URL}/user", headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()["login"]
