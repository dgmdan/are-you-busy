from queue import Queue
import logging
import os
import threading
import time

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
    def __init__(self):
        super().__init__("Busy Sign")
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
        # Turn the light off when exiting
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


def keep_checking_if_busy():
    # Initialize variables
    last_keypress_count: int = None
    light_is_on: bool = False
    busy_from_ui: bool = False

    # Make sure the busy light is off initially
    set_light_state(power_on=False)

    # Main loop. It's an infinite loop since we run it as a daemon.
    while True:
        busy = False

        # check if busy due to keypresses
        keypress_count = CGEventSourceCounterForEventType(kCGEventSourceStateCombinedSessionState,
                                                          kCGKeyboardEventKeyboardType)
        if last_keypress_count:
            keypress_diff = keypress_count - last_keypress_count
            if keypress_diff >= MIN_NEW_KEYPRESS_COUNT:
                logger.info(f'Busy due to keypresses ({keypress_diff} new keypresses)')
                busy = True
        last_keypress_count = keypress_count

        # check if busy due to zoom being open
        zoom_is_running = 'zoom.us' in (p.info['name'] for p in psutil.process_iter(['name']))
        if zoom_is_running:
            logger.info('Busy due to running Zoom application')
            busy = True

        # check if busy due to manual activation
        if not queue.empty():
            busy_from_ui = queue.get()
            queue.task_done()
        if busy_from_ui:
            busy = True
            logger.info('Busy due to manual activation')

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
