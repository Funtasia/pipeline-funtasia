import time

spinner = [
"0000",
"0001",
"0010",
"0011",
"0100",
"0101",
"0110",
"0111"
]

for i in range(100):
    print("\r" + spinner[i % len(spinner)], end="", flush=True)
    time.sleep(0.1)

print("\r✓ Done")