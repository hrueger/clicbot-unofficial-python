"""
Move all servo joints to 0°, wait, then move them to 90°,
then lock them in place.

This example also shows how to walk the module tree: every module
has a .parent and a .children list, so you can navigate the physical
structure the robot reported.
"""
import time
from clicbot_unofficial import ClicBot, BrainState, discover_first
from clicbot_unofficial.modules import ServoJointModule


def main() -> None:
    device = discover_first(timeout=5.0)
    print(f"Found: {device}")

    bot = ClicBot()
    bot.connect(device.ip, device.port)
    bot.send_client_info()
    bot.set_brain_state(BrainState.CUSTOM)

    bot.get_structure()

    # Flat list — handy shortcut
    joints = bot.servo_joints
    if not joints:
        print("No servo joints found.")
        bot.disconnect()
        return

    print(f"Found {len(joints)} joint(s)")

    # Tree traversal — same modules, reached via parent/children links
    print(f"\nBrain's direct children: {bot.root.children}")
    for joint in joints:
        print(f"  joint id={joint.id}  parent={type(joint.parent).__name__} id={joint.parent.id}  children={joint.children}")

    print("\nMoving all joints to 0°...")
    for joint in joints:
        joint.rotate_to(0, speed=50)
    time.sleep(2.0)

    print("Moving all joints to 90°...")
    for joint in joints:
        joint.rotate_to(90, speed=50)
    time.sleep(2.0)

    print("Locking all joints.")
    for joint in joints:
        joint.lock()

    time.sleep(0.5)
    bot.disconnect()


main()
