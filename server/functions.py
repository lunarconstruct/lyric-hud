from lib.lyriq import get_lyrics, Lyrics # used to fetch lyrics from the lrclib and parse them into a Lyrics object

def nav2lrc(lines):
    lrc_lines = [] # init a list for the lyrics to live in
    for line in lines:
        ms = line.get("start", 0)
        minutes = ms // 60000
        seconds = (ms % 60000) / 1000.0
        lrc_lines.append(f"[{minutes:02d}:{seconds:05.2f}] {line.get('value', '')}")

    # convert the list of lyrics into a single string for the parser
    lrc_string = "\n".join(lrc_lines)
    lyrics = Lyrics.from_lrc_string(lrc_string, none_char="♪") # set synced lyrics
    lyrics_text = lyrics.plain_lyrics # set plain text lyrics

    # put lyrics in time order for display during playback
    timed_lyrics = []
    for timestamp, line in lyrics.lyrics.items():
        if ":" in timestamp:
            minutes, seconds = timestamp.split(":")
            total_seconds = float(minutes) * 60 + float(seconds)
            timed_lyrics.append((total_seconds, line))
    timed_lyrics.sort()  # Sort by timestamp

    return timed_lyrics, lyrics_text

class TerminalDisplay:
    """for displaying the lyrics in the terminal instead of the display"""

    # looks like it specifically overwrites the functions for drawing text in the micropython display library
    # so we can use the same code on both the terminal and micropython/OLED display
    def printText(self, x, y, text, gs=15):
        print(text)