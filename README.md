# hfbot
hfbot is an automated cryptocurrency trader built with Python.

## Requirements
hfbot requires Python 3.11.x in order to run.

### Step 1: Install bot typing `pip install` in editable state

Install top level package **hfbot** using `pip`. The trick is to use the `-e` flag when doing the install. This way it is installed in an editable state, and all the edits made to the `.py` files will be automatically included in the installed package.

In the bot root directory, run:

	$ pip install -e .

### Step 2: Create a virtual environment

If you are familiar with virtual environments, activate one, and skip to the next step. Usage of virtual environments are not absolutely required, but they will really help you out in the long run.

Linux, macOS:

	$ pip install virtualenv
	$ virtualenv -p python venv
	$ source venv/bin/activate

Windows:

	$ pip install virtualenv
	$ virtualenv -p python venv
	$ .\venv\Scripts\activate


### Step 3: Run the bot

Linux, macOS:

	$ python ./bin/bot

Windows:

Create start.bat file in the bot root directory with the following line:

    python ./bin/bot
    
Run start.bat

### Quick installation and start

Linux, macOS:

	$ make install
	$ bot
	
#### Other's commands
+ `make install` - installing the bot.
+ `make unistall` - uninstalling the bot.
+ `make reinstall` - reinstalling the bot.
+ `make clean` - removing dist, build and egg-info files from this project.


#### Uptodate clock
The clock must be accurate, syncronized to a NTP server very frequently to avoid problems with communication to the exchanges.

![Time synchronization](./.gitlab/time_synchronization.png "Time synchronization")

#### Software requirements
+ Python 3.11.x
+ pip
+ tkinter
+ virtualenv (Recommended)
+ Docker (Recommended)
ccxt
asyncio
numpy
pandas
pytoml
cfscrape
psutil