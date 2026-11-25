import yaml
from types import SimpleNamespace

import cutlet
import jaconv
from korean_romanizer import Romanizer

# Initialize Cutlet converters once at startup
katsu_hepburn = cutlet.Cutlet("hepburn")
katsu_hepburn.use_foreign_spelling = False

katsu_kunrei = cutlet.Cutlet("kunrei")
katsu_kunrei.use_foreign_spelling = False

# global constants for lyric formats
VALID_LYRIC_FORMATS = {"orig", "kana", "hira", "hepburn", "kunrei", "passport", "none"}
KOREAN_LYRIC_FORMATS = {"orig", "romanized", "none"}
LYRIC_LANGUAGE_FORMATS = {
    "ja": VALID_LYRIC_FORMATS,
    "ko": KOREAN_LYRIC_FORMATS,
}
LYRIC_CONVERTERS = {}

# override readings for individual tokens
JAPANESE_READING_OVERRIDES = {
    ("私", "ワタクシ"): "ワタシ",
}

# replace known names and phrases with their readings before tokenization
JAPANESE_PHRASE_OVERRIDES = {
    "鏡音": "カガミネ",
    "･･･": "...",
}

# load settings
with open("settings.yaml", "r", encoding="utf-8") as f:
    yaml_settings = yaml.safe_load(f)

settings = SimpleNamespace(**{
    f"{language}_{line_number}_format": yaml_settings[f"{language}_{line_number}_format"]
    for language in LYRIC_LANGUAGE_FORMATS
    for line_number in ("line1", "line2")
})

def contains_hangul(text):
    """check if text contains any Hangul characters (Korean script)"""
    return any(
        "\uac00" <= char <= "\ud7a3"
        or "\u1100" <= char <= "\u11ff"
        or "\u3130" <= char <= "\u318f"
        for char in text
    )

def contains_japanese(text):
    """check if text contains any Japanese characters (Hiragana, Katakana, Kanji)"""
    return any(
        "\u3040" <= char <= "\u309f"      # Hiragana
        or "\u30a0" <= char <= "\u30ff"   # Katakana
        or "\u4e00" <= char <= "\u9faf"   # Kanji (CJK Unified Ideographs)
        or "\u3400" <= char <= "\u4dbf"   # Kanji Extension A (rare/older kanji)
        or "\uff66" <= char <= "\uff9f"   # Half-width Katakana
        for char in text
    )


def _japanese_kana(token):
    reading = token.feature.kana or token.surface
    return JAPANESE_READING_OVERRIDES.get((token.surface, reading), reading)


def _apply_japanese_phrase_overrides(line):
    replacements = {}
    for index, (phrase, reading) in enumerate(
        sorted(JAPANESE_PHRASE_OVERRIDES.items(), key=lambda item: len(item[0]), reverse=True)
    ):
        marker = f"QZXOVERRIDEQZX{'Q' * index}"
        while marker in line or marker in replacements:
            marker += "Q"
        line = line.replace(phrase, marker)
        replacements[marker] = reading
    return line, replacements

def _romanize_metadata(text):
    language = detect_lyric_language(text, None)
    if language == "ja":
        return convert_lyric_line(text, language)["hepburn"]
    if language == "ko":
        return convert_lyric_line(text, language)["romanized"]
    return None

def _romanize_japanese_line(line, converter):
    line, phrase_overrides = _apply_japanese_phrase_overrides(line)
    tokens = converter.tagger(line)
    romanized_tokens = converter.romaji_tokens(tokens, capitalize=False)

    for token, romanized_token in zip(tokens, romanized_tokens):
        if token.surface in phrase_overrides:
            romanized_token.surface = "".join(
                converter.romaji(phrase_overrides[token.surface], capitalize=False).lower().split()
            )
            continue

        reading = _japanese_kana(token)
        if reading != (token.feature.kana or token.surface):
            romanized_token.surface = converter.romaji(reading, capitalize=False).lower()

    return "".join(str(token) for token in romanized_tokens).strip().lower()


def convert_japanese_line(line):
    """Converts a Japanese lyric line into various formats. returns a dictionary with the original line and its romanized version."""
    # Parse once with fugashi to get accurate Katakana & Hiragana
    line_with_markers, phrase_overrides = _apply_japanese_phrase_overrides(line)
    tokens = katsu_hepburn.tagger(line_with_markers)
    kana = "".join(
        phrase_overrides.get(token.surface, _japanese_kana(token))
        for token in tokens
    )
    hira = jaconv.kata2hira(kana)

    hepburn = _romanize_japanese_line(line, katsu_hepburn)
    kunrei = _romanize_japanese_line(line, katsu_kunrei)

    results = {
        "orig": line,
        "kana": kana,
        "hira": hira,
        "hepburn": hepburn,
        "passport": hepburn,
        "kunrei": kunrei,
        "none": "",
    }

    return {
        format_name: results.get(format_name, line)
        for format_name in VALID_LYRIC_FORMATS
    }

def convert_korean_line(line):
    """Converts a Korean lyric line into various formats. returns a dictionary with the original line and its romanized version."""
    romanized = Romanizer(line).romanize()
    return {"orig": line, "romanized": romanized, "none": ""}

LYRIC_CONVERTERS.update({
    "ja": convert_japanese_line,
    "ko": convert_korean_line,
})

def detect_lyric_language(line, track_language):
    """ Detects the language of a lyric line based on its content and the track's language metadata.
    Returns 'ko' for Korean, 'ja' for Japanese, or the track's language code if it is supported.
    """
    if contains_hangul(line):
        return "ko"
    if contains_japanese(line):
        return "ja"
    if track_language in LYRIC_CONVERTERS:
        return track_language
    return None


def convert_lyric_line(line, language):
    """Converts a lyric line into various formats based on the detected language."""
    converter = LYRIC_CONVERTERS.get(language)
    if converter is None:
        return {"orig": line, "none": ""}
    return converter(line)

def get_formatted_lines(raw_line, lyrics_lang, settings):
    """Converts a raw lyric string into a (line1, line2) tuple based on settings."""
    if not raw_line:
        return ("", "")
        
    lang = detect_lyric_language(raw_line, lyrics_lang)
    formats = convert_lyric_line(raw_line, lang)
    
    if lang is None:
        return (formats["orig"], "")
        
    line1 = formats[getattr(settings, f"{lang}_line1_format")]
    line2 = formats[getattr(settings, f"{lang}_line2_format")]
    return (line1, line2)