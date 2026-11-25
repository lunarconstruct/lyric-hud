# lyric-hud
a hud for my car that displays lyrics in sync with a subsonic server !

this is quite literally my first peek into this kind of programming so its gonna be very scuffed, dont expect this to be anything polished or good

python is new to me and so is working with most physical hardware like microcontrollers so ! it's gonna be an adventure x3

---

## hardware
plans are for this to be built with:
- ESP32 microcontroller
- 5.5" 256x64 OLED SSD1322 Display
- 3D printed housing?
- (i have no clue if this will be adequate power but) hopefully plugs into the cigarette lighter plug in my car??

## features

---

## Credits and libraries

### Python server
- [Cutlet](https://github.com/polm/cutlet) for Japanese romanization
- [fugashi](https://github.com/polm/fugashi) and [unidic-lite](https://github.com/polm/unidic-lite) for Japanese tokenization and dictionary data
- [jaconv](https://github.com/ikegami-yukino/jaconv) for kana conversion
- [korean-romanizer](https://github.com/osori/korean-romanizer) for Korean romanization
- [langdetect](https://github.com/Mimino666/langdetect) for lyric language detection
- [Requests](https://github.com/psf/requests) for Navidrome API requests
- [PyYAML](https://github.com/yaml/pyyaml) for settings files
- [lyriq by TN3W](https://github.com/tn3w/lyriq) for LRCLIB lyrics

### ESP32
- [micropython-ssd1322 by rdagger](https://github.com/rdagger/micropython-ssd1322) for the OLED display driver
- [MicroPython aioble by Jim Mussared](https://github.com/micropython/micropython-lib/tree/master/micropython/bluetooth/aioble) for Bluetooth LE support
