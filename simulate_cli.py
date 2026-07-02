import sys
import time
import os

# Configuration
LOG_FILE_PATH = r"d:\capstone_project\MYGRATE---Capstone-Project\working\qwen3.5_cloud\charts4j\test\artifacts\cli_output.log"
DELAY = 1.0

BANNER = """\033[94m\033[1m
███╗   ███╗██╗   ██╗ ██████╗ ██████╗  █████╗ ████████╗███████╗
████╗ ████║╚██╗ ██╔╝██╔════╝ ██╔══██╗██╔══██╗╚══██╔══╝██╔════╝
██╔████╔██║ ╚████╔╝ ██║  ███╗██████╔╝███████║   ██║   █████╗  
██║╚██╔╝██║  ╚██╔╝  ██║   ██║██╔══██╗██╔══██║   ██║   ██╔══╝  
██║ ╚═╝ ██║   ██║   ╚██████╔╝██║  ██║██║  ██║   ██║   ███████╗
╚═╝     ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝  (TungBKDN)
\033[0m\033[36m                 ~ Automated Java Migration Wizard ~\033[0m
"""

def main():
    if len(sys.argv) > 1:
        try:
            global DELAY
            DELAY = float(sys.argv[1])
        except ValueError:
            print(f"Invalid delay value. Using default: {DELAY}s")

    # Show Banner
    print(BANNER)
    time.sleep(DELAY * 1.5)

    print("\033[36m[MYGRATE] Activating virtual environment (.venv)...\033[0m")
    time.sleep(DELAY)
    print("\033[32m[MYGRATE] Running cli_app.py...\033[0m")
    time.sleep(DELAY * 1.5)

    if not os.path.exists(LOG_FILE_PATH):
        print(f"Error: Log file not found at {LOG_FILE_PATH}")
        return

    with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.rstrip("\n")
        
        # Check if the line represents a key step
        is_step = any(indicator in line for indicator in [
            "ReAct iteration",
            "Calling tool:",
            "=== 🔄 LLM",
            "=== TRANSLATOR",
            "Migration Notes:",
            "overall_success",
            "Running mvn verify",
            "Running JaCoCo",
            "State Result Summary:",
            "MIGRATION RUN SUMMARY",
            "[AI RESPONSE]"
        ])

        # Print the line immediately (without typewriter/character-by-character delay)
        print(line)
        
        if is_step:
            time.sleep(DELAY)
        else:
            # Short delay for non-step lines so they print naturally but fast
            time.sleep(DELAY * 0.1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user.")
