import os
import sys

# define the display
# oled
class OLEDDisplay:
    """for displaying the lyrics on the OLED display"""

    def __init__(self):
        self.display = create_hardware_display()

    def draw_text8x8(self, x, y, text, gs=15):
        self.display.draw_text8x8(x, y, text, gs)

    def present(self):
        self.display.present()

    def printText(self, x, y, text, gs=15):
        self.display.draw_text8x8(x, y, text, gs)
        self.display.present()
        
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