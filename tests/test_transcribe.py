from scripts.transcribe import recommend, resolve


def _hw(apple=False, ram=16, nvidia=False, cores=8):
    return {"apple_silicon": apple, "ram_gb": ram, "has_nvidia": nvidia, "cores": cores}


def test_apple_silicon_big_ram_picks_turbo():
    backend, model, _ = recommend(_hw(apple=True, ram=16))
    assert backend == "mlx-whisper" and "turbo" in model


def test_apple_silicon_low_ram_picks_small():
    backend, model, _ = recommend(_hw(apple=True, ram=6))
    assert backend == "mlx-whisper" and model.endswith("whisper-small")


def test_nvidia_picks_faster_whisper_large():
    backend, model, _ = recommend(_hw(apple=False, nvidia=True))
    assert backend == "faster-whisper" and model == "large-v3"


def test_strong_cpu_picks_medium():
    backend, model, _ = recommend(_hw(apple=False, nvidia=False, cores=12))
    assert backend == "faster-whisper" and model == "medium"


def test_weak_cpu_picks_small():
    backend, model, _ = recommend(_hw(apple=False, nvidia=False, cores=2))
    assert backend == "faster-whisper" and model == "small"


def test_explicit_backend_overrides_auto():
    # 显式后端 + 指定模型，不走硬件推荐
    backend, model = resolve({"transcribe_backend": "faster-whisper", "whisper_model": "large-v3"})
    assert backend == "faster-whisper" and model == "large-v3"


def test_explicit_mlx_uses_configured_model():
    backend, model = resolve({"transcribe_backend": "mlx-whisper", "mlx_model": "mlx-community/whisper-medium"})
    assert backend == "mlx-whisper" and model.endswith("whisper-medium")
