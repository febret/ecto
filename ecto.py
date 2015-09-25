#-------------------------------------------------------------------------------
# setup mission control and porthole
from omega import *
import porthole
import sys

missionControlPort = getMissionControlServer().getPort()
webServerPort = 5005

# Launch the web server
porthole.initialize(webServerPort, './index.html')
webServer = porthole.getService()

#-------------------------------------------------------------------------------
# choose what services to launch here
#import monitor
import launcher
