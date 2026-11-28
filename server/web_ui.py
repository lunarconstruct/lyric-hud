import json
import os
import time

from lang_func import LYRIC_LANGUAGE_FORMATS, settings

class WebUI:
    """ a class for the web interface """

    ### class attributes (defaults for all instances of the class)
    BASE_DIR = os.path.dirname(__file__)
    STATE_PATH = os.path.join(BASE_DIR, "web/web_state.json")
    DEFAULTS_PATH = os.path.join(BASE_DIR, "web/default_state.json")
    RECONNECT_PATH = os.path.join(BASE_DIR, "web/reconnect.request")
    SETTINGS_PATH = os.path.join(BASE_DIR, "web/web_settings.json")

    def __init__(self):
        """ initialize web ui """
        with open(self.DEFAULTS_PATH, "r", encoding="utf-8") as defaults_file:
            self.defaults = json.load(defaults_file)

        self.web_state = self.defaults.copy()
        self.initialize_web_state()

    def initialize_web_state(self):
        """ reset the web UI state to its shared defaults """
        self.web_state.clear()
        self.web_state.update(self.defaults)
        self._save_web_state()

    def publish_web_state(self, **updates):
        """ push the current application state to the web ui state file """
        if not any(self.web_state.get(key) != value for key, value in updates.items()):
            return

        self.web_state.update(updates)
        self._save_web_state()

    def _save_web_state(self):
        """ helper function that does the saving in publish_web_state() function. """
        temporary_path = f"{self.STATE_PATH}.tmp"
        with open(temporary_path, "w", encoding="utf-8") as state_file:
            json.dump(self.web_state, state_file, ensure_ascii=False)
        os.replace(temporary_path, self.STATE_PATH)

    def wait_for_reconnect(self, timeout_seconds):
        """ wait up to the timeout for a reconnect request from the web UI """
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                os.unlink(self.RECONNECT_PATH)
                return True
            except FileNotFoundError:
                pass

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            time.sleep(min(0.25, remaining))

    def refresh_web_settings(self):
        """ check for changes in the settings defined on the website """
        if not os.path.isfile(self.SETTINGS_PATH):
            return

        with open(self.SETTINGS_PATH, "r", encoding="utf-8") as settings_file:
            saved_settings = json.load(settings_file)

        format_groups = {
            f"{language}_{line_number}_format": valid_formats
            for language, valid_formats in LYRIC_LANGUAGE_FORMATS.items()
            for line_number in ("line1", "line2")
        }
        for key, valid_formats in format_groups.items():
            if key not in saved_settings:
                continue
            value = saved_settings[key]
            if not isinstance(value, str) or value not in valid_formats:
                raise ValueError(f"Invalid {key} in web settings")
            setattr(settings, key, value)

    def clearUI(self, leaveMsg, display, status="waiting"):
        """ clears text from the screen and web state, and leaves behind a message if desired. """
        display.printText(0, 0, leaveMsg, gs=15)
        self.publish_web_state(
            status=status,
            title="",
            artist="",
            previous_line1="",
            previous_line2="",
            current_line1=leaveMsg,
            current_line2="",
            next_line1="",
            next_line2="",
            lyrics=""
        )