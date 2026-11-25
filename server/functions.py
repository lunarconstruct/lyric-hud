import json # used for reading/writing json files
import os
import time

from langdetect import detect
from lang_func import (
    LYRIC_LANGUAGE_FORMATS,
    _romanize_metadata,
    settings,
)

from lib.lyriq import get_lyrics, Lyrics # used to fetch lyrics from the lrclib and parse them into a Lyrics object
import requests # used to make HTTP requests to the navidrome api to get the current track and lyrics

## global variables
WEB_STATE_PATH = os.path.join(os.path.dirname(__file__), "web/web_state.json") # stores the current state for the web ui
WEB_STATE_DEFAULTS_PATH = os.path.join(os.path.dirname(__file__), "web/default_state.json")
WEB_RECONNECT_REQUEST_PATH = os.path.join(os.path.dirname(__file__), "web/reconnect.request")
WEB_SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "web/web_settings.json") # stores the current settings from the web ui
with open(WEB_STATE_DEFAULTS_PATH, "r", encoding="utf-8") as defaults_file:
    WEB_STATE_DEFAULTS = json.load(defaults_file)
web_state = WEB_STATE_DEFAULTS.copy()


def _save_web_state():
    temporary_path = f"{WEB_STATE_PATH}.tmp"
    with open(temporary_path, "w", encoding="utf-8") as state_file:
        json.dump(web_state, state_file, ensure_ascii=False)
    os.replace(temporary_path, WEB_STATE_PATH)


def initialize_web_state():
    """ reset the web UI state to its shared defaults """
    web_state.clear()
    web_state.update(WEB_STATE_DEFAULTS)
    _save_web_state()


def wait_for_reconnect(timeout_seconds):
    """ wait up to the timeout for a reconnect request from the web UI """
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            os.unlink(WEB_RECONNECT_REQUEST_PATH)
            return True
        except FileNotFoundError:
            pass

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(0.25, remaining))


def publish_web_state(**updates):
    """ push the current application state to the web ui state file """
    if not any(web_state.get(key) != value for key, value in updates.items()):
        return

    web_state.update(updates)
    _save_web_state()


def refresh_web_settings():
    """ check for changes in the settings defined on the website """
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

def clearUI(leaveMsg, display, status="waiting"):
    """ clears text from the screen and web state, and leaves behind a message if desired. """
    display.printText(0, 0, leaveMsg, gs=15)
    publish_web_state(
        status=status,
        title="",
        artist="",
        previous_line1="",
        previous_line2="",
        current_line1=leaveMsg,
        current_line2="",
        next_line1="",
        next_line2="",
        lyrics=""
    )

def pullSongInfo(nowPlaying):
    """ fetch the info for the new track and update the web state """
    # if we're not playing anything yet, use placeholders and stop running the function.
    if not nowPlaying:
        return None, None, 0, "empty", "", ""
        
    # collect information on what is currently playing
    track = nowPlaying[0]
    track_id = track.get("id")
    position_ms = track.get("positionMs", 0)
    listenState = track.get("state", "stopped")
    song_name = track.get("title", "Unknown")
    artist_name = track.get("artist", "Unknown")

    # post the grabbed information to the web state file
    publish_web_state(
        status=listenState,
        title=song_name,
        artist=artist_name
    )

    # expose the variables we set above
    return track, track_id, position_ms, listenState or "empty", song_name, artist_name

def pullLyrics(track_id, url, params, display, song_name, artist_name):
    """ grab the lyrics and lyric info from navidrome or lrclib
        timed_lyrics (synced lyrics), lyrics_text (plaintext lyrics), lyrics_from (lyrics provider), lyrics_lang (lyrics main language)"""

    timed_lyrics = None
    lyrics_text = ""
    lyrics_lang = None

    try:
        getSubsonicLyrics = requests.get(f"{url}getLyricsBySongId?id={track_id}", params=params, timeout=5).json()
    except requests.exceptions.JSONDecodeError as error:
        print(f"Navidrome returned invalid lyrics JSON; falling back to LRCLIB: {error}")
        getSubsonicLyrics = {}
    subsonicLyrics = (getSubsonicLyrics.get("subsonic-response", {}).get("lyricsList", {}).get("structuredLyrics", []))

    # if navidrome provided lyrics, use them.
    if subsonicLyrics:
        lyrics_from = "navidrome"
        # get lyric data from the API response and detect the language of the lyrics
        lyric_track = subsonicLyrics[0]
        lines = lyric_track.get("line", [])
        lyrics_text = "\n".join(item.get("value", "") for item in lines)
        lyrics_lang = detect(lyrics_text)

        # if there are synced lyrics
        if lyric_track.get("synced"):
            timed_lyrics, lyrics_text = nav2lrc(lines) # convert navidrome's lyric timestamps into .lrc format for the parser

        else: # if there are no synced lyrics, just display the plain text lyrics
            lyrics = None # set no synced lyrics
            lyrics_text = "\n".join(line.get("value", "") for line in lines) # set plain text lyrics
            display.printText(0, 0, "no time-synced lyrics available.", gs=15)
            display.printText(0, 0, lyrics_text, gs=15)
    
    else: # if navidrome did not provide lyrics, pull from lrclib
        lyrics_from = "lrclib"
        lyrics_obj = get_lyrics(song_name, artist_name)
        timed_lyrics, lyrics_text = parse_lyriq_obj(lyrics_obj)
        lyrics_lang = detect(lyrics_text) if lyrics_text and lyrics_text != "unknown" else None
    
    return timed_lyrics, lyrics_text, lyrics_from, lyrics_lang

def introduceSong(track_id, song_name, artist_name, display, url, params):
    """ format song information for displaying on screen and web ui """
    
    display.printText(0, 0, "-- loading next... --", gs=15)

    current_track_id = track_id # update the current track ID to the new track ID

    timed_lyrics = []
    lyrics_text = ""
    lyrics_lang = None

    # ask navidrome for the lyrics of the current track using the track ID
    timed_lyrics, lyrics_text, lyrics_from, lyrics_lang = pullLyrics(track_id, url, params, display, song_name, artist_name)

    song_info = f"{song_name} - {artist_name}"
    romanized_song_name = _romanize_metadata(song_name)
    romanized_artist_name = _romanize_metadata(artist_name)
    song_info2 = ""
    if romanized_song_name or romanized_artist_name:
        song_info2 = (
            f"{romanized_song_name or song_name} - "
            f"{romanized_artist_name or artist_name}"
        )
    lyrics_info = f"time-synced lyrics provided by {lyrics_from} | language: {lyrics_lang}" if timed_lyrics else "no synced lyrics :(",
             
    # display the song name, artist name, source of the lyrics and the detected language on the screen
    display.printText(0, 0, "------------------------", gs=15)
    display.printText(0, 0, song_info, gs=15)
    display.printText(0, 0, lyrics_info, gs=15)
    display.printText(0, 0, "------------------------", gs=15)

    # also push the track info to the web ui
    publish_web_state(
        status="playing",
        previous_line1=lyrics_info,
        previous_line2="",
        current_line1=song_info,
        current_line2=song_info2,
        next_line1=lyrics_info,
        next_line2="",
        lyrics=lyrics_text or "",
    )

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
