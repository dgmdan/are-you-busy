Are You Busy?
=============

---------------

*Are You Busy?* is a Python script that automates a "busy" or "do not disturb" light that you can put outside
your home office.

You can use this to help your family or roommates decide if it's a good time to come in and chat, without having 
to interrupt your work when you're focused.

The script continuously monitors to see if any of these conditions are met:

- You recently typed a lot of keystrokes. This is intended to be an indicator that you're focused.
- The Zoom application is currently open.
- You have manually requested the "busy" light to stay on.

If any of those conditions are met, the light turns on.  Otherwise, it turns off. Pretty simple!


Requirements
------------

- Python 3.8
- macOS 10.4+
- VeSync Smart Plug by Etekcity
- An iOS or Android phone with the VeSync app to configure the smart plug
- A light to use as your "busy" light (with a common wall plug)

Installation
------------

1. Clone the project


    git clone git@github.com:dgmdan/are-you-busy.git

2. Create a venv


    python3 -m venv ~/.venv/are-you-busy

3. Activate the venv and install dependencies


    source ~/.venv/are-you-busy/bin/activate
    cd ~/are-you-busy
    pip install -r requirements.txt

4. Set up the VeSync smart plug device:
   
* Download the VeSync app on your iOS or Android phone
* Create a user account on the app
* Use the app to scan the QR code on your smart plug 
* Follow the app's prompts to connect the smart plug to your WiFi network

5. Use Automator.app in macOS to create a new bash script application.
   
Contents of Bash script:

    killall ScriptMonitor
    export VESYNC_EMAIL='...'
    export VESYNC_PASSWORD='...'
    source ~/.venv/are-you-busy/bin/activate
    cd ~/are-you-busy
    python main.py

Replace `...` with your VeSync credentials. Replace paths of the venv and project to the actual paths on your machine.

6. Add the bash script application to your macOS user's Login Items (to auto-start the script on login)


Usage
-----

* After logging into macOS, you should see `Busy Sign` on your status bar. This means the script is running.
* Click `Busy Sign` >  `Stay On` to keep the busy light indefinitely.
* Click `Busy Sign` > `Auto` to allow the busy light to decide its on/off status automatically. 
* Click `Busy Sign` > `Quit` to turn the light off and quit. 


License
-------

Distributed under the GNU GPLv3 License. See [LICENSE](LICENSE) for more information.


Acknowledgements
----------------

* [CGEventSourceCounterForEventType Function in macOS](https://developer.apple.com/documentation/coregraphics/1408794-cgeventsourcecounterforeventtype)
* [pyobjc-framework-Quartz Package](https://pypi.org/project/pyobjc-framework-Quartz/)
* [pyvesync Package](https://pypi.org/project/pyvesync/)