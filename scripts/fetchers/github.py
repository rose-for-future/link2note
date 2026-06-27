import re
import json
import subprocess

from scripts.models import make_result
from scripts.fetchers import REGISTRY


def parse_repo_url(url: str) -> tuple:
    """Extract (owner, repo) from a GitHub URL.
    Handles trailing /tree/..., /blob/..., query strings, etc.
    Raises ValueError for non-GitHub URLs.
    """
    m = re.search(r"github\.com/([^/]+)/([^/#?]+)", url)
    if not m:
        raise ValueError(f"非法 GitHub 链接：{url}")
    return m.group(1), m.group(2)


def _build_text(desc: str, readme: str, stars=None) -> str:
    """Build the text content from description and README.
    Deliberately excludes stars/forks/watchers (noise).
    """
    parts = []
    if desc:
        parts.append(f"**仓库简介**：{desc}")
    if readme:
        if len(readme) > 20000:
            readme = readme[:20000] + "\n\n…(README 已截断)"
        parts.append("## README\n\n" + readme)
    return "\n\n".join(parts)


def _gh_json(owner: str, repo: str) -> dict:
    out = subprocess.run(
        ["gh", "api", f"repos/{owner}/{repo}"],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def _gh_readme(owner: str, repo: str) -> str:
    r = subprocess.run(
        ["gh", "api", f"repos/{owner}/{repo}/readme",
         "-H", "Accept: application/vnd.github.raw"],
        capture_output=True, text=True,
    )
    return r.stdout if r.returncode == 0 else ""


def fetch(url: str, cfg: dict) -> dict:
    owner, repo = parse_repo_url(url)
    meta = _gh_json(owner, repo)
    readme = _gh_readme(owner, repo)
    text = _build_text(meta.get("description") or "", readme)
    return make_result(
        "github", "repo", url, f"{owner}/{repo}", text,
        author=owner,
        extra={"language": meta.get("language")},
    )


REGISTRY["github"] = fetch
