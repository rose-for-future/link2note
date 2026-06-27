from scripts.fetchers.github import parse_repo_url, _build_text


def test_parse_repo_url():
    assert parse_repo_url("https://github.com/owner/repo") == ("owner", "repo")
    assert parse_repo_url("https://github.com/owner/repo/tree/main") == ("owner", "repo")


def test_build_text_excludes_noise():
    txt = _build_text(desc="一个工具", readme="# 用法\n安装步骤", stars=99999)
    assert "一个工具" in txt and "用法" in txt
    assert "99999" not in txt and "star" not in txt.lower()


def test_build_text_truncates_long_readme():
    long_readme = "A" * 30000
    txt = _build_text(desc="", readme=long_readme)
    assert len(txt) <= 20000 + 100  # 20000 chars + header + elision marker
    assert "…(README 已截断)" in txt
