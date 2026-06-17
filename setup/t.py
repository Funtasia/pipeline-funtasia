# import time
# import sys

# spinner = [
#     "⠋","⠙","⠹","⠸","⠼",
#     "⠴","⠦","⠧","⠇","⠏"
# ]
# print("\033[2J\033[H", end="")
# print("\033[?25l", end="")
# print("\n" * 5)  # reserve space

# for i in range(40):
#     frame = spinner[i % len(spinner)]

#     sys.stdout.write("\033[H")  # move to top-left

#     print(f"{frame} [1/3] Detecting Blender")
#     print("  [2/3] Detecting SketchUp")
#     print("  [3/3] Detecting Git")
#     print()

#     progress = min(i // 2, 20)
#     print(f"[{'█' * progress:<20}] {progress * 5}%")

#     sys.stdout.flush()
#     time.sleep(0.1)


import sys
import time

def progress(current, total, task="Installing"):
    width = 32

    percent = current / total
    filled = int(width * percent)

    bar = "█" * filled + " " * (width - filled)

    sys.stdout.write(
        f"\r{task:<18} │{bar}│ {percent:>6.1%}"
    )

    sys.stdout.flush()

    if current == total:
        print()

def progress_percent(percent, task="Working"):
    width = 32

    filled = int(width * percent / 100)

    bar = "█" * filled + "─" * (width - filled)

    print(
        f"\r{task:<18} │{bar}│ {percent:6.1f}%",
        end="",
        flush=True
    )

    if percent >= 100:
        print()

for i in range(100):
    progress_percent(i+1)
    time.sleep(0.1)