import time
import win32api
import win32con
import mss.tools
import concurrent.futures
import numpy as np
import cv2
import pyautogui
import os
import pygetwindow as gw

pyautogui.FAILSAFE = False
script_directory = os.path.dirname(__file__)


class ImageFinder:
    @staticmethod
    def capture_screen(cap_region):
        """
        Captures the screen within the specified region.

        Args:
        region (dict): Dictionary containing the region coordinates.

        Returns:
        np.array: Numpy array representing the screenshot image.
        """
        with mss.mss() as sct:
            sct_img = sct.grab(cap_region)
            # noinspection PyTypeChecker
            screenshot = np.array(sct_img)
            return screenshot

    @staticmethod
    def find_needle(file_path, cap_region):
        """
        Finds a needle image within a screenshot and returns its name, x, and y coordinates.

        Args:
        file_path (str): The file path of the needle image.

        Returns:
        tuple: (name, x, y) if needle is found, otherwise (None, None, None).
        """
        # Capture the screen
        screenshot = ImageFinder.capture_screen(cap_region)

        # Perform template matching
        match = ImageFinder.template_matching(screenshot, file_path, threshold=0.90)

        # Group similar rectangles
        match = ImageFinder.group_rectangles(match)

        # Return the name, x, and y coordinates of the first match
        if match and len(match) > 0:
            for match_item in match:
                name = match_item[0]
                x = match_item[1]
                y = match_item[2]
                return name, x, y
        else:
            return None, None, None

    @staticmethod
    def find_1_of_folder(folder, cap_region, multiple=False):
        """
        Find the first matching image in the given folder.

        Args:
        folder (str): The path to the folder containing the images.

        Returns:
        tuple: The coordinates of the first matching image, or None if no match is found.
        """

        # Get the paths of all PNG files in the folder
        paths = [os.path.join(folder, filename) for filename in os.listdir(folder) if filename.endswith(".png")]

        # Capture a screenshot
        screenshot = ImageFinder.capture_screen(cap_region)

        def match_template(path):
            """
            Match the given image template with the screenshot.

            Args:
            path (str): The path to the image file.

            Returns:
            tuple: The coordinates of the matching image, or None if no match is found.
            """
            match = ImageFinder.template_matching(screenshot, path)
            match = ImageFinder.group_rectangles(match)
            if match and len(match) > 0:
                return match[0]
            else:
                return None

        # Use ThreadPoolExecutor to match templates concurrently
        with concurrent.futures.ThreadPoolExecutor() as executor:
            matches = list(executor.map(match_template, paths))

        # Filter out None matches
        matches = [match for match in matches if match is not None]

        # Return the first match, or None if no matches are found
        if matches:
            if multiple:
                return matches
            else:
                return matches[0]
        else:
            return None, None, None

    @staticmethod
    def template_matching(haystack, image_path, threshold=0.93):
        global match_percent
        """
        Perform template matching to find the location of a template image within a larger image.

        Args:
        - haystack: The larger image to search within.
        - image_path: The path to the template image.

        Returns:
        - matches: A list of tuples containing the name of the template image, and the x and y coordinates of the center of each match.
        """

        # Load the template image
        needle = cv2.imread(image_path, cv2.IMREAD_COLOR)
        gray_needle = cv2.cvtColor(needle, cv2.COLOR_BGR2GRAY)

        # Convert the haystack image to grayscale
        gray_haystack = cv2.cvtColor(haystack, cv2.COLOR_BGR2GRAY)

        # Perform template matching
        result = cv2.matchTemplate(gray_haystack, gray_needle, cv2.TM_CCOEFF_NORMED)

        # Find the locations where the match exceeds the threshold
        loc = np.nonzero(result >= threshold)

        # Extract the matches and their coordinates
        matches = []
        for pt in zip(*loc[::-1]):
            x = pt[0]
            y = pt[1]
            img_w = needle.shape[1]
            img_h = needle.shape[0]
            center_x = x + img_w // 2
            center_y = y + img_h // 2
            image_name = os.path.splitext(os.path.basename(image_path))[0]
            match_percent = int(result[y, x] * 100)
            matches.append((image_name, center_x, center_y))

        return matches

    @staticmethod
    def group_rectangles(rectangles, max_distance=5):
        """
        Groups rectangles based on their proximity to each other.

        Args:
        rectangles (list): List of tuples representing rectangles, where each tuple contains image name, center_x, and
        center_y.
        max_distance (int): Maximum distance for two rectangles to be considered in the same group. Default is 5.

        Returns:
        list: List of grouped rectangles.
        """

        # Initialize an empty list to store grouped rectangles
        grouped_rectangles = []

        # Iterate through each rectangle
        for rect in rectangles:
            # Check if the rectangle is in the correct format
            if not isinstance(rect, tuple) or len(rect) != 3:
                continue
            # Extract image name, center_x, and center_y from the tuple
            image_name = rect[0]
            center_x = rect[1]
            center_y = rect[2]
            added = False
            # Iterate through existing grouped rectangles
            for idx, (group_image_name, group_center_x, group_center_y) in enumerate(grouped_rectangles):
                # Check if the current rectangle is close enough to be grouped with an existing one
                if abs(center_x - group_center_x) <= max_distance and abs(center_y - group_center_y) <= max_distance:
                    # Calculate the new center coordinates for the group
                    new_center_x = (center_x + group_center_x) // 2
                    new_center_y = (center_y + group_center_y) // 2
                    # Update the existing group with the new center coordinates
                    grouped_rectangles[idx] = (group_image_name, new_center_x, new_center_y)
                    added = True
                    break
            # If the rectangle was not added to an existing group, add it as a new group
            if not added:
                grouped_rectangles.append((image_name, center_x, center_y))

        # Sort the grouped rectangles based on center_x and center_y
        grouped_rectangles.sort(key=lambda rects: (rects[1], rects[2]))

        # Return the list of grouped rectangles
        return grouped_rectangles

    @staticmethod
    def resize_bluestacks_window():
        bluestacks_window = None
        desired_size = (500, 915)
        desired_xy = (0, 0)
        # Get all windows

        # Find window with name containing "Bluestacks"
        for window in gw.getAllWindows():
            if "bluestacks" in window.title.lower():
                bluestacks_window = window
                break

        # If Bluestacks window is found
        if bluestacks_window:
            print("Bluestacks window found")
            if (bluestacks_window.width, bluestacks_window.height) != desired_size or (
                    bluestacks_window.top, bluestacks_window.left) != desired_xy:
                print("Bluestacks window Rezized")
                # Resize the window
                bluestacks_window.resizeTo(desired_size[0], desired_size[1])
                bluestacks_window.moveTo(0, 0)  # Move the window to (0, 0) position


class MouseController:
    @staticmethod
    def left_click():
        """
        Simulate a left mouse click
        """
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)

    @staticmethod
    def mouse_pos(*args):
        """
        Set the mouse cursor position to the specified coordinates.

        Args:
            *args: Tuple of (x, y) or two separate arguments x and y.

        Raises:
            ValueError: If the input does not match the expected format.
        """
        if len(args) == 1:
            x, y = args[0]
        elif len(args) == 2:
            x, y = args
        else:
            raise ValueError("Expected either a tuple (x, y) or two separate arguments x and y.")

        win32api.SetCursorPos((x, y))


class AdAutomator:
    def __init__(self, start_no, capture_region):
        self.start_no = start_no
        self.capture_region = capture_region

    def find_arrow(self, game_region, debug=False):
        try:
            # Capture the screen (you may need to install mss)
            screenshot = ImageFinder.capture_screen(game_region)

            # Preprocess the image (e.g., convert to HSV color space and apply thresholding)
            hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)
            lower_green = np.array([40, 40, 40])
            upper_green = np.array([70, 255, 255])
            mask = cv2.inRange(hsv, lower_green, upper_green)

            # Find contours of the thresholded image
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Filter contours based on shape (e.g., aspect ratio)
            arrow_contours = []
            for contour in contours:
                # Approximate the contour to reduce the number of points
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)

                # Check if the contour has a certain number of vertices (e.g., 3 for a triangle)
                if len(approx) == 5:
                    arrow_contours.append(contour)

            # Select the contour with the largest area
            if arrow_contours:
                largest_contour = max(arrow_contours, key=cv2.contourArea)
                # Get the bounding rectangle of the largest contour
                x, y, w, h = cv2.boundingRect(largest_contour)
                # Extract coordinates of the arrow
                arrow_x = x + w // 2
                arrow_y = y + h // 2
                if debug:
                    # Draw a rectangle around the detected arrow (for debugging)
                    debug_image = cv2.rectangle(screenshot.copy(), (x, y), (x + w, y + h), (0, 255, 0), 2)
                    return arrow_x, arrow_y, debug_image
                else:
                    return arrow_x, arrow_y, None
            else:
                return None, None, None

        except (TypeError, ValueError, cv2.error) as e:
            print(f"An error occurred during image processing: {e}")
            return None, None, None

    def find_state(self, should_print=True):
        states_folder = os.path.join(script_directory, 'snip_images', 'states')
        name, _, _ = ImageFinder.find_1_of_folder(states_folder, self.capture_region)
        if name:
            if should_print:
                print(f"{name} Scene")
            return name.lower()
        if name is None:
            return "advert"

    def automate_ads(self):
        """
        This function automates the process of watching ads and opening chests in a game.
        It keeps track of the number of ads watched and opens chests as required.
        """

        ads_done = 1  # Initialize the number of ads watched
        ad_no = ads_done  # Initialize the current ad number
        running = True  # Set the running flag to True
        ImageFinder.resize_bluestacks_window()

        while running:  # Start a while loop to continue the process until running is False
            # Print the current ad number and total ads watched
            print(f"Ad Number: {ad_no}/{self.start_no} Total:{ads_done}")
            self.watch_first_ad()  # Call the method to watch the first ad

            print("Waiting for Advertising")  # Print a message indicating waiting for advertising

            state = "advert"  # If ad number is not equal to start number, set state to "advert"

            time.sleep(2)  # Pause for 2 seconds

            while state == "advert":  # Start a while loop while state is "advert"
                state = self.wait_for_ad_to_end()  # Call the method to wait for the ad to end

            while state == "openchest":  # Start a while loop while state is "openchest"
                img = os.path.join(script_directory, 'snip_images', 'open.png')
                screenshot = ImageFinder.capture_screen(region)  # Capture the screen
                match = ImageFinder.template_matching(screenshot, img, threshold=0.9)  # Perform template matching
                match = ImageFinder.group_rectangles(match)  # Group the matched rectangles
                if match and len(match) > 0:  # Check if there is a match
                    ad_no += 1  # Increment the ad number
                    ads_done += 1  # Increment the total ads watched
                    print("new ad ready")  # Print a message indicating a new ad is ready
                    break  # Break the loop
                if ad_no + 1 > self.start_no:  # Check if the ad number is equal to the start number
                    ad_no = 1  # Reset the ad number
                    time.sleep(4)  # Pause for 4 seconds
                    state = self.open_chest_and_skip()  # Call the method to open the chest and skip

            while state == "home":  # Start a while loop while state is "home"
                for _ in range(12):
                    state = self.find_state()
                    time.sleep(.3)
                if state == "home":
                    state = "open_next"

            while state == "chest":  # Start a while loop while state is "chest"
                ad_no = 1  # Reset the ad number
                state = self.open_chest_and_skip()  # Call the method to open the chest and skip

            loop_no = 0  # Initialize the loop counter
            while state == "open_next":  # Start a while loop while state is "open_next"
                window = self.find_state()
                if window != "home":
                    break

                loop_no += 1  # Increment the loop counter
                chest_folder = os.path.join(script_directory, 'snip_images', 'chests')
                # Find the chest image in the folder
                name, x, y = ImageFinder.find_1_of_folder(chest_folder, self.capture_region)
                if name:  # Check if a chest image is found
                    print(f"{name} found")  # Print a message indicating the chest image is found
                    # Call the method to get the amount of ads to watch
                    self.start_no, state = self.get_amount_ads_to_watch(name, x, y)
                if loop_no >= 120:  # Check if the loop counter is greater than or equal to 120
                    state = self.find_state()
                    if state == "home":
                        state = ""
                        # Print a message indicating the loop counter limit is reached
                        print("loop_no over 120 reached")

            while state == "free_reward":  # Start a while loop while state is "free_reward"
                state = " "  # Set the state to an empty string

            if state == "":  # Check if state is an empty string
                running = False  # Set the running flag to False
                print("No Ads Left")  # Print a message indicating the game is complete

    def watch_first_ad(self):
        """
        Watches the first ad based on the current state.
        """
        # Find the current state
        state = self.find_state()

        # Check the state and take action accordingly
        if state == "home":
            self.watch_ad()
        elif state == "openchest":
            self.click_watch_ad_button()

    def click_chest_then_video(self):
        """
        Clicks on the chest and then proceeds to watch a video ad.
        """
        # Find the arrow position
        arrow_x, arrow_y, _ = self.find_arrow(region)

        # If arrow not found, check ad
        if arrow_x is None or arrow_y is None:
            print("No Arrow Found Checking Ad")
        else:
            # Move the mouse to the arrow position and click
            MouseController.mouse_pos(arrow_x, arrow_y + 30)
            MouseController.left_click()
            time.sleep(0.5)

        # Click on the watch ad button
        self.click_watch_ad_button()

    def watch_ad(self):
        self.click_chest_then_video()  # Corrected function name

    def click_watch_ad_button(self):
        needle = os.path.join(script_directory, 'snip_images', 'open.png')
        _, x, y = ImageFinder.find_needle(needle, region)
        if x and y:
            MouseController.mouse_pos(x, y)
            MouseController.left_click()

    def wait_for_ad_to_end(self):
        """
        Waits for the ad to end and returns the state of the ad.
        """
        # Get the state of the ad
        state = self.find_state()

        # If state exists, convert it to lowercase
        if state:
            state = state.lower()

        # Find and close the ad
        self.find_close()

        # Return the state of the ad
        return state

    def open_chest_and_skip(self):
        """
        Function to open a chest and skip through a series of screens
        """
        # Define the image paths for the skip and continue buttons

        img_skip = os.path.join(script_directory, 'snip_images', 'skip.png')
        img_continue = os.path.join(script_directory, 'snip_images', 'continue.png')

        # Loop until the chest is opened and screens are skipped
        while True:
            # Find the "Skip" button
            _, x, y = ImageFinder.find_needle(img_skip, self.capture_region)
            if x:
                # Click the "Skip" button
                print("Skipping Opening")
                MouseController.mouse_pos(x, y)
                MouseController.left_click()
                time.sleep(3)
                # Find the "Continue" button
                _, x, y = ImageFinder.find_needle(img_continue, self.capture_region)
                if x:
                    # Click the "Continue" button
                    print("Continue")
                    MouseController.mouse_pos(x, y)
                    MouseController.left_click()
                    time.sleep(2)
                    # Set the state to open the next chest
                    state = "open_next"
                    return state
            else:
                time.sleep(.5)

    def get_amount_ads_to_watch(self, name, x, y):
        """
        Determine the number of ads to watch based on the chest type.

        Args:
        - name (str): The type of the chest
        - x (int): x-coordinate
        - y (int): y-coordinate

        Returns:
        - start_no (int): The number of ads to watch
        - state (str): Resets state to '' to initiate next loop
        """
        state = " "
        if name == "silver_chest":
            start_no = 4
            self.start_new_chest(x, y)

        elif name == "platinum_chest":
            start_no = 12
            self.start_new_chest(x, y)

        elif name == "gold_chest":
            start_no = 8
            self.start_new_chest(x, y)
        else:
            print(f"Unknown {name} add it!")
            start_no = 4
        return start_no, state

    def start_new_chest(self, x, y):
        """
        Clicks on the specified coordinates to start a new chest.

        Args:
        x (int): The x-coordinate of the point to click
        y (int): The y-coordinate of the point to click
        """
        # Set the path to the image file
        img = os.path.join(script_directory, 'snip_images', 'start.png')

        # Move the mouse to the specified coordinates and click
        MouseController.mouse_pos(x, y)
        MouseController.left_click()
        time.sleep(2)

        # Find the start.png image and click on it if found
        _, x, y = ImageFinder.find_needle(img, region)
        if x and y:
            MouseController.mouse_pos(x, y)
            MouseController.left_click()
            time.sleep(2)

    # enables code completion
    def find_close(self):
        """
        Finds and clicks on a close button within a folder.
        """
        # Press the escape key
        pyautogui.press('esc')

        # Define the folder path for close button images
        close_folder = os.path.join(script_directory, 'snip_images', 'close')
        # Find the first image in the folder
        name, x, y = ImageFinder.find_1_of_folder(close_folder, self.capture_region)

        # Check if the image is found at the expected position (adjust if you find an x that is different)
        if x and x > 10 and y < 700:
            string = f"{name} found"

            # Add match percentage to the string if available
            if match_percent:
                string += f" with {match_percent}% Confidence"

            # Print the result string
            print(string)

            # Move the mouse to the found location
            MouseController.mouse_pos(x, y)

            # Perform a left click
            MouseController.left_click()

            # Wait for 1 second
            time.sleep(1)


if __name__ == '__main__':
    region = {'left': 0, 'top': 0, 'width': 500, 'height': 915}  # Adjust as needed
    ads_automator = AdAutomator(8, region)
    ads_automator.automate_ads()
