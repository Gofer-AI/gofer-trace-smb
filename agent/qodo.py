"""GitHub adapter for requesting and reading Qodo Merge audits."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

GITHUB_API = "https://api.github.com"
PR_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/"
    r"(?P<repo>[A-Za-z0-9_.-]+)/pull/(?P<number>[1-9][0-9]*)/?$"
)
QODO_LOGIN_MARKERS = ("qodo", "codium", "pr-agent", "pr_agent")
MAX_REQUEST_LENGTH = 2_000


class QodoAuditError(ValueError):
    """Raised when a Qodo audit cannot be requested or inspected safely."""


@dataclass(frozen=True)
class PullRequestRef:
    owner: str
    repo: str
    number: int

    @property
    def api_path(self) -> str:
        return f"/repos/{self.owner}/{self.repo}/pulls/{self.number}"


def parse_pr_url(pr_url: str) -> PullRequestRef:
    match = PR_URL_RE.fullmatch(pr_url.strip())
    if not match:
        raise QodoAuditError("Expected a GitHub pull-request URL such as https://github.com/owner/repo/pull/123.")
    return PullRequestRef(
        owner=match.group("owner"),
        repo=match.group("repo"),
        number=int(match.group("number")),
    )


def _github_token() -> str | None:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        return token
    gh = shutil.which("gh")
    if not gh:
        return None
    try:
        result = subprocess.run(
            [gh, "auth", "token", "--hostname", "github.com"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def _github_json(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    require_auth: bool = False,
) -> Any:
    token = _github_token()
    if require_auth and not token:
        raise QodoAuditError(
            "Posting a Qodo review requires GITHUB_TOKEN, GH_TOKEN, or an authenticated GitHub CLI "
            "session with pull-request comment access."
        )
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "gofer-trueforge-qodo-auditor",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(f"{GITHUB_API}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        detail = exc.reason
        try:
            body = json.load(exc)
            detail = body.get("message", detail)
        except Exception:
            pass
        raise QodoAuditError(f"GitHub returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise QodoAuditError(f"Could not reach GitHub: {exc.reason}") from exc


def _clean_request(agent_request: str) -> str:
    cleaned = " ".join(agent_request.split()).replace('"', "'")
    if not cleaned:
        raise QodoAuditError("agent_request cannot be empty.")
    if len(cleaned) > MAX_REQUEST_LENGTH:
        raise QodoAuditError(f"agent_request must be {MAX_REQUEST_LENGTH} characters or fewer.")
    return cleaned


def request_review(pr_url: str, agent_request: str) -> dict[str, Any]:
    """Ask the installed Qodo GitHub App to audit a PR against an agent request."""
    ref = parse_pr_url(pr_url)
    cleaned = _clean_request(agent_request)
    audit_id = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:12]
    instructions = (
        "Audit whether this PR safely and completely fulfills the following TrueForge agent request. "
        "Prioritize logic bugs, security-boundary violations, unintended side effects, data loss, "
        "credential exposure, missing tests, and changes outside the request's scope. "
        f"Agent request: {cleaned}"
    )
    body = (
        f"<!-- trueforge-qodo-audit:{audit_id} -->\n"
        f'/review --pr_reviewer.extra_instructions="{instructions}"'
    )
    comment = _github_json(
        "POST",
        f"/repos/{ref.owner}/{ref.repo}/issues/{ref.number}/comments",
        payload={"body": body},
        require_auth=True,
    )
    return {
        "status": "requested",
        "audit_id": audit_id,
        "pr_url": pr_url,
        "comment_url": comment.get("html_url"),
        "next_step": "Wait for Qodo to respond, then call qodo_audit_status. A request is not approval.",
    }


def _is_qodo_author(login: str) -> bool:
    normalized = login.casefold()
    return any(marker in normalized for marker in QODO_LOGIN_MARKERS)


def _feedback_item(item: dict[str, Any], source: str) -> dict[str, Any]:
    body = item.get("body") or ""
    return {
        "source": source,
        "author": item.get("user", {}).get("login"),
        "state": item.get("state"),
        "submitted_at": item.get("submitted_at") or item.get("created_at"),
        "url": item.get("html_url"),
        "body": body[:8_000],
        "truncated": len(body) > 8_000,
    }


def audit_status(pr_url: str) -> dict[str, Any]:
    """Read Qodo comments and reviews for a PR without treating feedback as approval."""
    ref = parse_pr_url(pr_url)
    comments = _github_json(
        "GET", f"/repos/{ref.owner}/{ref.repo}/issues/{ref.number}/comments?per_page=100"
    )
    reviews = _github_json("GET", f"{ref.api_path}/reviews?per_page=100")
    feedback = [
        _feedback_item(item, source)
        for source, items in (("comment", comments), ("review", reviews))
        for item in items
        if _is_qodo_author(item.get("user", {}).get("login", ""))
    ]
    feedback.sort(key=lambda item: item.get("submitted_at") or "", reverse=True)
    return {
        "status": "reviewed" if feedback else "pending_or_not_installed",
        "pr_url": pr_url,
        "qodo_feedback_count": len(feedback),
        "feedback": feedback[:10],
        "decision": "human_required",
        "guidance": (
            "Qodo feedback is advisory. Resolve material findings and obtain the normal human approval "
            "before consequential actions."
        ),
    }
