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

## Tech Stack

- Python 3.10+
- PySide6 / Qt für die Desktop-UI
- PyMuPDF für PDF-Verarbeitung
- i18n via Qt Linguist

## Lizenz

GPL-3.0-or-later, siehe [LICENSE](LICENSE).

## Contributing

Hinweise für Beiträge finden sich in [CONTRIBUTING.md](CONTRIBUTING.md).
