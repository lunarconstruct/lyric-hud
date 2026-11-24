## default libraries?
import json
import os
import time # used to sleep between polling the navidrome api for the current track and lyrics
import requests # used to make HTTP requests to the navidrome api to get the current track and lyrics

## third-party libraries
from bisect import bisect_right # used to find the index of the current lyric line based on the current playback time

## my modules
from functions import (
    convert_lyric_line,
    detect_lyric_language,
    introduceSong,
    publish_web_state,
    refresh_web_settings,
    setSongInfo,
    settings,
    get_formatted_lines,
)
from display import TerminalDisplay

with open(os.path.join(os.path.dirname(__file__), "credentials.json"), "r", encoding="utf-8") as credentials_file:
    credentials = json.load(credentials_file)

url = credentials["url"]
params = credentials["params"]

####### o kaaaayyyyy imports done lets actually Do the Thing

def main():
    # create the display object
    display = TerminalDisplay()
    # initialize the web ui state
    publish_web_state(status="waiting", title="", artist="", current_line="", lyrics="")

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
            publish_web_state(status=listenState)

            # stop/pause/empty check
            if listenState != "playing":
                if current_track_id is not None:
                    msg = "-- nothing is playing --" if listenState == "empty" else "-- music stopped --"
                    display.printText(0, 0, msg, gs=15)
                    current_track_id = None
                    publish_web_state(title="", artist="", current_line="", lyrics="")
                time.sleep(.25)
                continue

            # if the track ID that gets pulled from the API is different from the current track ID,
            if track_id != current_track_id:
                poll_time = time.monotonic() # note what time we polled the API
                # fetch the info for the new track and update the current track ID
                current_track_id, timed_lyrics, lyrics_text, lyrics_lang = introduceSong(track, track_id, display, url, params)
                # also push the track info to the web ui
                publish_web_state(
                    status="playing",
                    title=track.get("title", "Unknown"),
                    artist=track.get("artist", "Unknown"),
                    current_line="" if timed_lyrics else "no synced lyrics",
                    lyrics=lyrics_text or "",
                )
                
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

            ### LYRIC LOOP ###
            timed_lyrics = [item for item in timed_lyrics if len(item) == 2]

            if timed_lyrics:
                current_pos_sec = time.monotonic() - song_start_time
                start_index = max(0, bisect_right(timed_lyrics, current_pos_sec, key=lambda x: x[0]) - 1)
                next_index = start_index + 1
                
                prev_rendered = ("", "")

                for i in range(start_index, len(timed_lyrics)):
                    time_sec, line = timed_lyrics[i]
                    
                    wait_time = time_sec - (time.monotonic() - song_start_time)
                    if wait_time > 0:
                        time.sleep(wait_time)

                    # Check for updated settings once per lyric line
                    refresh_web_settings()

                    # get and format current line
                    rendered_line = get_formatted_lines(line, lyrics_lang, settings)

                    # get and format next line
                    if i + 1 < len(timed_lyrics):
                        _, raw_next_line = timed_lyrics[i + 1]
                        next_rendered = get_formatted_lines(raw_next_line, lyrics_lang, settings)
                    else:
                        next_rendered = ("", "")  # Default to blank on the final line of the song
                    
                    # set variables for each line
                    line1, line2 = rendered_line
                    prev1, prev2 = prev_rendered
                    next1, next2 = next_rendered

                    # print the lines on the terminal or OLED
                    display.printText(
                        0, 0,
                        f"{line1}\n{line2}" if line2 else line1,
                        gs=15
                    )
                    
                    # post the lines for the web ui to pull
                    publish_web_state(
                        previous_line=f"{prev1}\n{prev2}" if prev2 else prev1,
                        current_line=f"{line1}\n{line2}" if line2 else line1,
                        next_line=f"{next1}\n{next2}" if next2 else next1
                    )
                    
                    # when finished rendering this line, set it to the prevline variable
                    prev_rendered = rendered_line 

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
