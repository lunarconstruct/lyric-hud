import os
import sys
import time
import datetime
import requests
from bisect import bisect_right

# Prefer the package source directory when running from this workspace.
lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
if os.path.isdir(lib_dir) and lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)


# import lyriq library for getting lyrics
from lyriq import get_lyrics

# navidrome api stuff???
url = "https://navidrome.big-gay.party/rest/"
params = {
    "u": "LunarConstruct",
    "p": "Childrenofdust7!",
    "v": "1.16.1",
    "c": "lyric-hud",
    "f": "json",
}

nowplaying = requests.get(f"{url}getNowPlaying", params=params)
nowplaying_data = nowplaying.json()

entries = nowplaying_data.get("subsonic-response", {}).get("nowPlaying", {}).get("entry", [])

if entries:
    current_track = entries[0]
    song_name = current_track.get("title")
    artist_name = current_track.get("artist")

    # figure out current position
    position_ms = current_track.get("positionMs", 0)
    position = datetime.timedelta(milliseconds=position_ms)

    total_seconds, milliseconds = divmod(position_ms, 1000) # split total milliseconds into total seconds and remaining milliseconds
    minutes, seconds = divmod(total_seconds, 60) # split total seconds into minutes and remaining seconds

    # print song info
    print(f"Now playing: {song_name} by {artist_name}")
    print(f"position: {minutes:02d}:{seconds:02d}.{milliseconds:03d}")

else:
    print("Nothing is currently playing.")


class TerminalDisplay:
    """for displaying the lyrics in the terminal instead of the display, for testing"""

    # looks like it specifically overwrites the functions for drawing text in the micropython display library
    # so we can use the same code on both the terminal and micropython/OLED display
    def draw_text8x8(self, x, y, text, gs=15):
        print(text)

    def present(self):
        pass


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

# here's the main shebang
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

    # retrieve the lyrics !!!
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

    current_pos_sec = position_ms / 1000.0
    index = bisect_right(timed_lyrics, current_pos_sec, key=lambda x: x[0]) - 1

    # Start at the active lyric (or 0 if the song hasn't reached the first lyric yet)
    start_index = max(0, index)
    song_start_time = time.monotonic() - current_pos_sec
    last_time = current_pos_sec

    for time_sec, line in timed_lyrics[start_index:]:
        # Check how far into the song we actually are right now
        elapsed = time.monotonic() - song_start_time
        wait_time = time_sec - elapsed

        # Only sleep for the remaining time (automatically skips if behind or already active)
        if wait_time > 0:
            time.sleep(wait_time)

        display.draw_text8x8(0, 0, f"{line}", gs=15)
        display.present()

        # Poll Subsonic API (any network delay here is absorbed by the next elapsed calculation)
        now_playing = (
            requests.get(f"{url}getNowPlaying", params=params)
            .json()
            .get("subsonic-response", {})
            .get("nowPlaying", {})
            .get("entry", [])
        )
        if not now_playing:
            display.draw_text8x8(0, 0, "-- music stopped --", gs=15)
            display.present()
            break
    


if __name__ == "__main__":
    main()