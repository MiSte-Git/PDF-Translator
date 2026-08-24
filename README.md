# PDF-Translator

Ein Tool zum Übersetzen von PDF-Dokumenten, das Layout und Formatierung des
Originals so weit wie möglich erhält. Ein separates Modul zur Übersetzung von
Text in Bildern (z. B. gescannte Seiten) ist geplant.

🚧 In aktiver Entwicklung – noch nicht production-ready.

## Features

**Stand jetzt**

- PDF-Extraktion und -Rekonstruktion auf Basis von PyMuPDF
- Grundgerüst für Übersetzungs-Provider (DeepL, Google, OpenAI)
- Grundgerüst für eine Desktop-UI

**Geplant**

- Layout-treues Reflow übersetzter Textblöcke
- OCR und Inpainting für Bildinhalte
- Separates Modul zur Übersetzung von Text in Bildern
- Mehrsprachige UI (i18n via Qt Linguist)

## Systemvoraussetzungen

- Python 3.10+
- Entwickelt und getestet unter Linux (Debian). PySide6/Qt ist grundsätzlich
  auch unter Windows und macOS lauffähig, das ist hier aber nicht der primäre
  Testfall.
- Für die optionale OCR-Funktionalität zusätzlich das Tesseract-Binary über
  den System-Paketmanager (z. B. `apt install tesseract-ocr` unter
  Debian/Ubuntu, `brew install tesseract` unter macOS) – siehe
  [requirements-ocr.txt](requirements-ocr.txt).
- Alternativ zwei weitere wählbare OCR-Engines (Phase 3, 23.08.2026), beide
  mit paragraphenweiser statt zeilenweiser Texterkennung – hilfreich bei
  dicht gepackten Layouts (siehe Backlog.md):
  - **Google Cloud Vision** (Cloud) – braucht einen Google-API-Key mit
    aktivierter Vision API (derselbe Key wie für den Google-Übersetzer
    kann wiederverwendet werden, wenn beide APIs im selben Google-Cloud-
    Projekt aktiviert sind).
  - **PaddleOCR** (lokal, kein Cloud-Zugang nötig) – siehe
    [requirements-paddleocr.txt](requirements-paddleocr.txt). Lädt beim
    ersten Lauf automatisch Modelle herunter (normaler Internetzugang
    nötig). Falls beim Erkennen ein `NotImplementedError` rund um
    "ConvertPirAttribute2RuntimeAttribute" auftritt: bekannte Regression
    in PaddlePaddle 3.3.x, siehe requirements-paddleocr.txt.
- Für optionales GPU-Inpainting (LaMa, Phase 3) zusätzlich eine
  CUDA-fähige GPU – siehe [requirements-gpu.txt](requirements-gpu.txt).

## Installation für Entwickler

```bash
git clone https://github.com/MiSte-Git/TranslatePDF.git
cd TranslatePDF
pip install -r requirements.txt
```

Für optionale OCR-Funktionalität zusätzlich:

```bash
pip install -r requirements-ocr.txt
```

Für die optionale PaddleOCR-Engine (siehe oben) zusätzlich:

```bash
pip install -r requirements-paddleocr.txt
```

## Start

```bash
python -m ui.app
```

Startet die Desktop-UI (PySide6). Details zur Bedienung stehen in
[ui/README.md](ui/README.md).

## Tech Stack

- Python 3.10+
- PySide6 / Qt für die Desktop-UI
- PyMuPDF für PDF-Verarbeitung
- i18n via Qt Linguist

## Lizenz

GPL-3.0-or-later, siehe [LICENSE](LICENSE).

## Contributing

Hinweise für Beiträge finden sich in [CONTRIBUTING.md](CONTRIBUTING.md).
