# Changelog

Формат: [Keep a Changelog](https://keepachangelog.com/uk/1.1.0/), версії: [SemVer](https://semver.org/lang/uk/).
Format: Keep a Changelog, versions follow SemVer.

## [Unreleased]

### Added / Додано
- `app/version.py` — єдине місце з версією; `/api/whoami` тепер повертає `version`.
  Single source of truth for the version; `/api/whoami` now returns `version`.
- `CHANGELOG.md` і бейджі в README. / `CHANGELOG.md` and README badges.

## [0.1.0-alpha.1] — 2026-09-09

Перша публічна альфа. / First public alpha.

### Added / Додано
- Бібліотека відео з превʼю, паспорт файлу (ffprobe, VFR/HDR), дедуплікація.
  Video library with thumbnails, file passport (ffprobe, VFR/HDR), de-duplication.
- Проба перед рендером: 1 кадр або 10-секундний кліп із найдинамічнішої сцени; порівняння шторкою, A/B, 1:1.
  Preview before render: one frame or a 10-second clip from the most dynamic scene; slider, A/B and 1:1 compare.
- Чесна оцінка часу за власними замірами, уточнення після кожної проби.
  Honest ETA from your own measurements, recalibrated after every preview.
- Два рушії: Vulkan (`realesrgan-ncnn-vulkan`, будь-яка карта) і PyTorch + CUDA + TensorRT (NVIDIA, `.pth/.safetensors`).
  Two engines: Vulkan (any GPU) and PyTorch + CUDA + TensorRT (NVIDIA, reads `.pth/.safetensors`).
- Каталог моделей OpenModelDB + дзеркала HuggingFace: 670+ моделей, 300 ставляться однією кнопкою з перевіркою sha256.
  OpenModelDB + HuggingFace model catalog: 670+ models, 300 one-click installs with sha256 verification.
- Оцінка якості моделей (LPIPS) на кадрах із власної бібліотеки.
  Model quality scoring (LPIPS) on frames from your own library.
- Черга із сегментним конвеєром (пік тимчасових файлів ~10 ГБ замість 136 ГБ на 10 хв 4K), сторож диска і зависань, докручування після збою.
  Queue with a segmented pipeline (~10 GB peak temp instead of 136 GB for 10 min of 4K), disk and hang watchdogs, resume after failure.
- Установка `tools/setup.ps1`, окрема тека даних через майстер першого запуску, інтерфейс uk/ru/en.
  `tools/setup.ps1` installer, separate data folder chosen on first run, uk/ru/en UI.

[Unreleased]: https://github.com/life332/apskeyl/compare/v0.1.0-alpha.1...HEAD
[0.1.0-alpha.1]: https://github.com/life332/apskeyl/releases/tag/v0.1.0-alpha.1
