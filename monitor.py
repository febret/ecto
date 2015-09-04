import porthole
import subprocess
from time import sleep
import sys

mcc = getMissionControlClient()
hostname = mcc.getName()

# Configuration
serverName = "gozer.at.northwestern.edu"

nodeNames = [
    'ray', 'peter', 'egon', 'winston', 'slimer', 'zuul', 'staypuft'
]

# update settings    
updateInterval = 1   
lastUpdateTime = 0


# This var stores data from the nodes
data = {}

# this will store the porthole service on the master node
ps = None

#-------------------------------------------------------------------------------
# master functions

# kill all monitor slaves on the cluster
def kill_slaves(nodeNames):
    from time import sleep
    for node in nodeNames:
        # find pid of process executing monitor_slave and kill it.
        cmd = "ssh -n {0} kill $(pgrep -f monitor)".format(node)
        olaunch(cmd)
        sleep(0.1)

def setup_master():
    missionControlPort = int(sys.argv[1])
    webServerPort = int(sys.argv[2])
    
    # do a cleanup, and also register kill_slaves to be called on exit.
    kill_slaves(nodeNames)
    import atexit
    atexit.register(kill_slaves, nodeNames)

    # Launch the monitor slaves
    for node in nodeNames:
        cmd = "ssh -n {0} cd {1}; {2} -c system/headless.cfg monitor.py --mc @{3}:{4} -N {5} -L off --interactive-off".format(
            node, os.getcwd(), ogetexecpath(), serverName, missionControlPort, node)
        olaunch(cmd)
        sleep(0.1)

    # Launch the web server
    global ps
    porthole.initialize(webServerPort, './index.html')
    ps = porthole.getService()

#-------------------------------------------------------------------------------
# slave functions

def getcputime():
    cpu_infos = {} 
    with open('/proc/stat') as f:
        for l in f:
            if(l.startswith('cpu')):
                cpu_line = l.split()
                cpu_line = [cpu_line[0]]+[float(i) for i in cpu_line[1:]]#type casting
                #print cpu_line
                cpu_id,user,nice,system,idle,iowait,irq,softrig,steal,guest = cpu_line

                Idle=idle+iowait
                NonIdle=user+nice+system+irq+softrig+steal

                Total=Idle+NonIdle
                cpu_infos.update({cpu_id:{'total':Total,'idle':Idle}})
    return cpu_infos

def poll_cpus():
    start = getcputime()
    sleep(updateInterval)
    stop = getcputime()

    cpu_load = []

    for cpu in start:
        Total = stop[cpu]['total']
        PrevTotal = start[cpu]['total']

        Idle = stop[cpu]['idle']
        PrevIdle = start[cpu]['idle']
        CPU_Percentage=((Total-PrevTotal)-(Idle-PrevIdle))/(Total-PrevTotal)*100
        cpu_load.append((cpu, CPU_Percentage))
    return cpu_load

def poll_gpus():
    out = subprocess.check_output(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv'])
    res = []
    for l in out.splitlines():
        if(not l.startswith('utilization')):
            vals = l.split()
            res.append(int(vals[0]))
    return res

#-------------------------------------------------------------------------------
# update functions

# master update function: send data to webpages
def update_master(frame, time, dt):
    global lastUpdateTime
    if(time - lastUpdateTime > updateInterval):
        lastUpdateTime = time 
        ps.broadcastjs("data = {0}; update()".format(data), '')

# slave update function: poll usage data and send it back to baster
def update_slave(frame, time, dt):
    global lastUpdateTime
    if(time - lastUpdateTime > updateInterval):
        lastUpdateTime = time 
        cpuUsage = poll_cpus()  
        gpuUsage = poll_gpus()
        #print hostname + " " + str(cpuUsage)
        mcc.postCommand('@server: data["{0}"] = [{1}, {2}]'.format(hostname, cpuUsage, gpuUsage))
        
if(hostname == "server"):
    setup_master()
    setUpdateFunction(update_master)
else:
    setUpdateFunction(update_slave)