## default libraries?
import json
import os
import time # used to sleep between polling the navidrome api for the current track and lyrics
import requests # used to make HTTP requests to the navidrome api to get the current track and lyrics
import traceback

## third-party libraries
from bisect import bisect_right # used to find the index of the current lyric line based on the current playback time

## my modules
import functions as f # general functions, accessed with a "f." prefix
import lang_func as lf # language functions, accessed with a "lf." prefix
from display import TerminalDisplay # class for the display

with open(os.path.join(os.path.dirname(__file__), "credentials.json"), "r", encoding="utf-8") as credentials_file:
    credentials = json.load(credentials_file)

url = credentials["url"]
params = credentials["params"]


def get_now_playing_entries():
    response = requests.get(f"{url}getNowPlaying", params=params, timeout=5).json()
    return response.get("subsonic-response", {}).get("nowPlaying", {}).get("entry", [])


####### o kaaaayyyyy imports done lets actually Do the Thing

def main():
    retry_interval = 1
    max_retry_interval = 30
    playback_poll_interval = 1

    # create the display object
    display = TerminalDisplay()
    # initialize the web ui state
    f.initialize_web_state()

    # initialize the current track ID to None so we can detect when a new song starts
    current_track_id = None
    display.printText(0,0,"-- waiting for a song... --",gs=15)

    ### MAIN LOOP ###
    while True: # while true allows it to keep looping, since true is always true
        try: # try block allows error handling instead of errors crashing the program

            ### GET NOW PLAYING INFO FROM NAVIDROME API ###
            # ask navidrome for the current track and relevant info
            nowPlaying = get_now_playing_entries()

            # assign track info to variables for easier access
            track, track_id, position_ms, listenState, song_name, artist_name = f.pullSongInfo(nowPlaying)
            if nowPlaying:
                retry_interval = 1

            # stop/pause/empty check
            if listenState != "playing":
                if current_track_id is not None:
                    leaveMsg = "-- nothing is playing --" if listenState == "empty" else "-- music stopped --"
                    if listenState == "paused":
                        display.printText(0, 0, "-- music paused --", gs=15)
                    else:
                        f.clearUI(leaveMsg, display, status="waiting" if listenState == "empty" else listenState)
                    current_track_id = None

                if listenState == "empty":
                    if f.wait_for_reconnect(retry_interval):
                        retry_interval = 1
                    else:
                        retry_interval = min(retry_interval * 2, max_retry_interval)
                else:
                    f.wait_for_reconnect(.25)
                continue

            # if the track ID that gets pulled from the API is different from the current track ID,
            if track_id != current_track_id:

                poll_time = time.monotonic() # note what time we polled the API

                # fetch the info for the new track and update the current track ID
                current_track_id, timed_lyrics, lyrics_text, lyrics_lang = f.introduceSong(track_id, song_name, artist_name, display, url, params)

                # Re-check position right after fetching lyrics in case the client updated it
                post_entry = get_now_playing_entries()
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
                
                prev_rendered = ("", "")
                playback_interrupted = False

                for i in range(start_index, len(timed_lyrics)):
                    time_sec, line = timed_lyrics[i]
                    
                    while True:
                        wait_time = time_sec - (time.monotonic() - song_start_time)
                        if wait_time <= 0:
                            break

                        time.sleep(min(wait_time, playback_poll_interval))
                        active_entries = get_now_playing_entries()
                        if not active_entries:
                            f.clearUI("-- nothing is playing --", display, status="waiting")
                            current_track_id = None
                            playback_interrupted = True
                            break

                        active_track = active_entries[0]
                        active_state = active_track.get("state", "stopped")
                        if active_track.get("id") != current_track_id or active_state != "playing":
                            f.pullSongInfo(active_entries)
                            if active_state == "paused":
                                display.printText(0, 0, "-- music paused --", gs=15)
                            elif active_state != "playing":
                                f.clearUI("-- music stopped --", display, status=active_state)
                            current_track_id = None
                            playback_interrupted = True
                            break

                    if playback_interrupted:
                        break

                    # Check for updated settings once per lyric line
                    f.refresh_web_settings()

                    # get and format current line
                    rendered_line = lf.get_formatted_lines(line, lyrics_lang, lf.settings)

                    # get and format next line
                    if i + 1 < len(timed_lyrics):
                        _, raw_next_line = timed_lyrics[i + 1]
                        next_rendered = lf.get_formatted_lines(raw_next_line, lyrics_lang, lf.settings)
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
                    f.publish_web_state(
                        previous_line1=prev1 if prev1 else "",
                        previous_line2=prev2 if prev2 else "",
                        current_line1=line1 if line1 else "",
                        current_line2=line2 if line2 else "",
                        next_line1=next1 if next1 else "",
                        next_line2=next2 if next2 else "",
                    )
                    
                    # when finished rendering this line, set it to the prevline variable
                    prev_rendered = rendered_line 

                    # Check if the song was skipped, changed, or stopped mid-playback
                    active_entries = get_now_playing_entries()
                    listenState = active_entries[0].get("state") if active_entries else "stopped" # get the user's listening state (playing, paused, stopped, etc.)

                    # based on the user's listening state (if playback stopped OR the track ID changed), break out to the outer loop
                    if not active_entries or active_entries[0].get("id") != current_track_id or listenState != "playing":
                        if current_track_id is not None: # if the user WAS listening but has now stopped,
                            if listenState == "paused":
                                f.pullSongInfo(active_entries)
                                display.printText(0, 0, "-- music paused --", gs=15)
                            elif active_entries:
                                f.pullSongInfo(active_entries)
                                f.clearUI("-- music stopped --", display, status=listenState)
                            else:
                                f.clearUI("-- nothing is playing --", display, status="waiting")
                            current_track_id = None # and reset the current track ID to None so we can detect when a new song starts
                        break

            else:
                # Using `for ... else` ensures this ONLY runs if the song wasn't skipped early
                while True:
                    time.sleep(1)
                    active_entries = get_now_playing_entries()
                    listenState = active_entries[0].get("state") if active_entries else "stopped" # get the user's listening state (playing, paused, stopped, etc.)

                    # based on the user's listening state (if playback stopped OR the track ID changed), break out to the outer loop
                    if not active_entries or active_entries[0].get("id") != current_track_id or listenState != "playing":
                        if current_track_id is not None: # if the user WAS listening but has now stopped,
                            if listenState == "paused":
                                f.pullSongInfo(active_entries)
                                display.printText(0, 0, "-- music paused --", gs=15)
                            elif active_entries:
                                f.pullSongInfo(active_entries)
                                f.clearUI("-- music stopped --", display, status=listenState)
                            else:
                                f.clearUI("-- nothing is playing --", display, status="waiting")
                            current_track_id = None # and reset the current track ID to None so we can detect when a new song starts
                        break

            # Brief pause at the end of a song before polling for the next track
            time.sleep(.25)

        ### ERROR HANDLING ###

        # if the navidrome API poll fails, retry in diminishing intervals
        except requests.exceptions.RequestException as e:
            print(f"Navidrome request failed; retrying in {retry_interval} seconds: {e}")
            if f.wait_for_reconnect(retry_interval):
                retry_interval = 1
            else:
                retry_interval = min(retry_interval * 2, max_retry_interval)

        # general error handling
        except Exception as e:
            print(f"Polling error: {e}")
            traceback.print_exc()
            time.sleep(.25)


# actually run the code lol
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting lyric-hud...")
