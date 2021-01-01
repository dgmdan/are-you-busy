import logging
import os
import psutil
import time

from Quartz import CGEventSourceCounterForEventType, kCGEventSourceStateCombinedSessionState, kCGKeyboardEventKeyboardType
from pyvesync import VeSync


###################
# Settings

# How many new keypresses since last update are required to be considered busy?
MIN_NEW_KEYPRESS_COUNT = 80

# How often should we update to see if we're busy (in seconds)?
UPDATE_INTERVAL = 20

# VEsync credentials (WiFi power outlet)
VESYNC_EMAIL = os.environ.get('VESYNC_EMAIL')
VESYNC_PASSWORD = os.environ.get('VESYNC_PASSWORD')

###################
# Main script

logger = logging.getLogger(__name__)


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


# Initialize variables
last_keypress_count: int = None
light_is_on: bool = False

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

    # TODO: check if busy due to manual activation

    # turn the light on or off if needed
    if busy and not light_is_on:
        set_light_state(power_on=True)
        light_is_on = True
    elif not busy and light_is_on:
        set_light_state(power_on=False)
        light_is_on = False

    # wait between updates
    time.sleep(UPDATE_INTERVAL)
