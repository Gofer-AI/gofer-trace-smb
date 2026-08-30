from unittest.mock import patch

import pytest

from agent.qodo import QodoAuditError, audit_status, parse_pr_url, request_review


def test_parse_pr_url():
    ref = parse_pr_url("https://github.com/Gofer-AI/gofer-trace-smb/pull/42")
    assert (ref.owner, ref.repo, ref.number) == ("Gofer-AI", "gofer-trace-smb", 42)


@pytest.mark.parametrize(
    "url",
    [
        "https://gitlab.com/owner/repo/pull/1",
        "https://github.com/owner/repo/issues/1",
        "https://github.com/owner/repo/pull/0",
        "https://github.com/owner/repo/pull/1/files",
    ],
)
def test_rejects_non_pr_urls(url: str):
    with pytest.raises(QodoAuditError):
        parse_pr_url(url)


@patch("agent.qodo._github_json")
def test_request_review_posts_scoped_qodo_command(github_json):
    github_json.return_value = {"html_url": "https://github.com/o/r/pull/1#comment"}
    result = request_review("https://github.com/o/r/pull/1", "Fix auth without exposing keys")
    payload = github_json.call_args.kwargs["payload"]
    assert payload["body"].startswith("<!-- trueforge-qodo-audit:")
    assert "/review" in payload["body"]
    assert "Fix auth without exposing keys" in payload["body"]
    assert result["status"] == "requested"
    assert result["next_step"].endswith("A request is not approval.")


@patch("agent.qodo._github_json")
def test_audit_status_returns_only_qodo_feedback(github_json):
    github_json.side_effect = [
        [
            {"user": {"login": "qodo-merge[bot]"}, "body": "Finding", "created_at": "2026-01-01", "html_url": "q"},
            {"user": {"login": "person"}, "body": "Looks good", "created_at": "2026-01-02", "html_url": "p"},
        ],
        [],
    ]
    result = audit_status("https://github.com/o/r/pull/1")
    assert result["status"] == "reviewed"
    assert result["qodo_feedback_count"] == 1
    assert result["feedback"][0]["author"] == "qodo-merge[bot]"
    assert result["decision"] == "human_required"
