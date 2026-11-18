import os
import sys
import time

# Prefer the package source directory when running from this workspace.
lyriq_source = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lyriq")
if os.path.isdir(lyriq_source) and lyriq_source not in sys.path:
    sys.path.insert(0, lyriq_source)

# import lyriq library for getting lyrics
from lyriq import get_lyrics

# set the song and artist name for testing
# manual for now but will eventually pull from navidrome/subsonic? or maybe symfonium directly if theres an api for it
song_name = "Pay No Mind"
artist_name = "Madeon"


class TerminalDisplay:
    """for displaying the lyrics in the terminal instead of the display, for testing"""

    # looks like it specifically overwrites the functions for drawing text in the micropython display library
    # so we can use the same code on both the terminal and micropython/OLED display
    def draw_text8x8(self, x, y, text, gs=15):
        print(f"[display at {x},{y}, gs={gs}]\n{text}")

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

    display.draw_text8x8(0, 0, f"Found synchronized lyrics for '{lyrics.track_name}' by {lyrics.artist_name}", gs=15)
    display.present()

    # Get timestamps and lyrics sorted by time
    timed_lyrics = []
    for timestamp, line in lyrics.lyrics.items():
        if ":" in timestamp:
            minutes, seconds = timestamp.split(":")
            total_seconds = float(minutes) * 60 + float(seconds)
            timed_lyrics.append((total_seconds, line))

    timed_lyrics.sort()  # Sort by timestamp

    last_time = 0
    for i, (time_sec, line) in enumerate(timed_lyrics):
        # wait until first lyric starts
        if i == 0:
            time.sleep(time_sec)
        # for each subsequent lyric, wait for the difference in time from the last lyric
        if i > 0:
            wait_time = time_sec - last_time
            time.sleep(wait_time)

        minutes = int(time_sec // 60)
        seconds = time_sec % 60
        print(f"{line}")
        last_time = time_sec

    print(f"that was {song_name} by {artist_name}!")


if __name__ == "__main__":
    main()