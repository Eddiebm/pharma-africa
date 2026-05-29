"""
Scraper Generator — uses OpenRouter to write a new scraper given portal HTML.
"""
import os
import re
import httpx
from openai import OpenAI
from pathlib import Path

BODIES_DIR = Path(__file__).parent.parent / "scraper" / "bodies"
EXAMPLES = ["zamra_zambia.py", "ghana_fda.py", "rwanda_rda.py", "ppb_kenya.py"]

def _load_examples() -> str:
    out = []
    for fname in EXAMPLES:
        p = BODIES_DIR / fname
        if p.exists():
            out.append(f"### Example: {fname}\n```python\n{p.read_text()}\n```")
    return "\n\n".join(out)

def _load_base() -> str:
    p = Path(__file__).parent.parent / "scraper" / "base.py"
    return p.read_text() if p.exists() else ""

def fetch_portal(url: str, timeout: int = 20) -> str:
    """Fetch portal HTML, return truncated content for analysis."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; research bot)"}
        r = httpx.get(url, headers=headers, timeout=timeout,
                      follow_redirects=True, verify=False)
        return r.text[:12000]
    except Exception as e:
        return f"FETCH_ERROR: {e}"

MODEL = "models/gemini-2.5-flash-lite"

def generate_scraper(market: dict, portal_html: str) -> str | None:
    """Call Gemini via Google's OpenAI-compatible endpoint to generate a scraper."""
    client = OpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=os.environ["GEMINI_API_KEY"],
    )

    base_src = _load_base()
    examples_src = _load_examples()

    prompt = f"""You are an expert Python web scraper engineer. Your task is to write a scraper for an African pharmaceutical regulatory portal.

## Base class interface (must extend this)
```python
{base_src}
```

## Existing scrapers to follow as examples
{examples_src}

## Target market
Country: {market['country']}
Country code (ISO 3166-1 alpha-3): {market['code']}
Regulatory body code: {market['body']}
Full body name: {market['body_full']}
Portal URL: {market['portal_hint']}
Language: {market['lang']}

## Portal HTML (first 12000 chars)
```html
{portal_html[:8000]}
```

## Instructions
1. Write a complete Python scraper following the exact pattern of the examples
2. Class name: `{market['country'].replace(' ', '').replace('-', '')}Scraper`
3. `body_code` = `"{market['body']}_{market['code']}"`
4. `country_code` = `"{market['code']}"`
5. The `fetch()` method must return `list[RegistrationRecord]`
6. Use httpx (not requests). Handle pagination. De-duplicate by registration_no.
7. If the portal requires search queries, use short common prefixes like single letters a-z
8. If the portal has no public drug search (government homepage only), return [] with a log.warning explaining why
9. Map available fields to RegistrationRecord: inn, brand_name, registration_no, holder, status, expiry_date, dosage_forms
10. Add a module docstring explaining the portal strategy
11. Import from: base, normalize, os, logging, httpx, bs4

Output ONLY the Python source code, no explanation, no markdown fences."""

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
            )

    code = response.choices[0].message.content.strip()
    # Strip markdown fences if the model added them anyway
    code = re.sub(r"^```python\n?", "", code)
    code = re.sub(r"\n?```$", "", code)

    # Validate: must contain a class extending BaseRegulatoryScraper
    if "BaseRegulatoryScraper" not in code:
        # Retry once with a harder instruction
        retry_prompt = prompt + "\n\nIMPORTANT: Your previous response was incomplete. You MUST output a complete Python class that extends BaseRegulatoryScraper. Even if the portal has no public drug search, write the class with fetch() returning []."
        response2 = client.chat.completions.create(
            model=MODEL,
            max_tokens=8192,
            messages=[{"role": "user", "content": retry_prompt}],
                    )
        code = response2.choices[0].message.content.strip()
        code = re.sub(r"^```python\n?", "", code)
        code = re.sub(r"\n?```$", "", code)

    return code
