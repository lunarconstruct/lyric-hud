import json
import langdetect
from lib.lyriq import Lyrics # used to fetch lyrics from the lrclib and parse them into a Lyrics object
import requests # used to make HTTP requests to the navidrome api to get the current track and lyrics

class NavidromeClient:

    def __init__(self, credentials_path):
        """ initializes the navidrome/subsonic client with the credentials file. """
        with open(credentials_path, "r", encoding="utf-8") as f:
            creds = json.load(f)
        
        self.url = creds["url"]
        self.params = creds["params"]
        self.track = None
        self.track_id = None
        self.position_ms = 0
        self.listenState = "empty"
        self.song_name = ""
        self.artist_name = ""
        self.timed_lyrics = None
        self.lyrics_text = ""
        self.lyrics_from = None
        self.lyrics_lang = None

    def get_now_playing_entries(self):
        response = requests.get(f"{self.url}getNowPlaying", params=self.params, timeout=5).json()
        self.nowPlaying = response.get("subsonic-response", {}).get("nowPlaying", {}).get("entry", [])

    def pullSongInfo(self):
        """ fetch the info for the new track and update the web state """

        if self.nowPlaying: # if playing smth, get its info
            self.track = self.nowPlaying[0]
            self.track_id = self.track.get("id")
            self.position_ms = self.track.get("positionMs", 0)
            self.listenState = self.track.get("state", "stopped")
            self.song_name = self.track.get("title", "Unknown")
            self.artist_name = self.track.get("artist", "Unknown")
          
        else: # if we're not playing anything yet, use placeholders and stop running the function.
            self.track = None
            self.track_id = None
            self.position_ms = 0
            self.listenState = "empty"
            self.song_name = ""
            self.artist_name = ""

    def pullLyrics(self):
        """ grab the lyrics and lyric info from navidrome or lrclib
            timed_lyrics (synced lyrics), lyrics_text (plaintext lyrics), lyrics_from (lyrics provider), lyrics_lang (lyrics main language)"""

        self.timed_lyrics = None
        self.lyrics_text = ""
        self.lyrics_from = None
        self.lyrics_lang = None

        try:
            getSubsonicLyrics = requests.get(f"{self.url}getLyricsBySongId?id={self.track_id}", params=self.params, timeout=5).json()
        except requests.exceptions.JSONDecodeError as error:
            print(f"Navidrome returned invalid lyrics JSON; falling back to LRCLIB: {error}")
            getSubsonicLyrics = {}
        subsonicLyrics = (getSubsonicLyrics.get("subsonic-response", {}).get("lyricsList", {}).get("structuredLyrics", []))

        # if navidrome provided lyrics, use them.
        if subsonicLyrics:
            self.lyrics_from = "navidrome"
            # get lyric data from the API response and detect the language of the lyrics
            self.lyric_track = subsonicLyrics[0]
            self.lines = self.lyric_track.get("line", [])
            self.lyrics_text = "\n".join(item.get("value", "") for item in self.lines)
            self.lyrics_lang = langdetect.detect(self.lyrics_text)

            # if there are synced lyrics
            if self.lyric_track.get("synced"):
                self.timed_lyrics, self.lyrics_text = self.nav2lrc(self.lines) # convert navidrome's lyric timestamps into .lrc format for the parser

            else: # if there are no synced lyrics, just display the plain text lyrics
                self.timed_lyrics = None

        else: # if navidrome did not provide lyrics, pull from lrclib
            self.lyrics_from = "lrclib"
            lyrics_obj = Lyrics.get_lyrics(self.song_name, self.artist_name)
            self.timed_lyrics, self.lyrics_text = self.parse_lyriq_obj(lyrics_obj)
            self.lyrics_lang = langdetect.detect(self.lyrics_text) if self.lyrics_text and self.lyrics_text != "unknown" else None
        
        return self.timed_lyrics, self.lyrics_text, self.lyrics_from, self.lyrics_lang

    def nav2lrc(self, lines):
        """ converts navidrome lyric files to lrc format for the parser """
        lrc_lines = []
        for line in lines:
            ms = line.get("start", 0)
            minutes = ms // 60000
            seconds = (ms % 60000) / 1000.0
            lrc_lines.append(f"[{minutes:02d}:{seconds:05.2f}] {line.get('value', '')}")

        lrc_string = "\n".join(lrc_lines)
        lyrics_obj = Lyrics.from_lrc_string(lrc_string, none_char="♪")
        return self.parse_lyriq_obj(lyrics_obj)

    def parse_lyriq_obj(self, lyrics_obj):
        """ parses the lyrics into timed_lyrics to be displayed """
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
