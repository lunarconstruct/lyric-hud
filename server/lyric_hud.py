## default libraries?
import os
import time # used to sleep between polling the navidrome api for the current track and lyrics
import requests # used to make HTTP requests to the navidrome api to get the current track and lyrics
import traceback

from display import TerminalDisplay # class for the display(s)
from navidrome_client import NavidromeClient # class for getting info from navidrome
from web_ui import WebUI # class for the web ui

from bisect import bisect_right # used to find the index of the current lyric line based on the current playback time

import lang_func as lf # language functions, accessed with a "lf." prefix

class LyricHUD:
    def __init__(self):
        base_dir = os.path.dirname(__file__)
        self.display = TerminalDisplay()
        self.nav = NavidromeClient(os.path.join(base_dir, "credentials.json"))
        self.web = WebUI()

        self.retry_interval = 1
        self.max_retry_interval = 30
        self.playback_poll_interval = 1
        self.current_track_id = None
        self.song_start_time = 0.0

        self.display.printText(0, 0, "-- waiting for a song... --", gs=15)

    def introduceSong(self):
        """ format song information for displaying on screen and web ui """
        
        self.display.printText(0, 0, "-- loading next... --", gs=15)

        self.current_track_id = self.nav.track_id # update the current track ID to the new track ID

        # ask navidrome for the lyrics of the current track using the track ID
        self.nav.pullLyrics()

        song_info = f"{self.nav.song_name} - {self.nav.artist_name}"
        romanized_song_name = lf._romanize_metadata(self.nav.song_name)
        romanized_artist_name = lf._romanize_metadata(self.nav.artist_name)
        song_info2 = ""
        if romanized_song_name or romanized_artist_name:
            song_info2 = (
                f"{romanized_song_name or self.nav.song_name} - "
                f"{romanized_artist_name or self.nav.artist_name}"
            )
        lyrics_info = f"time-synced lyrics provided by {self.nav.lyrics_from} | language: {self.nav.lyrics_lang}" if self.nav.timed_lyrics else "no synced lyrics :("
                
        # display the song name, artist name, source of the lyrics and the detected language on the screen
        self.display.printText(0, 0, "------------------------", gs=15)
        self.display.printText(0, 0, song_info, gs=15)
        self.display.printText(0, 0, lyrics_info, gs=15)
        self.display.printText(0, 0, "------------------------", gs=15)

        # also push the track info to the web ui
        self.web.publish_web_state(
            status="playing",
            title=self.nav.song_name,
            artist=self.nav.artist_name,
            previous_line1=lyrics_info,
            previous_line2="",
            current_line1=song_info,
            current_line2=song_info2,
            next_line1=lyrics_info,
            next_line2="",
            lyrics=self.nav.lyrics_text or "",
        )

    def _handle_inactive_state(self):
        """ Handle paused, stopped, or empty playback in the main loop """
        state = self.nav.listenState
        leave_msg = "-- nothing is playing --" if state == "empty" else "-- music paused --"

        if self.current_track_id is not None:
            if state != "paused":
                status = "waiting" if state == "empty" else state
                self.web.clearUI(leave_msg, self.display, status=status)
            self.current_track_id = None

        if state == "empty":
            if self.web.wait_for_reconnect(self.retry_interval):
                self.retry_interval = 1
            else:
                self.retry_interval = min(self.retry_interval * 2, self.max_retry_interval)
        else:
            self.web.wait_for_reconnect(0.25)

    def _playback_interrupted(self):
        """ Check if the track changed, paused, or stopped mid-playback """
        self.nav.get_now_playing_entries()
        self.nav.pullSongInfo()

        if (
            self.nav.nowPlaying
            and self.nav.track_id == self.current_track_id
            and self.nav.listenState == "playing"
        ):
            return False

        if self.current_track_id is not None:
            if self.nav.listenState == "paused":
                self.display.printText(0, 0, "-- music paused --", gs=15)
                self.web.publish_web_state(status="paused")
            elif self.nav.nowPlaying:
                self.web.clearUI("-- music stopped --", self.display, status=self.nav.listenState)
            else:
                self.web.clearUI("-- nothing is playing --", self.display, status="waiting")
            self.current_track_id = None

        return True

    def _play_lyrics(self):
        """ Step through synced lyrics in real time """
        timed_lyrics = [item for item in (self.nav.timed_lyrics or []) if len(item) == 2]
        if not timed_lyrics:
            return

        current_pos_sec = time.monotonic() - self.song_start_time
        start_index = max(0, bisect_right(timed_lyrics, current_pos_sec, key=lambda x: x[0]) - 1)
        prev_rendered = ("", "")

        for i in range(start_index, len(timed_lyrics)):
            time_sec, line = timed_lyrics[i]

            while True:
                wait_time = time_sec - (time.monotonic() - self.song_start_time)
                if wait_time <= 0:
                    break

                time.sleep(min(wait_time, self.playback_poll_interval))
                if self._playback_interrupted():
                    return

            # Check for updated settings once per lyric line
            self.web.refresh_web_settings()

            rendered_line = lf.get_formatted_lines(line, self.nav.lyrics_lang, lf.settings)

            if i + 1 < len(timed_lyrics):
                _, raw_next_line = timed_lyrics[i + 1]
                next_rendered = lf.get_formatted_lines(raw_next_line, self.nav.lyrics_lang, lf.settings)
            else:
                next_rendered = ("", "")

            line1, line2 = rendered_line
            prev1, prev2 = prev_rendered
            next1, next2 = next_rendered

            self.display.printText(
                0, 0,
                f"{line1}\n{line2}" if line2 else line1,
                gs=15
            )

            self.web.publish_web_state(
                previous_line1=prev1 or "",
                previous_line2=prev2 or "",
                current_line1=line1 or "",
                current_line2=line2 or "",
                next_line1=next1 or "",
                next_line2=next2 or "",
            )

            prev_rendered = rendered_line

            if self._playback_interrupted():
                return

        # Wait at the end of the song until the track changes or stops
        while not self._playback_interrupted():
            time.sleep(1)

    def run(self):
        """ Main polling loop """
        while True:
            try:
                self.nav.get_now_playing_entries()
                self.nav.pullSongInfo()

                if self.nav.nowPlaying:
                    self.retry_interval = 1

                if self.nav.listenState != "playing":
                    self._handle_inactive_state()
                    continue

                if self.nav.track_id != self.current_track_id:
                    poll_time = time.monotonic()
                    initial_pos_ms = self.nav.position_ms

                    self.introduceSong()

                    # Re-check position right after fetching lyrics
                    self.nav.get_now_playing_entries()
                    fresh_pos_ms = self.nav.nowPlaying[0].get("positionMs", 0) if self.nav.nowPlaying else 0

                    if fresh_pos_ms > initial_pos_ms:
                        self.song_start_time = time.monotonic() - (fresh_pos_ms / 1000.0)
                    else:
                        CLIENT_OFFSET_SEC = 1.5
                        self.song_start_time = poll_time - (initial_pos_ms / 1000.0) - CLIENT_OFFSET_SEC

                self._play_lyrics()
                time.sleep(0.25)

            except requests.exceptions.RequestException as e:
                print(f"Navidrome request failed; retrying in {self.retry_interval} seconds: {e}")
                if self.web.wait_for_reconnect(self.retry_interval):
                    self.retry_interval = 1
                else:
                    self.retry_interval = min(self.retry_interval * 2, self.max_retry_interval)

            except Exception as e:
                print(f"Polling error: {e}")
                traceback.print_exc()
                time.sleep(0.25)