import json # used for reading/writing json files
import os
from types import SimpleNamespace

import yaml # used for file path manipulation and checking if files exist
from lib.lyriq import get_lyrics, Lyrics # used to fetch lyrics from the lrclib and parse them into a Lyrics object
import requests # used to make HTTP requests to the navidrome api to get the current track and lyrics
from langdetect import detect
from korean_romanizer import Romanizer
import pykakasi # used to convert Japanese lyrics into romaji/kana/hiragana
kks = pykakasi.kakasi()


## global variables
WEB_STATE_PATH = os.path.join(os.path.dirname(__file__), "web_state.json") # stores the current state for the web ui
WEB_SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "web_settings.json") # stores the current settings from the web ui
VALID_LYRIC_FORMATS = {"orig", "kana", "hira", "hepburn", "kunrei", "passport", "none"}
KOREAN_LYRIC_FORMATS = {"orig", "romanized", "none"}
# default web state, will be updated by the publish_web_state function
web_state = {
    "status": "waiting",
    "title": "",
    "artist": "",
    "current_line": "",
    "lyrics": "",
}

# Load per-language settings.
with open("settings.yaml", "r", encoding="utf-8") as f:
    yaml_settings = yaml.safe_load(f)

LYRIC_LANGUAGE_FORMATS = {
    "ja": VALID_LYRIC_FORMATS,
    "ko": KOREAN_LYRIC_FORMATS,
}

LYRIC_CONVERTERS = {}

settings = SimpleNamespace(**{
    f"{language}_{line_number}_format": yaml_settings[f"{language}_{line_number}_format"]
    for language in LYRIC_LANGUAGE_FORMATS
    for line_number in ("line1", "line2")
})

def publish_web_state(**updates):
    if not any(web_state.get(key) != value for key, value in updates.items()):
        return

    web_state.update(updates)
    temporary_path = f"{WEB_STATE_PATH}.tmp"
    with open(temporary_path, "w", encoding="utf-8") as state_file:
        json.dump(web_state, state_file, ensure_ascii=False)
    os.replace(temporary_path, WEB_STATE_PATH)


def refresh_web_settings():
    if not os.path.isfile(WEB_SETTINGS_PATH):
        return

    with open(WEB_SETTINGS_PATH, "r", encoding="utf-8") as settings_file:
        saved_settings = json.load(settings_file)

    format_groups = {
        f"{language}_{line_number}_format": valid_formats
        for language, valid_formats in LYRIC_LANGUAGE_FORMATS.items()
        for line_number in ("line1", "line2")
    }
    for key, valid_formats in format_groups.items():
        if key not in saved_settings:
            continue
        value = saved_settings[key]
        if not isinstance(value, str) or value not in valid_formats:
            raise ValueError(f"Invalid {key} in web settings")
        setattr(settings, key, value)


def contains_hangul(text):
    return any(
        "\uac00" <= char <= "\ud7a3"
        or "\u1100" <= char <= "\u11ff"
        or "\u3130" <= char <= "\u318f"
        for char in text
    )


def convert_japanese_line(line):
    converted = kks.convert(line)
    return {
        format_name: (
            "" if format_name == "none"
            else " ".join(item[format_name] for item in converted)
        )
        for format_name in VALID_LYRIC_FORMATS
    }


def convert_korean_line(line):
    romanized = Romanizer(line).romanize()
    return {"orig": line, "romanized": romanized, "none": ""}


LYRIC_CONVERTERS.update({
    "ja": convert_japanese_line,
    "ko": convert_korean_line,
})


def detect_lyric_language(line, track_language):
    if contains_hangul(line):
        return "ko"
    if track_language in LYRIC_CONVERTERS:
        return track_language
    return None


def convert_lyric_line(line, language):
    converter = LYRIC_CONVERTERS.get(language)
    if converter is None:
        return {"orig": line, "none": ""}
    return converter(line)

def setSongInfo(nowPlaying):
    if not nowPlaying:
        return None, None, 0, "empty"
        
    track = nowPlaying[0]
    track_id = track.get("id")
    position_ms = track.get("positionMs", 0)
    listenState = track.get("state", "stopped")

    return track, track_id, position_ms, listenState

def introduceSong(track, track_id, display, url, params):
    current_track_id = track_id # update the current track ID to the new track ID
    lyrics = None
    timed_lyrics = []
    lyrics_text = ""
    lyrics_lang = None
    
    display.printText(0, 0, "-- loading next... --", gs=15)
    song_name = track.get("title", "Unknown") # get the song name from the API response, "unknown" by default
    artist_name = track.get("artist", "Unknown") # get the artist name from the API response, "unknown" by default
                    
    # ask navidrome for the lyrics of the current track using the track ID
    try:
        getSubsonicLyrics = requests.get(
            f"{url}getLyricsBySongId?id={track_id}", params=params, timeout=5
        ).json()
    except requests.exceptions.JSONDecodeError as error:
        print(f"Navidrome returned invalid lyrics JSON; falling back to LRCLIB: {error}")
        getSubsonicLyrics = {}
    subsonicLyrics = (getSubsonicLyrics.get("subsonic-response", {}).get("lyricsList", {}).get("structuredLyrics", []))

    # display the song name and artist name on the screen
    display.printText(0, 0, "------------------------", gs=15)
    display.printText(0, 0, f"{song_name} - {artist_name}", gs=15)

    # if navidrome provided lyrics, use them.
    if subsonicLyrics:
        # get lyric data from the API response and detect the language of the lyrics
        lyric_track = subsonicLyrics[0]
        lines = lyric_track.get("line", [])
        lyrics_text = "\n".join(item.get("value", "") for item in lines)
        lyrics_lang = detect(lyrics_text)

        # display the source of the lyrics and the detected language
        display.printText(0, 0, f"lyrics provided by navidrome | language: {lyrics_lang}", gs=15)
        display.printText(0, 0, "------------------------", gs=15)

        # if there are synced lyrics
        if lyric_track.get("synced"):
            timed_lyrics, lyrics_text = nav2lrc(lines) # convert navidrome's lyric timestamps into .lrc format for the parser

        else: # if there are no synced lyrics, just display the plain text lyrics
            lyrics = None # set no synced lyrics
            lyrics_text = "\n".join(line.get("value", "") for line in lines) # set plain text lyrics
            display.printText(0, 0, "no time-synced lyrics available. displaying all lyrics.", gs=15)
            display.printText(0, 0, lyrics_text, gs=15)
    
    else: # if navidrome did not provide lyrics, pull from lrclib
        display.printText(0, 0, "lyrics provided by lrclib", gs=15)
        lyrics_obj = get_lyrics(song_name, artist_name)
        timed_lyrics, lyrics_text = parse_lyriq_obj(lyrics_obj)
        lyrics_lang = detect(lyrics_text) if lyrics_text and lyrics_text != "lyrics not found :(" else None

        if not timed_lyrics:
            display.printText(0, 0, lyrics_text, gs=15)

    return current_track_id, timed_lyrics or [], lyrics_text, lyrics_lang

def parse_lyriq_obj(lyrics_obj):
    if not lyrics_obj or not getattr(lyrics_obj, "lyrics", None):
        return None, (lyrics_obj.plain_lyrics if lyrics_obj else "lyrics not found :(")

    timed_lyrics = []
    for timestamp, line in lyrics_obj.lyrics.items():
        if ":" in timestamp:
            minutes, seconds = timestamp.split(":")
            total_seconds = float(minutes) * 60 + float(seconds)
            timed_lyrics.append((total_seconds, line))
    timed_lyrics.sort()

    # If the Lyrics object had no synced timestamps, return None for timed_lyrics
    return (timed_lyrics if timed_lyrics else None), lyrics_obj.plain_lyrics


def nav2lrc(lines):
    lrc_lines = []
    for line in lines:
        ms = line.get("start", 0)
        minutes = ms // 60000
        seconds = (ms % 60000) / 1000.0
        lrc_lines.append(f"[{minutes:02d}:{seconds:05.2f}] {line.get('value', '')}")

    lrc_string = "\n".join(lrc_lines)
    lyrics_obj = Lyrics.from_lrc_string(lrc_string, none_char="♪")
    return parse_lyriq_obj(lyrics_obj)
