
from datetime import timedelta
from PIL import Image
import ad_skip_test as askip
import cv2
import datetime
import pyautogui
import pytesseract
import subprocess
import time
import os
import ctypes
script_directory = os.path.dirname(__file__)
pyautogui.FAILSAFE = False
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
amt_ads_done = 0


def resize_terminal(width, height):
    """Check terminal size and resize if necessary."""
    try:
        current_size = os.get_terminal_size()
        current_width, current_height = current_size.columns, current_size.lines

        if current_width != width or current_height != height:
            cmd = f"mode {width},{height}"
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            ctypes.windll.user32.MoveWindow(hwnd, 495, 0, width, height, True)
            os.system(cmd)

    except OSError as e:
        print("Error:", e)


def get_timer_text(screen_region):
    screenshot = askip.ImageFinder.capture_screen(screen_region)
    screenshot = process_image(screenshot)

    text = pytesseract.image_to_string(Image.fromarray(screenshot), lang='eng',
                                       config='--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789:').strip()
    if len(text) == 8:
        return text
    else:
        print("time not correct (8 chars) returning None")
        return None


def find_timer_regions():
    free_folder = os.path.join(script_directory, 'snip_images', 'collect_rewards')
    images = askip.ImageFinder.find_1_of_folder(free_folder, region, multiple=True)
    regions = []
    for im in images:
        region2 = {'left': im[1] - 60, 'top': im[2] + 88, 'width': 124, 'height': 35}  # Adjust as needed
        regions.append(region2)
    return regions


def process_image(image):
    # Convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 235, 255, cv2.THRESH_BINARY)

    # Invert the colors (optional)
    thresh = cv2.bitwise_not(thresh)

    # Noise reduction (optional)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    thresh = cv2.erode(thresh, kernel, iterations=1)
    thresh = cv2.dilate(thresh, kernel, iterations=1)

    # Show the output image
    return thresh


def parse_time(time_str):
    try:
        # Parse time string to extract hours, minutes, and seconds
        hours, minutes, seconds = map(int, time_str.split(':'))
        # Create a timedelta object representing the duration
        return timedelta(hours=hours, minutes=minutes, seconds=seconds)
    except ValueError:
        # Handle parsing errors (e.g., if time_str does not match expected format)
        print("Error parsing time string assuming update ready")
        return timedelta(hours=99, minutes=99, seconds=99)


def find_shortest_time(time_strs):
    valid_times = []
    for time_str, left_value in time_strs:  # Unpack both time_str and left value
        time_obj = parse_time(time_str)
        if time_obj:
            valid_times.append((time_obj, left_value))  # Append tuple of time object and left value

    if valid_times:
        shortest_time, shortest_left = min(valid_times, key=lambda x: x[0])  # Find the tuple with the shortest time
        return shortest_time, shortest_left  # Return shortest time and its corresponding left value

    return None, None


def get_sleep_time():
    times = []
    regis = find_timer_regions()
    if regis and len(regis) == 3:
        for reg in regis:
            txt = get_timer_text(reg)
            if txt:
                times.append((txt, reg['left']))  # Append tuple of text and left value
    shortest_time, shortest_left = find_shortest_time(times)
    if shortest_time:
        # Convert timedelta to seconds
        end_time = datetime.datetime.now() + shortest_time
        return end_time, shortest_left


def iterate_sleep_function(iterations):
    shortest_time = None
    left_loc = None
    for _ in range(iterations):
        sleep_time, left_loc = get_sleep_time()
        if shortest_time is None or sleep_time < shortest_time:
            shortest_time = sleep_time
    return shortest_time, left_loc


def wait_until_time(target_time, left):
    goal = get_goal(left)

    while datetime.datetime.now() < target_time:
        clear_console()
        # Calculate the remaining time until the target time
        remaining_time = target_time - datetime.datetime.now()
        formatted_time = str(remaining_time).split(".")[0]
        formatted_finish_time = target_time.strftime("%I:%M %p")

        print("Goal:", goal)
        print("Finish time:", formatted_finish_time)
        print("Waiting for:", formatted_time)
        print("Total Ads Done:", amt_ads_done)
        time.sleep(0.99)  # Sleep for 1 second

    print("Time reached:", target_time)


def get_goal(left):
    goal = None
    if left:
        if left == 44:
            goal = "Silver Chest"
        elif left == 189:
            goal = "Gems"
        elif left == 334:
            goal = "Gold Chest"
    return goal


def clear_console():
    # For Windows
    if os.name == 'nt':
        _ = os.system('cls')
    # For Unix/Linux/MacOS
    else:
        _ = os.system('clear')


def open_bluestacks():
    # Open Bluestacks
    subprocess.Popen("C:\\Program Files\\BlueStacks_nxt\\HD-Player.exe")
    while ads_automator.find_state(should_print=False) != "bluestacks_loading":
        time.sleep(1)  # Adjust the sleep time based on your system's speed

    print("Bluestacks opened.")
    while True:
        ads_automator.find_close()
        if ads_automator.find_state(should_print=False) == "android_home":
            break
        else:
            print("Bluestacks not loaded yet. Waiting...")
            time.sleep(5)


def close_bluestacks():
    # Close Bluestacks
    subprocess.Popen("taskkill /f /im HD-Player.exe")

    # Wait for Bluestacks to close
    time.sleep(2)  # Adjust the sleep time if necessary
    print("Bluestacks closed.")


def open_game():
    image_path = os.path.join(script_directory, 'snip_images', 'game_logo.png')
    _, x, y = askip.ImageFinder.find_needle(image_path, region)
    if x:
        askip.MouseController.mouse_pos(x, y)
        askip.MouseController.left_click()


def goto_rewards_page():
    while ads_automator.find_state(should_print=False) != "free_reward":
        image_path = os.path.join(script_directory, 'snip_images', 'rewards.png')
        _, x, y = askip.ImageFinder.find_needle(image_path, region)
        if x:
            askip.MouseController.mouse_pos(x, y)
            askip.MouseController.left_click()
            time.sleep(2)


def are_rewards_ready():
    image_path = os.path.join(script_directory, 'snip_images', 'free.png')
    _, x, y = askip.ImageFinder.find_needle(image_path, region)
    if x:
        askip.MouseController.mouse_pos(x, y)
        askip.MouseController.left_click()
        time.sleep(5)
        if x == 105:
            print(f"Free Chest Ready at {x}, {y}")
            return "free_chest"

        elif x == 231:
            print(f"Free Gems Ready at {x}, {y}")
            return "free_gems"

        else:
            print(f"Free Gold Chest Ready at {x}, {y}")
            return "free_gold_chest"

    else:
        if ads_automator.find_state(should_print=False) == "free_reward":
            print("Rewards not ready")
            return None


def load_game():
    while ads_automator.find_state(should_print=False) != "home":
        time.sleep(1)
        state = ads_automator.find_state(should_print=False)
        if state == "deal":
            image_path = os.path.join(script_directory, 'snip_images', 'red_cross.png')
            _, x, y = askip.ImageFinder.find_needle(image_path, region)
            if x:
                askip.MouseController.mouse_pos(x, y)
                askip.MouseController.left_click()
                time.sleep(1)


def click_ads():
    global amt_ads_done
    ads_clicked = False
    while not ads_clicked:
        ad = are_rewards_ready()
        if ad:
            if ad == "free_chest":
                ads_automator.open_chest_and_skip()
                time.sleep(2)
                amt_ads_done += 1

            elif ad == "free_gems":
                handle_ad()
                time.sleep(2)
                amt_ads_done += 1

            elif ad == "free_gold_chest":
                handle_ad()
                time.sleep(5)
                ads_automator.open_chest_and_skip()
                time.sleep(2)
                amt_ads_done += 1

        else:
            ads_clicked = True


def handle_ad():
    state = "advert"
    while state == "advert":
        state = ads_automator.wait_for_ad_to_end()


def main():
    while True:
        open_bluestacks()
        askip.ImageFinder.resize_bluestacks_window()
        open_game()
        load_game()
        goto_rewards_page()
        time.sleep(2)
        click_ads()
        s_time, left = iterate_sleep_function(4)
        close_bluestacks()
        wait_until_time(s_time, left)


region = {'left': 0, 'top': 0, 'width': 500, 'height': 915}  # Adjust as needed

ads_automator = askip.AdAutomator(4, region)
if __name__ == '__main__':
    resize_terminal(50, 10)  # Set console size to 100 columns width and 30 rows height
    main()
