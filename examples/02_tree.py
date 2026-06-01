"""
Connect to a robot and print its physical module tree.

Each module shows its type and id. Indentation reflects
how the pieces are physically connected to each other.

Example output:

    BrainModule      id=0
      ServoJointModule  id=1
        ServoJointModule  id=2
          ServoWheelModule  id=3
      ServoJointModule  id=4
"""
from clicbot_unofficial import ClicBot, BrainState, discover_first
from clicbot_unofficial.modules import ClicBotModule


def print_tree(module: ClicBotModule, indent: int = 0) -> None:
    prefix = "  " * indent
    print(f"{prefix}{type(module).__name__:<22} id={module.id}")
    for child in module.children:
        print_tree(child, indent + 1)


def main() -> None:
    device = discover_first(timeout=5.0)
    print(f"Found: {device}\n")

    bot = ClicBot()
    bot.connect(device.ip, device.port)
    bot.send_client_info()
    bot.set_brain_state(BrainState.CUSTOM)

    bot.get_structure()

    print("Module tree:")
    print_tree(bot.root)

    print(f"\nAll modules flat: {list(bot.modules.values())}")
    print(f"Servo joints:     {bot.servo_joints}")
    print(f"Servo wheels:     {bot.servo_wheels}")

    # Walking parent links — every non-root module knows its parent
    for module in bot.servo_joints:
        print(f"\n  joint id={module.id}  →  parent is {type(module.parent).__name__} id={module.parent.id}")

    bot.disconnect()


main()
