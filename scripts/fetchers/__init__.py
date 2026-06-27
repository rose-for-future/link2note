REGISTRY = {}   # platform -> fetch(url, cfg) -> ContentResult；各 fetcher 任务里注册

_loaded = False


def load_all():
    """Import all fetcher modules so they register themselves into REGISTRY.
    Safe to call repeatedly (idempotent via _loaded guard).
    """
    global _loaded
    if _loaded:
        return
    _loaded = True
    from scripts.fetchers import douyin  # noqa: F401
    from scripts.fetchers import xiaohongshu  # noqa: F401
    from scripts.fetchers import podcast  # noqa: F401
    from scripts.fetchers import github  # noqa: F401
