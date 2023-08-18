import time
import subprocess

def main():
    while True:
        try:
            # Run your script. Replace 'your_script.py' with your script's path.
            subprocess.run(['python', 'sync.py'], check=True)
            
            # Wait for 50 minutes (300 seconds)
            time.sleep(300)
            
        except subprocess.CalledProcessError as e:
            print(f"Error occurred while running the script: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()