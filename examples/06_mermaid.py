"""
Save a Mermaid diagram of the robot's physical module structure to a file.

Usage:
    IP=192.168.x.x python3 examples/06_mermaid.py
    IP=192.168.x.x OUT=my-robot.md python3 examples/06_mermaid.py
"""
import os
from clicbot_unofficial import ClicBot, BrainState, to_mermaid, discover_first

HOST = os.environ.get("IP")
OUT  = os.environ.get("OUT", "structure.md")


def main() -> None:
    if HOST:
        bot = ClicBot()
        bot.connect(HOST, int(os.environ.get("PORT", 9632)))
    else:
        print("No IP set — scanning network...")
        device = discover_first(timeout=5.0)
        print(f"Found {device.name} at {device.ip}:{device.port}")
        bot = ClicBot()
        bot.connect(device.ip, device.port)

    bot.send_client_info()
    bot.set_brain_state(BrainState.CUSTOM)
    bot.get_structure()
    bot.disconnect()

    diagram = to_mermaid(bot._raw_structure)

    with open(OUT, "w") as f:
        f.write("```mermaid\n")
        f.write(diagram)
        f.write("\n```\n")

    print(f"Saved to {OUT}")
    print("View it at https://mermaid.live — paste the diagram content (without the fences).")
    print(f"\n{len(bot._raw_structure)} modules.")


main()
