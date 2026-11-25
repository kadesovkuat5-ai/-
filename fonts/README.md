# Fonts with full Kazakh Cyrillic

Every font here was checked to contain all Kazakh letters: Ә Ғ Қ Ң Ө Ұ Ү Һ І (upper and lower case).
All are variable fonts (any weight) from Google Fonts under the SIL Open Font License (see `OFL-*.txt`).

| File | Use for |
|---|---|
| `Montserrat.ttf` | bold headlines, Reels titles |
| `Oswald.ttf` | narrow tall kinetic type, big words |
| `Inter.ttf` | captions, body text, UI |
| `Rubik.ttf` | soft rounded headlines |
| `NotoSerif.ttf` | documentary / historical cards |

Checked and NOT suitable (Kazakh letters missing): Unbounded, Manrope.

HyperFrames: copy the file into the project's `assets/fonts/` and declare it:
```css
@font-face { font-family: "Montserrat"; src: url("assets/fonts/Montserrat.ttf"); font-weight: 100 900; }
```
