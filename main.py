## default libraries?
import sys # used to check if we're running on a MicroPython device or not, and to import the machine module if we are
import time # used to sleep between polling the navidrome api for the current track and lyrics
import requests # used to make HTTP requests to the navidrome api to get the current track and lyrics

## third-party libraries
from pykakasi import kakasi as kks # used to convert Japanese lyrics into romaji/kana/hiragana
from bisect import bisect_right # used to find the index of the current lyric line based on the current playback time
from lib.lyriq import get_lyrics, Lyrics # used to fetch lyrics from the lrclib and parse them into a Lyrics object
from langdetect import detect # used to detect the language of the lyrics

## my modules
from displays import OLEDDisplay, TerminalDisplay # used to create the display object, either for the terminal or for the hardware
from credentials import params, url # used to store the navidrome api credentials and url
import settings # imports settings variables

# o kaaaayyyyy imports done lets actually Do the Thing

def main():
    ### TEST MODE SETUP ###
    # check if we're in test mode
    test_mode = "--test" in sys.argv

    # if we're not in test mode, try to import the machine module to see if we're running on a MicroPython device
    if not test_mode:
        try:
            from machine import Pin, SPI  # type: ignore  # noqa: F401
        except ImportError:
            test_mode = True # if it gives an error, we're not on a MicroPython device, so we should switch to test mode

    # create the display object, either for the terminal or for the hardware
    display = TerminalDisplay() if test_mode else OLEDDisplay()

    # initialize the current track ID to None so we can detect when a new song starts
    current_track_id = None

    ### MAIN LOOP ###
    while True: # while true allows it to keep looping, since true is always true
        try: # try block allows error handling instead of errors crashing the program

            ### GET NOW PLAYING INFO FROM NAVIDROME API ###
            # ask navidrome for the current track and relevant info
            getNowPlaying = requests.get(f"{url}getNowPlaying", params=params, timeout=5).json() 
            nowPlaying = getNowPlaying.get("subsonic-response", {}).get("nowPlaying", {}).get("entry", [])

            # assign track info to variables for easier access
            track = nowPlaying[0] # set the API response to the track variable
            track_id = track.get("id") # get the track's ID
            position_ms = track.get("positionMs", 0) # get the user's position in the song in milliseconds
            isListening = track.get("state", []) # get the user's listening state (playing, paused, stopped, etc.)

            # based on the user's listening state, decide what to do next.
            if isListening != "playing": # if the user is not currently listening,
                if current_track_id is not None: # if the user WAS listening but has now stopped,
                    display.printText(0, 0, "-- music stopped --", gs=15) # display "music stopped" message
                    current_track_id = None # and reset the current track ID to None so we can detect when a new song starts
                continue

            # using monotonic time allows us to get the current playback position without worrying about API latency or delay
            song_start_time = time.monotonic() - (position_ms / 1000.0)

            # if the track ID that gets pulled from the API is different from the current track ID,
            if track_id != current_track_id:
                current_track_id = track_id # update the current track ID to the new track ID
                display.printText(0, 0, "-- song changing... --", gs=15)
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
                    lyrics_lang = detect(lyric_track.get("line", [{}])[0].get("value", ""))
                    lines = lyric_track.get("line", [])

                    # display the source of the lyrics and the detected language
                    display.printText(0, 0, f"lyrics provided by navidrome | language: {lyrics_lang}", gs=15)
                    display.printText(0, 0, "------------------------", gs=15)

                    # if there are synced lyrics
                    if lyric_track.get("synced"):

                        # convert navidrome's lyric timestamps into .lrc format for the parser
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

                    else: # if there are no synced lyrics, just display the plain text lyrics
                        lyrics = None # set no synced lyrics
                        lyrics_text = "\n".join(line.get("value", "") for line in lines) # set plain text lyrics
                        display.printText(0, 0, "no time-synced lyrics available. displaying all lyrics.", gs=15)
                        display.printText(0, 0, lyrics_text, gs=15)
                
                else: # if navidrome did not provide lyrics, pull from lrclib
                    display.printText(0, 0, "lyrics provided by lrclib", gs=15)
                    lyrics = get_lyrics(song_name, artist_name)
                    lyrics_text = lyrics.plain_lyrics if lyrics else "lyrics not found :("

            # 4. Play through the lyrics for the current song
            current_pos_sec = time.monotonic() - song_start_time
            start_index = max(0, bisect_right(timed_lyrics, current_pos_sec, key=lambda x: x[0]) - 1)
            
            prevline = None

            for time_sec, line in timed_lyrics[start_index:]:
                wait_time = time_sec - (time.monotonic() - song_start_time)
                if wait_time > 0:
                    time.sleep(wait_time)

                # convert lyrics writing system (kana, hiragana, etc) if the settings call for it
                kksresult = kks.convert(line)
                line1 = " ".join(item[settings.line1_format] for item in kksresult)
                line2 = " ".join(item[settings.line2_format] for item in kksresult)
                
                if not prevline == kksresult:
                    display.printText(0, 0, line1, gs=15)
                    display.printText(0, 0, line2, gs=15) if lyrics_lang == "ja" else ""

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

        except Exception as e: # catch any errors that occur during the main loop and print them to the console
            print(f"Polling error: {e}")
            time.sleep(3)
        

# actually run the code lol
if __name__ == "__main__":
    main()