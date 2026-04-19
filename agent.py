import base64
import json
import logging
import os
import sys

import faiss
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from tools import get_readme_content
from google import genai
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.genai import types
from google.genai import types as genai_types
from pydantic import BaseModel
from google.adk.agents import Agent,SequentialAgent,LlmAgent,ParallelAgent
from google.adk.models.lite_llm import LiteLlm
load_dotenv()


# Logging 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app.log"),
    ],
)

logger = logging.getLogger("resume_agent_api")


# Environment 
GITHUB_TOKEN   = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER   = os.getenv("GITHUB_OWNER", "rashadmin")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GITHUB_TOKEN:
    logger.warning("GITHUB_TOKEN is not set — GitHub API calls will fail")
if not GOOGLE_API_KEY:
    logger.warning("GOOGLE_API_KEY is not set — embedding calls will fail")

BASE_URL = "https://api.github.com"
HEADERS  = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept":        "application/vnd.github.v3+json",
}



import hashlib
import pickle
import time as _time
 
BASE_DIR        = os.path.dirname(__file__)
CACHE_DIR       = os.path.join(BASE_DIR, "output", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
 
README_TTL      = 7 * 24 * 3600   # 7 days
QUERY_TTL       = 24 * 3600       # 24 hours
EXTRACTION_TTL  = 24 * 3600       # 24 hours
 
 
class ResumeCache:
    """Manages all four cache levels for the resume builder pipeline."""
 
    # ── helpers ───────────────────────────────────────────────────────────────
 
    @staticmethod
    def _sha(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]
 
    @staticmethod
    def _jpath(filename: str) -> str:
        return os.path.join(CACHE_DIR, filename)
 
    @staticmethod
    def _load_json(path: str) -> dict | None:
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return None
 
    @staticmethod
    def _save_json(path: str, data: dict) -> None:
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False)
 
    # ── Level 1 — README content ──────────────────────────────────────────────
 
    @staticmethod
    def get_readme(repo_name: str, pushed_at: str) -> str | None:
        """Return cached README text if still fresh, else None."""
        key  = f"{repo_name}:{pushed_at}"
        path = ResumeCache._jpath(f"readme_{ResumeCache._sha(key)}.json")
        data = ResumeCache._load_json(path)
        if data and _time.time() - data.get("ts", 0) < README_TTL:
            logger.info(f"[CACHE L1] HIT  readme:{repo_name}")
            return data["content"]
        return None
 
    @staticmethod
    def set_readme(repo_name: str, pushed_at: str, content: str) -> None:
        key  = f"{repo_name}:{pushed_at}"
        path = ResumeCache._jpath(f"readme_{ResumeCache._sha(key)}.json")
        ResumeCache._save_json(path, {"content": content, "ts": _time.time()})
        logger.info(f"[CACHE L1] SET  readme:{repo_name}")
 
    # ── Level 2 — FAISS index ─────────────────────────────────────────────────
 
    @staticmethod
    def _index_version(repo_keys: list[str]) -> str:
        """Stable hash of sorted repo cache keys — changes only when a repo changes."""
        return ResumeCache._sha("|".join(sorted(repo_keys)))
 
    @staticmethod
    def get_index(repo_keys: list[str]) -> tuple[object, list, list] | None:
        """Return (faiss_index, repos, contents) if cached index matches current repos."""
        ver       = ResumeCache._index_version(repo_keys)
        meta_path = ResumeCache._jpath(f"index_{ver}_meta.json")
        idx_path  = ResumeCache._jpath(f"index_{ver}.faiss")
        meta      = ResumeCache._load_json(meta_path)
        if not meta or not os.path.exists(idx_path):
            return None
        try:
            idx = faiss.read_index(idx_path)
            logger.info(f"[CACHE L2] HIT  faiss index version={ver}")
            return idx, meta["repos"], meta["contents"]
        except Exception:
            return None
 
    @staticmethod
    def set_index(repo_keys: list[str], index, repos: list, contents: list) -> None:
        ver       = ResumeCache._index_version(repo_keys)
        meta_path = ResumeCache._jpath(f"index_{ver}_meta.json")
        idx_path  = ResumeCache._jpath(f"index_{ver}.faiss")
        faiss.write_index(index, idx_path)
        ResumeCache._save_json(meta_path, {"repos": repos, "contents": contents, "ts": _time.time()})
        logger.info(f"[CACHE L2] SET  faiss index version={ver}")
 
    # ── Level 3 — Query results ───────────────────────────────────────────────
 
    @staticmethod
    def _query_key(job_description: str, repo_keys: list[str]) -> str:
        ver = ResumeCache._index_version(repo_keys)
        return ResumeCache._sha(job_description + ver)
 
    @staticmethod
    def get_query(job_description: str, repo_keys: list[str]) -> list | None:
        key  = ResumeCache._query_key(job_description, repo_keys)
        path = ResumeCache._jpath(f"query_{key}.json")
        data = ResumeCache._load_json(path)
        if data and _time.time() - data.get("ts", 0) < QUERY_TTL:
            logger.info(f"[CACHE L3] HIT  query key={key}")
            return data["matches"]
        return None
 
    @staticmethod
    def set_query(job_description: str, repo_keys: list[str], matches: list) -> None:
        key  = ResumeCache._query_key(job_description, repo_keys)
        path = ResumeCache._jpath(f"query_{key}.json")
        ResumeCache._save_json(path, {"matches": matches, "ts": _time.time()})
        logger.info(f"[CACHE L3] SET  query key={key}")
 
    # ── Level 4 — Extraction payload ─────────────────────────────────────────
 
    @staticmethod
    def get_extraction(match_report: str, job_description: str) -> dict | None:
        key  = ResumeCache._sha(match_report + job_description)
        path = ResumeCache._jpath(f"extraction_{key}.json")
        data = ResumeCache._load_json(path)
        if data and _time.time() - data.get("ts", 0) < EXTRACTION_TTL:
            logger.info(f"[CACHE L4] HIT  extraction key={key}")
            return data["payload"]
        return None
 
    @staticmethod
    def set_extraction(match_report: str, job_description: str, payload: dict) -> None:
        key  = ResumeCache._sha(match_report + job_description)
        path = ResumeCache._jpath(f"extraction_{key}.json")
        ResumeCache._save_json(path, {"payload": payload, "ts": _time.time()})
        logger.info(f"[CACHE L4] SET  extraction key={key}")
 
    # ── Cache management ──────────────────────────────────────────────────────
 
    @staticmethod
    def clear_all() -> int:
        """Delete all cache files. Returns count of files removed."""
        removed = 0
        for f in os.listdir(CACHE_DIR):
            if f.endswith((".json", ".faiss")):
                os.remove(os.path.join(CACHE_DIR, f))
                removed += 1
        logger.info(f"[CACHE] Cleared {removed} cache files")
        return removed
 
    @staticmethod
    def stats() -> dict:
        """Return counts and sizes of cached items by level."""
        files = os.listdir(CACHE_DIR)
        return {
            "readme_entries":     sum(1 for f in files if f.startswith("readme_")),
            "index_versions":     sum(1 for f in files if f.endswith(".faiss")),
            "query_entries":      sum(1 for f in files if f.startswith("query_")),
            "extraction_entries": sum(1 for f in files if f.startswith("extraction_")),
            "total_size_kb":      round(sum(
                os.path.getsize(os.path.join(CACHE_DIR, f)) for f in files
            ) / 1024, 1),
        }
 
 
_cache = ResumeCache()


#  Shared state 
_state: dict = {"index": None, "repos": [],'jd':None, "contents": [], "client": None}


def _get_client() -> genai.Client:
    if _state["client"] is None:
        _state["client"] = genai.Client(api_key=GOOGLE_API_KEY)
    return _state["client"]


def _fetch_readme(repo_url: str) -> str | None:
    """Fetch and base64-decode the README for a single repo API URL."""
    try:
        resp = requests.get(f"{repo_url}/readme", headers=HEADERS)
        if resp.status_code != 200:
            return None
        encoded = resp.json().get("content", "")
        return base64.b64decode(encoded).decode("utf-8", errors="ignore")
    except Exception:
        return None

# AGENT 1 — Repo matcher
# Tools: fetch_and_embed_readmes, query_vector_db

def set_job_description(jd: str) -> dict:
    """
    Stores the job description in shared state.

    Args:
        jd: Job description text (already extracted if from image)

    Returns:
        dict with success status
    """
    logger.info("[TOOL] set_job_description called")

    try:
        if not jd or not jd.strip():
            return {"success": False, "error": "Empty job description"}

        _state["jd"] = jd.strip()

        return {
            "success": True,
            "message": "Job description stored successfully"
        }

    except Exception as e:
        logger.exception("[TOOL] set_job_description failed")
        return {"success": False, "error": str(e)}

def fetch_and_embed_readmes() -> dict:
    """
    Fetch READMEs from every repo the authenticated GitHub user owns,
    generate embeddings with gemini-embedding-001, and store them in a
    FAISS IndexFlatL2 for later similarity search.

    Returns:
        A dict with keys:
          - success (bool)
          - repos_indexed (int)   — number of repos with a README
          - repo_names (list)     — names of indexed repos
          - error (str)           — populated only on failure
    """
    logger.info("[TOOL] fetch_and_embed_readmes called")
    try:
        repo_response = requests.get(f"{BASE_URL}/user/repos", headers=HEADERS)
        repo_list     = repo_response.json()
 
        # ── Level 1 cache: per-repo README — skip fetch if repo unchanged ────
        readmes    = {}
        repo_keys  = []   # "repo_name:pushed_at" — used as L2 cache key
        for repo in repo_list:
            name      = repo["name"].split("/")[-1]
            pushed_at = repo.get("pushed_at", "")
            repo_keys.append(f"{name}:{pushed_at}")
            cached = _cache.get_readme(name, pushed_at)
            if cached is not None:
                readmes[name] = cached
            else:
                content_text = _fetch_readme(repo["url"])
                if content_text:
                    readmes[name] = content_text
                    _cache.set_readme(name, pushed_at, content_text)
        
        
        df = pd.Series(readmes).reset_index().rename(columns={"index": "repo", 0: "content"}).dropna().reset_index(drop=True)
            
        repos: list[str]    = df["repo"].tolist()
        contents: list[str] = df["content"].tolist()

        if not contents:
            return {"success": False, "repos_indexed": 0, "repo_names": [], "error": "No READMEs found."}

	# ── Level 2 cache: FAISS index — skip embedding if nothing changed ───
        cached_index = _cache.get_index(repo_keys)
        if cached_index is not None:
            index, cached_repos, cached_contents = cached_index
            _state["index"]    = index
            _state["repos"]    = cached_repos
            _state["contents"] = cached_contents
            logger.info(f"[TOOL] fetch_and_embed_readmes — L2 cache hit, skipped embedding")
            return {"success": True, "repos_indexed": len(cached_repos),
                    "repo_names": cached_repos, "error": "", "cache": "L2_hit"}

        client = _get_client()
        all_embeddings = []
        for i in range(0, len(contents), 100):
            batch  = contents[i : i + 100]
            result = client.models.embed_content(
                model="gemini-embedding-001",
                contents=batch,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
            )
            all_embeddings.extend([e.values for e in result.embeddings])
            logger.info(f"[TOOL] Embedded batch {i // 100 + 1} ({len(batch)} docs).")

        matrix = np.array(all_embeddings, dtype=np.float32)
        index  = faiss.IndexFlatL2(matrix.shape[1])
        index.add(matrix)

        _state["index"] = index
        _state["repos"] = repos
        _state["contents"] = contents

	        # Save to L2 cache for next run
        _cache.set_index(repo_keys, index, repos, contents)
        

        logger.info(f"[TOOL] FAISS index built — {index.ntotal} vectors")
        return {"success": True, "repos_indexed": len(repos), "repo_names": repos, "error": ""}

    except Exception as e:
        logger.exception("[TOOL] fetch_and_embed_readmes failed")
        return {"success": False, "repos_indexed": 0, "repo_names": [], "error": str(e)}


def query_vector_db(job_description: str, top_k: int = 6) -> dict:
    """
    Embed the job description and retrieve the top-k most relevant repos
    from the FAISS index built by fetch_and_embed_readmes.

    Args:
        job_description: Plain text of the job description.
        top_k:           Number of top matches to return (default 5).

    Returns:
        A dict with keys:
          - success (bool)
          - matches (list[dict])  — rank, repo, distance, readme_preview
          - error (str)
    """
    logger.info(f"[TOOL] query_vector_db called | top_k={top_k}")
    if _state["index"] is None:
        return {"success": False, "matches": [], "error": "Vector DB is empty. Run fetch_and_embed_readmes first."}

    try:
    	# ── Level 3 cache: query results ─────────────────────────────────────
        repo_keys = [f"{r}:{c[:32]}" for r, c in zip(_state["repos"], _state["contents"])]
        cached_matches = _cache.get_query(job_description, repo_keys)
        if cached_matches is not None:
            logger.info(f"[TOOL] query_vector_db — L3 cache hit, skipped embedding + search")
            return {"success": True, "matches": cached_matches, "error": "", "cache": "L3_hit"}
            
        client    = _get_client()
        result    = client.models.embed_content(
            model="gemini-embedding-001",
            contents=[job_description],
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        query_vec = np.array(result.embeddings[0].values, dtype=np.float32).reshape(1, -1)
        k = min(top_k, _state["index"].ntotal)
        distances, indices = _state["index"].search(query_vec, k)

        matches = [{"rank": rank,"repo": _state["repos"][idx],"distance":round(float(dist), 4),"readme_preview": _state["contents"][idx].replace("\n", " "),}for rank, (dist, idx) in enumerate(zip(distances[0], indices[0]), start=1)]
        _cache.set_query(job_description, repo_keys, matches)
        logger.info(f"[TOOL] query_vector_db returned {k} matches")
        return {"success": True, "matches": matches, "error": ""}

    except Exception as e:
        logger.exception("[TOOL] query_vector_db failed")
        return {"success": False, "matches": [], "error": str(e)}


agent_1_repo_matcher = Agent(
    name="agent_1_repo_matcher",
    model="gemini-3.1-flash-lite-preview",
    description=(
        "Fetches the user's GitHub READMEs, embeds them, and retrieves the "
        "repos most semantically relevant to the job description."
    ),
    instruction="""
You are Agent 1 in a resume builder pipeline. Your job is to identify which of
the user's GitHub projects are most relevant to a given job description.

You natively understand images — if the job description arrives as an image or
screenshot, read it directly without a separate OCR step.

## Workflow

### Step 0 — set_job_description
If the user provides a job description (text or image), extract the text and store it using this tool.

### Step 1 — fetch_and_embed_readmes
Always call this first. It fetches every GitHub README owned by the authenticated
user, embeds them, and stores them in a FAISS index.

### Step 2 — query_vector_db
Pass the full job description text to this tool. It returns the top 5 repos
ranked by semantic similarity.

## Output
Return a structured match report:
  - Each repo listed by rank
  - Why it is relevant (from README preview)
  - Similarity distance (lower = better)
  - Flag the top 2 as "strong matches" if distance < 1.0

Do not generate resume content. Your output is consumed by Agent 2.
If any tool returns success: false, report the error and stop.
""",
    tools=[
        FunctionTool(set_job_description),
        FunctionTool(fetch_and_embed_readmes),
        FunctionTool(query_vector_db),
    ],
)


# AGENT 2 — Extraction orchestrator  (4 parallel sub-agents)


def _parse_json_response(raw: str, log_tag: str) -> dict:
    """Strip markdown fences and parse JSON, returning a dict."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    result = json.loads(raw.strip())
    logger.info(f"[TOOL] {log_tag} — JSON parsed OK")
    return result

def _strip_markdown(text: str) -> str:
    """
    Remove markdown formatting from text so it renders as clean plain text
    in a Word document. Preserves snake_case identifiers like medic_ai_agent.
    Removes: **bold**, *italic*, `code`, # headings, [link](url).
    """
    import re as _re
    # Bold: **text** or __text__
    text = _re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = _re.sub(r"__(.+?)__",     r"\1", text)
    # Italic: *text* — single asterisk, not inside **
    text = _re.sub(r"(?<!\*)\*(?!\*)(\S[^*]*?\S|\S)\*(?!\*)", r"\1", text)
    # Italic: _text_ — only when flanked by spaces/punctuation, NOT inside words
    # This preserves snake_case like medic_ai_agent
    text = _re.sub(r"(?<=[\s(,])_([^_\s][^_]*[^_\s]|[^_\s])_(?=[\s),.:;!?]|$)", r"\1", text)
    # Inline code: `text`
    text = _re.sub(r"`(.+?)`", r"\1", text)
    # Headings: # Heading
    text = _re.sub(r"^#{1,6}\s+", "", text, flags=_re.MULTILINE)
    # Links: [text](url) — keep just the text
    text = _re.sub(r"\[(.+?)\]\(.*?\)", r"\1", text)
    # Horizontal rules
    text = _re.sub(r"^[-*_]{3,}\s*$", "", text, flags=_re.MULTILINE)
    # Trailing whitespace per line
    text = _re.sub(r"[ \t]+$", "", text, flags=_re.MULTILINE)
    return text.strip()
 
def extract_all(
    match_report: str,
    job_description: str = "",
    base_summary: str = "",
) -> dict:
    """
    Three-phase ATS-optimised extraction:
 
    Phase 1 — Extract from job description
      Pull required skills, technologies, keywords, and role expectations
      directly from the JD. These become the ATS target list.
 
    Phase 2 — Extract from matched READMEs
      Pull demonstrated skills, technologies, achievements, and project
      details from the candidate's actual repos.
 
    Phase 3 — ATS merge
      Merge JD requirements with repo evidence. JD keywords that have a
      similar demonstrated skill in the repos are included verbatim.
      Experience bullets echo the JD's exact language where possible.
      Skills and technologies lists are JD-first, repo-supplemented.
 
    Args:
        match_report:    Full match report from Agent 1 — complete README content.
        job_description: Raw job description text — parsed first for ATS keywords.
        base_summary:    Candidate's base summary paragraph to tailor.
 
    Returns a dict with keys:
      - success (bool)
      - payload (dict) with keys:
          summary, skills, technologies, experience, projects
      - error (str)
    """
    logger.info("[TOOL] extract_all called")
    # Strip markdown formatting from inputs so it doesn't leak into extracted text
    match_report    = _strip_markdown(match_report)
    job_description = _strip_markdown(job_description)
    cached_payload = _cache.get_extraction(match_report, job_description)
    if cached_payload is not None:
        logger.info("[TOOL] extract_all — L4 cache hit, skipped Gemini call")
        return {"success": True, "payload": cached_payload, "error": "", "cache": "L4_hit"}
    prompt = f"""You are a world-class ATS resume strategist and senior technical
resume writer specialising in AI/ML, data science, and software engineering.
 
You work in THREE PHASES. Complete each phase fully before moving to the next.
 
════════════════════════════════════════════════════════════════════════
INPUTS
════════════════════════════════════════════════════════════════════════
 
JOB DESCRIPTION:
{job_description}
 
BASE SUMMARY (candidate's own words — preserve voice and structure):
{base_summary}
 
README CONTENT (candidate's actual GitHub projects):
{match_report}
 
════════════════════════════════════════════════════════════════════════
PHASE 1 — EXTRACT FROM JOB DESCRIPTION
════════════════════════════════════════════════════════════════════════
Read the job description carefully and extract:
 
1a. JD REQUIRED SKILLS
    Every competency, ability, or domain the JD explicitly or implicitly
    requires. These are your ATS keyword targets.
    Examples of what to look for:
    - Explicit: "experience with LLMs", "prompt engineering", "RAG"
    - Implicit: if JD says "build autonomous agents" → "Autonomous Agent Design"
    - Seniority signals: "lead", "architect", "design" → "System Architecture"
    Extract 15-25 skill phrases.
 
1b. JD REQUIRED TECHNOLOGIES
    Every specific tool, language, framework, platform, or service the JD
    names or clearly implies. Include exact names as written in the JD.
    Examples: if JD says "Python and FastAPI" → ["Python", "FastAPI"]
    Extract all you find — even if mentioned once.
 
1c. JD KEY ACTION VERBS AND PHRASES
    Exact phrases the JD uses that should appear verbatim in bullets.
    Examples: "scalable AI systems", "production-ready", "real-time processing",
    "cross-functional teams", "LLM orchestration", "autonomous workflows"
    Collect 10-20 exact phrases to mirror in experience bullets.
 
1d. JD ROLE EXPECTATIONS
    What the employer wants this person to DO day-to-day. These inform
    experience bullet topics. Extract as action-verb phrases.
    Examples: "design and deploy", "integrate APIs", "optimise performance"
 
════════════════════════════════════════════════════════════════════════
PHASE 2 — EXTRACT FROM README CONTENT
════════════════════════════════════════════════════════════════════════
Read every README carefully and extract:
 
2a. DEMONSTRATED SKILLS
    Every competency actually shown in the repos — same format as 1a.
    Read every line — don't skim.
 
2b. DEMONSTRATED TECHNOLOGIES
    Every tool, language, library, framework, database, API actually used.
    Be exhaustive — every import, every mentioned dependency counts.
 
2c. ACHIEVEMENTS AND BULLETS
    Specific accomplishments, design decisions, and outcomes from each repo.
    Each one starts with a strong past-tense action verb.
    Collect raw material for experience bullets and project bullets separately.
    Note which repo each achievement comes from.
 
2d. PROJECT DETAILS
    For each of the top 3-4 repos: what was built, how it was architected,
    what challenges were solved, what outcomes were achieved.
 
════════════════════════════════════════════════════════════════════════
PHASE 3 — ATS MERGE AND PRODUCE OUTPUT
════════════════════════════════════════════════════════════════════════
Now combine phases 1 and 2 to produce the final output sections.
 
──────────────────────────────────────────────────────────────────────
SECTION 1 — PROFESSIONAL SUMMARY
──────────────────────────────────────────────────────────────────────
Rewrite the base summary using:
- The candidate's existing voice, structure, and sentence count (4-5 sentences)
- JD key phrases woven in naturally (use Phase 1c phrases verbatim where they fit)
- 2-3 specific tools from the top repos (Phase 2b) that match JD requirements
- No fabricated claims — every statement must be supported by the READMEs
 
──────────────────────────────────────────────────────────────────────
SECTION 2 — CORE SKILLS
──────────────────────────────────────────────────────────────────────
TWO strict sources only — do not invent anything outside these two:
 
  SOURCE A — JD Required Skills (Phase 1a): list every skill the JD
    explicitly or implicitly requires. These go FIRST.
 
  SOURCE B — Repo Demonstrated Skills (Phase 2a): skills actually visible
    in the matched READMEs that are NOT already in Source A. Add these
    after Source A items.
 
STRICT RULES:
  ✓ Only include a skill if it appears in Source A or Source B
  ✗ Do NOT invent skills not in the JD or the READMEs
  ✗ Do NOT add skills because they "seem relevant" or are "commonly expected"
  ✗ Do NOT include tool/library names here (those go in Section 3)
  ✓ Format: short 2-5 word phrases
  ✓ Deduplicate — if a JD skill and a repo skill are the same concept, list once
 
──────────────────────────────────────────────────────────────────────
SECTION 3 — CORE TOOLS
──────────────────────────────────────────────────────────────────────
TWO strict sources only:
 
  SOURCE A — JD Required Technologies (Phase 1b): every tool, language,
    framework, platform, or service the JD names. Include EXACT names,
    verbatim. These go FIRST.
 
  SOURCE B — Repo Demonstrated Technologies (Phase 2b): every tool
    actually used in the matched READMEs not already in Source A.
 
STRICT RULES:
  ✓ Only include a technology if it appears in Source A or Source B
  ✗ Do NOT add tools because they are commonly used alongside listed tools
  ✗ Do NOT invent tools not named in the JD or the READMEs
  ✓ Return flat strings, no grouping
  ✓ Deduplicate
 
──────────────────────────────────────────────────────────────────────
SECTION 4 — PROFESSIONAL EXPERIENCE  (1 or 2 entries — you decide)
──────────────────────────────────────────────────────────────────────
Decision rule (same as before):
  1 role  — if all repos share one primary domain
  2 roles — ONLY if repos clearly span two genuinely distinct domains
 
ATS BULLET RULES — these are critical:
  ✓ Mirror the JD's exact phrases verbatim in bullets where evidence exists
    e.g. JD says "scalable AI systems" → bullet says "...built scalable AI systems..."
    e.g. JD says "LLM orchestration" → bullet says "...LLM orchestration using..."
  ✓ Use the JD's action verbs where they match what was done
    e.g. JD says "architect" → bullet says "Architected..." not "Built..."
  ✓ Each bullet covers something from BOTH the JD (language) AND the repo (evidence)
  ✓ 7-9 bullets per role
  ✓ role_title must match the domain of the bullets — never mismatch
  ✗ Do NOT use generic phrases not in either the JD or the READMEs
  ✗ Do NOT repeat bullets between experience and projects
 
For each role:
  role_title:   Accurate title matching bullets AND close to JD job title
  date_range:   Infer from READMEs, or "2024 – Present" / "2022 – Present"
  organisation: "Independent Projects / Research work"
  bullets:      7-9 ATS-optimised bullets as described above
 
──────────────────────────────────────────────────────────────────────
SECTION 5 — PROJECTS  (3-4 entries)
──────────────────────────────────────────────────────────────────────
Top 3-4 repos as individual showcase entries.
Go deeper than experience bullets — architecture, implementation, outcomes.
 
For each project:
  name:    Repo name, title-cased
  bullets: 3-4 bullets:
    - What was architected and how
    - Specific technical challenge solved
    - Measurable or notable outcome
    - At least 1 bullet should echo a JD phrase verbatim if evidence exists
 
Rules:
  - Bullets DIFFERENT from experience bullets
  - Each starts with a strong past-tense action verb
  - NO tagline, NO stack field
 
════════════════════════════════════════════════════════════════════════
GLOBAL RULES
════════════════════════════════════════════════════════════════════════
- Skills and technologies come ONLY from the JD or the matched READMEs
- Do NOT invent, extrapolate, or add "expected" skills not present in either source
- JD items take priority — list them first in skills and technologies
- Every experience/project bullet grounded in README content — no fabrication
- Skills (Section 2) and Tools (Section 3) must NOT overlap
- Experience bullets and Project bullets must NOT duplicate
- Return ONLY valid JSON — no markdown fences, no commentary
 
════════════════════════════════════════════════════════════════════════
OUTPUT JSON SCHEMA
════════════════════════════════════════════════════════════════════════
{{
  "summary": "Result-oriented ... [4-5 sentences with JD phrases woven in]",
  "skills": [
    "Prompt Engineering",
    "LLM Orchestration",
    "Agentic Workflow Design",
    "... JD skills first, then repo skills ..."
  ],
  "technologies": [
    "Python",
    "LangGraph",
    "... JD tools first, then repo tools ..."
  ],
  "experience": [
    {{
      "role_title":    "Agentic AI Engineer / Prompt Engineer",
      "date_range":    "2024 – Present",
      "organisation":  "Independent Projects / Research work",
      "bullets": [
        "Architected scalable AI systems using LangGraph for stateful multi-step agent orchestration",
        "Engineered production-ready LLM pipelines integrating Google Gemini for real-time conversational AI",
        "... 7-9 bullets total, JD phrases mirrored verbatim where evidence exists ..."
      ]
    }}
  ],
  "projects": [
    {{
      "name": "Medic AI Agent",
      "bullets": [
        "Architected stateful LangGraph flow with custom nodes for symptom extraction and triage logic",
        "Implemented Pydantic schema validation to enforce strict data structures across agent transitions",
        "Extended agent with YouTube search tool enabling real-time retrieval of first-aid instructional videos"
      ]
    }}
  ]
}}
"""
 
    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )
        payload = _parse_json_response(response.text, "extract_all")
 
        for key in ("summary", "skills", "technologies", "experience", "projects"):
            if key not in payload:
                raise ValueError(f"Missing key in extraction payload: {key}")
            if not payload[key]:
                logger.warning(f"[TOOL] extract_all — '{key}' is empty")
 
        logger.info(
            f"[TOOL] extract_all — summary={'yes' if payload.get('summary') else 'NO'}, "
            f"skills={len(payload.get('skills', []))}, "
            f"technologies={len(payload.get('technologies', []))}, "
            f"experience={len(payload.get('experience', []))}, "
            f"projects={len(payload.get('projects', []))}"
        )
        
        # Strip any markdown that leaked into extracted text
        def _clean_strings(obj):
            if isinstance(obj, str):
                return _strip_markdown(obj)
            if isinstance(obj, list):
                return [_clean_strings(i) for i in obj]
            if isinstance(obj, dict):
                return {k: _clean_strings(v) for k, v in obj.items()}
            return obj
 
        payload = _clean_strings(payload)
        logger.info("[TOOL] extract_all — markdown stripped from payload")
        
        # Save to L4 cache for next run with same inputs
        _cache.set_extraction(match_report, job_description, payload)
        
        return {"success": True, "payload": payload, "error": ""}
 
    except Exception as e:
        logger.exception("[TOOL] extract_all failed")
        return {"success": False, "payload": {}, "error": str(e)}
 
 
agent_2_extractor = Agent(
    name="agent_2_extractor",
    model="gemini-3.1-flash-lite-preview",
    description=(
        "Receives the Agent 1 match report and performs a single holistic "
        "extraction pass, returning the full payload for Agent 3."
    ),
    instruction="""
You are Agent 2 (extractor) in a resume builder pipeline.
You receive a message containing two clearly labelled sections:
  - JOB DESCRIPTION: the raw job description text
  - MATCH REPORT: the full GitHub match report from Agent 1
 
## Workflow
 
### Step 1 — extract_all
Call extract_all with THREE arguments:
  - match_report:    the MATCH REPORT section (full text, verbatim)
  - job_description: the JOB DESCRIPTION section (full text, verbatim)
  - base_summary:    pass an empty string ""
 
CRITICAL: Pass both sections separately and completely. Do NOT merge them,
summarise them, or drop any content. The tool needs the JD and READMEs as
separate inputs to perform ATS-optimised extraction.
 
### Step 2 — Return
Return the tool's output verbatim. Do NOT filter, rephrase, or summarise.
Do NOT return success: true with an empty payload.
The payload will be consumed by Agent 3 (the resume writer).
 
If extract_all returns success: false, report the error clearly and stop.
""",
    tools=[FunctionTool(extract_all)],
)
 
 
agent_2_extractor = Agent(
    name="agent_2_extractor",
    model="gemini-3.1-flash-lite-preview",
    description=(
        "Receives the Agent 1 match report and performs a single holistic "
        "extraction pass, returning the full payload for Agent 3."
    ),
    instruction="""
You are Agent 2 (extractor) in a resume builder pipeline.
You receive a message containing two clearly labelled sections:
  - JOB DESCRIPTION: the raw job description text
  - MATCH REPORT: the full GitHub match report from Agent 1
 
## Workflow
 
### Step 1 — extract_all
Call extract_all with THREE arguments:
  - match_report:    the MATCH REPORT section (full text, verbatim)
  - job_description: the JOB DESCRIPTION section (full text, verbatim)
  - base_summary:    pass an empty string ""
 
CRITICAL: Pass both sections separately and completely. Do NOT merge them,
summarise them, or drop any content. The tool needs the JD and READMEs as
separate inputs to perform ATS-optimised extraction.
 
### Step 2 — Return
Return the tool's output verbatim. Do NOT filter, rephrase, or summarise.
Do NOT return success: true with an empty payload.
The payload will be consumed by Agent 3 (the resume writer).
 
If extract_all returns success: false, report the error clearly and stop.
""",
    tools=[FunctionTool(extract_all)],
)
 

# AGENT 3 — Resume writer  (docx skill)
# Tools: generate_resume_js, build_resume_docx
# 
 
# ── Load SKILL.md at startup ──────────────────────────────────────────────────
_SKILL_PATH = os.path.join(os.path.dirname(__file__), "SKILL.md")
try:
    with open(_SKILL_PATH, "r") as _f:
        _DOCX_SKILL = _f.read()
    logger.info("[AGENT3] SKILL.md loaded successfully")
except FileNotFoundError:
    _DOCX_SKILL = ""
    logger.warning(f"[AGENT3] SKILL.md not found at {_SKILL_PATH} — docx skill unavailable")
 
# ── Output directory for generated resumes ────────────────────────────────────
RESUME_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output", "resumes")
os.makedirs(RESUME_OUTPUT_DIR, exist_ok=True)
 
 
def generate_resume_js(
    js_code: str,
    payload: dict,
    candidate_name: str = "Ameen Abdulrasheed",
) -> dict:
    """
    Write the Node.js resume script and a payload JSON sidecar to disk.
 
    The payload (skills, technologies, experience, projects, summary) is written
    to a separate JSON file that the Node.js script reads at runtime using
    fs.readFileSync. This means the agent never has to hardcode any resume data
    as string literals inside the JS — eliminating the truncation problem where
    long arrays get silently cut off mid-script.
 
    The JS script should load data like this:
        const payload = JSON.parse(
            fs.readFileSync(path.join(__dirname, "<candidate_name>_payload.json"), "utf8"));
 
    Args:
        js_code:        Complete Node.js source. Must NOT contain hardcoded
                        skills/technologies/bullets arrays — read them from payload JSON.
        payload:        The full extraction dict from Agent 2 with keys:
                        summary, skills, technologies, experience, projects.
        candidate_name: Filename stem (default "candidate").
 
    Returns:
        A dict with keys:
          - success (bool)
          - script_path (str)    — absolute path of the .js file
          - payload_path (str)   — absolute path of the _payload.json file
          - output_path (str)    — absolute path where the .docx will be written
          - error (str)
    """
    logger.info(f"[TOOL] generate_resume_js called | candidate={candidate_name} | code_length={len(js_code)} | payload_keys={list(payload.keys()) if payload else []}")
    try:
        script_path  = os.path.join(RESUME_OUTPUT_DIR, f"{candidate_name}_resume.js")
        payload_path = os.path.join(RESUME_OUTPUT_DIR, f"{candidate_name}_payload.json")
        output_path  = os.path.join(RESUME_OUTPUT_DIR, f"{candidate_name}_resume.docx")

       
        # ── Validate navy color ─────────────────────────────────────────────
        if '"1F3864"' not in js_code and "'1F3864'" not in js_code:
            msg = (
                "Script is missing navy color 1F3864. "
                "Set color: \"1F3864\" on Heading1 style, role_title TextRun, and project name TextRun."
            )
            logger.warning(f"[TOOL] generate_resume_js — {msg}")
            return {"success": False, "script_path": "", "payload_path": "", "output_path": "", "error": msg}
 
        # ── Validate payload has all required keys and is non-empty ─────────
        required_keys = ["summary", "skills", "technologies", "experience", "projects"]
        missing_keys  = [k for k in required_keys if not payload.get(k)]
        if missing_keys:
            msg = f"Payload is missing or empty for keys: {missing_keys}. Pass the full Agent 2 payload."
            logger.warning(f"[TOOL] generate_resume_js — {msg}")
            return {"success": False, "script_path": "", "payload_path": "", "output_path": "", "error": msg}
 
        # ── Server-side enforcement: strip any hardcoded payload object ───────
        # The agent frequently hardcodes `const payload = { ... }` instead of
        # reading from file. We detect this pattern and replace it with the
        # correct fs.readFileSync call regardless of what the agent wrote.
        import re as _re
 
        # Remove any hardcoded `const payload = { ... };` block (multi-line)
        js_code = _re.sub(
            r'const\s+payload\s*=\s*\{[\s\S]*?\};',
            "",
            js_code,
        )
 
        # Fix BorderStyle.NONE → BorderStyle.NIL everywhere in the script
        js_code = js_code.replace("BorderStyle.NONE", "BorderStyle.NIL")
 
        # Ensure the correct payload load line exists right after the profile load.
        # If it's already there (correct form), leave it. Otherwise inject it.
        correct_load = f'const payload = JSON.parse(fs.readFileSync(path.join(__dirname, "{candidate_name}_payload.json"), "utf8"));'
        if correct_load not in js_code:
            # Inject after the profile readFileSync line
            profile_load = 'const profile = JSON.parse(fs.readFileSync(path.join(__dirname, "candidate_profile.json"), "utf8"));'
            if profile_load in js_code:
                js_code = js_code.replace(
                    profile_load,
                    profile_load + "\n" + correct_load,
                    1,
                )
                logger.info("[TOOL] generate_resume_js — injected payload load line after profile load")
            else:
                # Fallback: inject after all require() lines
                last_require_pos = js_code.rfind('require(')
                end_of_line      = js_code.find('\n', last_require_pos)
                js_code = js_code[:end_of_line+1] + correct_load + "\n" + js_code[end_of_line+1:]
                logger.info("[TOOL] generate_resume_js — injected payload load line after requires")
 
        logger.info(f"[TOOL] generate_resume_js — BorderStyle.NONE patched to NIL, payload load enforced")
 
        # ── Enforce contact line has all 6 fields including linkedin ────────
        # The agent sometimes uses a template literal that concatenates fields
        # and accidentally drops profile.linkedin. We check for it and patch.
        if "profile.linkedin" not in js_code:
            # Find the contact paragraph (the one with profile.portfolio)
            # and replace with the correct multi-TextRun version
            contact_replacement = (
                "new Paragraph({ alignment: AlignmentType.CENTER, "
                "spacing: { before: 0, after: 140 }, children: ["
                "new TextRun({ text: profile.email, size: 18, font: \"Arial\", color: \"1F3864\" }),"
                "new TextRun({ text: \"  |  \", size: 18, font: \"Arial\", color: \"AAAAAA\" }),"
                "new TextRun({ text: profile.phone, size: 18, font: \"Arial\", color: \"1F3864\" }),"
                "new TextRun({ text: \"  |  \", size: 18, font: \"Arial\", color: \"AAAAAA\" }),"
                "new TextRun({ text: profile.portfolio, size: 18, font: \"Arial\", color: \"1F3864\" }),"
                "new TextRun({ text: \"  |  \", size: 18, font: \"Arial\", color: \"AAAAAA\" }),"
                "new TextRun({ text: profile.github, size: 18, font: \"Arial\", color: \"1F3864\" }),"
                "new TextRun({ text: \"  |  \", size: 18, font: \"Arial\", color: \"AAAAAA\" }),"
                "new TextRun({ text: profile.linkedin, size: 18, font: \"Arial\", color: \"1F3864\" }),"
                "new TextRun({ text: \"  |  \", size: 18, font: \"Arial\", color: \"AAAAAA\" }),"
                "new TextRun({ text: profile.location, size: 18, font: \"Arial\", color: \"1F3864\" })"
                "] })"
            )
            # Replace any contact paragraph that has profile.portfolio but not linkedin
            js_code = _re.sub(
                r"new Paragraph\(\{[^}]*?alignment:\s*AlignmentType\.CENTER[^}]*?profile\.portfolio[^}]*?\}\)",
                contact_replacement,
                js_code,
                flags=_re.DOTALL,
            )
            logger.info("[TOOL] generate_resume_js — patched contact line to include all 6 fields")
 
        # ── Inject output_path placeholder ──────────────────────────────────
        PLACEHOLDER = "OUTPUT_PATH_PLACEHOLDER"
        if PLACEHOLDER in js_code:
            js_code = js_code.replace(PLACEHOLDER, output_path)
            logger.info("[TOOL] generate_resume_js — injected output_path via placeholder")
        else:
            import re as _re
            js_code = _re.sub(
                r"fs\.writeFileSync\(\s*['\"].*?\.docx['\"]",
                f'fs.writeFileSync("{output_path}"',
                js_code,
            )
            logger.warning("[TOOL] generate_resume_js — placeholder missing; patched via regex")
 
        # ── Write payload JSON sidecar ───────────────────────────────────────
        with open(payload_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        logger.info(f"[TOOL] generate_resume_js — payload written to {payload_path} | "
                    f"skills={len(payload.get('skills',[]))}, "
                    f"technologies={len(payload.get('technologies',[]))}, "
                    f"experience={len(payload.get('experience',[]))}, "
                    f"projects={len(payload.get('projects',[]))}")
 
        # ── Write JS script ──────────────────────────────────────────────────
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(js_code)
        logger.info(f"[TOOL] generate_resume_js — script written to {script_path}")
 
        return {
            "success":      True,
            "script_path":  script_path,
            "payload_path": payload_path,
            "output_path":  output_path,
            "error":        "",
        }
 
    except Exception as e:
        logger.exception("[TOOL] generate_resume_js failed")
        return {"success": False, "script_path": "", "payload_path": "", "output_path": "", "error": str(e)}
 

 
 
def build_resume_docx(script_path: str) -> dict:
    """
    Execute the Node.js docx-js script at script_path to produce the final
    .docx resume file.
 
    Requires Node.js >= 18 and the `docx` npm package (`npm install -g docx`).
 
    Args:
        script_path: Absolute path to the fully-populated .js file.
 
    Returns:
        A dict with keys:
          - success (bool)
          - output_path (str)   — absolute path of the generated .docx
          - stdout (str)        — Node.js stdout (truncated to 500 chars)
          - stderr (str)        — Node.js stderr (truncated to 500 chars)
          - error (str)
    """
    import subprocess
 
    logger.info(f"[TOOL] build_resume_docx called | script={script_path}")
    try:
        result = subprocess.run(
            ["node", script_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
 
        stdout  = result.stdout[:500]
        stderr  = result.stderr[:500]
        success = result.returncode == 0
 
        if not success:
            logger.warning(f"[TOOL] build_resume_docx — node exited {result.returncode} | stderr: {stderr}")
        else:
            logger.info("[TOOL] build_resume_docx — .docx built successfully")
 
        output_path = script_path.replace(".js", ".docx")
 
        return {
            "success":     success,
            "output_path": output_path if success else "",
            "stdout":      stdout,
            "stderr":      stderr,
            "error":       stderr if not success else "",
        }
 
    except FileNotFoundError:
        msg = "Node.js not found — install Node.js and run `npm install -g docx`"
        logger.error(f"[TOOL] build_resume_docx — {msg}")
        return {"success": False, "output_path": "", "stdout": "", "stderr": "", "error": msg}
 
    except subprocess.TimeoutExpired:
        msg = "Node.js script timed out after 60 seconds"
        logger.error(f"[TOOL] build_resume_docx — {msg}")
        return {"success": False, "output_path": "", "stdout": "", "stderr": "", "error": msg}
 
    except Exception as e:
        logger.exception("[TOOL] build_resume_docx failed")
        return {"success": False, "output_path": "", "stdout": "", "stderr": "", "error": str(e)}
 
 
 
def confirm_docx_built(script_path: str) -> dict:
    """
    Confirm that build_resume_docx was called and the .docx file exists on disk.
 
    Call this tool IMMEDIATELY after a successful build_resume_docx call.
    It acts as a mandatory checkpoint — the agent MUST NOT return a final
    response until this tool confirms the .docx is present.
 
    Args:
        script_path: The script_path returned by generate_resume_js (used to
                     derive the expected .docx path).
 
    Returns:
        A dict with keys:
          - success (bool)     — True only if the .docx file exists and is non-empty
          - output_path (str)  — absolute path of the confirmed .docx
          - size_bytes (int)   — file size in bytes (0 if missing)
          - error (str)
    """
    import os as _os
    output_path = script_path.replace(".js", ".docx")
    logger.info(f"[TOOL] confirm_docx_built | checking {output_path}")
    try:
        if _os.path.exists(output_path) and _os.path.getsize(output_path) > 0:
            size = _os.path.getsize(output_path)
            logger.info(f"[TOOL] confirm_docx_built — OK | {size} bytes")
            return {"success": True, "output_path": output_path, "size_bytes": size, "error": ""}
        elif _os.path.exists(output_path):
            msg = "File exists but is empty — build_resume_docx may have failed silently"
            logger.warning(f"[TOOL] confirm_docx_built — {msg}")
            return {"success": False, "output_path": output_path, "size_bytes": 0, "error": msg}
        else:
            msg = f".docx not found at {output_path} — build_resume_docx was not called or failed"
            logger.warning(f"[TOOL] confirm_docx_built — {msg}")
            return {"success": False, "output_path": output_path, "size_bytes": 0, "error": msg}
    except Exception as e:
        logger.exception("[TOOL] confirm_docx_built failed")
        return {"success": False, "output_path": output_path, "size_bytes": 0, "error": str(e)}
 
 



agent_3_resume_writer = Agent(
    name="agent_3_resume_writer",
    model="gemini-3.1-flash-lite-preview",
    description=(
        "Receives the unified extraction payload from Agent 2 and the original "
        "job description, then generates a professionally formatted .docx resume "
        "using the docx-js skill."
    ),
        instruction="""
You are Agent 3 (resume_writer) in a resume builder pipeline.
 
You receive:
  1. The extraction payload from Agent 2:
     keys: summary, skills, technologies, experience (2 entries), projects (3-4 entries)
  2. The original job description.
 
You also read the candidate profile at runtime from:
  candidate_profile.json  (in the same directory as the generated .js script)
 
  const profile = JSON.parse(
    fs.readFileSync(path.join(__dirname, "candidate_profile.json"), "utf8"));
 
Profile fields used: name, title, email, phone, portfolio, github, linkedin,
location, education[]
 
---
 
## DOCX SKILL REFERENCE  (follow every rule exactly)
 
""" + _DOCX_SKILL + """
 
---
 
## Workflow
 
### Step 1 — Compose the complete Node.js script
 
MANDATORY FIRST LINES — copy EXACTLY:
  const fs   = require("fs");
  const path = require("path");
  const { Document, Packer, Paragraph, TextRun,
          AlignmentType, LevelFormat, BorderStyle, WidthType, ShadingType,
          TabStopType, TabStopPosition, HeadingLevel, PageBreak, PageOrientation,
          PageNumber, ExternalHyperlink, VerticalAlign } = require("docx");
 
NOTE: Table, TableRow, TableCell are NOT imported — skills and tools use
tab-stop paragraphs instead of tables. Do NOT add table imports back.
 
Then immediately read profile AND payload from disk — replace <candidate_name>
with the actual snake_case slug you pass to generate_resume_js:
  const profile = JSON.parse(
    fs.readFileSync(path.join(__dirname, "candidate_profile.json"), "utf8"));
  const payload = JSON.parse(
    fs.readFileSync(path.join(__dirname, "<candidate_name>_payload.json"), "utf8"));
 
CRITICAL — DO NOT hardcode any resume data in the script:
  ✗ const skills = ["Agentic Workflow Design", "Prompt Engineering", ...]
  ✓ const skills = payload.skills;   // reads ALL items from the JSON sidecar
  ✗ const summary = "Result-oriented AI Engineer..."
  ✓ const summary = payload.summary;
  ✗ entry.bullets.forEach(b => ...) where bullets is a hardcoded array
  ✓ entry.bullets.forEach(b => ...) where entry comes from payload.experience
 
Every array in the resume — skills, technologies, experience bullets, project
bullets — must be read from payload, not written as a literal in the script.
 
Build the document following the DOCX SKILL REFERENCE spec exactly:
  HEADER → PROFESSIONAL SUMMARY → CORE SKILLS → PROFESSIONAL EXPERIENCE
  → PROJECTS → CORE TOOLS → EDUCATION
 
Pre-checklist — verify ALL before calling generate_resume_js:
  ✓ All classes present in require() including VerticalAlign
  ✓ const path = require("path") present
  ✓ candidate_profile.json read with path.join(__dirname, ...)
  ✓ Page size width 12240, height 15840 — NO orientation property
  ✓ Margins top 620, bottom 620, left 900, right 900
  ✓ NO tables used for skills or tools — tab-stop paragraphs only
  ✓ Core Skills: 3 per row, TabStopType.LEFT at 3480 and 6960, bullet prefix
  ✓ Core Tools: 6 per row, TabStopType.LEFT at 2610, 5220, 7830, no prefix
  ✓ Section order: Summary → Core Skills → Core Tools → Experience → Projects → Education
  ✓ LevelFormat.BULLET used — no unicode bullet directly in TextRun bullets
  ✓ Separate numbering reference per project (proj-0, proj-1, ...)
    Use "proj-" + pi where pi is the forEach index
    or any variable not defined in scope. proj-0 through proj-3 must all exist
    in numbering.config
  ✓ No \n inside any TextRun
  ✓ Packer.toBuffer ends with fs.writeFileSync("OUTPUT_PATH_PLACEHOLDER", buf) — verbatim, do not replace it with a real path
  ✓ Script ends with Packer.toBuffer(...).then(...).catch(err => process.exit(1))
 
### Step 2 — generate_resume_js
Call with THREE arguments:
  - js_code:        the complete Node.js script from Step 1
  - payload:        the FULL payload dict received from Agent 2 — pass it
                    entirely, do not summarise or filter it
  - candidate_name: snake_case slug of the candidate name
 
The tool writes the payload to a JSON sidecar file automatically.
Your script must read it from disk — never hardcode any data.
 
If the tool returns success:false, fix the reported issue and call again.
 
### Step 3 — build_resume_docx
MANDATORY — call with script_path immediately after generate_resume_js.
On failure read stderr and fix:
  - ReferenceError: X is not defined  → add X to require()
  - columnWidths mismatch             → verify sum equals 10440
  - ShadingType error                 → use ShadingType.CLEAR
  - Unexpected token                  → check unescaped quotes in TextRun text
Retry max 2 times.
 
### Step 4 — confirm_docx_built
MANDATORY — call after every successful build_resume_docx.
Do NOT return a final response until this returns success: true.
 
### Step 5 — Return
Return the output_path and a one-line summary.
If all retries fail, return the last stderr and broken script for debugging.
""",
    tools=[
        FunctionTool(generate_resume_js),
        FunctionTool(build_resume_docx),
        FunctionTool(confirm_docx_built),
    ],
)
 
 

# PIPELINE ORCHESTRATOR — owns Agents 1, 2, 3

 
pipeline_orchestrator = SequentialAgent(
    name="pipeline_orchestrator",
    description=(
        "Top-level orchestrator for the resume builder pipeline. "
        "Delegates to Agent 1 (repo matching), Agent 2 (single holistic extraction), "
        "and Agent 3 (resume writing) in strict sequence."
    ),
    sub_agents=[
        agent_1_repo_matcher,
        agent_2_extractor,
        agent_3_resume_writer,
    ],
)
 
 
# ══════════════════════════════════════════════════════════════════════════════
# Session + runner
# ══════════════════════════════════════════════════════════════════════════════
 
session_service = InMemorySessionService()
APP_NAME        = "resume_agent_app"
 
pipeline_runner = Runner(
    agent=pipeline_orchestrator,
    app_name=APP_NAME,
    session_service=session_service,
)
 
 
# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(title="Resume Agent API")
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type", "Content-Length"]
)
 
 
# ── Request schema ─────────────────────────────────────────────────────────────
class ResumeRequest(BaseModel):
    job_description: str
 
 
# ── SSE helper ─────────────────────────────────────────────────────────────────
def sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"
 
 
# ── Tool / agent labels for the frontend progress feed ────────────────────────
TOOL_LABELS: dict[str, str] = {
    # Pipeline orchestrator delegating to agents
    "agent_1_repo_matcher":  "Matching repos to job description",
    "agent_2_extractor":     "Extracting resume signals",
    "agent_3_resume_writer": "Writing resume",
    # Agent 1 tools
    "fetch_and_embed_readmes": "Fetching and embedding GitHub READMEs",
    "query_vector_db":         "Searching for relevant repos",
    # Agent 2 tool
    "extract_all":             "Extracting all resume content",
    # Agent 3 tools
    "generate_resume_js":    "Generating resume JS script",
    "build_resume_docx":     "Building .docx resume",
    "confirm_docx_built":    "Confirming .docx was built",
}
 
 
# ── Agent progress labels — emitted as status events on agent transitions ──────
AGENT_LABELS: dict[str, str] = {
    "pipeline_orchestrator":  "Pipeline orchestrator running",
    "agent_1_repo_matcher":   "Agent 1 — matching repos",
    "agent_2_extractor":      "Agent 2 — extracting resume content",
    "agent_3_resume_writer":  "Agent 3 — writing resume",
}
 
# The root agent name — only its final response ends the stream
_ROOT_AGENT = "pipeline_orchestrator"
 # ── Pipeline SSE streaming generator ──────────────────────────────────────────
async def stream_pipeline(job_description: str):
    """
    Async generator — drives the full pipeline orchestrator and yields SSE
    events in real time covering every agent delegation, tool call, and the
    final resume output.
 
    Key behaviour:
      - `done` is ONLY emitted when the ROOT orchestrator (pipeline_orchestrator)
        emits is_final_response(). Sub-agent final responses are surfaced as
        `agent_done` status events so the frontend can show progress, but they
        do NOT terminate the stream.
      - `event.author` identifies which agent produced each event, enabling
        accurate per-agent progress reporting.
 
    Event shapes:
      status      { message }
      agent_start { agent, label }
      agent_done  { agent, label, summary }   ← sub-agent finished, pipeline continues
      tool_start  { tool, label, input, agent }
      tool_done   { tool, label, output, agent }
      done        { response }                ← root orchestrator finished
      error       { message }
    """
    yield sse({"type": "status", "message": "Pipeline starting..."})
 
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=job_description[:64],
    )
 
    user_message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=job_description)],
    )
 
    pending_tool: str | None = None
    current_agent: str | None = None
 
    try:
        async for event in pipeline_runner.run_async(
            user_id=job_description[:64],
            session_id=session.id,
            new_message=user_message,
        ):
            # Identify which agent produced this event
            author = getattr(event, "author", None) or ""
 
            # ── Agent transition — new agent became active ─────────────────
            if author and author != current_agent:
                current_agent = author
                label = AGENT_LABELS.get(author, author)
                logger.info(f"[PIPELINE] Agent active: {author}")
                yield sse({
                    "type":  "agent_start",
                    "agent": author,
                    "label": label,
                })
 
            # ── Tool / agent-delegation call fired ────────────────────────
            if event.get_function_calls():
                for fn in event.get_function_calls():
                    pending_tool = fn.name
                    label        = TOOL_LABELS.get(fn.name, fn.name)
                    logger.info(f"[PIPELINE] Call: {fn.name} | author: {author} | args: {fn.args}")
                    yield sse({
                        "type":  "tool_start",
                        "tool":  fn.name,
                        "label": label,
                        "input": fn.args,
                        "agent": author,
                    })
 
            # ── Tool / agent-delegation result returned ───────────────────
            if event.get_function_responses():
                for fn in event.get_function_responses():
                    result_preview = str(fn.response)[:300]
                    label          = TOOL_LABELS.get(pending_tool or "", pending_tool or "")
                    logger.info(f"[PIPELINE] Result for {pending_tool}: {result_preview[:200]}")
                    yield sse({
                        "type":   "tool_done",
                        "tool":   pending_tool,
                        "label":  label,
                        "output": result_preview,
                        "agent":  author,
                    })
                    pending_tool = None
 
            # ── Final response from an agent ──────────────────────────────
            if event.is_final_response():
                final_text = ""
                if event.content and event.content.parts:
                    final_text = "".join(
                        p.text for p in event.content.parts if hasattr(p, "text")
                    )
 
                if author == _ROOT_AGENT:
                    # Root orchestrator finished — the whole pipeline is done
                    # Extract the .docx filename from the final response text
                    # so the frontend can build the download URL immediately.
                    import re as _re_done
                    filename = None
                    # Try to find a .docx filename in the response text
                    match = _re_done.search(r"([\w\s\-]+_resume\.docx)", final_text)
                    if match:
                        filename = os.path.basename(match.group(1).strip())
                    else:
                        # Fallback: scan RESUME_OUTPUT_DIR for the newest .docx
                        try:
                            docx_files = [
                                f for f in os.listdir(RESUME_OUTPUT_DIR)
                                if f.endswith("_resume.docx")
                            ]
                            if docx_files:
                                filename = max(
                                    docx_files,
                                    key=lambda f: os.path.getmtime(
                                        os.path.join(RESUME_OUTPUT_DIR, f)
                                    ),
                                )
                        except Exception:
                            pass
 
                    logger.info(
                        f"[PIPELINE] ROOT final response | "
                        f"length={len(final_text)} | filename={filename}"
                    )
                    yield sse({
                        "type":     "done",
                        "response": final_text,
                        "filename": filename,
                        "download_url": f"/download/{filename}" if filename else None,
                    })
 
                else:
                    # Sub-agent finished — surface as progress, keep stream open
                    summary = final_text[:200] if final_text else "(no text)"
                    logger.info(f"[PIPELINE] Sub-agent '{author}' finished | summary={summary[:100]}")
                    yield sse({
                        "type":    "agent_done",
                        "agent":   author,
                        "label":   AGENT_LABELS.get(author, author),
                        "summary": summary,
                    })
 
    except Exception as e:
        logger.exception(f"[PIPELINE] Error | snippet={job_description[:60]}")
        yield sse({"type": "error", "message": str(e)})
 
# ── Endpoints ──────────────────────────────────────────────────────────────────
@app.get("/build-resume")
async def build_resume(job_description: str):
    """
    Single SSE endpoint for the full resume builder pipeline.

    Streams real-time progress events as the pipeline orchestrator delegates
    across Agent 1 (repo matching), Agent 2 (parallel extraction), and
    Agent 3 (resume writing).

    Event types emitted:
      - status     — pipeline lifecycle messages
      - tool_start — an agent or tool was invoked  { tool, label, input }
      - tool_done  — an agent or tool returned      { tool, label, output }
      - done       — final resume Markdown           { response }
      - error      — pipeline failure                { message }

    Usage: GET /build-resume?job_description=<text>
    """
    logger.info(f"[API] /build-resume called | snippet={job_description[:60]}")
    return StreamingResponse(
        stream_pipeline(job_description),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
        },
    )





@app.get("/download/{filename}")
async def download_resume(filename: str):
    """
    Serve a generated .docx resume file for download.
 
    The filename is returned in the done SSE event from /build-resume as
    the `filename` field. The frontend should use this to build the URL:
        GET /download/<filename>
 
    Security: only files inside RESUME_OUTPUT_DIR are served.
    Path traversal attempts (../../etc) are rejected with 400.
    """
    # Sanitise — strip any path components, allow only the bare filename
    safe_name = os.path.basename(filename)
    if not safe_name or safe_name != filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename — must be a bare filename with no path separators.",
        )
 
    file_path = os.path.join(RESUME_OUTPUT_DIR, safe_name)
 
    # Confirm the resolved path is still inside RESUME_OUTPUT_DIR
    resolved      = os.path.realpath(file_path)
    resolved_dir  = os.path.realpath(RESUME_OUTPUT_DIR)
    if not resolved.startswith(resolved_dir + os.sep):
        raise HTTPException(status_code=400, detail="Invalid filename.")
 
    if not os.path.exists(resolved):
        raise HTTPException(
            status_code=404,
            detail=f"File '{safe_name}' not found. "
                   f"The resume may still be generating, or the filename is incorrect.",
        )
 
    logger.info(f"[API] /download/{safe_name} — serving file")
    return FileResponse(
        path=resolved,
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        ),
        filename=safe_name,
        headers={
            # Force browser to download rather than open inline
            "Content-Disposition": f'attachment; filename="{safe_name}"',
        },
    )



@app.get("/cache/stats")
async def cache_stats():
    """Return counts and total size of cached items by level."""
    return _cache.stats()
 
 
@app.delete("/cache/clear")
async def cache_clear():
    """Delete all cache files. Use when repos have changed significantly."""
    removed = _cache.clear_all()
    return {"status": "cleared", "files_removed": removed}

# i need perfect extraction, perfect formtting. default template, fully utilized space per page.
@app.get("/health")
async def health():
    return {"status": "ok"}
