class TerminalDisplay:
    """for displaying the lyrics in the terminal instead of the display"""

    # looks like it specifically overwrites the functions for drawing text in the micropython display library
    # so we can use the same code on both the terminal and micropython/OLED display
    def printText(self, x, y, text, gs=15):
        print(text)