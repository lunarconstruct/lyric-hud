from lib.lyriq import get_lyrics, Lyrics # used to fetch lyrics from the lrclib and parse them into a Lyrics object
import requests # used to make HTTP requests to the navidrome api to get the current track and lyrics
from langdetect import detect

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
    lyrics_text = ""
    lyrics_lang = None
    
    display.printText(0, 0, "-- loading next... --", gs=15)
    song_name = track.get("title", "Unknown") # get the song name from the API response, "unknown" by default
    artist_name = track.get("artist", "Unknown") # get the artist name from the API response, "unknown" by default
                    
    # ask navidrome for the lyrics of the current track using the track ID
    getSubsonicLyrics = requests.get(f"{url}getLyricsBySongId?id={track_id}", params=params, timeout=5).json()
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

    return current_track_id, timed_lyrics, lyrics_text, lyrics_lang

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
