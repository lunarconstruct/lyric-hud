import os
import sys
# Prefer the package source directory when running from this workspace.
lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
if os.path.isdir(lib_dir) and lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)

import time
import datetime
import requests
import pykakasi
from bisect import bisect_right
from lyriq import get_lyrics, Lyrics



# define the displays (terminal and oled)
# terminal
class TerminalDisplay:
    """for displaying the lyrics in the terminal instead of the display, for testing"""

    # looks like it specifically overwrites the functions for drawing text in the micropython display library
    # so we can use the same code on both the terminal and micropython/OLED display
    def draw_text8x8(self, x, y, text, gs=15):
        print(text)

    def present(self):
        pass

# oled
def create_hardware_display():
    """Create the SPI/display objects used on the MicroPython device."""
    lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
    if lib_path not in sys.path:
        sys.path.append(lib_path)

    from machine import Pin, SPI  # type: ignore
    from ssd1322 import Display  # type: ignore

    spi = SPI(
        1,
        baudrate=10_000_000,
        polarity=0,
        phase=0,
        sck=Pin(18),
        mosi=Pin(23),
    )

    return Display(
        spi,
        cs=Pin(5),
        dc=Pin(16),
        rst=Pin(17),
        width=256,
        height=64,
    )




# navidrome api stuff???
url = "https://navidrome.big-gay.party/rest/"
params = {
    "u": "LunarConstruct",
    "p": "Childrenofdust7!",
    "v": "1.16.1",
    "c": "lyric-hud",
    "f": "json",
}

def main():
    # check if we're in test mode
    test_mode = "--test" in sys.argv 

    # if we're not in test mode, try to import the machine module to see if we're running on a MicroPython device
    if not test_mode:
        try:
            from machine import Pin, SPI  # type: ignore  # noqa: F401
        except ImportError:
            test_mode = True # if it gives an error, we're not on a MicroPython device, so we should switch to test mode

    # create the display object, either for the terminal or for the hardware
    display = TerminalDisplay() if test_mode else create_hardware_display()

    current_track_id = None

    while True:
        try:
            # 1. Poll Subsonic for the active track
            resp = requests.get(f"{url}getNowPlaying", params=params, timeout=5).json()
            entries = resp.get("subsonic-response", {}).get("nowPlaying", {}).get("entry", [])

            # 2. If nothing is playing, show idle screen and wait 2 seconds before checking again
            if not entries:
                if current_track_id is not None:
                    display.draw_text8x8(0, 0, "-- music stopped --", gs=15)
                    display.present()
                    current_track_id = None
                time.sleep(2)
                continue

            track = entries[0]
            track_id = track.get("id")
            position_ms = track.get("positionMs", 0)
            
            # Anchor the clock immediately upon receiving the API response
            song_start_time = time.monotonic() - (position_ms / 1000.0)

            # 3. Only fetch and parse lyrics when a NEW song starts
            if track_id != current_track_id:
                current_track_id = track_id
                song_name = track.get("title", "Unknown")
                artist_name = track.get("artist", "Unknown")
                                
                # retrieve the lyrics !!!
                getsubsoniclyrics = requests.get(f"{url}getLyricsBySongId?id={track_id}", params=params, timeout=5).json()

                subsonic_lyrics = (
                    getsubsoniclyrics.get("subsonic-response", {})
                    .get("lyricsList", {})
                    .get("structuredLyrics", [])
                )

                lyrics_lang = (
                    subsonic_lyrics[0]
                    .get("lang", [])
                )

                display.draw_text8x8(0, 0, f"{song_name} - {artist_name}", gs=15)
                display.present()

                if subsonic_lyrics:
                    print(f"lyrics pulled from navidrome | language: {lyrics_lang}")
                    print("------------------------")
                    lyric_track = subsonic_lyrics[0]
                    lines = lyric_track.get("line", [])
                    
                    if lyric_track.get("synced"):
                        # Convert Navidrome milliseconds into [mm:ss.xx] LRC format
                        lrc_lines = []
                        for line in lines:
                            ms = line.get("start", 0)
                            minutes = ms // 60000
                            seconds = (ms % 60000) / 1000.0
                            lrc_lines.append(f"[{minutes:02d}:{seconds:05.2f}] {line.get('value', '')}")
                        
                        lrc_string = "\n".join(lrc_lines)
                        lyrics = Lyrics.from_lrc_string(lrc_string, none_char="♪")
                        lyrics_text = lyrics.plain_lyrics
                    else:
                        # Handle unsynced lyrics directly as plain text
                        lyrics = None
                        lyrics_text = "\n".join(line.get("value", "") for line in lines)
                else:
                    print("subsonic doesnt have lyrics, pulling from lrclib")
                    lyrics = get_lyrics(song_name, artist_name)
                    lyrics_text = lyrics.plain_lyrics if lyrics else "lyrics not found :("
                
                
                
                # Check if we have synchronized lyrics, and if we dont?
                if not lyrics.synced_lyrics:
                    display.draw_text8x8(0, 0, "No synchronized lyrics available for this song.", gs=15)
                    display.present()

                    # display the plaintext lyrics
                    display.draw_text8x8(0, 0, lyrics_text, gs=15)
                    display.present()
                    sys.exit(1)

                # Get timestamps and lyrics sorted by time
                timed_lyrics = []
                for timestamp, line in lyrics.lyrics.items():
                    if ":" in timestamp:
                        minutes, seconds = timestamp.split(":")
                        total_seconds = float(minutes) * 60 + float(seconds)
                        timed_lyrics.append((total_seconds, line))

                timed_lyrics.sort()  # Sort by timestamp

            # 4. Play through the lyrics for the current song
            current_pos_sec = time.monotonic() - song_start_time
            start_index = max(0, bisect_right(timed_lyrics, current_pos_sec, key=lambda x: x[0]) - 1)
            kks = pykakasi.kakasi()
            prevline = None

            for time_sec, line in timed_lyrics[start_index:]:
                wait_time = time_sec - (time.monotonic() - song_start_time)
                if wait_time > 0:
                    time.sleep(wait_time)

                # set desired lyrics format (‘orig’, ‘kana’, ‘hira’, ‘hepburn’, ‘kunrei’, ‘passport’, 'none')
                line1_format = 'orig'
                line2_format = 'hepburn'

                kksresult = kks.convert(line)
                line1 = " ".join(item[line1_format] for item in kksresult)
                line2 = " ".join(item[line2_format] for item in kksresult)

                if not prevline == kksresult:
                    display.draw_text8x8(0, 0, line1, gs=15)
                    display.draw_text8x8(0, 0, line2, gs=15)
                    display.present()

                # Check if the song was skipped, changed, or stopped mid-playback
                poll = requests.get(f"{url}getNowPlaying", params=params, timeout=5).json()
                active_entries = poll.get("subsonic-response", {}).get("nowPlaying", {}).get("entry", [])
                
                # Break out to the outer loop if playback stopped OR the track ID changed
                if not active_entries or active_entries[0].get("id") != current_track_id:
                    break

            else:
                # Using `for ... else` ensures this ONLY runs if the song wasn't skipped early
                while True:
                    time.sleep(1)
                    poll = requests.get(f"{url}getNowPlaying", params=params, timeout=5).json()
                    active_entries = poll.get("subsonic-response", {}).get("nowPlaying", {}).get("entry", [])
                    
                    # Finally break out to the main outer loop when the track changes or stops
                    if not active_entries or active_entries[0].get("id") != current_track_id:
                        break

            # Brief pause at the end of a song before polling for the next track
            time.sleep(1)
            prevline = kksresult

        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(3)
        


if __name__ == "__main__":
    main()