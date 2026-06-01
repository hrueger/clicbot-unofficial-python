"""Scan the local network and find the first discovered ClicBot robot."""
from clicbot_unofficial import discover_first


def main() -> None:
    print("Finding first robot (max. 5s)...")
    device = discover_first(timeout=5.0)

    if not device:
        print("Unfortinately no robot was found... Are you sure it is powered on and connected to the same Wi-Fi network?")
        return

    print(f"  {device.name}  {device.ip}:{device.port}  brain_state={device.brain_state}")


main()
