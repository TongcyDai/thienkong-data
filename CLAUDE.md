# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Hakka language dictionary data processing project that converts the "Taiwan Siyen/Hoiliuk Hakka Dictionary" from HTML format into structured JSON data with multiple pronunciation systems. The project processes two Hakka dialects: Siyen (四縣腔) and Hoiliuk (海陸腔).

## Key Commands

### Data Processing Pipeline

The complete workflow for processing dictionary data:

```bash
# Step 1: Convert PUA (Private Use Area) characters to standard Unicode
python pua_translator.py
# Edit the script to set input/output files (siyen_raw.html -> siyen_new.html)

# Step 2: Parse HTML to JSON
python hakka_parser.py <HTML_FILE> [OUTPUT_JSON]
# Example: python hakka_parser.py siyen_new.html siyen.json

# Step 3: Add pronunciation variants (numbered, marked, PFS)
python hakka_pronunciation_converter.py <DIALECT> <INPUT_JSON> <OUTPUT_JSON>
# Example: python hakka_pronunciation_converter.py siyen siyen.json siyen_pr.json
# Example: python hakka_pronunciation_converter.py hoiliuk hoiliuk.json hoiliuk_pr.json
```

## Architecture

### Data Flow

```
Raw HTML (_raw.html)
  ↓ [pua_translator.py]
Cleaned HTML (_new.html)
  ↓ [hakka_parser.py]
Base JSON (.json)
  ↓ [hakka_pronunciation_converter.py]
Enhanced JSON (_pr.json)
```

### Core Components

**1. pua_translator.py**
- Converts Private Use Area (U+E000-U+F8FF) characters to standard Unicode
- Maps custom font characters (numbered circles, special CJK characters) to standard equivalents
- Provides statistics on PUA character usage before/after conversion

**2. hakka_parser.py**
- Main HTML parser using BeautifulSoup
- Extracts dictionary entries from HTML format
- Handles multiple entry types:
  - `headword`: Pronunciation + list of characters sharing that pronunciation
  - `character`: Individual character with classical notes, definitions, examples
  - `word`: Multi-character compound words with definitions
- Preserves diacritical marks using Unicode combining characters (U+0331 for underline)
- Text normalization: removes spaces between CJK characters, preserves spaces between Latin characters

**3. hakka_pronunciation_converter.py**
- Converts original pronunciation to three formats:
  - `numbered`: Tone number system (e.g., "pa5")
  - `marked`: Tone mark system (e.g., "paˇ")
  - `pfs`: Pha̍k-fa-sṳ (white-letter romanization, Siyen only)
- Handles dialect-specific tone systems (6 tones for Siyen, 7 for Hoiliuk)
- Converts checked tone finals: p→b, t→d, k→g
- Siyen-specific: z/c/s → j/q/x before i-initial rhymes (not ii)

### Data Structure

JSON entries follow this schema:

```json
{
  "total": <count>,
  "entries": [
    {
      "id": "entry_XXXXXX",
      "type": "headword" | "character" | "word",
      "pronunciation": {
        "original": "<diacritical marks>",
        "numbered": "<tone numbers>",
        "marked": "<tone symbols>",
        "pfs": "<white-letter romanization>"  // Siyen only
      },
      // Type-specific fields:
      // headword: "characters": [...], "create_character_entries": true
      // character: "character": "X", "classical_notes": "...", "definitions": [...]
      // word: "headword": "...", "definitions": [...], "source": "...", "variants": [...]
    }
  ]
}
```

### Key Parsing Patterns

**Entry Type Detection:**
- Headword: Large font (14pt/size=4) + italic bold Times New Roman + CJK characters in bold
- Character: Bold single CJK character + small font parenthetical notes (8pt/size=1)
- Word: Latin pronunciation + CJK characters + definition (with/without `=` separator)
- Definition paragraph: Indented (margin-left/text-indent) or starts with circled numbers ①②③

**Text Processing:**
- Underline preservation: `<u>o</u>` → `o\u0331` (combining underline)
- Space normalization: Keep spaces between Latin letters, remove between CJK
- Definition markers: ①-⑲, ❶-❿ for numbered definitions
- Example markers: 📌, ⚫ for example sentences
- Inline notes: Preserved in parentheses within text

**Tone System:**
- Siyen: 6 tones (1=ˊ, 2=ˋ, 3=none, 4=ˋ, 5=ˇ, 8=none)
- Hoiliuk: 7 tones (1=ˋ, 2=ˊ, 3=ˇ, 4=none, 5=none, 7=+, 8=ˋ)
- Tone detection based on Unicode combining diacritics (U+0301 acute, U+0300 grave, U+0304 macron, U+0331 macron below, U+0323 dot below)

## File Naming Convention

- `*_raw.html`: Original HTML files from source
- `*_new.html`: HTML files after PUA character conversion
- `*.json`: Basic parsed JSON (original pronunciation only)
- `*_pr.json`: Enhanced JSON with all pronunciation variants
- `test.*`: Sample files for development/testing

## Dependencies

Required Python packages (install with `pip install`):
- `beautifulsoup4`: HTML parsing
- `unicodedata`: Unicode normalization (built-in)
- `pathlib`: File handling (built-in)

## Development Notes

- Python 3.11+ recommended
- All text processing uses UTF-8 encoding
- NFD normalization used for diacritic extraction, NFC for output
- The parser tracks `current_pronunciation` context to associate characters with their headword pronunciation
- Character entries can be created from headwords (basic placeholders) then enhanced by dedicated character entry paragraphs
