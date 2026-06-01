"""
Connect to a robot, switch to custom mode, spin all wheel modules
forward for 2 seconds, then stop.
"""

import time

from clicbot_unofficial import BrainState, ClicBot, discover_first


def main() -> None:
    device = discover_first(timeout=5.0)
    print(f"Found: {device}")

    bot = ClicBot()
    bot.connect(device.ip, device.port)
    bot.send_client_info()
    bot.set_brain_state(BrainState.CUSTOM)

    bot.get_structure()

    wheels = bot.servo_wheels
    if not wheels:
        print("No wheel modules found.")
        bot.disconnect()
        return

    print(f"Spinning {len(wheels)} wheel(s) forward at speed 60...")
    for wheel in wheels:
        wheel.rotate_start(forward=True, speed=60)

    time.sleep(2.0)

    print("Stopping.")
    wheels[0].rotate_stop()  # stops all rotating modules, so just call one of them

    time.sleep(2.5)
    bot.disconnect()


main()
