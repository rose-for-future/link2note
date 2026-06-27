"""统一转写入口：返回纯文字稿，不写文件。

后端：
- mlx-whisper：Apple Silicon GPU/Neural Engine（Metal），最快，默认 large-v3-turbo。
- faster-whisper：跨平台 CPU 兜底（CTranslate2）。
- sensevoice：阿里 FunASR，中文强但依赖重、环境挑（funasr/llvmlite 常装不上）。
- auto：Apple Silicon 且装了 mlx_whisper → mlx-whisper，否则 faster-whisper。
所有重依赖均在函数内惰性导入。
"""

_SENSEVOICE = None


def _resolve_backend(backend: str) -> str:
    if backend != "auto":
        return backend
    import platform
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        try:
            import mlx_whisper  # noqa: F401
            return "mlx-whisper"
        except ImportError:
            return "faster-whisper"
    return "faster-whisper"


def _mlx_whisper(audio_path: str, model_repo: str) -> str:
    import mlx_whisper
    res = mlx_whisper.transcribe(
        audio_path, path_or_hf_repo=model_repo, language="zh",
    )
    return (res.get("text") or "").strip()


def _faster_whisper(audio_path: str, model_size: str) -> str:
    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_path, language="zh")
    return "".join(seg.text for seg in segments).strip()


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
    backend = _resolve_backend(cfg.get("transcribe_backend", "auto"))
    if backend == "mlx-whisper":
        return _mlx_whisper(audio_path, cfg.get("mlx_model", "mlx-community/whisper-large-v3-turbo"))
    if backend == "faster-whisper":
        return _faster_whisper(audio_path, cfg.get("whisper_model", "small"))
    if backend == "sensevoice":
        return _sensevoice(audio_path)
    raise ValueError(f"未知 transcribe_backend: {backend}")
