from lyric_hud import LyricHUD

if __name__ == "__main__":
    try:
        hud = LyricHUD()
        hud.run()
    except KeyboardInterrupt:
        print("\nExiting lyric-hud...")
