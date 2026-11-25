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

def convert_japanese_line(line):
    """Converts a Japanese lyric line into various formats. returns a dictionary with the original line and its romanized version."""
    # Parse once with fugashi to get accurate Katakana & Hiragana
    tokens = katsu_hepburn.tagger(line)
    kana = "".join(token.feature.kana or token.surface for token in tokens)
    hira = jaconv.kata2hira(kana)

    # Pre-compute Hepburn once since both 'hepburn' and 'passport' can use it
    hepburn = katsu_hepburn.romaji(line).lower()

    results = {
        "orig": line,
        "kana": kana,
        "hira": hira,
        "hepburn": hepburn,
        "passport": hepburn,
        "kunrei": katsu_kunrei.romaji(line).lower(),
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