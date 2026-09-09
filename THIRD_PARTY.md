# Third-party components / Сторонние компоненты

Apskeyl's own code is MIT. Everything below is downloaded by the setup scripts or by the
user and keeps its **own** license. Nothing here is redistributed inside this repository.

| Component | What it does here | License | Notes |
|---|---|---|---|
| [FFmpeg](https://ffmpeg.org) (gyan.dev "essentials" build) | decode/encode, frame extraction, scaling | **GPL v3** (build includes x264) | downloaded by `tools/setup.ps1`, not bundled |
| [Real-ESRGAN-ncnn-vulkan](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan) | engine 1 — runs `.param/.bin` models on any Vulkan GPU | MIT | downloaded by `tools/setup.ps1` |
| [ncnn](https://github.com/Tencent/ncnn) | inference framework inside engine 1 | BSD-3 | part of the binary above |
| [Real-ESRGAN models](https://github.com/xinntao/Real-ESRGAN) — `realesr-animevideov3`, `realesrgan-x4plus`, `realesrgan-x4plus-anime`, `realesr-general-x4v3` | base upscaling models | BSD-3 | ship with the ncnn release |
| [PyTorch](https://pytorch.org) + torchvision | engine 2 (CUDA) | BSD-3 | `tools/setup_engine2.ps1`, optional |
| [spandrel](https://github.com/chaiNNer-org/spandrel) | loads `.pth`/`.safetensors` of many architectures | MIT | engine 2 |
| [TensorRT](https://developer.nvidia.com/tensorrt) (`tensorrt_cu12` wheels) | ×2.5 speed-up for ESRGAN-class models | **NVIDIA proprietary license** | installed from NVIDIA's PyPI index by the user; not redistributed |
| [ONNX](https://onnx.ai) | model export for TensorRT | Apache-2.0 | engine 2 |
| [LPIPS](https://github.com/richzhang/PerceptualSimilarity) | perceptual quality metric (model rating) | BSD-2 | engine 2; AlexNet weights downloaded on first use |
| [FastAPI](https://fastapi.tiangolo.com) / Starlette / Pydantic | local API server | MIT / BSD-3 / MIT | `requirements.txt` |
| [uvicorn](https://www.uvicorn.org) | ASGI server | BSD-3 | `requirements.txt` |
| [pywebview](https://pywebview.flowrl.com) + pythonnet | native window over WebView2 | BSD-3 / MIT | `requirements.txt` |
| [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) | renders the UI | Microsoft EULA | already present on Windows 10/11; not bundled |
| [OpenModelDB](https://openmodeldb.info) | model catalogue for the 🧭 tab (metadata only) | CC0 data; per-model licenses vary | downloaded on demand |
| [Ollama](https://ollama.com) + `qwen3:8b` | optional: translates model descriptions into the UI language | MIT / Apache-2.0 | only if you run Ollama locally; otherwise originals are shown |

## Community models — READ THIS BEFORE COMMERCIAL USE

The best-looking models in the "ЯК / HOW" menu are community models from OpenModelDB.
Most of them are **CC BY-NC-SA 4.0 — non-commercial**:

| Model | Author | License |
|---|---|---|
| 4x-UltraSharp | Kim2091 | CC BY-NC-SA 4.0 |
| 4x-NMKD-Siax-200k | NMKD | CC BY-NC-SA 4.0 |
| 4xLSDIRplus | Phhofm | CC BY-NC-SA 4.0 |
| 2x-StarSample (V2 Lite / HQ) | umzi | CC BY-NC-SA 4.0 |
| most other OpenModelDB entries | various | shown on each model's card in the 🧭 tab |

Apskeyl downloads them **only when you click ⬇** and shows the license on the card.
If you upscale videos for money, use the BSD-licensed Real-ESRGAN models
(`realesrgan-x4plus`, `realesr-general-x4v3`, `realesr-animevideov3`) or check each
model's terms yourself. The app itself does not enforce anything — that is on you.

---

## Українською / По-русски

Код Apskeyl — MIT. Усе з таблиці вище **не входить у репозиторій**: його качають
`tools/setup.ps1` / `tools/setup_engine2.ps1` або ви самі, і воно лишається під своїми
ліцензіями. Головне: ffmpeg (збірка з x264) — GPL; TensorRT — ліцензія NVIDIA; більшість
найкращих моделей з OpenModelDB (UltraSharp, Siax, LSDIRplus, StarSample…) — **некомерційні**
(CC BY-NC-SA 4.0). Для комерційної роботи беріть моделі Real-ESRGAN (BSD) або читайте умови
кожної моделі на її картці у вкладці 🧭.
