# Проверка и экспорт

Полный порядок ревью — `hyperframes/references/review.md`; команды — скилл `/hyperframes-cli`.

## Проверка (каждый раз перед сдачей)
```bash
npx hyperframes check --json            # контракт: исправить все ошибки
npx hyperframes snapshot --review       # контактные листы: сцены, стыки, кадры на 360 px
npx hyperframes snapshot --range 0,0.5 --frames 6        # первые 0,5 с
npx hyperframes snapshot --range <конец-0.5>,<конец> --frames 6   # последние 0,5 с
```
Смотреть: читается ли каждая надпись за своё время, нет ли обрезки у краёв и под интерфейсом Reels (верх ~220 px, низ ~380 px), казахские знаки не подменились, нет артефактов на стыках.

## Рендер и проверка файла
```bash
npx hyperframes render --output out/<name>.mp4
npx hyperframes audio out/<name>.mp4 --json             # звук: есть, акценты, громкость
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,pix_fmt,sample_rate -of compact out/<name>.mp4
```
Ожидается: `h264`, `yuv420p`, 30/1 fps (или 60), `aac` 48000 Гц, нужный размер.

Если рендер дал другое — перекодируй:
```bash
ffmpeg -i in.mp4 -c:v libx264 -pix_fmt yuv420p -r 30 -crf 18 -preset slow -c:a aac -ar 48000 -b:a 192k -movflags +faststart out.mp4
```

## Сдача
- MP4 + папка проекта HyperFrames рядом (исходники для правок).
- Коротко: что проверено, что нет (например, «звук не прослушан, проверены только уровни»).
- HTML-превью — не готовое видео; MP4 — не редактируемый проект.
