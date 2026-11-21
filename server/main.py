## default libraries?
import time # used to sleep between polling the navidrome api for the current track and lyrics
import requests # used to make HTTP requests to the navidrome api to get the current track and lyrics
import yaml # to read yaml config files
from types import SimpleNamespace

## third-party libraries
from bisect import bisect_right # used to find the index of the current lyric line based on the current playback time
from lib.lyriq import get_lyrics, Lyrics # used to fetch lyrics from the lrclib and parse them into a Lyrics object
from langdetect import detect # used to detect the language of the lyrics
import pykakasi # used to convert Japanese lyrics into romaji/kana/hiragana
kks = pykakasi.kakasi()

## my modules
from credentials import params, url # used to store the navidrome api credentials and url
from functions import nav2lrc, introduceSong, setSongInfo # misc functions and classes
from display import TerminalDisplay

# import settings from settings.yaml
with open("settings.yaml", "r", encoding="utf-8") as f:
    settings = SimpleNamespace(**yaml.safe_load(f))

####### o kaaaayyyyy imports done lets actually Do the Thing

def main():
    # create the display object
    display = TerminalDisplay()

    # initialize the current track ID to None so we can detect when a new song starts
    current_track_id = None
    display.printText(0,0,"-- waiting for a song... --",gs=15)

    ### MAIN LOOP ###
    while True: # while true allows it to keep looping, since true is always true
        try: # try block allows error handling instead of errors crashing the program

            ### GET NOW PLAYING INFO FROM NAVIDROME API ###
            # ask navidrome for the current track and relevant info
            getNowPlaying = requests.get(f"{url}getNowPlaying", params=params, timeout=5).json() 
            nowPlaying = getNowPlaying.get("subsonic-response", {}).get("nowPlaying", {}).get("entry", [])

            # assign track info to variables for easier access
            track, track_id, position_ms, listenState = setSongInfo(nowPlaying)

            # stop/pause/empty check
            if listenState != "playing":
                if current_track_id is not None:
                    msg = "-- nothing is playing --" if listenState == "empty" else "-- music stopped --"
                    display.printText(0, 0, msg, gs=15)
                    current_track_id = None
                time.sleep(.25)
                continue

            # if the track ID that gets pulled from the API is different from the current track ID,
            if track_id != current_track_id:
                poll_time = time.monotonic()
                current_track_id, timed_lyrics, lyrics_text, lyrics_lang = introduceSong(track, track_id, display, url, params)
                
                # Re-check position right after fetching lyrics in case the client updated it
                post_fetch = requests.get(f"{url}getNowPlaying", params=params, timeout=5).json()
                post_entry = post_fetch.get("subsonic-response", {}).get("nowPlaying", {}).get("entry", [])
                fresh_pos_ms = post_entry[0].get("positionMs", 0) if post_entry else 0

                if fresh_pos_ms > position_ms:
                    song_start_time = time.monotonic() - (fresh_pos_ms / 1000.0)
                else:
                    # Client (like Feishin) isn't updating positionMs live, so anchor to when we first saw the track start
                    # Add a ~0.5s - 1.0s offset to account for polling interval + Feishin's initial scrobble delay
                    CLIENT_OFFSET_SEC = 1.5
                    song_start_time = poll_time - (position_ms / 1000.0) - CLIENT_OFFSET_SEC

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
                line1 = " ".join(item[settings.line1_format] for item in kksresult) if settings.line1_format != "none" else ""
                line2 = " ".join(item[settings.line2_format] for item in kksresult) if settings.line2_format != "none" else ""
                
                if not prevline == kksresult:
                    display.printText(0, 0, f"{line1}", gs=15)
                    if lyrics_lang == "ja":
                        display.printText(0, 0, line2, gs=15) 
                    prevline = kksresult

                # Check if the song was skipped, changed, or stopped mid-playback
                poll = requests.get(f"{url}getNowPlaying", params=params, timeout=5).json()
                active_entries = poll.get("subsonic-response", {}).get("nowPlaying", {}).get("entry", [])
                listenState = active_entries[0].get("state") if active_entries else "stopped" # get the user's listening state (playing, paused, stopped, etc.)

                # based on the user's listening state (if playback stopped OR the track ID changed), break out to the outer loop
                if not active_entries or active_entries[0].get("id") != current_track_id or listenState != "playing":
                    if current_track_id is not None: # if the user WAS listening but has now stopped,
                        display.printText(0, 0, "-- music stopped --", gs=15) # display "music stopped" message
                        current_track_id = None # and reset the current track ID to None so we can detect when a new song starts
                    break

            else:
                # Using `for ... else` ensures this ONLY runs if the song wasn't skipped early
                while True:
                    time.sleep(1)
                    poll = requests.get(f"{url}getNowPlaying", params=params, timeout=5).json()
                    active_entries = poll.get("subsonic-response", {}).get("nowPlaying", {}).get("entry", [])
                    listenState = active_entries[0].get("state") if active_entries else "stopped" # get the user's listening state (playing, paused, stopped, etc.)

                    # based on the user's listening state (if playback stopped OR the track ID changed), break out to the outer loop
                    if not active_entries or active_entries[0].get("id") != current_track_id or listenState != "playing":
                        if current_track_id is not None: # if the user WAS listening but has now stopped,
                            display.printText(0, 0, "-- music stopped --", gs=15) # display "music stopped" message
                            current_track_id = None # and reset the current track ID to None so we can detect when a new song starts
                        break

            # Brief pause at the end of a song before polling for the next track
            time.sleep(.25)
            

        except Exception as e: # catch any errors that occur during the main loop and print them to the console
            print(f"Polling error: {e}")
            time.sleep(3)


# actually run the code lol
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting lyric-hud...")
