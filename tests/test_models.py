from scripts.models import make_result, clean_title

def test_make_result_fills_defaults():
    r = make_result("douyin", "video", "http://x", "标题", "全文")
    assert r["author"] == "" and r["images"] == [] and r["media"] == {} and r["extra"] == {}
    assert r["text"] == "全文" and r["platform"] == "douyin"

def test_clean_title_strips_illegal():
    assert clean_title('a/b:c*?"<>|d') == "abcd"

def test_clean_title_truncates():
    assert len(clean_title("长" * 200)) == 80

def test_clean_title_empty():
    assert clean_title("   ") == "未命名"
