from queue import Queue
import logging
import os
import threading
import time
import typing

from pyvesync import VeSync
from Quartz import CGEventSourceCounterForEventType, kCGEventSourceStateCombinedSessionState, kCGKeyboardEventKeyboardType
import psutil
import rumps


###################
# Settings

# How many new keypresses since last update are required to be considered busy?
MIN_NEW_KEYPRESS_COUNT = 40

# How often should we update to see if we're busy (in seconds)?
UPDATE_INTERVAL = 10

# VEsync credentials (WiFi power outlet)
VESYNC_EMAIL = os.environ.get('VESYNC_EMAIL')
VESYNC_PASSWORD = os.environ.get('VESYNC_PASSWORD')

###################
# Main script

logger = logging.getLogger(__name__)


class OfficeBusyStatusBarUI(rumps.App):
    """
    Provide user interface on the OS X status bar. User can make the busy light stay on, return to auto mode, and
    quit the program.
    """
    def __init__(self):
        super().__init__("Busy Sign")
        # Disable the default quit action, because we provide a custom one in the "quit" method below.
        self.quit_button = None

    @rumps.clicked("Auto")
    def auto(self, _):
        logger.info('Set auto mode through UI')
        queue.empty()
        queue.put(False)

    @rumps.clicked("Stay On")
    def on(self, _):
        logger.info('Forced busy status through UI')
        # Turn light on immediately, so we don't wait for the next update
        set_light_state(power_on=True)
        queue.empty()
        queue.put(True)

    @rumps.clicked("Quit")
    def quit(self, sender):
        # Custom quit method so we turn the light off when exiting
        logger.info('Quitting from UI')
        set_light_state(power_on=False)
        rumps.quit_application(sender)


def set_light_state(power_on: bool) -> None:
    """
    Turns the VeSync power outlet on or off, which controls the "busy" light.

    :param power_on: Should the light be powered on?
    """
    manager = VeSync(VESYNC_EMAIL, VESYNC_PASSWORD)
    manager.login()
    manager.update()
    my_switch = manager.outlets[0]
    if power_on:
        my_switch.turn_on()
        logger.info('Turning light on')
    else:
        my_switch.turn_off()
        logger.info('Turning light off')


def is_busy_from_keypresses(last_keypress_count: typing.Optional[int]) -> typing.Tuple[bool, int]:
    """
    Check if user is considered busy due to having enough keypresses since the last update.

    :param last_keypress_count: The keypress count when we last checked (for comparison to current value)
    :return: a tuple like (is_busy, keypress_count)
    """
    keypress_count = CGEventSourceCounterForEventType(kCGEventSourceStateCombinedSessionState,
                                                      kCGKeyboardEventKeyboardType)
    if last_keypress_count:
        keypress_diff = keypress_count - last_keypress_count
        if keypress_diff >= MIN_NEW_KEYPRESS_COUNT:
            logger.info(f'Busy due to keypresses ({keypress_diff} new keypresses)')
            return True, keypress_count
    return False, keypress_count


def is_busy_from_zoom() -> bool:
    """
    Check if user is considered busy due to zoom being open.
    """
    zoom_is_running = 'zoom.us' in (p.info['name'] for p in psutil.process_iter(['name']))
    if zoom_is_running:
        logger.info('Busy due to running Zoom application')
        return True
    return False


def is_busy_from_ui(last_state: bool) -> bool:
    """
    Check if user is considered busy due to "stay on" being enabled in the user interface.

    :param last_state: should be True if the user was busy due to "stay on" on the last update. In this case, we leave
    the light on until the user sets it back to "automatic".
    """
    if queue.empty() and last_state:
        return True

    if not queue.empty():
        stay_on = queue.get()
        queue.task_done()
        if stay_on:
            logger.info('Busy due to manual activation')
            return True

    return False


def keep_checking_if_busy() -> None:
    last_keypress_count: typing.Optional[int] = None
    light_is_on: bool = False
    busy_from_ui: bool = False

    # Make sure the busy light is off initially
    set_light_state(power_on=False)

    # Main loop. It's an infinite loop since we run it as a daemon.
    while True:
        busy_from_ui = is_busy_from_ui(busy_from_ui)
        busy_from_zoom = is_busy_from_zoom()
        busy_from_keypresses, last_keypress_count = is_busy_from_keypresses(last_keypress_count)

        busy = busy_from_ui or busy_from_zoom or busy_from_keypresses

        # turn the light on or off if needed
        if busy and not light_is_on:
            set_light_state(power_on=True)
            light_is_on = True
        elif not busy and light_is_on:
            set_light_state(power_on=False)
            light_is_on = False

        # wait between updates
        time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    # Establish queue so that the UI can send messages to the background job
    queue = Queue()

    # Start background job to keep checking if we're busy
    thread = threading.Thread(target=keep_checking_if_busy, daemon=True).start()

    # Start the UI to allow user to manually set busy status
    OfficeBusyStatusBarUI().run()
