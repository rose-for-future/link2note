"""统一转写入口 + 按硬件自适应选模型。返回纯文字稿，不写文件。

后端：
- mlx-whisper：Apple Silicon 跑 Metal GPU / 神经引擎，最快。
- faster-whisper：跨平台 CTranslate2，device="auto"（有 NVIDIA 用 CUDA，否则 CPU）。
- sensevoice：阿里 FunASR，中文强但依赖重、环境挑（funasr/llvmlite 常装不上）。

`transcribe_backend="auto"`（默认）会**按硬件探测自动选 后端 + 模型**，并在 stderr
打印选择理由（让人/AI 都看得到选了啥、为什么）。想锁定模型就把 backend 设成具体值
（mlx-whisper / faster-whisper）再配 mlx_model / whisper_model。

所有重依赖均在函数内惰性导入。
"""
import os
import sys
import shutil
import platform

_SENSEVOICE = None

# mlx-community 上的 MLX 格式 Whisper 模型
_MLX = {
    "turbo": "mlx-community/whisper-large-v3-turbo",
    "medium": "mlx-community/whisper-medium",
    "small": "mlx-community/whisper-small",
}


def _ram_gb() -> float:
    """物理内存 GB；探测不到返回 0。"""
    try:
        return os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / (1024 ** 3)
    except (ValueError, OSError, AttributeError):
        pass
    try:
        import subprocess
        out = subprocess.run(["sysctl", "-n", "hw.memsize"],
                             capture_output=True, text=True).stdout
        return int(out.strip()) / (1024 ** 3)
    except Exception:
        return 0.0


def detect_hardware() -> dict:
    return {
        "apple_silicon": platform.system() == "Darwin" and platform.machine() == "arm64",
        "ram_gb": _ram_gb(),
        "has_nvidia": shutil.which("nvidia-smi") is not None,
        "cores": os.cpu_count() or 4,
    }


def recommend(hw: dict) -> tuple:
    """按硬件 → (backend, model, 理由)。纯函数，可单测。"""
    if hw["apple_silicon"]:
        ram = hw["ram_gb"]
        if not ram or ram < 8:   # 探测失败(0)也按小内存兜底，避免选 turbo 在低配机 OOM
            tag = f"{ram:.0f}GB" if ram else "内存未知"
            return "mlx-whisper", _MLX["small"], f"Apple Silicon · {tag} → small 防爆内存"
        return "mlx-whisper", _MLX["turbo"], f"Apple Silicon · {ram:.0f}GB 内存 → large-v3-turbo(跑 GPU)"
    if hw["has_nvidia"]:
        return "faster-whisper", "large-v3", "检测到 NVIDIA GPU → large-v3(CUDA)"
    if hw["cores"] >= 8:
        return "faster-whisper", "medium", f"纯 CPU · {hw['cores']} 核 → medium(平衡)"
    return "faster-whisper", "small", f"纯 CPU · {hw['cores']} 核(偏弱) → small(防卡死)"


def resolve(cfg: dict) -> tuple:
    """→ (backend, model)。auto 走硬件推荐；显式后端用 cfg 指定的模型。"""
    backend = cfg.get("transcribe_backend", "auto")
    if backend == "auto":
        backend, model, reason = recommend(detect_hardware())
        print(f"🖥 转写自适应：{reason}", file=sys.stderr)
        return backend, model
    if backend == "mlx-whisper":
        return backend, cfg.get("mlx_model", _MLX["turbo"])
    if backend == "faster-whisper":
        return backend, cfg.get("whisper_model", "small")
    return backend, cfg.get("whisper_model", "small")  # sensevoice 不看 model


def _mlx_whisper(audio_path: str, model_repo: str) -> str:
    import mlx_whisper
    res = mlx_whisper.transcribe(audio_path, path_or_hf_repo=model_repo, language="zh")
    segs = res.get("segments") or []
    if segs:  # 按片段分行，长稿可读
        return "\n".join((s.get("text") or "").strip() for s in segs if (s.get("text") or "").strip())
    return (res.get("text") or "").strip()


def _faster_whisper(audio_path: str, model_size: str) -> str:
    from faster_whisper import WhisperModel
    # device="auto"：有 CUDA 自动用 GPU，否则 CPU；int8 在两端都可用
    model = WhisperModel(model_size, device="auto", compute_type="int8")
    segments, _ = model.transcribe(audio_path, language="zh")
    return "\n".join(seg.text.strip() for seg in segments if seg.text.strip())


def _sensevoice(audio_path: str) -> str:
    global _SENSEVOICE
    from funasr import AutoModel
    from funasr.utils.postprocess_utils import rich_transcription_postprocess
    if _SENSEVOICE is None:
        _SENSEVOICE = AutoModel(
            model="iic/SenseVoiceSmall", trust_remote_code=True,
            vad_model="fsmn-vad", vad_kwargs={"max_single_segment_time": 30000},
            device="cpu",
        )
    res = _SENSEVOICE.generate(input=audio_path, language="zh",
                               use_itn=True, batch_size_s=60)
    return rich_transcription_postprocess(res[0]["text"])


def transcribe_audio(audio_path: str, cfg: dict) -> str:
    backend, model = resolve(cfg)
    if backend == "mlx-whisper":
        return _mlx_whisper(audio_path, model)
    if backend == "faster-whisper":
        return _faster_whisper(audio_path, model)
    if backend == "sensevoice":
        return _sensevoice(audio_path)
    raise ValueError(f"未知 transcribe_backend: {backend}")
