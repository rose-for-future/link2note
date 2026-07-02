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


def test_extract_page():
    from scripts.bili_api import extract_page
    assert extract_page("https://www.bilibili.com/video/BV1x?p=5") == 5
    assert extract_page("https://www.bilibili.com/video/BV1x/") == 1
    assert extract_page("https://www.bilibili.com/video/BV1x?spm=a&p=3&x=1") == 3


def test_data_validates_bili_response():
    from scripts.bili_api import _data
    with pytest.raises(RuntimeError):        # code!=0 / data=null → 可读报错，非裸TypeError
        _data({"code": -404, "data": None, "message": "啥都木有"}, "取信息")
    assert _data({"code": 0, "data": {"t": 1}}, "x") == {"t": 1}
