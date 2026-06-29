import pytest
from scripts.bili_api import extract_bvid, _TAB


def test_extract_bvid_short_and_full():
    assert extract_bvid("https://www.bilibili.com/video/BV1ogVZ6ZEAn/") == "BV1ogVZ6ZEAn"
    assert extract_bvid("https://www.bilibili.com/video/BV1ogVZ6ZEAn/?spm=x&vd_source=y") == "BV1ogVZ6ZEAn"
    assert extract_bvid("BV1ogVZ6ZEAn") == "BV1ogVZ6ZEAn"


def test_extract_bvid_invalid_raises():
    with pytest.raises(ValueError):
        extract_bvid("https://www.bilibili.com/")


def test_wbi_mixin_table_sane():
    # WBI 混淆表必须 64 项、取值都在 0..63（错了签名就废）
    assert len(_TAB) == 64
    assert all(0 <= x < 64 for x in _TAB)
