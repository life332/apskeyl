/* 💎 АПСКЕЙЛ — фронт. Vanilla JS, без збірки. */
"use strict";
const $ = s => document.querySelector(s);

/* ── мови (власник 28.08: «вибір мови, і щоб від вибору мінялось») ── */
const I18N = {
  uk: {
    tab_lib: "Бібліотека", tab_queue: "Черга", tab_done: "Готове", tab_settings: "Налаштування",
    add_video: "＋ Додати відео", search_ph: "🔍 пошук у розділі…", free: "вільно",
    gpu_busy: "GPU: зайнятий іншим realesrgan",
    dz_title: "кинь відео сюди", dz_sub: "або тисни «＋ Додати відео»", panel_empty: "обери відео зліва",
    improve: "✨ УЛУЧШИ", what: "ЩО", how: "ЯК", how_sub: "— модель", extra: "ДОДАТКОВО",
    extra_sub: "— діє і на пробу, і на рендер", scene: "СЦЕНА ДЛЯ ПРОБИ",
    scene_sub: "(артефакти видно на русі — дефолт: найдинамічніша)",
    grp_top: "🏆 Топ-якість", grp_top_sub: "· повільно", grp_bal: "⚖ Баланс", grp_fast: "⚡ Швидко",
    more_models: "ще одна модель", m_ultrasharp_d: "топ за твоїм вердиктом",
    m_siax_d: "природна, добра на обличчях", m_x4plus: "🔬 Детальна", m_x4plus_d: "x4plus, класика",
    m_x4v3: "🧠 Реальне відео", m_anime: "🎨 Мультяшна", m_anime_d: "animevideov3, згладжує",
    m_lsdir_d: "новіша реалістична",
    op_sharpen: "🔪 Різкість після", op_grain: "🎞 Кінозерно", op_grain_d: "маскує «пластилін»",
    op_denoise: "🧹 Денойз перед", op_denoise_d: "для пожатого джерела", op_codec: "💾 Кодек",
    codec_q: "🎯 Якість", codec_f: "⚡ Швидко", codec_q_note: "H.264, crf16", codec_f_note: "H.265 NVENC, файл менший",
    codec_q_long: "🎯 Якість (H.264 crf16)", codec_f_long: "⚡ Швидко (H.265 NVENC)",
    probe1: "👁 1 кадр (~5 с)", probe10: "🎬 10 секунд", probe10_t: "10 с руху: мерехтіння видно лише у відео",
    enqueue: "🚀 Покращити відео", enqueue_t: "Порахувати все відео у фоні (вкладка ⏳)",
    probe_on: "проба на", hot_scene: "🔥 найдинамічніша сцена (авто)", frame_fail: "⚠ кадр не витягся",
    tag_before: "ДО", tag_after: "ПІСЛЯ", cmp_hold: "👁 Тримай = ДО", cmp_pause: "⏸ Пауза", cmp_play: "▶ Далі",
    cmp_hint: "тягни лінію · затисни кнопку/пробіл = ДО · Esc — вийти", cmp_close: "✕ Закрити",
    queue_empty: "⏳ Черга порожня. Обери відео → УЛУЧШИ → 🚀 Покращити відео.",
    queue_empty_sub: "Вікно можна закривати — рахунок іде у фоні, ПК не засне, поки не дорахує.",
    done_empty: "✅ Ще нічого не готове. Результати лягають у",
    st_title: "🛠 Налаштування", st_grp_ui: "ІНТЕРФЕЙС", st_grp_files: "ФАЙЛИ",
    st_lang: "Мова", st_lang_note: "повідомлення движка (прогнози, причини) — українською",
    st_model: "Модель", st_target: "Ціль", st_codec: "Кодек", st_out: "Тека результатів",
    st_pick: "📁 Обрати…", st_open: "📂 Відкрити", st_tmp: "Тимчасові файли", st_cleanup: "🧹 Очистити",
    st_logs: "📄 Логи", st_yield: "🛡 Ефір має пріоритет",
    st_yield_d: "поки ефір іде — один GPU-потік, ffmpeg упівсили, рушій поступається при просіданні",
    st_threads: "Потоки рушія (-j)", st_threads_d: "load:proc:save · без ефіру", st_tile: "Тайл рушія (-t)",
    st_tile_d: "0 = авто; ≥200, якщо видно шви на небі", st_save: "💾 Зберегти",
    st_grp_models: "МОДЕЛІ", st_models_sub: "— що показувати в меню «ЯК»",
    st_pool_disk: "Файли моделей", st_pool_reset: "Повернути дефолт", q_videos: "відео", q_frames_short: "кадри",
    st_pool_note: "🗑 прибирає файли з диска назавжди; базові моделі з архіву рушія повертаються при старті — їх ховай перемикачем",
    p_missing: "файлів нема", p_base: "базова", p_up: "вище", p_down: "нижче",
    p_del: "видалити файли моделі", g_extra: "📦 Ще",
    pool_empty: "усі моделі приховані — увімкни хоч одну в 🛠 → МОДЕЛІ",
    t_pool_saved: "пул збережено", t_pool_deleted: "файли моделі видалено",
    t_pool_reset: "пул повернуто до дефолту", m_fast: "⚡ без нейромережі",
    tab_scout: "Моделі", sc_refresh: "🔄 Перевірити зараз", u_day: "дн",
    sc_usable: "лише ті, що ставляться одним кліком", sc_new: "лише нові",
    sc_nomatch: "нічого не підходить під фільтри — зніми «лише нові» або зміни пошук", sc_justnow: "щойно",
    sc_h_model: "модель", sc_h_arch: "архітектура · масштаб", sc_h_purpose: "призначення", sc_h_speed: "10 хв відео 1080p",
    sc_scale_hint: "масштаб: у скільки разів збільшує кадр (не швидкість)",
    chip_hint: "у скільки разів повільніше за мультяшну (animevideov3 = ×1)", chip_longer: "довше",
    chip_legend: "якість — наскільки результат схожий на оригінал на твоїх кадрах (100 % = не відрізнити) · ⏱ — скільки рендериться 10 хв відео 1080p→4K",
    q_pct_lbl: "якість", q_of: "з", q_pct_hint: "схожість з оригіналом на твоїх кадрах (LPIPS): 100 % = не відрізнити",
    chip_time_hint: "час рендера 10 хв відео 1080p→4K на цій машині",
    q_better: "краще", q_worse: "гірше", q_base: "база", q_vs: "проти", q_frames: "кадрів з твоєї бібліотеки",
    q_running: "міряю", q_queued: "у черзі", q_measured: "заміряно", q_none: "ще нічого не заміряно — фон почне сам, коли GPU вільний",
    q_started: "у чергу на замір", q_all_done: "усе вже заміряно", st_quality: "Доміряти", st_quality_all: "Переміряти всі",
    q_force_q: "Переміряти всі моделі заново? Це кілька хвилин GPU",
    st_quality_lbl: "Якість моделей", st_quality_note: "LPIPS: кожну модель женемо 1080p→4K на кадрах з твоєї бібліотеки (найдинамічніші моменти найбільших відео) і порівнюємо з оригіналом. ⭐ ×N = у стільки разів ближче до оригіналу, ніж мультяшна. Межа: вхід — чистий даунскейл, не YouTube-стиснення",
    sc_h_avail: "доступність",
    sc_any_scale: "масштаб: будь-який", sc_any_purpose: "призначення: будь-яке",
    sc_seg_all: "усі", sc_seg_usable: "можна скачати", sc_seg_new: "нові", sc_cancel: "✕ скасувати",
    sc_canceled: "скачування скасовано",
    sc_more: "показати ще", sc_empty: "🧭 Каталог ще не завантажено. Тисни «🔄 Перевірити зараз» — це 1.2 МБ і кілька секунд.",
    sc_working: "качаю каталог", sc_never: "каталогу ще нема", sc_models: "моделей",
    sc_checked: "перевірено", sc_next: "наступна через", sc_no_engine2: "другого рушія нема — .pth нічим рахувати",
    sc_installed: "✅ у меню «ЯК» → Ще", sc_mirror: "⬇ дзеркало", sc_direct: "⬇ можна скачати",
    sc_new_note: "за 30 дн нових: {n} — показую {k} останніх релізів (найсвіжіший {d})",
    sc_seg_installed: "скачані", sc_done_where: "скачано · шукай у меню «ЯК» → 📦 Ще",
    sc_sort_new: "спочатку нові", sc_sort_quality: "за класом якості", sc_sort_speed: "за швидкістю", sc_sort_name: "за назвою",
    sc_hf_src: "збірка HuggingFace, OpenModelDB її не знає — архітектура й опис невідомі:",
    sc_full_close: "✕ закрити", sc_dbl_hint: "подвійний клік — на весь екран",
    sc_translated: "🌐 переклад Ollama", sc_original: "показати оригінал", sc_show_translation: "показати переклад",
    sc_translating: "🌐 перекладаю…", sc_m_author: "автор", sc_m_date: "дата", sc_m_size: "розмір",
    sc_m_license: "ліцензія", sc_m_src: "файл", sc_del: "видалити модель з апскейлу",
    sc_del_q: "Видалити файли моделі",
    sc_badformat: "формат не наш:", sc_manual: "🔗 лише вручну", sc_frame: "кадр",
    sc_10min: "10 хв відео", sc_estimate: "(оцінка)", sc_info: "ⓘ Детальніше",
    sc_page: "🔗 Сторінка", sc_install: "⬇ Скачати", sc_installing: "качаю…",
    sc_loading: "читаю…", sc_done: "поставлено", sc_sha_ok: "sha256 звірено",
    s_QUEUED: "у черзі", s_PREPARING: "готую", s_PROCESSING: "рахую", s_ENCODING: "кодую", s_VERIFYING: "перевіряю",
    s_DONE: "готово", s_FAILED: "помилка", s_PAUSED: "пауза", s_CANCELED: "скасовано",
    j_frames: "кадрів", j_seg: "сегмент", j_fps: "кадр/с", j_left: "ще ~", j_elapsed: "минуло",
    j_dead: "двигун не відповідає", j_resume: "▶ Продовжити", j_show: "📂 Показати",
    j_drop_t: "прибрати зі списку (файл лишається)",
    t_added: "додано", t_removed: "прибрано", t_removed_sub: "файл на диску лишився", t_saved: "налаштування збережено",
    t_queued: "🚀 пішло", t_watch: "стеж у ⏳", t_freed: "звільнено", t_tmp_busy: "зараз іде робота — прибирання після",
    t_dialog_only: "нативний діалог доступний лише у вікні програми",
    u_min: "хв", u_hour: "год", u_sec: "с", u_mb: "МБ", u_gb: "ГБ", c_yes: "Так", c_no: "Ні", app_name: "💎 Апскейл",
    tile_unknown: "тривалість невідома — тільки проба", tile_minutes: "≈хвилини", tile_peak: "пік",
    fc_unknown: "⚠ тривалість файлу невідома (битий контейнер?) — прогноз неможливий, але проба працює",
    fc_peak: "💽 пік диска", fc_out: "📦 вихід", fc_free: "вільно на", fc_low: "МАЛО МІСЦЯ",
    busy_frames: "готую кадри…", busy_probe_fast: "рахую швидкий шлях…", busy_probe_nn: "ганяю кадр через нейромережу (~5-10 с)…",
    busy_clip: "готую кліп…", busy_cancel: "скасовую…", cancel: "✕ Скасувати", clip_frames: "кадрів",
    rec_title: "🤖 РЕКОМЕНДАЦІЯ", no_sound: "без звуку", vfr_flag: "⚠ змінний fps — таймінги вирівняємо, звук перевір",
    hdr_flag: "⚠ HDR-джерело — вихід буде SDR (движок 8-біт)", chip_vert: "📱 верт.", chip_vfr: "змінний fps",
    chip_missing: "файл не знайдено", card_del_t: "Прибрати з бібліотеки (файл на диску лишається)",
    n_videos: "відео",
  },
  ru: {
    tab_lib: "Библиотека", tab_queue: "Очередь", tab_done: "Готово", tab_settings: "Настройки",
    add_video: "＋ Добавить видео", search_ph: "🔍 поиск в разделе…", free: "свободно",
    gpu_busy: "GPU: занят другим realesrgan",
    dz_title: "кинь видео сюда", dz_sub: "или жми «＋ Добавить видео»", panel_empty: "выбери видео слева",
    improve: "✨ УЛУЧШИТЬ", what: "ЧТО", how: "КАК", how_sub: "— модель", extra: "ДОПОЛНИТЕЛЬНО",
    extra_sub: "— действует и на пробу, и на рендер", scene: "СЦЕНА ДЛЯ ПРОБЫ",
    scene_sub: "(артефакты видны в движении — по умолчанию: самая динамичная)",
    grp_top: "🏆 Топ-качество", grp_top_sub: "· медленно", grp_bal: "⚖ Баланс", grp_fast: "⚡ Быстро",
    more_models: "ещё одна модель", m_ultrasharp_d: "топ по твоему вердикту",
    m_siax_d: "естественная, хороша на лицах", m_x4plus: "🔬 Детальная", m_x4plus_d: "x4plus, классика",
    m_x4v3: "🧠 Реальное видео", m_anime: "🎨 Мультяшная", m_anime_d: "animevideov3, сглаживает",
    m_lsdir_d: "новая реалистичная",
    op_sharpen: "🔪 Резкость после", op_grain: "🎞 Киноплёнка", op_grain_d: "маскирует «пластилин»",
    op_denoise: "🧹 Денойз до", op_denoise_d: "для пережатого источника", op_codec: "💾 Кодек",
    codec_q: "🎯 Качество", codec_f: "⚡ Быстро", codec_q_note: "H.264, crf16", codec_f_note: "H.265 NVENC, файл меньше",
    codec_q_long: "🎯 Качество (H.264 crf16)", codec_f_long: "⚡ Быстро (H.265 NVENC)",
    probe1: "👁 1 кадр (~5 с)", probe10: "🎬 10 секунд", probe10_t: "10 с движения: мерцание видно только в видео",
    enqueue: "🚀 Улучшить видео", enqueue_t: "Посчитать всё видео в фоне (вкладка ⏳)",
    probe_on: "проба на", hot_scene: "🔥 самая динамичная сцена (авто)", frame_fail: "⚠ кадр не извлёкся",
    tag_before: "ДО", tag_after: "ПОСЛЕ", cmp_hold: "👁 Держи = ДО", cmp_pause: "⏸ Пауза", cmp_play: "▶ Дальше",
    cmp_hint: "тяни линию · зажми кнопку/пробел = ДО · Esc — выйти", cmp_close: "✕ Закрыть",
    queue_empty: "⏳ Очередь пуста. Выбери видео → УЛУЧШИТЬ → 🚀 Улучшить видео.",
    queue_empty_sub: "Окно можно закрывать — счёт идёт в фоне, ПК не уснёт, пока не досчитает.",
    done_empty: "✅ Пока ничего не готово. Результаты ложатся в",
    st_title: "🛠 Настройки", st_grp_ui: "ИНТЕРФЕЙС", st_grp_files: "ФАЙЛЫ",
    st_lang: "Язык", st_lang_note: "сообщения движка (прогнозы, причины) — на украинском",
    st_model: "Модель", st_target: "Цель", st_codec: "Кодек", st_out: "Папка результатов",
    st_pick: "📁 Выбрать…", st_open: "📂 Открыть", st_tmp: "Временные файлы", st_cleanup: "🧹 Очистить",
    st_logs: "📄 Логи", st_yield: "🛡 Эфир в приоритете",
    st_yield_d: "пока идёт эфир — один GPU-поток, ffmpeg вполсилы, движок уступает при просадке",
    st_threads: "Потоки движка (-j)", st_threads_d: "load:proc:save · без эфира", st_tile: "Тайл движка (-t)",
    st_tile_d: "0 = авто; ≥200, если видны швы на небе", st_save: "💾 Сохранить",
    st_grp_models: "МОДЕЛИ", st_models_sub: "— что показывать в меню «КАК»",
    st_pool_disk: "Файлы моделей", st_pool_reset: "Вернуть дефолт", q_videos: "видео", q_frames_short: "кадра",
    st_pool_note: "🗑 убирает файлы с диска навсегда; базовые модели из архива движка возвращаются при старте — их прячь переключателем",
    p_missing: "файлов нет", p_base: "базовая", p_up: "выше", p_down: "ниже",
    p_del: "удалить файлы модели", g_extra: "📦 Ещё",
    pool_empty: "все модели скрыты — включи хоть одну в 🛠 → МОДЕЛИ",
    t_pool_saved: "пул сохранён", t_pool_deleted: "файлы модели удалены",
    t_pool_reset: "пул возвращён к дефолту", m_fast: "⚡ без нейросети",
    tab_scout: "Модели", sc_refresh: "🔄 Проверить сейчас", u_day: "дн",
    sc_usable: "только те, что ставятся одним кликом", sc_new: "только новые",
    sc_nomatch: "ничего не подходит под фильтры — сними «только новые» или измени поиск", sc_justnow: "только что",
    sc_h_model: "модель", sc_h_arch: "архитектура · масштаб", sc_h_purpose: "назначение", sc_h_speed: "10 мин видео 1080p",
    sc_scale_hint: "масштаб: во сколько раз увеличивает кадр (не скорость)",
    chip_hint: "во сколько раз медленнее мультяшной (animevideov3 = ×1)", chip_longer: "дольше",
    chip_legend: "качество — насколько результат похож на оригинал на твоих кадрах (100 % = не отличить) · ⏱ — сколько рендерится 10 мин видео 1080p→4K",
    q_pct_lbl: "качество", q_of: "из", q_pct_hint: "схожесть с оригиналом на твоих кадрах (LPIPS): 100 % = не отличить",
    chip_time_hint: "время рендера 10 мин видео 1080p→4K на этой машине",
    q_better: "лучше", q_worse: "хуже", q_base: "база", q_vs: "против", q_frames: "кадров из твоей библиотеки",
    q_running: "меряю", q_queued: "в очереди", q_measured: "замерено", q_none: "ещё ничего не замерено — фон начнёт сам, когда GPU свободен",
    q_started: "в очередь на замер", q_all_done: "всё уже замерено", st_quality: "Домерить", st_quality_all: "Перемерить все",
    q_force_q: "Перемерить все модели заново? Это несколько минут GPU",
    st_quality_lbl: "Качество моделей", st_quality_note: "LPIPS: каждую модель гоним 1080p→4K на кадрах из твоей библиотеки (самые динамичные моменты самых больших видео) и сравниваем с оригиналом. ⭐ ×N = во столько раз ближе к оригиналу, чем мультяшная. Предел: вход — чистый даунскейл, не YouTube-сжатие",
    sc_h_avail: "доступность",
    sc_any_scale: "масштаб: любой", sc_any_purpose: "назначение: любое",
    sc_seg_all: "все", sc_seg_usable: "можно скачать", sc_seg_new: "новые", sc_cancel: "✕ отменить",
    sc_canceled: "скачивание отменено",
    sc_more: "показать ещё", sc_empty: "🧭 Каталог ещё не загружен. Жми «🔄 Проверить сейчас» — это 1.2 МБ и пара секунд.",
    sc_working: "качаю каталог", sc_never: "каталога ещё нет", sc_models: "моделей",
    sc_checked: "проверено", sc_next: "следующая через", sc_no_engine2: "второго движка нет — .pth нечем считать",
    sc_installed: "✅ в меню «КАК» → Ещё", sc_mirror: "⬇ зеркало", sc_direct: "⬇ можно скачать",
    sc_new_note: "за 30 дн новых: {n} — показываю {k} последних релизов (самый свежий {d})",
    sc_seg_installed: "скачанные", sc_done_where: "скачано · ищи в меню «КАК» → 📦 Ещё",
    sc_sort_new: "сначала новые", sc_sort_quality: "по классу качества", sc_sort_speed: "по скорости", sc_sort_name: "по названию",
    sc_hf_src: "сборка HuggingFace, OpenModelDB её не знает — архитектура и описание неизвестны:",
    sc_full_close: "✕ закрыть", sc_dbl_hint: "двойной клик — на весь экран",
    sc_translated: "🌐 перевод Ollama", sc_original: "показать оригинал", sc_show_translation: "показать перевод",
    sc_translating: "🌐 перевожу…", sc_m_author: "автор", sc_m_date: "дата", sc_m_size: "размер",
    sc_m_license: "лицензия", sc_m_src: "файл", sc_del: "удалить модель из апскейла",
    sc_del_q: "Удалить файлы модели",
    sc_badformat: "формат не наш:", sc_manual: "🔗 только вручную", sc_frame: "кадр",
    sc_10min: "10 мин видео", sc_estimate: "(оценка)", sc_info: "ⓘ Подробнее",
    sc_page: "🔗 Страница", sc_install: "⬇ Скачать", sc_installing: "качаю…",
    sc_loading: "читаю…", sc_done: "поставлено", sc_sha_ok: "sha256 сверено",
    s_QUEUED: "в очереди", s_PREPARING: "готовлю", s_PROCESSING: "считаю", s_ENCODING: "кодирую", s_VERIFYING: "проверяю",
    s_DONE: "готово", s_FAILED: "ошибка", s_PAUSED: "пауза", s_CANCELED: "отменено",
    j_frames: "кадров", j_seg: "сегмент", j_fps: "кадр/с", j_left: "ещё ~", j_elapsed: "прошло",
    j_dead: "движок не отвечает", j_resume: "▶ Продолжить", j_show: "📂 Показать",
    j_drop_t: "убрать из списка (файл остаётся)",
    t_added: "добавлено", t_removed: "убрано", t_removed_sub: "файл на диске остался", t_saved: "настройки сохранены",
    t_queued: "🚀 пошло", t_watch: "следи в ⏳", t_freed: "освобождено", t_tmp_busy: "сейчас идёт работа — уборка после",
    t_dialog_only: "нативный диалог доступен только в окне программы",
    u_min: "мин", u_hour: "ч", u_sec: "с", u_mb: "МБ", u_gb: "ГБ", c_yes: "Да", c_no: "Нет", app_name: "💎 Апскейл",
    tile_unknown: "длительность неизвестна — только проба", tile_minutes: "≈минуты", tile_peak: "пик",
    fc_unknown: "⚠ длительность файла неизвестна (битый контейнер?) — прогноз невозможен, но проба работает",
    fc_peak: "💽 пик диска", fc_out: "📦 выход", fc_free: "свободно на", fc_low: "МАЛО МЕСТА",
    busy_frames: "готовлю кадры…", busy_probe_fast: "считаю быстрый путь…", busy_probe_nn: "гоняю кадр через нейросеть (~5-10 с)…",
    busy_clip: "готовлю клип…", busy_cancel: "отменяю…", cancel: "✕ Отменить", clip_frames: "кадров",
    rec_title: "🤖 РЕКОМЕНДАЦИЯ", no_sound: "без звука", vfr_flag: "⚠ переменный fps — тайминги выровняем, звук проверь",
    hdr_flag: "⚠ HDR-источник — выход будет SDR (движок 8-бит)", chip_vert: "📱 верт.", chip_vfr: "переменный fps",
    chip_missing: "файл не найден", card_del_t: "Убрать из библиотеки (файл на диске остаётся)",
    n_videos: "видео",
  },
  en: {
    tab_lib: "Library", tab_queue: "Queue", tab_done: "Done", tab_settings: "Settings",
    add_video: "＋ Add video", search_ph: "🔍 search this tab…", free: "free",
    gpu_busy: "GPU: busy (Automontage)",
    dz_title: "drop a video here", dz_sub: "or press “＋ Add video”", panel_empty: "pick a video on the left",
    improve: "✨ ENHANCE", what: "WHAT", how: "HOW", how_sub: "— model", extra: "EXTRAS",
    extra_sub: "— applies to preview and render", scene: "PREVIEW SCENE",
    scene_sub: "(artifacts show in motion — default: the busiest scene)",
    grp_top: "🏆 Top quality", grp_top_sub: "· slow", grp_bal: "⚖ Balanced", grp_fast: "⚡ Fast",
    more_models: "one more model", m_ultrasharp_d: "your pick as the best",
    m_siax_d: "natural, good on faces", m_x4plus: "🔬 Detailed", m_x4plus_d: "x4plus, the classic",
    m_x4v3: "🧠 Real video", m_anime: "🎨 Cartoon", m_anime_d: "animevideov3, smooths",
    m_lsdir_d: "newer realistic",
    op_sharpen: "🔪 Sharpen after", op_grain: "🎞 Film grain", op_grain_d: "hides the “plastic” look",
    op_denoise: "🧹 Denoise before", op_denoise_d: "for heavily compressed sources", op_codec: "💾 Codec",
    codec_q: "🎯 Quality", codec_f: "⚡ Fast", codec_q_note: "H.264, crf16", codec_f_note: "H.265 NVENC, smaller file",
    codec_q_long: "🎯 Quality (H.264 crf16)", codec_f_long: "⚡ Fast (H.265 NVENC)",
    probe1: "👁 1 frame (~5 s)", probe10: "🎬 10 seconds", probe10_t: "10 s of motion: flicker only shows in video",
    enqueue: "🚀 Enhance video", enqueue_t: "Process the whole video in background (⏳ tab)",
    probe_on: "preview at", hot_scene: "🔥 busiest scene (auto)", frame_fail: "⚠ frame not extracted",
    tag_before: "BEFORE", tag_after: "AFTER", cmp_hold: "👁 Hold = BEFORE", cmp_pause: "⏸ Pause", cmp_play: "▶ Play",
    cmp_hint: "drag the line · hold button/space = BEFORE · Esc — close", cmp_close: "✕ Close",
    queue_empty: "⏳ Queue is empty. Pick a video → ENHANCE → 🚀 Enhance video.",
    queue_empty_sub: "You can close the window — work continues in background, the PC won't sleep until done.",
    done_empty: "✅ Nothing finished yet. Results go to",
    st_title: "🛠 Settings", st_grp_ui: "INTERFACE", st_grp_files: "FILES",
    st_lang: "Language", st_lang_note: "engine messages (estimates, reasons) are in Ukrainian",
    st_model: "Model", st_target: "Target", st_codec: "Codec", st_out: "Output folder",
    st_pick: "📁 Choose…", st_open: "📂 Open", st_tmp: "Temporary files", st_cleanup: "🧹 Clean up",
    st_logs: "📄 Logs", st_yield: "🛡 Stream has priority",
    st_yield_d: "while the stream is live — one GPU thread, ffmpeg at half power, engine yields on dips",
    st_threads: "Engine threads (-j)", st_threads_d: "load:proc:save · when no stream", st_tile: "Engine tile (-t)",
    st_tile_d: "0 = auto; ≥200 if seams show in skies", st_save: "💾 Save",
    st_grp_models: "MODELS", st_models_sub: "— what shows in the “HOW” menu",
    st_pool_disk: "Model files", st_pool_reset: "Restore defaults", q_videos: "videos", q_frames_short: "frames",
    st_pool_note: "🗑 removes files from disk for good; base models are copied back on start — hide those with the switch",
    p_missing: "files missing", p_base: "base", p_up: "up", p_down: "down",
    p_del: "delete model files", g_extra: "📦 More",
    pool_empty: "all models are hidden — enable one in 🛠 → MODELS",
    t_pool_saved: "pool saved", t_pool_deleted: "model files deleted",
    t_pool_reset: "pool restored to defaults", m_fast: "⚡ no neural net",
    tab_scout: "Models", sc_refresh: "🔄 Check now", u_day: "d",
    sc_usable: "one-click installable only", sc_new: "new only",
    sc_nomatch: "nothing matches the filters — untick “new only” or change the search", sc_justnow: "just now",
    sc_h_model: "model", sc_h_arch: "architecture · scale", sc_h_purpose: "purpose", sc_h_speed: "10-min 1080p video",
    sc_scale_hint: "scale: how many times it enlarges the frame (not speed)",
    chip_hint: "how many times slower than the cartoon model (animevideov3 = ×1)", chip_longer: "longer",
    chip_legend: "quality — how close the result is to the original on your frames (100 % = indistinguishable) · ⏱ — render time for a 10-min 1080p→4K video",
    q_pct_lbl: "quality", q_of: "of", q_pct_hint: "similarity to the original on your frames (LPIPS): 100 % = indistinguishable",
    chip_time_hint: "render time for a 10-min 1080p→4K video on this machine",
    q_better: "better", q_worse: "worse", q_base: "baseline", q_vs: "vs", q_frames: "frames from your library",
    q_running: "measuring", q_queued: "queued", q_measured: "measured", q_none: "nothing measured yet — runs by itself when the GPU is free",
    q_started: "queued for measuring", q_all_done: "everything is measured", st_quality: "Measure missing", st_quality_all: "Re-measure all",
    q_force_q: "Re-measure every model? A few minutes of GPU",
    st_quality_lbl: "Model quality", st_quality_note: "LPIPS: every model is run 1080p→4K on frames from your library (busiest moments of the largest videos) and compared with the original. ⭐ ×N = that many times closer to the original than the cartoon model. Limit: input is a clean downscale, not YouTube compression",
    sc_h_avail: "availability",
    sc_any_scale: "scale: any", sc_any_purpose: "purpose: any",
    sc_seg_all: "all", sc_seg_usable: "downloadable", sc_seg_new: "new", sc_cancel: "✕ cancel",
    sc_canceled: "download canceled",
    sc_more: "show more", sc_empty: "🧭 Catalogue not fetched yet. Hit “🔄 Check now” — it's 1.2 MB and a few seconds.",
    sc_working: "fetching catalogue", sc_never: "no catalogue yet", sc_models: "models",
    sc_checked: "checked", sc_next: "next in", sc_no_engine2: "second engine missing — nothing can run .pth",
    sc_installed: "✅ in HOW menu → More", sc_mirror: "⬇ mirror", sc_direct: "⬇ downloadable",
    sc_new_note: "new in 30 days: {n} — showing the {k} latest releases (newest {d})",
    sc_seg_installed: "downloaded", sc_done_where: "downloaded · find it in HOW menu → 📦 More",
    sc_sort_new: "new first", sc_sort_quality: "by quality class", sc_sort_speed: "by speed", sc_sort_name: "by name",
    sc_hf_src: "HuggingFace collection unknown to OpenModelDB — architecture and description unknown:",
    sc_full_close: "✕ close", sc_dbl_hint: "double-click — full screen",
    sc_translated: "🌐 Ollama translation", sc_original: "show original", sc_show_translation: "show translation",
    sc_translating: "🌐 translating…", sc_m_author: "author", sc_m_date: "date", sc_m_size: "size",
    sc_m_license: "license", sc_m_src: "file", sc_del: "remove model from Apskeyl",
    sc_del_q: "Delete model files",
    sc_badformat: "unsupported format:", sc_manual: "🔗 manual only", sc_frame: "frame",
    sc_10min: "10-min video", sc_estimate: "(estimate)", sc_info: "ⓘ Details",
    sc_page: "🔗 Page", sc_install: "⬇ Download", sc_installing: "downloading…",
    sc_loading: "loading…", sc_done: "installed", sc_sha_ok: "sha256 verified",
    s_QUEUED: "queued", s_PREPARING: "preparing", s_PROCESSING: "processing", s_ENCODING: "encoding", s_VERIFYING: "verifying",
    s_DONE: "done", s_FAILED: "failed", s_PAUSED: "paused", s_CANCELED: "canceled",
    j_frames: "frames", j_seg: "segment", j_fps: "fps", j_left: "~", j_elapsed: "elapsed",
    j_dead: "engine not responding", j_resume: "▶ Resume", j_show: "📂 Show",
    j_drop_t: "remove from list (file stays)",
    t_added: "added", t_removed: "removed", t_removed_sub: "file kept on disk", t_saved: "settings saved",
    t_queued: "🚀 started", t_watch: "watch in ⏳", t_freed: "freed", t_tmp_busy: "work in progress — clean up later",
    t_dialog_only: "native dialog is available only inside the app window",
    u_min: "min", u_hour: "h", u_sec: "s", u_mb: "MB", u_gb: "GB", c_yes: "Yes", c_no: "No", app_name: "💎 Upscale",
    tile_unknown: "duration unknown — preview only", tile_minutes: "≈minutes", tile_peak: "peak",
    fc_unknown: "⚠ file duration unknown (broken container?) — no estimate, but preview works",
    fc_peak: "💽 disk peak", fc_out: "📦 output", fc_free: "free on", fc_low: "LOW DISK SPACE",
    busy_frames: "preparing frames…", busy_probe_fast: "computing fast path…", busy_probe_nn: "running the frame through the network (~5-10 s)…",
    busy_clip: "preparing clip…", busy_cancel: "canceling…", cancel: "✕ Cancel", clip_frames: "frames",
    rec_title: "🤖 RECOMMENDATION", no_sound: "no audio", vfr_flag: "⚠ variable fps — timings will be fixed, check audio",
    hdr_flag: "⚠ HDR source — output will be SDR (8-bit engine)", chip_vert: "📱 vert.", chip_vfr: "variable fps",
    chip_missing: "file not found", card_del_t: "Remove from library (file stays on disk)",
    n_videos: "videos",
  },
};
let LANG = "uk";
const t = k => (I18N[LANG] && I18N[LANG][k]) || I18N.uk[k] || k;
function applyLang(lang) {
  LANG = I18N[lang] ? lang : "uk";
  document.documentElement.lang = LANG;
  document.querySelectorAll("[data-i18n]").forEach(el => el.textContent = t(el.dataset.i18n));
  document.querySelectorAll("[data-i18n-title]").forEach(el => el.title = t(el.dataset.i18nTitle));
  document.querySelectorAll("[data-i18n-ph]").forEach(el => el.placeholder = t(el.dataset.i18nPh));
  $("#gpubadge").textContent = t("gpu_busy");
  $("#tbMin").title = "";
}
/* будь-яка не-2xx відповідь має ставати ПОМИЛКОЮ з текстом, а не мовчазним TypeError */
async function api(p, opt) {
  const r = await fetch(p, opt);
  let j = null;
  try { j = await r.json(); } catch (e) { /* не JSON */ }
  if (!r.ok) throw new Error((j && (j.error || j.detail)) || ("HTTP " + r.status));
  return j;
}
const esc = s => String(s ?? "").replace(/[&<>"']/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

let LIB = [];            // бібліотека
let SEL = null;          // вибраний item
let TARGET = "4k";       // плитка
let EST = null;          // останній /api/estimate
let scrubTimer = null;

/* ── утиліти ── */
// власне підтвердження по центру (власник 08.09: системний confirm() WebView2 липне до верхньої грані)
function askConfirm(text) {
  return new Promise(res => {
    const box = $("#confirmBox"); $("#confirmText").textContent = text;
    box.classList.remove("hidden");
    const done = v => { box.classList.add("hidden"); document.removeEventListener("keydown", onKey); res(v); };
    const onKey = e => { if (e.key === "Escape") done(false); else if (e.key === "Enter") done(true); };
    document.addEventListener("keydown", onKey);
    $("#confirmYes").onclick = () => done(true);
    $("#confirmNo").onclick = () => done(false);
    box.onclick = e => { if (e.target === box) done(false); };
    $("#confirmYes").focus();
  });
}
function toast(msg, err) {
  const d = document.createElement("div");
  d.className = "toast" + (err ? " err" : "");
  d.textContent = msg;
  $("#toasts").append(d);
  setTimeout(() => d.remove(), err ? 6000 : 3500);
}
function busy(on, text) {
  $("#busy").classList.toggle("hidden", !on);
  if (text) $("#busyText").textContent = text;
  if (!on) { $("#busyBar").classList.add("hidden"); $("#busyCancel").classList.add("hidden");
             $("#busyFill").style.width = "0"; }
}
const fmtSec = s => s < 90 ? `${Math.round(s)} ${t("u_sec")}` : s < 5400 ? `${Math.round(s/60)} ${t("u_min")}`
                                                            : `${(s/3600).toFixed(1)} ${t("u_hour")}`;
/* ── пошук у розділі (власник 28.08) ── */
let SEARCH = "";
$("#search").addEventListener("input", () => { SEARCH = $("#search").value.trim().toLowerCase(); renderLib(); renderJobs(); });
const matches = name => !SEARCH || name.toLowerCase().includes(SEARCH);
const fmtDur = s => {
  s = Math.round(s || 0);
  const m = Math.floor(s / 60), ss = String(s % 60).padStart(2, "0");
  return m >= 60 ? `${Math.floor(m/60)}:${String(m%60).padStart(2,"0")}:${ss}` : `${m}:${ss}`;
};
const fmtGB = b => b < 1e9 ? Math.max(1, Math.round(b / 1e6)) + " " + t("u_mb")
                           : (b / 1e9).toFixed(b > 5e9 ? 0 : 1) + " " + t("u_gb");
const fmtMin = (lo, hi) => lo >= 60 ? `${(lo/60).toFixed(1)}-${(hi/60).toFixed(1)} ${t("u_hour")}`
                                    : `${Math.round(lo)}-${Math.round(hi)} ${t("u_min")}`;
const resBadge = i => i.short >= 2100 ? "4K" : i.short >= 1400 ? "2K"
                    : i.short >= 1000 ? "1080p" : i.short >= 700 ? "720p" : i.short + "p";
const baseName = p => p.split(/[\\/]/).pop();

/* ── вкладки ── */
document.querySelectorAll(".railbtn").forEach(b => b.onclick = () => {
  document.querySelectorAll(".railbtn").forEach(x => x.classList.remove("active"));
  b.classList.add("active");
  document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
  $("#tab-" + b.dataset.tab).classList.add("active");
  $("#topbar").classList.toggle("hidden", b.dataset.tab === "settings");   // у налаштуваннях бар ні до чого
  $("#btnAdd").classList.toggle("hidden", b.dataset.tab !== "lib");        // «Додати» — лише в бібліотеці
  // права панель «обери відео зліва» — лише в бібліотеці (власник 08.09: у черзі, готовому,
  // моделях і налаштуваннях їй нема чого робити, а ширину з'їдає)
  $("#app").classList.toggle("noaside", b.dataset.tab !== "lib");
  // каталог моделей вантажимо лише коли на нього справді зайшли (671 запис)
  if (b.dataset.tab === "scout" && !SCOUT.items.length) scLoad(false);
});

/* ── бібліотека ── */
async function refresh() {
  let j;
  try { j = await api("/api/library"); }
  catch (e) { toast("бібліотека не відповіла: " + e.message, true); return; }
  LIB = j.items;
  renderLib();
}
function renderLib() {
  const grid = $("#grid");
  grid.innerHTML = "";
  $("#dropzone").style.display = LIB.length ? "none" : "flex";
  $("#counter").textContent = LIB.length ? LIB.length + " " + t("n_videos") : "";
  for (const it of LIB) {
    if (!matches(baseName(it.path))) continue;
    const i = it.info;
    const c = document.createElement("div");
    c.className = "card" + (it.exists ? "" : " missing") + (SEL && SEL.id === it.id ? " sel" : "");
    c.innerHTML = `
      <div class="cthumb"><img loading="lazy" src="/thumb/${encodeURIComponent(it.thumb)}">
        <span class="cdur mono">${fmtDur(i.dur)}</span></div>
      <div class="cbody">
        <div class="cname" title="${esc(it.path)}">${esc(baseName(it.path))}</div>
        <div class="cmeta">
          <span class="chip res">${resBadge(i)}</span>
          <span class="chip">${i.fps} fps</span>
          <span class="chip">${fmtGB(i.size)}</span>
          ${i.vertical ? `<span class="chip">${t("chip_vert")}</span>` : ""}
          ${i.vfr ? `<span class="chip" style="color:var(--err)">${t("chip_vfr")}</span>` : ""}
          ${it.exists ? "" : `<span class="chip" style="color:var(--err)">${t("chip_missing")}</span>`}
          <span class="flex1"></span>
          <button class="cdel" title="${t("card_del_t")}">🗑</button>
        </div></div>`;
    c.onclick = () => select(it);
    c.querySelector(".cdel").onclick = async e => {
      e.stopPropagation();
      try {
        await api(`/api/item/${it.id}`, { method: "DELETE" });
        if (SEL && SEL.id === it.id) { SEL = null; $("#panel").classList.add("empty");
          $("#panelEmpty").classList.remove("hidden"); $("#panelBody").classList.add("hidden"); }
        toast(`${t("t_removed")}: ${baseName(it.path)} (${t("t_removed_sub")})`);
        refresh();
      } catch (err) { toast(err.message, true); }
    };
    grid.append(c);
  }
}

async function addPaths(paths) {
  if (!paths || !paths.length) return;
  busy(true, "читаю файли (паспорт + превʼю)…");
  try {
    const j = await api("/api/add", { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paths }) });
    let ok = 0;
    for (const r of j.results) {
      if (r.ok) ok++;
      else toast(`${baseName(r.path)}: ${r.why}`, r.why !== "уже в бібліотеці");
    }
    if (ok) toast(`${t("t_added")}: ${ok}`);
    await refresh();
  } finally { busy(false); }
}

$("#btnAdd").onclick = async () => {
  if (!window.pywebview) { toast(t("t_dialog_only"), true); return; }
  const files = await window.pywebview.api.pick_files();
  addPaths(files);
};
$("#btnInbox").onclick = async () => {
  busy(true, "сканую приймальню…");
  try {
    const j = await api("/api/scan_inbox", { method: "POST" });
    const ok = j.results.filter(r => r.ok).length;
    toast(ok ? `з приймальні додано: ${ok}` : `у приймальні порожньо (${j.inbox || "inbox"})`);
    await refresh();
  } finally { busy(false); }
};

/* drag&drop: у WebView2 File.path часто відсутній — тоді чесно шлемо до «＋» */
const dz = document.body;
dz.addEventListener("dragover", e => { e.preventDefault(); $("#dropzone").classList.add("drag"); });
dz.addEventListener("dragleave", () => $("#dropzone").classList.remove("drag"));
dz.addEventListener("drop", e => {
  e.preventDefault();
  $("#dropzone").classList.remove("drag");
  const paths = [...(e.dataTransfer.files || [])].map(f => f.path).filter(Boolean);
  if (paths.length) addPaths(paths);
  else toast("Провідник не віддав шлях — тисни «＋ Додати відео»", true);
});

/* ── вибір і панель ── */
async function select(it) {
  SEL = it;
  document.querySelectorAll(".card").forEach(c => c.classList.remove("sel"));
  refreshCardSel();
  $("#panel").classList.remove("empty");
  $("#panelEmpty").classList.add("hidden");
  $("#panelBody").classList.remove("hidden");
  $("#menu").classList.add("hidden");
  const i = it.info;
  $("#pv").src = "/thumb/" + it.thumb;
  $("#passport").innerHTML =
    `<b>${esc(baseName(it.path))}</b><br>` +
    `${i.w}×${i.h} · ${i.fps} fps · ${fmtDur(i.dur)} · ${i.vcodec}` +
    (i.acodec ? ` · 🔊 ${i.acodec}${i.atracks > 1 ? " ×" + i.atracks : ""}` : " · " + t("no_sound")) +
    ` · ${fmtGB(i.size)}` +
    (i.vfr ? `<br><span class="vfrflag">${t("vfr_flag")}</span>` : "") +
    (i.hdr ? `<br><span class="vfrflag">${t("hdr_flag")}</span>` : "");
  const rec = it.rec || {};
  $("#recbox").innerHTML = `<div class="rectitle">${t("rec_title")}</div>${rec.text || ""}`;
  // вердикт власника 28.08: дефолт — швидкий шлях; нейромережа — опція, яку радимо
  // лише для малої роздільної / сильно пожатого джерела
  // дефолтна модель — з налаштувань (рейтинг власника 28.08: UltraSharp)
  const def = (SETTINGS && SETTINGS.model) || "4x-UltraSharp-opt-fp16";
  document.querySelectorAll('input[name=model]').forEach(r => r.checked = r.value === def);
}

/* ── Етап 3: у чергу ── */
$("#btnQueue").onclick = async () => {
  if (!SEL) return;
  const model = curModel();
  if (!model) { toast(t("pool_empty"), true); return; }
  const e = EST && EST[TARGET];
  const est = e && !e.unknown ? ` (≈${fmtMin(e.minutes_lo, e.minutes_hi)})` : "";
  try {
    const j = await api("/api/jobs", { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: SEL.id, target: TARGET, model, ops: opsNow() }) });
    toast(`${t("t_queued")}: ${baseName(SEL.path)} → ${TARGET.toUpperCase()}${est} · ${t("t_watch")}`);
    document.querySelector('.railbtn[data-tab=queue]').click();
    pollJobs();
  } catch (err) { toast(err.message, true); }
};

/* ── черга і готове ── */
const STATE_CLS = { QUEUED: "", PREPARING: "run", PROCESSING: "run", ENCODING: "run", VERIFYING: "run",
  DONE: "ok", FAILED: "err", PAUSED: "pause", CANCELED: "" };
const RUNNING_STATES = ["PREPARING", "PROCESSING", "ENCODING", "VERIFYING"];
// підпис моделі — з пулу (Етап 6 п.4): перейменував у налаштуваннях → змінилось і в черзі
const recipeName = r => (r.target || "4k").toUpperCase() + " · " + modelLabel(r.model) +
  (r.ops && (r.ops.sharpen > 0 || r.ops.grain || r.ops.denoise || r.ops.codec === "hevc_nvenc")
    ? " · " + [r.ops.sharpen > 0 ? `різк ${r.ops.sharpen}` : "", r.ops.grain ? "зерно" : "",
               r.ops.denoise ? "денойз" : "", r.ops.codec === "hevc_nvenc" ? "H.265" : ""]
              .filter(Boolean).join("+") : "");
let JOBS = [];
async function pollJobs() {
  let j;
  try { j = await api("/api/jobs"); } catch (e) { return; }
  JOBS = j.jobs;
  const badge = $("#qbadge");
  badge.textContent = j.active || "";
  badge.classList.toggle("hidden", !j.active);
  renderJobs();
}
function renderJobs() {
  const q = JOBS.filter(x => x.state !== "DONE" && matches(x.name)),
        d = JOBS.filter(x => x.state === "DONE" && matches(x.name));
  $("#queueEmpty").classList.toggle("hidden", q.length > 0);
  $("#doneEmpty").classList.toggle("hidden", d.length > 0);
  $("#queueList").innerHTML = q.slice().reverse().map(jobCard).join("");
  $("#doneList").innerHTML = d.slice().reverse().map(jobCard).join("");
}
function jobCard(x) {
  const label = t("s_" + x.state), cls = STATE_CLS[x.state] || "";
  const running = RUNNING_STATES.includes(x.state);
  const meta = [];
  if (running || x.state === "PAUSED") {
    if (x.frames_total) meta.push(`${x.frames_done}/${x.frames_total} ${t("j_frames")}`);
    if (x.seg_total > 1) meta.push(`${t("j_seg")} ${Math.min(x.seg_done + 1, x.seg_total)}/${x.seg_total}`);
    if (x.speed) meta.push(`${x.speed} ${t("j_fps")}`);
    if (x.eta_s > 0) meta.push(`${t("j_left")}${fmtSec(x.eta_s)}`);
  }
  if (x.elapsed_s) meta.push(`${t("j_elapsed")} ${fmtSec(x.elapsed_s)}`);
  if (x.state === "DONE") meta.push(fmtGB(x.out_size || 0));
  if (x.reason) meta.push(esc(x.reason));
  if (running && !x.alive) meta.push(`<span style="color:var(--err)">${t("j_dead")}</span>`);
  const btns = [];
  if (running) btns.push(`<button class="btn ghost" onclick="jobDo(${x.id},'pause')">⏸</button>`,
                         `<button class="btn ghost" onclick="jobDo(${x.id},'cancel')">✕</button>`);
  if (x.state === "QUEUED") btns.push(`<button class="btn ghost" onclick="jobDo(${x.id},'pause')">⏸</button>`,
                                     `<button class="btn ghost" onclick="jobDo(${x.id},'cancel')">✕</button>`);
  if (x.state === "PAUSED" || x.state === "FAILED")
    btns.push(`<button class="btn ghost" onclick="jobDo(${x.id},'resume')">${t("j_resume")}</button>`,
              `<button class="btn ghost" onclick="jobDo(${x.id},'cancel')">✕</button>`);
  if (x.state === "DONE") btns.push(`<button class="btn ghost" onclick="openOut(${x.id})">${t("j_show")}</button>`);
  if (["DONE", "FAILED", "CANCELED"].includes(x.state))
    btns.push(`<button class="btn ghost" onclick="jobDrop(${x.id})" title="${t("j_drop_t")}">🗑</button>`);
  return `<div class="job ${running ? "running" : ""} ${x.state === "FAILED" ? "failed" : ""} ${x.state === "DONE" ? "done" : ""}">
    <div class="jhead"><span class="jname" title="${esc(x.src)}">${esc(x.name)}</span>
      <span class="dim mono">${recipeName(x.recipe)}</span>
      <span class="jstate ${cls}">${label}</span></div>
    <div class="jbar"><div class="jfill" style="width:${x.state === "DONE" ? 100 : x.pct}%"></div></div>
    <div class="jhead"><div class="jmeta mono">${meta.join(" · ")}</div><span class="flex1"></span>
      <div class="jbtns">${btns.join("")}</div></div></div>`;
}
window.jobDo = async (id, action) => {
  try { await api(`/api/job/${id}/${action}`, { method: "POST" }); } catch (e) { toast(e.message, true); }
  pollJobs();
};
window.jobDrop = async id => {
  try { await api(`/api/job/${id}`, { method: "DELETE" }); } catch (e) { toast(e.message, true); }
  pollJobs();
};
window.openOut = async id => {
  const x = JOBS.find(j => j.id === id);
  if (!x || !x.out_path) return;
  try { await api("/api/open_folder", { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path: x.out_path }) }); }
  catch (e) { toast(e.message, true); }
};
setInterval(pollJobs, 2000);
pollJobs();
function refreshCardSel() {
  const cards = [...document.querySelectorAll(".card")];
  LIB.forEach((it, idx) => {
    if (SEL && it.id === SEL.id && cards[idx]) cards[idx].classList.add("sel");
  });
}

/* ── меню «що і як» ── */
$("#btnImprove").onclick = async () => {
  $("#menu").classList.toggle("hidden");
  if (!$("#menu").classList.contains("hidden")) {
    initScrub();
    await recalc();
  }
};
document.addEventListener("change", e => {
  if (e.target.name === "model") recalc();
});

async function recalc() {
  if (!SEL) return;
  const model = curModel();
  if (!model) return;                       // пул порожній — прогнозувати нічим
  try {
    EST = await api("/api/estimate", { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: SEL.id, target: TARGET, model }) });
  } catch (e) { toast("прогноз не порахувався: " + e.message, true); return; }
  const tiles = $("#tiles");
  tiles.innerHTML = "";
  const names = { fhd: "Full HD", "2k": "2K", "4k": "4K" };
  for (const key of ["fhd", "2k", "4k"]) {
    const e = EST[key];
    const tile = document.createElement("div");
    const muted = e.plan.op === "clean";
    const warny = !!e.plan.down;
    tile.className = "tile" + (TARGET === key ? " sel" : "") + (muted ? " muted" : "")
      + (warny ? " warny" : "");
    tile.innerHTML = `<div class="tname">${names[key]}</div>
      <div class="tnote">${e.plan.note}</div>
      <div class="tcost mono">${e.unknown ? t("tile_unknown")
        : (model === "fast" || muted ? t("tile_minutes") : "≈" + fmtMin(e.minutes_lo, e.minutes_hi))
          + ` · ${t("tile_peak")} ` + e.peak_gb + " " + t("u_gb")}</div>`;
    tile.onclick = () => { TARGET = key; recalc(); persistPanel(); };
    tiles.append(tile);
  }
  const e = EST[TARGET];
  // Етап 2: кнопка «10 секунд» з ЧЕСНИМ часом (x4plus → десятки хвилин, хай бачить)
  const b10 = $("#btnProbe10");
  b10.disabled = false;
  b10.textContent = `${t("probe10")} (~${fmtSec(e.clip_s || 0)})`;
  b10.classList.toggle("warnbtn", (e.clip_s || 0) > 180);
  const drv = (SETTINGS && SETTINGS.out_drive) || "A";
  $("#forecast").innerHTML = e.unknown
    ? t("fc_unknown")
    : `⏱ ≈ <b>${fmtMin(e.minutes_lo, e.minutes_hi)}</b>` +
      ` · ${t("fc_peak")} ${e.peak_gb} ${t("u_gb")} · ${t("fc_out")} ~${e.out_gb} ${t("u_gb")} · ${t("fc_free")} ${drv}: ${e.free_gb} ${t("u_gb")}` +
      (e.free_gb < 25 ? ` · <span style="color:var(--err)">${t("fc_low")}</span>` : "");
}

/* скрубер сцени */
function initScrub() {
  const i = SEL.info;
  const s = $("#scrubT");
  s.max = Math.max(1, i.dur - 0.5);
  s.value = SEL.hard_t || i.dur * 0.4;
  scrubShow();
}
function scrubShow() {
  const tv = parseFloat($("#scrubT").value);
  $("#scrubLabel").textContent = `${t("probe_on")} ${fmtDur(tv)}` +
    (Math.abs(tv - (SEL.hard_t || -1)) < 1 ? " · " + t("hot_scene") : "");
  clearTimeout(scrubTimer);
  scrubTimer = setTimeout(() => {
    const img = $("#scrubImg");
    img.onerror = () => { $("#scrubLabel").textContent += " · " + t("frame_fail"); };
    img.src = `/api/frame/${SEL.id}?t=${tv}&r=${Date.now()}`;
  }, 180);
}
$("#scrubT").addEventListener("input", scrubShow);

/* ── проба 1 кадра ── */
$("#btnProbe1").onclick = async () => {
  if (!SEL) return;
  const model = curModel();
  if (!model) { toast(t("pool_empty"), true); return; }
  const tv = parseFloat($("#scrubT").value);
  busy(true, model === "fast" ? t("busy_probe_fast") : t("busy_probe_nn"));
  try {
    const j = await api("/api/probe", { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: SEL.id, t: tv, target: TARGET, model, ops: opsNow() }) });
    if (j.error) { toast(j.error, true); return; }
    openCompare(j);
  } catch (e) { toast("проба не вдалась: " + e, true); }
  finally { busy(false); }
};

/* ── проба 10 секунд (Етап 2) ── */
$("#btnProbe10").onclick = async () => {
  if (!SEL) return;
  const model = curModel();
  if (!model) { toast(t("pool_empty"), true); return; }
  const tv = parseFloat($("#scrubT").value);
  busy(true, t("busy_clip"));
  $("#busyBar").classList.remove("hidden");
  $("#busyCancel").classList.remove("hidden"); $("#busyCancel").textContent = t("cancel");
  const poll = setInterval(async () => {
    try {
      const p = await api("/api/probe_clip_progress");
      if (!p.phase) return;
      let txt = p.phase;
      if (p.total && p.phase === "нейромережа") {
        const left = p.fps > 0 ? (p.total - p.done) / p.fps : 0;
        txt += ` · ${p.done}/${p.total} ${t("clip_frames")} · ${p.fps} ${t("j_fps")}` +
               (left > 0 ? ` · ${t("j_left")}${fmtSec(left)}` : "");
        $("#busyFill").style.width = (100 * p.done / p.total).toFixed(1) + "%";
      }
      $("#busyText").textContent = txt;
    } catch (e) { /* сервер зайнятий — нічого */ }
  }, 700);
  try {
    const j = await api("/api/probe_clip", { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: SEL.id, t: tv, target: TARGET, model, ops: opsNow() }) });
    if (j.error) { toast(j.error, !j.canceled); return; }
    openCompareClip(j);
  } catch (e) { toast("проба кліпу не вдалась: " + e.message, true); }
  finally { clearInterval(poll); busy(false); }
};
$("#busyCancel").onclick = async () => {
  $("#busyText").textContent = t("busy_cancel");
  try { await api("/api/probe_clip_cancel", { method: "POST" }); } catch (e) { /* ок */ }
};

/* ── порівняння ── */
let dragLine = false;
let CMP = { before: "", after: "", clip: false };   // поточні URL (А/Б у 1:1 підміняє src)
function stopVideos() {
  for (const id of ["#cmpAfterV", "#cmpBeforeV"]) {
    const v = $(id); v.pause(); v.removeAttribute("src"); v.load();
  }
}
function openCompare(j) {
  stopVideos();
  $("#compare").classList.remove("hidden");
  $("#cmpStage").classList.remove("isclip");
  $("#btnPlay").classList.add("hidden"); $("#btn11").classList.remove("hidden");
  $("#cmpClock").classList.add("hidden");
  CMP = { before: j.before + "?r=" + Date.now(), after: j.after + "?r=" + Date.now(), clip: false };
  $("#cmpBefore").src = CMP.before;
  $("#cmpAfter").src = CMP.after;
  $("#cmpMode").textContent = `${j.mode} · ${j.w}×${j.h} · ${(j.ms/1000).toFixed(1)} с`;
  $("#cmpStage").classList.remove("mode11");
  setLine(0.5);
}
/* два синхронні плеєри: «після» веде, «до» підтягується, обидва по колу */
function openCompareClip(j) {
  stopVideos();
  $("#compare").classList.remove("hidden");
  const st = $("#cmpStage");
  st.classList.remove("mode11"); st.classList.add("isclip");
  $("#btn11").classList.add("hidden");        // 1:1 для відео — Етап 4
  $("#btnPlay").classList.remove("hidden"); $("#btnPlay").textContent = t("cmp_pause");
  CMP = { before: j.before + "?r=" + Date.now(), after: j.after + "?r=" + Date.now(), clip: true };
  const a = $("#cmpAfterV"), b = $("#cmpBeforeV");
  a.src = CMP.after; b.src = CMP.before;
  $("#cmpMode").textContent = `${j.mode} · ${j.w}×${j.h} · ${j.secs} ${t("u_sec")} @ ${fmtDur(j.t)} · ` +
    `${j.frames} ${t("clip_frames")}` + (j.engine_fps ? ` · ${j.engine_fps} ${t("j_fps")}` : "") +
    ` · ${(j.ms/1000).toFixed(0)} ${t("u_sec")}`;
  setLine(0.5);
  // 28.08: у власника у WebView2 кліп стояв «статикою», хоча в Edge грає. Тому плеєр
  // тепер сам себе діагностує: якщо за 2 с після play() час не пішов — кажемо ЧОМУ
  // (readyState/код помилки) і пробуємо ще раз; є видимий лічильник часу.
  // 🚨 28.08 (відтворено у справжньому WebView2): `currentTime = 0` перед play() запускає
  // сік, сік знову кидає canplay, обробник знову ставить 0 — 9 кіл, відео вічно на 0.00
  // («статика»), а повторний play() ловить AbortError. Тому: чекаємо готовності ОДИН раз
  // (once), НІЧОГО не сікаємо перед стартом, вирівнюємо «до» один раз уже під час гри.
  let started = false, attempts = 0;
  const waitReady = v => new Promise(res => {
    if (v.readyState >= 3) return res();
    v.addEventListener("canplay", () => res(), { once: true });
    setTimeout(res, 6000);
  });
  // Упертий старт: AbortError у WebView2 траплявся і на правильному коді (вікно після
  // важких рендерів, VRAM під зав'язку) — тоді перезавантажуємо джерела і пробуємо ще,
  // а в тості кажемо ПОВНИЙ текст причини, щоб було з чим працювати.
  const tryPlay = () => Promise.all([a.play(), b.play()])
    .then(() => { started = true;
      setTimeout(() => { if (Math.abs(b.currentTime - a.currentTime) > 0.15) b.currentTime = a.currentTime; }, 800); })
    .catch(e => {
      attempts++;
      const why = (e && (e.name + ": " + (e.message || ""))) || String(e);
      if (attempts <= 2) {
        toast(`плеєр не пішов (${why.slice(0, 90)}) — спроба ${attempts + 1}…`, true);
        a.src = CMP.after; b.src = CMP.before; a.load(); b.load();
        return Promise.all([waitReady(a), waitReady(b)]).then(() => new Promise(r => setTimeout(r, 400))).then(tryPlay);
      }
      toast(`плеєр не запустився: ${why.slice(0, 120)} · visibility=${document.visibilityState} — закрий і відкрий програму`, true);
    });
  Promise.all([waitReady(a), waitReady(b)]).then(tryPlay);
  setTimeout(() => {
    if ($("#compare").classList.contains("hidden") || !CMP.clip || attempts > 0) return;
    if (a.currentTime < 0.3) {
      toast(`плеєр стоїть (ready ${a.readyState}/${b.readyState}, помилка `
        + `${a.error ? a.error.code : "нема"}/${b.error ? b.error.code : "нема"}, `
        + `paused ${a.paused}) — пробую ще раз`, true);
      tryPlay();
    }
  }, 3500);
  // мʼяка синхронізація: «до» підтягуємо лише при розбіжності >150 мс і не частіше
  // раз на секунду — кожен сік коштує декодування від ключового кадру
  let lastSync = 0;
  a.ontimeupdate = () => {
    $("#cmpClock").textContent = `${a.currentTime.toFixed(1)} / ${j.secs} ${t("u_sec")}`;
    const now = performance.now();
    if (now - lastSync < 1000) return;
    if (Math.abs(b.currentTime - a.currentTime) > 0.15) { b.currentTime = a.currentTime; lastSync = now; }
  };
  $("#cmpClock").textContent = `0.0 / ${j.secs} ${t("u_sec")}`;
  $("#cmpClock").classList.remove("hidden");
}
$("#btnPlay").onclick = () => {
  const a = $("#cmpAfterV"), b = $("#cmpBeforeV");
  if (a.paused) { b.currentTime = a.currentTime;
                  Promise.all([a.play(), b.play()]).catch(e => toast("▶: " + (e && e.name || e), true));
                  $("#btnPlay").textContent = t("cmp_pause"); }
  else { a.pause(); b.pause(); b.currentTime = a.currentTime;
         $("#btnPlay").textContent = t("cmp_play"); }
};
function setLine(frac) {
  frac = Math.max(0, Math.min(1, frac));
  const st = $("#cmpStage");
  $("#cmpLine").style.left = (frac * 100) + "%";
  $("#cmpBeforeWrap").style.clipPath = `inset(0 ${(1 - frac) * 100}% 0 0)`;
  st.dataset.frac = frac;
}
$("#cmpStage").addEventListener("pointerdown", e => { dragLine = true; moveLine(e); });
window.addEventListener("pointermove", e => { if (dragLine) moveLine(e); });
window.addEventListener("pointerup", () => dragLine = false);
function moveLine(e) {
  const r = $("#cmpStage").getBoundingClientRect();
  setLine((e.clientX - r.left) / r.width);
}
/* A/B: тримаєш — бачиш ДО. У режимі 1:1 шторки нема — підміняємо src єдиної картинки */
function holdB(on) {
  if ($("#cmpStage").classList.contains("mode11")) {
    $("#cmpAfter").src = on ? CMP.before : CMP.after;
    return;
  }
  $("#cmpBeforeWrap").style.clipPath = on ? "inset(0 0 0 0)"
    : `inset(0 ${(1 - ($("#cmpStage").dataset.frac || .5)) * 100}% 0 0)`;
}
$("#btnHold").addEventListener("pointerdown", () => holdB(true));
$("#btnHold").addEventListener("pointerup", () => holdB(false));
$("#btnHold").addEventListener("pointerleave", () => holdB(false));
$("#btnHold").addEventListener("pointercancel", () => holdB(false));
window.addEventListener("blur", () => { holdB(false); dragLine = false; });
window.addEventListener("keydown", e => {
  if ($("#compare").classList.contains("hidden")) return;
  if (e.code === "Space") { e.preventDefault(); holdB(true); }
  if (e.code === "Escape") closeCompare();
});
function closeCompare() { $("#compare").classList.add("hidden"); stopVideos(); }
window.addEventListener("keyup", e => { if (e.code === "Space") holdB(false); });
$("#btn11").onclick = () => {
  const st = $("#cmpStage");
  st.classList.toggle("mode11");
  if (st.classList.contains("mode11")) {
    $("#cmpAfter").src = CMP.after;       // 1:1 = одна картинка натурального розміру
    st.scrollTo((st.scrollWidth - st.clientWidth) / 2,
                (st.scrollHeight - st.clientHeight) / 2);
  } else {
    $("#cmpAfter").src = CMP.after;
    setLine(0.5);
  }
};
$("#btnCmpClose").onclick = closeCompare;

/* ── здоровʼя ── */
let toolsWarned = false;
async function health() {
  try {
    const h = await api("/api/health");
    // бейдж = диск РЕЗУЛЬТАТІВ (власник обирає теку); tmp-диск — у підказці, якщо інший
    $("#diskbadge").textContent = `${h.out_drive}: ${h.free_gb} ${t("u_gb")} ${t("free")}`;
    $("#diskbadge").title = h.tmp_drive !== h.out_drive
      ? `tmp ${h.tmp_drive}: ${h.tmp_free_gb} ${t("u_gb")} ${t("free")}` : "";
    $("#gpubadge").classList.toggle("hidden", !h.gpu_busy_other);
    if (h.tools_missing.length && !toolsWarned) {
      toolsWarned = true;                  // одне попередження, а не тост кожні 30 с
      toast(h.tools_missing[0], true);
    }
  } catch (e) { /* сервер перезапускається */ }
}
/* ── Етап 4: операції «ЯК ще» + налаштування ── */
/* ── Етап 6 п.4: ПУЛ МОДЕЛЕЙ ──────────────────────────────────────────────────
   Меню «ЯК» і підписи в черзі більше не зашиті трьома списками в HTML/JS — усе
   будується з /api/pool (<дані>\models\pool.json). Підпис перекладаємо, поки
   власник не переписав його СВОЇМИ словами (тоді показуємо його текст як є). */
let POOL = [];
const i18nHas = k => !!(k && ((I18N[LANG] && I18N[LANG][k]) || I18N.uk[k]));
const poolTitle = m => (!(m.custom || []).includes("title") && i18nHas(m.i18n_title))
  ? t(m.i18n_title) : m.title;
const poolDesc = m => (!(m.custom || []).includes("desc") && i18nHas(m.i18n_desc))
  ? t(m.i18n_desc) : m.desc;
const grpName = g => ({ top: t("grp_top"), bal: t("grp_bal"), fast: t("grp_fast"),
                        extra: t("g_extra") }[g] || g);
const modelLabel = n => {
  if (n === "fast") return t("m_fast");
  const m = POOL.find(x => x.name === n);
  return m ? poolTitle(m) : n;
};
/* меню може лишитись порожнім (власник вимкнув усе) — тоді жодного :checked нема,
   і прямий .value кинув би TypeError на пробі/черзі */
const curModel = () => {
  const r = document.querySelector('input[name=model]:checked');
  return r ? r.value : null;
};

async function loadPool() {
  try { POOL = (await api("/api/pool")).pool || []; } catch (e) { return; }
  renderModelMenu();
  renderPool();
}

const chipCls = c => (c >= 10 ? "slow" : c >= 2 ? "mid" : "fast");
// «×1» = мультяшна; швидші за неї показуємо дробом (×0.5), інакше округлюємо
const chipTxt = c => (c >= 10 ? Math.round(c) : String(c).replace(/\.0$/, ""));
// Дві прості цифри замість «⭐ ×1.5 гірше / ⏱ ×17 довше» (власник 08.09: «замудрено, зірка не
// зрозуміла»): «якість 93 %» = схожість з оригіналом на його кадрах (ЛИШЕ виміряна, app/quality.py;
// нема заміру — нема чіпа), «⏱ ≈ 23 год» = час на 10 хв відео 1080p→4K. Колір — місце серед заміряних.
function qchip(m, small) {
  if (!m.q_pct) return "";
  const third = Math.max(1, Math.ceil((m.q_total || 1) / 3));
  const cls = m.q_rank <= third ? "fast" : m.q_rank > m.q_total - third ? "slow" : "mid";
  const title = `${t("q_pct_hint")} · №${m.q_rank} ${t("q_of")} ${m.q_total} · LPIPS ${m.q_lpips} · ${m.q_n} ${t("q_frames")}`;
  return `<span class="${small ? "pbadge" : "mchip " + cls}" title="${esc(title)}">${esc(t("q_pct_lbl"))} ${m.q_pct} %</span>`;
}
function tchip(m, small) {
  if (!m.h10) return "";
  const h = m.h10, cls = h <= 2 ? "fast" : h <= 8 ? "mid" : "slow";
  const txt = h >= 1 ? `${h >= 10 ? Math.round(h) : h.toFixed(1)} ${t("u_hour")}` : `${Math.round(h * 60)} ${t("u_min")}`;
  return `<span class="${small ? "pbadge" : "mchip " + cls}" title="${esc(t("chip_time_hint") + " · " + (m.measured ? "заміряно" : "оцінка"))}">⏱ ≈ ${txt}</span>`;
}
// у меню «ЯК» цифри — одним дрібним рядком під назвою (власник 08.09: «меню завелике, пустота» —
// два чіпи стовпчиком робили кожен рядок утричі вищим); кольорові слова замість рамок
function mstats(m) {
  const p = [];
  if (m.q_pct) {
    const third = Math.max(1, Math.ceil((m.q_total || 1) / 3));
    const cls = m.q_rank <= third ? "fast" : m.q_rank > m.q_total - third ? "slow" : "mid";
    p.push(`<span class="mst ${cls}" title="${esc(`${t("q_pct_hint")} · №${m.q_rank} ${t("q_of")} ${m.q_total}`)}">${esc(t("q_pct_lbl"))} ${m.q_pct} %</span>`);
  }
  if (m.h10) {
    const h = m.h10, cls = h <= 2 ? "fast" : h <= 8 ? "mid" : "slow";
    const txt = h >= 1 ? `${h >= 10 ? Math.round(h) : h.toFixed(1)} ${t("u_hour")}` : `${Math.round(h * 60)} ${t("u_min")}`;
    p.push(`<span class="mst ${cls}" title="${esc(t("chip_time_hint") + " · " + (m.measured ? "заміряно" : "оцінка"))}">⏱ ${txt}</span>`);
  }
  return p.length ? `<span class="mstats">${p.join('<span class="dim"> · </span>')}</span>` : "";
}
const mrow = m => `<label class="mrow"><input type="radio" name="model" value="${esc(m.name)}">` +
  `<span class="mtext"><span class="mname">${esc(poolTitle(m))}</span>` +
  `<span class="mdesc">${esc(poolDesc(m))}</span>${mstats(m)}</span></label>`;

function renderModelMenu() {
  const box = $("#models");
  if (!box) return;
  const shown = POOL.filter(m => m.enabled && m.present);
  let html = "";
  for (const g of ["top", "bal", "fast"]) {
    const rows = shown.filter(m => m.group === g);
    if (!rows.length) continue;
    html += `<div class="mgroup">${esc(grpName(g))}` +
      (g === "top" ? ` <span class="dim">${esc(t("grp_top_sub"))}</span>` : "") + `</div>` +
      rows.map(mrow).join("");
  }
  const extra = shown.filter(m => m.group === "extra");
  if (extra.length) html += `<details id="strongModels"><summary class="dim">` +
    `${esc(t("more_models"))}</summary>${extra.map(mrow).join("")}</details>`;
  // легенди нема (власник: «пустота») — пояснення живуть у підказках цифр і в 🛠 → Якість моделей
  box.innerHTML = html || `<div class="dim" style="padding:8px 2px">${esc(t("pool_empty"))}</div>`;
  const radios = [...box.querySelectorAll('input[name=model]')];
  const pick = radios.find(r => r.value === (SETTINGS && SETTINGS.model)) || radios[0];
  if (pick) pick.checked = true;
}

function renderPool() {
  const box = $("#poolList");
  if (!box) return;
  const inGrp = m => POOL.filter(x => x.group === m.group);
  box.innerHTML = POOL.map(m => {
    const sib = inGrp(m), i = sib.indexOf(m);
    const badges = [];
    if (!m.present) badges.push(`<span class="pbadge miss">${esc(t("p_missing"))}</span>`);
    if (m.base) badges.push(`<span class="pbadge">${esc(t("p_base"))}</span>`);
    if (m.q_pct) badges.push(qchip(m, true));
    if (m.h10) badges.push(tchip(m, true));
    if (m.size_mb) badges.push(`<span class="pbadge">${m.size_mb} ${esc(t("u_mb"))}</span>`);
    return `<div class="poolrow${m.enabled ? "" : " off"}" data-name="${esc(m.name)}">` +
      `<label class="switch"><input type="checkbox" class="pEn"${m.enabled ? " checked" : ""}` +
      `${m.present ? "" : " disabled"}><span class="knob"></span></label>` +
      `<span class="ptext"><span class="pname">${esc(poolTitle(m))}</span>` +
      `<span class="pmono mono dim">${esc(m.name)}</span></span>` +
      `<span class="pbadges">${badges.join("")}</span>` +
      `<select class="pGrp">${["top", "bal", "fast", "extra"].map(g =>
        `<option value="${g}"${m.group === g ? " selected" : ""}>${esc(grpName(g))}</option>`).join("")}</select>` +
      `<button class="btn ghost pUp" title="${esc(t("p_up"))}"${i === 0 ? " disabled" : ""}>↑</button>` +
      `<button class="btn ghost pDn" title="${esc(t("p_down"))}"${i === sib.length - 1 ? " disabled" : ""}>↓</button>` +
      `<button class="btn ghost pDel" title="${esc(t("p_del"))}"` +
      `${(m.base || !m.present) ? " disabled" : ""}>🗑</button></div>`;
  }).join("");
  $("#poolSize").textContent =
    POOL.reduce((s, m) => s + (m.size_mb || 0), 0).toFixed(1) + " " + t("u_mb");
}

async function savePool(items, note) {
  try {
    POOL = (await api("/api/pool", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ items }) })).pool;
    renderModelMenu(); renderPool();
    if (note) toast(note);
  } catch (e) { toast(e.message, true); }
}

/* делеговано: рядки пулу перемальовуються цілком після кожної зміни */
$("#poolList").addEventListener("change", e => {
  const row = e.target.closest(".poolrow");
  if (!row) return;
  const name = row.dataset.name;
  if (e.target.classList.contains("pEn"))
    savePool([{ name, enabled: e.target.checked }]);
  else if (e.target.classList.contains("pGrp"))
    savePool([{ name, group: e.target.value }]);
});
$("#poolList").addEventListener("click", async e => {
  const btn = e.target.closest("button");
  const row = e.target.closest(".poolrow");
  if (!btn || !row || btn.disabled) return;
  const name = row.dataset.name;
  const me = POOL.find(m => m.name === name);
  if (!me) return;
  if (btn.classList.contains("pDel")) {
    if (!await askConfirm(`${t("p_del")}: ${poolTitle(me)} (${me.size_mb} ${t("u_mb")})?`)) return;
    try {
      const r = await api("/api/pool/delete", { method: "POST",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) });
      POOL = r.pool; renderModelMenu(); renderPool();
      toast(`${t("t_pool_deleted")} · ${t("t_freed")} ${r.freed_mb} ${t("u_mb")}`);
    } catch (err) { toast(err.message, true); }
    return;
  }
  // ↑/↓ міняються місцями з сусідом У СВОЇЙ групі (група перемикається окремим списком)
  const sib = POOL.filter(m => m.group === me.group);
  const i = sib.indexOf(me);
  const j = btn.classList.contains("pUp") ? i - 1 : i + 1;
  if (j < 0 || j >= sib.length) return;
  savePool([{ name: me.name, order: sib[j].order }, { name: sib[j].name, order: me.order }]);
});
/* ── Етап 6 п.1-3: вкладка 🧭 МОДЕЛІ — розвідник ───────────────────────────────
   Каталог OpenModelDB (671 модель) тягне і класифікує `app/scout.py`; сам себе
   перевіряє раз на 4 дні. Тут — тільки показ, фільтри і кнопка «поставити». */
const SC_PAGE = 60;
// seg: усі | usable (одним кліком) | new; installing: {key, text} поки йде скачування
let SCOUT = { items: [], total: 0, offset: 0, state: {}, open: null, seg: "usable", installing: null };

const scFilters = () => ({
  q: ($("#search") && $("#search").value || "").trim(),
  only_usable: SCOUT.seg === "usable" ? 1 : 0,
  only_new: SCOUT.seg === "new" ? 1 : 0,
  only_installed: SCOUT.seg === "installed" ? 1 : 0,
  scale: $("#scScale").value, purpose: $("#scPurpose").value, sort: $("#scSort").value,
  lang: LANG,                                   // сервер перекладає описи видимої сторінки наперед
});

async function scLoad(more) {
  const f = scFilters();
  const off = more ? SCOUT.offset + SC_PAGE : 0;
  const qs = new URLSearchParams({ ...f, limit: SC_PAGE, offset: off }).toString();
  let j;
  try { j = await api("/api/scout?" + qs); } catch (e) { toast(e.message, true); return; }
  SCOUT.items = more ? SCOUT.items.concat(j.items) : j.items;
  SCOUT.total = j.total; SCOUT.offset = off; SCOUT.state = j.state;
  SCOUT.days = j.check_every_days; SCOUT.newNote = j.new_note;
  // скачування, що почалось до перезапуску вікна, підхоплюємо і показуємо прогрес далі
  const inst = (j.state || {}).install;
  if (inst && inst.running && !SCOUT.installing) {
    SCOUT.installing = { key: inst.key, text: scProgText(inst) };
    scWatchInstall();
  }
  scRender();
}

// прогрес скачування живе в колонці «доступність» (лінійка + % + МБ + МБ/с), а в діях — лише ✕:
// власник 08.09: «лінійка і МБ/с маленькі і йдуть під бейдж „можна скачати“»
const scDlHtml = () => `<div class="scdl"><div class="scdlbar"><i style="width:${(SCOUT.installing || {}).pct || 0}%"></i></div>` +
  `<span class="scdltxt mono">${esc((SCOUT.installing || {}).text || t("sc_installing"))}</span></div>`;
function scProgText(s) {
  const mb = b => (b / 1e6).toFixed(1);
  const sp = s.speed ? ` · ${s.speed.toFixed(1)} ${t("u_mb")}/${t("u_sec")}` : "";
  return (s.total ? `${s.pct}% · ${mb(s.done)}/${mb(s.total)} ${t("u_mb")}` : `${mb(s.done)} ${t("u_mb")}`) + sp;
}
async function scWatchInstall() {
  // прогрес скачування раз на 0.6 с; коли закінчилось — пул і меню «ЯК» оновлюються
  for (;;) {
    await new Promise(r => setTimeout(r, 600));
    let s;
    try { s = await api("/api/scout/install_state"); } catch (e) { continue; }
    if (s.running) {
      const prev = SCOUT.installing || {}, now = Date.now();
      // швидкість — за останні ~2 с (EMA), щоб цифра не стрибала
      let speed = prev.speed || 0;
      if (prev.t && s.done > (prev.done || 0)) {
        const inst = (s.done - prev.done) / 1e6 / Math.max(0.2, (now - prev.t) / 1000);
        speed = speed ? speed * 0.6 + inst * 0.4 : inst;
      }
      s.speed = speed;
      SCOUT.installing = { key: s.key, text: scProgText(s), pct: s.pct, done: s.done, t: now, speed };
      const sel = `.sccard[data-key="${CSS.escape(s.key)}"]`;
      document.querySelectorAll(`${sel} .scdltxt, #sfBadges .scdltxt`).forEach(el => el.textContent = SCOUT.installing.text);
      document.querySelectorAll(`${sel} .scdlbar i, #sfBadges .scdlbar i`).forEach(el => el.style.width = s.pct + "%");
      continue;
    }
    SCOUT.installing = null;
    const it = SCOUT.items.find(x => x.key === s.key);
    if (s.error) toast(s.error, !s.canceled);
    else if (s.result) {
      POOL = s.result.pool; renderModelMenu(); renderPool();
      if (it) it.installed = true;
      if (SF.m && SF.m.key === s.key) SF.m.installed = true;
      // власник 08.09: «встановили — де побачити, куди з'являється?» → кажемо прямо і
      // розгортаємо групу «📦 Ще» в меню «ЯК», куди модель і лягла
      const grp = $("#strongModels"); if (grp) grp.open = true;
      toast(`${t("sc_done_where")}: ${(it || {}).name || s.key} · ${s.result.size_mb} ${t("u_mb")}` +
            (s.result.sha_checked ? ` · ${t("sc_sha_ok")}` : ""));
    }
    scRender(); sfRenderActs();
    return;
  }
}

function scStateLine() {
  const s = SCOUT.state || {};
  if (s.running) return `⏳ ${esc(s.phase || t("sc_working"))}…`;
  if (!s.count) return t("sc_never");
  const ago = s.last_check ? fmtAgo(s.last_check) : "?";
  const left = s.next_check ? fmtAgo(s.next_check, true) : "";
  return `${s.count} ${t("sc_models")} · ${t("sc_checked")} ${ago}` +
    (left ? ` · ${t("sc_next")} ${left}` : "") +
    (s.new_count ? ` · 🆕 ${s.new_count}` : "") +
    (SCOUT.seg === "new" && SCOUT.newNote ? ` · ${t("sc_new_note").replace("{n}", SCOUT.newNote.fresh_30d)
      .replace("{k}", SCOUT.newNote.shown).replace("{d}", SCOUT.newNote.newest || "?")}` : "") +
    (s.engine2 ? "" : ` · ⚠ ${t("sc_no_engine2")}`);
}
function fmtAgo(ts, future) {
  const d = Math.abs((future ? ts * 1000 - Date.now() : Date.now() - ts * 1000)) / 1000;
  if (!future && d < 60) return t("sc_justnow");            // «перевірено 0 хв» читалось дивно
  if (d < 3600) return Math.round(d / 60) + " " + t("u_min");
  if (d < 86400) return Math.round(d / 3600) + " " + t("u_hour");
  return Math.round(d / 86400) + " " + t("u_day");
}

// векторні іконки замість ⓘ 🔗 🗑 ⬇ ✅ (власник 08.09: «пікселять зарази» — емодзі/гліфи на 12 px
// WebView2 малює нечітко; SVG у currentColor гострий на будь-якому масштабі)
const ICO = {
  info: '<svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="8" cy="8" r="6.3"/><path d="M8 7.2v4M8 4.9v.3"/></svg>',
  link: '<svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M6.6 9.4l2.8-2.8M7.1 4.6l1-1a2.6 2.6 0 013.7 3.7l-1 1M8.9 11.4l-1 1a2.6 2.6 0 01-3.7-3.7l1-1"/></svg>',
  trash: '<svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M3 4.5h10M6.4 4.5V3h3.2v1.5M4.4 4.5l.6 8.5h6l.6-8.5M6.8 7v4M9.2 7v4"/></svg>',
  x: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><path d="M4 4l8 8M12 4l-8 8"/></svg>',
  dl: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2.5v8M4.8 7.3L8 10.5l3.2-3.2M3 13h10"/></svg>',
  check: '<svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8.5l3.2 3L13 4.5"/></svg>',
};
// i18n-тексти починаються з емодзі (⬇ / 🔗 / ✅ / ✕) — знімаємо його і ставимо SVG
const withIco = (txt, key) => `${ICO[key]} ${esc(String(txt).replace(/^[⬇\u{1F517}✅✕✖❌]️?\s*/u, ""))}`;
const scUsable = m => (m.avail === "direct" || m.avail === "mirror") &&
                      ["pth", "safetensors"].includes(m.type);
const scAvailHtml = m => m.installed ? `<span class="scb ok">${withIco(t("sc_installed"), "check")}</span>`
  : scUsable(m) ? `<span class="scb ok">${withIco(m.avail === "mirror" ? t("sc_mirror") : t("sc_direct"), "dl")}</span>`
  : m.type && !["pth", "safetensors"].includes(m.type)
    ? `<span class="scb warn">${esc(t("sc_badformat"))} ${esc(m.type)}</span>`
    : `<span class="scb warn">${withIco(t("sc_manual"), "link")}</span>`;
function scSpeedTxt(m) {
  const hrs = +m.hours_10min || 0;
  return hrs >= 1 ? `${hrs.toFixed(1)} ${t("u_hour")}` : `${Math.round(hrs * 60)} ${t("u_min")}`;
}
// кнопки дії — однакові в рядку списку і в повноекранній картці
const scActsHtml = (m, withInfo = true) =>
  (withInfo ? `<button class="btn ghost ico scInfo" title="${esc(t("sc_info"))}">${ICO.info}</button>` : "") +
  `<button class="btn ghost ico scPage" title="${esc(t("sc_page"))}">${ICO.link}</button>` +
  (SCOUT.installing && SCOUT.installing.key === m.key
    ? `<button class="btn ghost ico scCancel" title="${esc(t("sc_cancel"))}">${ICO.x}</button>`
    : m.installed ? `<button class="btn ghost ico scDel" title="${esc(t("sc_del"))}">${ICO.trash}</button>`   // власник: «може сюди кнопку видалити»
    : scUsable(m) ? `<button class="btn primary scGet">${withIco(t("sc_install"), "dl")}</button>` : "");
const scAvailCell = m => (SCOUT.installing && SCOUT.installing.key === m.key) ? scDlHtml() : scAvailHtml(m);

function scCard(m) {
  const usable = scUsable(m), av = scAvailHtml(m), speed = scSpeedTxt(m);
  // рядок списку (власник 08.09: картки «стрем какой»): архітектура — коротким кодом, людське
  // пояснення у підказці; цифра одна — час на 10 хв відео, решта дрібним і тихим.
  // Подвійний клік по рядку → повноекранна картка (scOpenFull).
  return `<div class="sccard${m.new ? " isnew" : ""}${m.installed ? " inst" : ""}" data-key="${esc(m.key)}" title="${esc(t("sc_dbl_hint"))}">
    <div class="scrowm">
      <div class="scc scc-name"><span class="scname">${esc(m.name)}${m.new ? `<span class="scb new">🆕</span>` : ""}</span>
        <span class="scmeta mono dim">${esc(m.author || "?")}${m.date ? " · " + esc(m.date) : ""}${
          m.size_mb ? " · " + m.size_mb + " " + t("u_mb") : ""}${
          m.license ? " · " + esc(m.license) : ""}</span></div>
      <div class="scc scc-arch" title="${esc(m.arch_human || (m.src ? t("sc_hf_src") + " " + m.src.slice(3) : ""))}">${m.arch ? `<span class="sctier t${m.tier || 2}" title="${
        esc(m.tier_human || "")}">${"▮".repeat(m.tier || 2)}${"▯".repeat(3 - (m.tier || 2))}</span>${esc(m.arch.toUpperCase())}` : `<span class="dim">HF</span>`}${
        m.scale ? `<span class="scb" title="${esc(t("sc_scale_hint"))}">${m.scale}x</span>` : ""}</div>
      <div class="scc scc-purpose" title="${esc((m.purpose || []).join(" · "))}">${(m.purpose || []).map(p => esc(p)).join(" · ")}</div>
      <div class="scc scc-speed mono">${+m.sec_per_frame ? `<b>≈ ${speed}</b><span class="dim">${(+m.sec_per_frame).toFixed(2)} ${
        t("u_sec")}/${t("sc_frame")} · ${esc(t("sc_estimate"))}</span>` : `<span class="dim">?</span>`}</div>
      <div class="scc scc-avail">${scAvailCell(m)}</div>
      <div class="scc scacts">${scActsHtml(m)}</div>
    </div>
  </div>`;
}
const scHead = () => `<div class="sclhead"><div>${esc(t("sc_h_model"))}</div><div>${esc(t("sc_h_arch"))}</div>` +
  `<div>${esc(t("sc_h_purpose"))}</div><div style="text-align:right">${esc(t("sc_h_speed"))}</div>` +
  `<div>${esc(t("sc_h_avail"))}</div><div></div></div>`;

function scRender() {
  const st = SCOUT.state || {};
  $("#scState").textContent = scStateLine();
  // порожньо буває з двох причин: каталогу ще нема АБО фільтри нічого не пропустили
  // («лише нові» при 0 нових) — і тексти в цих випадках різні; data-i18n оновлюємо теж,
  // щоб перемикання мови не повернуло старий напис
  const key = st.count ? "sc_nomatch" : "sc_empty", sp = $("#scoutEmpty span");
  sp.dataset.i18n = key; sp.textContent = t(key);
  $("#scoutEmpty").classList.toggle("hidden", SCOUT.items.length > 0 || st.running);
  $("#scoutList").innerHTML = (SCOUT.items.length ? scHead() : "") + SCOUT.items.map(scCard).join("");
  $("#scoutMore").classList.toggle("hidden", SCOUT.items.length >= SCOUT.total);
  const b = $("#sbadge"), n = (SCOUT.state || {}).new_count || 0;
  b.textContent = n || ""; b.classList.toggle("hidden", !n);
}

async function scOpenPage(m) {
  try { await api("/api/open_url", { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url: m.page }) }); }
  catch (err) { toast(err.message, true); }
}
async function scInstall(key, btn) {
  // скачування йде у фоні на сервері (власник 08.09: «немає кнопки скасувати»):
  // кнопка стає прогресом + ✕, а scWatchInstall доводить до пулу або до скасування
  btn.disabled = true; btn.textContent = t("sc_installing");
  try {
    await api("/api/scout/install", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ key }) });
    SCOUT.installing = { key, text: t("sc_installing") };
    scRender(); sfRenderActs();
    scWatchInstall();
  } catch (err) { toast(err.message, true); btn.disabled = false; btn.innerHTML = withIco(t("sc_install"), "dl"); }
}
async function scCancelInstall(btn) {
  btn.disabled = true;
  try { await api("/api/scout/install_cancel", { method: "POST" }); }
  catch (err) { toast(err.message, true); btn.disabled = false; }
}
async function scDelete(m, btn) {
  // те саме, що 🗑 у 🛠 → МОДЕЛІ: файл гине, запис із пулу теж, меню «ЯК» перебудовується
  if (!await askConfirm(`${t("sc_del_q")}: ${m.name} (${m.size_mb || "?"} ${t("u_mb")})?`)) return;
  btn.disabled = true;
  try {
    const r = await api("/api/pool/delete", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: m.key }) });
    POOL = r.pool; renderModelMenu(); renderPool();
    m.installed = false;
    if (SF.m && SF.m.key === m.key) SF.m.installed = false;
    toast(`${t("t_pool_deleted")} · ${t("t_freed")} ${r.freed_mb} ${t("u_mb")}`);
    scRender(); sfRenderActs();
  } catch (err) { toast(err.message, true); btn.disabled = false; }
}
function scDispatch(btn, m) {
  if (btn.classList.contains("scPage")) scOpenPage(m);
  else if (btn.classList.contains("scInfo")) scOpenFull(m.key);
  else if (btn.classList.contains("scGet")) scInstall(m.key, btn);
  else if (btn.classList.contains("scCancel")) scCancelInstall(btn);
  else if (btn.classList.contains("scDel")) scDelete(m, btn);
}
$("#scoutList").addEventListener("click", e => {
  const btn = e.target.closest("button"); if (!btn) return;
  const card = e.target.closest(".sccard"); if (!card) return;
  const m = SCOUT.items.find(x => x.key === card.dataset.key);
  if (m) scDispatch(btn, m);
});
// власник 08.09: «подвійний клік на панельку відкриває її на весь екран з подробним описом»
$("#scoutList").addEventListener("dblclick", e => {
  if (e.target.closest("button, a")) return;
  const card = e.target.closest(".sccard");
  if (card) scOpenFull(card.dataset.key);
});

/* ── повноекранна картка моделі ── */
let SF = { key: null, m: null, full: null, desc: null, showOrig: false };
const sfBadgesHtml = m => (m.new ? `<span class="scb new">🆕</span>` : "") +
  (m.scale ? `<span class="scb" title="${esc(t("sc_scale_hint"))}">${m.scale}x</span>` : "") + scAvailCell(m);
function sfRenderActs() {
  if (!SF.m) return;
  $("#sfActs").innerHTML = scActsHtml(SF.m, false);
  $("#sfBadges").innerHTML = sfBadgesHtml(SF.m);
}
function sfMetaHtml(m, d) {
  const rows = [[t("sc_m_author"), m.author], [t("sc_m_date"), m.date],
    [t("sc_m_size"), m.size_mb ? `${m.size_mb} ${t("u_mb")}` : ""], [t("sc_m_license"), m.license],
    [t("sc_h_arch"), (m.arch_human || m.arch || "") + (m.scale ? ` · ×${m.scale}` : "")],
    [t("sc_h_purpose"), (m.purpose || []).join(" · ")],
    [t("sc_h_speed"), `≈ ${scSpeedTxt(m)} · ${(+m.sec_per_frame || 0).toFixed(2)} ${t("u_sec")}/${t("sc_frame")} ${t("sc_estimate")}`],
    [t("sc_m_src"), d && d.url ? d.url : ""]];
  return rows.filter(r => r[1]).map(r =>
    `<div class="dim">${esc(r[0])}</div><div class="mono">${esc(String(r[1]))}</div>`).join("");
}
// описи OpenModelDB — легкий markdown (**жирний**, _курсив_, [текст](url), ## заголовки);
// спершу екрануємо, потім підміняємо розмітку — сирий HTML з мережі у сторінку не потрапляє
function mdLite(s) {
  let h = esc(s || "");
  h = h.replace(/^#{1,6}\s+(.+)$/gm, "<h4>$1</h4>");
  h = h.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_, txt, url) => `<a href="#" data-url="${url}">${txt}</a>`);
  h = h.replace(/\*\*([^*\n]+)\*\*/g, "<b>$1</b>");
  h = h.replace(/(^|[\s(])_([^_\n]+)_(?=[\s).,;:!?]|$)/g, "$1<i>$2</i>");
  h = h.replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s).,;:!?]|$)/g, "$1<i>$2</i>");
  return h;
}
$("#sfDesc").addEventListener("click", e => {
  const a = e.target.closest("a[data-url]"); if (!a) return;
  e.preventDefault(); scOpenPage({ page: a.dataset.url });   // сервер пускає лише відомі хости
});
function sfRenderDesc() {
  const r = SF.desc, d = SF.full || {};
  if (!r || r.source === "original") {
    $("#sfDesc").innerHTML = mdLite(d.desc || "");
    $("#sfNote").textContent = r && r.note ? `${t("sc_original")} · ${r.note}` : "";
    return;
  }
  $("#sfDesc").innerHTML = mdLite(SF.showOrig ? (d.desc || "") : r.text);
  $("#sfNote").innerHTML = `${esc(t("sc_translated"))} · <a href="#" id="sfToggleOrig">${
    esc(SF.showOrig ? t("sc_show_translation") : t("sc_original"))}</a>`;
  $("#sfToggleOrig").onclick = e => { e.preventDefault(); SF.showOrig = !SF.showOrig; sfRenderDesc(); };
}
async function scOpenFull(key) {
  const m = SCOUT.items.find(x => x.key === key); if (!m) return;
  SF = { key, m, full: null, desc: null, showOrig: false };
  $("#sfName").textContent = m.name;
  sfRenderActs();                                   // бейджі + кнопки
  $("#sfDesc").textContent = t("sc_loading"); $("#sfImgs").innerHTML = "";
  $("#sfNote").textContent = ""; $("#sfTags").innerHTML = ""; $("#sfMeta").innerHTML = sfMetaHtml(m, null);
  $("#sfBody").classList.add("noimg");
  $("#scFull").classList.remove("hidden"); $("#scFull").scrollTop = 0;
  try {
    const d = await api("/api/scout/model/" + encodeURIComponent(key));
    if (SF.key !== key) return;
    SF.full = d;
    const imgs = (d.images || []).map(i => i.SR || i.url).filter(Boolean).slice(0, 4);
    $("#sfBody").classList.toggle("noimg", !imgs.length);      // без картинок опис на всю ширину
    $("#sfImgs").innerHTML = imgs.map(u => `<img loading="lazy" src="${esc(u)}" alt="">`).join("");
    $("#sfTags").innerHTML = (d.tags || []).slice(0, 12).map(x => `<span class="scb">${esc(x)}</span>`).join("");
    $("#sfMeta").innerHTML = sfMetaHtml(m, d);
    $("#sfDesc").innerHTML = mdLite(d.desc || "");
    if (LANG !== "en" && (d.desc || "").trim()) {
      $("#sfNote").textContent = t("sc_translating");          // перший раз 5-20 с (Ollama), далі з кешу
      const r = await api(`/api/scout/desc/${encodeURIComponent(key)}?lang=${LANG}`);
      if (SF.key !== key) return;
      SF.desc = r; sfRenderDesc();
    } else $("#sfNote").textContent = "";
  } catch (err) { if (SF.key === key) $("#sfNote").textContent = err.message; }
}
function scCloseFull() { SF = { key: null, m: null }; $("#scFull").classList.add("hidden"); }
$("#sfClose").onclick = scCloseFull;
document.addEventListener("keydown", e => {
  if (e.key === "Escape" && !$("#scFull").classList.contains("hidden")) scCloseFull();
});
$("#sfActs").addEventListener("click", e => {
  const btn = e.target.closest("button");
  if (btn && SF.m) scDispatch(btn, SF.m);
});
$("#scRefresh").onclick = async () => {
  try {
    await api("/api/scout/refresh", { method: "POST" });
    SCOUT.state = { ...SCOUT.state, running: true, phase: t("sc_working") };
    $("#scState").textContent = scStateLine();
    // перевірка триває секунди — тихо перепитуємо, поки не закінчиться
    const iv = setInterval(async () => {
      await scLoad(false);
      if (!(SCOUT.state || {}).running) clearInterval(iv);
    }, 2500);
  } catch (e) { toast(e.message, true); }
};
$("#scAvailSeg").addEventListener("click", e => {
  const b = e.target.closest(".scsegbtn"); if (!b || b.dataset.v === SCOUT.seg) return;
  SCOUT.seg = b.dataset.v;
  document.querySelectorAll("#scAvailSeg .scsegbtn").forEach(x => x.classList.toggle("active", x === b));
  scLoad(false);
});
["#scScale", "#scPurpose", "#scSort"].forEach(s => $(s).addEventListener("change", () => scLoad(false)));
$("#scMore").onclick = () => scLoad(true);
let scSearchTimer = null;                      // верхній пошук фільтрує і каталог теж
$("#search").addEventListener("input", () => {
  if (!$("#tab-scout").classList.contains("active")) return;
  clearTimeout(scSearchTimer);
  scSearchTimer = setTimeout(() => scLoad(false), 350);
});

/* 📏 проба якості (LPIPS на кадрах власника): кнопка в 🛠 + рядок стану; фон міряє сам */
let qualTimer = null;
async function loadQuality(poll) {
  let q;
  try { q = await api("/api/quality"); } catch (e) { return; }
  const el = $("#qualState"); if (!el) return;
  const n = Object.keys(q.models || {}).length;
  // імена файлів — лише в підказці: у рядку вони розпирали налаштування ширше за вікно (08.09)
  const nSrc = new Set((q.sources || []).map(s => s.name)).size, nFr = (q.sources || []).length;
  let line = q.running ? `⏳ ${t("q_running")}: ${q.model} · ${q.phase}` :
    q.queue.length ? `⏳ ${t("q_queued")}: ${q.queue.length}` : n ? `✅ ${n} ${t("q_measured")}` : t("q_none");
  if (q.target) line += ` · ${q.target / 2}p→${q.target === 2160 ? "4K" : q.target + "p"} · ${nSrc} ${t("q_videos")}, ${nFr} ${t("q_frames_short")}`;
  if (q.last_error) line += ` · ⚠ ${q.last_error}`;
  el.textContent = line;
  el.title = (q.sources || []).map(s => `${s.name} @ ${s.t} ${t("u_sec")}`).join("\n");
  if (poll) {
    clearTimeout(qualTimer);
    if (q.running || q.queue.length) qualTimer = setTimeout(() => loadQuality(true), 4000);
    else await loadPool();                               // чіпи ⭐ у меню «ЯК» і в пулі
  }
}
$("#stQuality").onclick = async () => {
  try {
    const r = await api("/api/quality/run", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ force: false }) });
    toast(r.queued.length ? `${t("q_started")}: ${r.queued.length}` : t("q_all_done"));
    loadQuality(true);
  } catch (e) { toast(e.message, true); }
};
$("#stQualityAll").onclick = async () => {
  if (!await askConfirm(t("q_force_q"))) return;
  try {
    const r = await api("/api/quality/run", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ force: true }) });
    toast(`${t("q_started")}: ${r.queued.length}`); loadQuality(true);
  } catch (e) { toast(e.message, true); }
};
$("#stPoolReset").onclick = async () => {
  try {
    POOL = (await api("/api/pool/reset", { method: "POST" })).pool;
    renderModelMenu(); renderPool(); toast(t("t_pool_reset"));
  } catch (e) { toast(e.message, true); }
};
let SETTINGS = null;
function opsNow() {
  return { sharpen: parseFloat($("#opSharpen").value) || 0, grain: $("#opGrain").checked,
           denoise: $("#opDenoise").checked,
           codec: (document.querySelector('input[name=codec]:checked') || {}).value || "libx264" };
}
$("#opSharpen").addEventListener("input", () => $("#opSharpenV").textContent = $("#opSharpen").value);
document.querySelectorAll('input[name=codec]').forEach(r => r.addEventListener("change", () => {
  $("#codecNote").textContent = r.value === "hevc_nvenc" ? t("codec_f_note") : t("codec_q_note");
}));
async function loadSettings() {
  try { SETTINGS = await api("/api/settings"); } catch (e) { return; }
  applyLang(SETTINGS.lang || "uk");
  // меню «ЯК» будується з пулу (Етап 6 п.4) — і вже там ставить дефолтну модель
  await loadPool();
  loadQuality(true);
  // бейдж «нові моделі» має світитись одразу, не чекаючи заходу на вкладку 🧭
  api("/api/scout?limit=1").then(j => { SCOUT.state = j.state; scRender(); }).catch(() => {});
  $("#opSharpen").value = SETTINGS.sharpen; $("#opSharpenV").textContent = SETTINGS.sharpen;
  $("#opGrain").checked = !!SETTINGS.grain; $("#opDenoise").checked = !!SETTINGS.denoise;
  document.querySelectorAll('input[name=codec]').forEach(r => r.checked = r.value === SETTINGS.codec);
  $("#codecNote").textContent = SETTINGS.codec === "hevc_nvenc" ? t("codec_f_note") : t("codec_q_note");
  if (["fhd", "2k", "4k"].includes(SETTINGS.target)) TARGET = SETTINGS.target;
  // вкладка налаштувань (модель/ціль/кодек живуть збоку і запам'ятовуються самі)
  $("#stLang").value = SETTINGS.lang || "uk";
  $("#stOutDir").value = SETTINGS.out_dir || ""; $("#stOutDir").placeholder = SETTINGS.out_dir_effective;
  $("#doneDir").textContent = SETTINGS.out_dir_effective;
  $("#stTmp").textContent = `${SETTINGS.tmp_gb} ${t("u_gb")}`;
  $("#stAbout").textContent = `${SETTINGS.out_dir_effective} · :8391 · realesrgan-ncnn-vulkan (-g 0)`;
  renderLib(); renderJobs(); health();
}
$("#stLang").addEventListener("change", () => {                                // міняється одразу
  applyLang($("#stLang").value); renderLib(); renderJobs(); health();
  renderModelMenu(); renderPool();          // підписи моделей і груп теж перекладаються
  loadQuality(false); if (SCOUT.items.length) scRender(); sfRenderActs();   // статус якості, каталог, повна картка
  if (SEL) { const cur = SEL; select(cur); }
});
$("#stSave").onclick = async () => {
  const values = { lang: $("#stLang").value, out_dir: $("#stOutDir").value.trim() };
  try {
    const s = await api("/api/settings", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ values }) });
    toast(t("t_saved")); if (s.warn) toast(s.warn, true);
    await loadSettings();
  } catch (e) { toast(e.message, true); }
};
/* вибір збоку (модель, ціль, кодек, додатково) запам'ятовується САМ — без кнопки «зберегти» */
let persistTimer = null;
function persistPanel() {
  clearTimeout(persistTimer);
  persistTimer = setTimeout(() => {
    const m = document.querySelector('input[name=model]:checked');
    const values = { model: m ? m.value : undefined, target: TARGET, ...opsNow() };
    api("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ values }) }).then(s => { if (SETTINGS) Object.assign(SETTINGS, values); })
      .catch(() => {});
  }, 400);
}
document.addEventListener("change", e => {
  if (["model", "codec"].includes(e.target.name) || ["opSharpen", "opGrain", "opDenoise"].includes(e.target.id))
    persistPanel();
});
$("#stPickOut").onclick = async () => {
  if (!window.pywebview) { toast(t("t_dialog_only"), true); return; }
  const d = await window.pywebview.api.pick_folder();
  if (d) $("#stOutDir").value = d;
};
$("#stOpenOut").onclick = async () => {
  const p = ($("#stOutDir").value.trim() || (SETTINGS && SETTINGS.out_dir_effective) || "") + "\\.";
  try { await api("/api/open_folder", { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path: p }) }); }
  catch (e) { toast(e.message, true); }
};
$("#stLogs").onclick = async () => {
  try { await api("/api/open_folder", { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path: SETTINGS.logs_dir + "\\." }) }); }
  catch (e) { toast(e.message, true); }
};
$("#stCleanup").onclick = async () => {
  try { const r = await api("/api/cleanup_tmp", { method: "POST" });
    toast(`${t("t_freed")} ${r.freed_gb} ${t("u_gb")}`); await loadSettings(); }
  catch (e) { toast(e.message, true); }
};
loadSettings();

/* ── власний заголовок вікна (лише всередині pywebview) ── */
function nativeReady() {
  document.body.classList.add("native");
  $("#tbMin").onclick = () => window.pywebview.api.win_min();
  $("#tbMax").onclick = () => window.pywebview.api.win_max();
  $("#tbClose").onclick = () => window.pywebview.api.win_close();
  document.querySelector(".tb-drag").ondblclick = () => window.pywebview.api.win_max();
  initEdgeResize();
}
/* розтягування безрамкового вікна за краї — зі сторінки (pywebview маршалить move/resize
   у UI-потік сам; нативні хаки WinForms вішали вікно — див. desktop.py) */
function initEdgeResize() {
  const B = 7;
  let drag = null;
  const edgeAt = (x, y) => {
    const W = window.innerWidth, H = window.innerHeight;
    const l = x < B, r = x > W - B, t = y < B, b = y > H - B;
    if (t && l) return "nw"; if (t && r) return "ne"; if (b && l) return "sw"; if (b && r) return "se";
    if (l) return "w"; if (r) return "e"; if (t) return "n"; if (b) return "s";
    return "";
  };
  const cursors = { n: "ns-resize", s: "ns-resize", e: "ew-resize", w: "ew-resize",
                    nw: "nwse-resize", se: "nwse-resize", ne: "nesw-resize", sw: "nesw-resize" };
  // 08.09 (власник: «не працює розтягування»): краї — окремі невидимі ручки поверх усього
  // (z-index 100, свій курсор). Раніше край визначався по координатах, а курсор ставився на body —
  // будь-який елемент зі своїм cursor під краєм ховав підказку, і здавалось, що край мертвий.
  const handles = {};
  for (const ed of Object.keys({ n: 1, s: 1, e: 1, w: 1, nw: 1, ne: 1, sw: 1, se: 1 })) {
    const h = document.createElement("div");
    h.className = "winedge winedge-" + ed; h.dataset.edge = ed;
    document.body.appendChild(h); handles[ed] = h;
  }
  for (const [ed, h] of Object.entries(handles)) h.style.cursor = cursors[ed];
  window.__edgeLog = [];
  const dbg = m => { window.__edgeLog.push(m); if (window.__edgeLog.length > 50) window.__edgeLog.shift(); };
  let armed = false;
  // drag-зона заголовка (pywebview слухає mousedown) не має перехоплювати верхній край
  document.addEventListener("mousedown", e => { if (armed) e.stopImmediatePropagation(); }, true);
  // натискання біля краю → тягнемо зі сторінки через Win32-геометрію (власник 28.08
  // підтвердив: «збільшення, зменшення, розтягнення працює»). Нативний варіант через
  // WM_NCLBUTTONDOWN (Api.win_size_drag) лишено в коді, але не використовується.
  document.addEventListener("pointerdown", async e => {
    // край — це ручка під курсором (надійно), а координати — запасний варіант
    const hd = e.target && e.target.closest ? e.target.closest(".winedge") : null;
    const edge = hd ? hd.dataset.edge : edgeAt(e.clientX, e.clientY);
    if (!edge || e.button !== 0) return;
    armed = true; setTimeout(() => armed = false, 300);
    e.preventDefault(); e.stopPropagation();
    dbg(`down ${edge} @${e.clientX},${e.clientY}`);
    try { document.body.setPointerCapture(e.pointerId); } catch (err) { dbg("capture: " + err.name); }
    try {
      const g = await window.pywebview.api.win_geom();
      drag = { edge, sx: e.screenX, sy: e.screenY, g, pending: null, busy: false };
    } catch (err) { dbg("win_geom: " + err); }
  }, true);
  const flush = () => {
    if (!drag || drag.busy || !drag.pending) return;
    const p = drag.pending; drag.pending = null; drag.busy = true;
    window.pywebview.api.win_set(p.x, p.y, p.w, p.h)
      .catch(err => dbg("win_set: " + err))
      .finally(() => { if (drag) { drag.busy = false; flush(); } });
  };
  document.addEventListener("pointermove", e => {
    if (!drag) return;
    const k = window.devicePixelRatio || 1;          // Win32-геометрія фізична, screenX — CSS
    const dx = Math.round((e.screenX - drag.sx) * k), dy = Math.round((e.screenY - drag.sy) * k);
    const g = drag.g, ed = drag.edge, minW = Math.round(1040 * k), minH = Math.round(680 * k);
    let x = g.x, y = g.y, w = g.w, h = g.h;
    if (ed.includes("e")) w = g.w + dx;
    if (ed.includes("s")) h = g.h + dy;
    if (ed.includes("w")) { w = Math.max(minW, g.w - dx); x = g.x + (g.w - w); }
    if (ed.includes("n")) { h = Math.max(minH, g.h - dy); y = g.y + (g.h - h); }
    drag.pending = { x, y, w: Math.max(minW, w), h: Math.max(minH, h) };
    flush();
  });
  const end = () => { drag = null; document.body.style.cursor = ""; };
  document.addEventListener("pointerup", end);
  document.addEventListener("pointercancel", end);
}
if (window.pywebview) nativeReady();
else window.addEventListener("pywebviewready", nativeReady);

refresh();
health();
setInterval(health, 30000);
