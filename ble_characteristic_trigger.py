import time
import os
from gpiozero import Button
from wpa_characteristics import main


BUTTON_GPIO = 2

button = Button(BUTTON_GPIO)


was_pressed = False



while True:
    if button.is_pressed and not was_pressed:
        print("Button pressed! Running BLE Interface...")
        os.system("bluetoothctl power on")
        main()
        was_pressed = True
        time.sleep(0.2)
    elif not button.is_pressed:
        was_pressed = False

    time.sleep(0.1)