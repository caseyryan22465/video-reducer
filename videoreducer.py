import subprocess, atexit, threading
import os, sys, signal, getopt, time
import psutil

#on keyboard interrupt, dont print trace
signal.signal(signal.SIGINT, lambda x, y: sys.exit(1))

processes = []
threads = []
exitFlag = False
class inputHandlerThread(threading.Thread):
    def __init__(self):
        super(inputHandlerThread, self).__init__()
        self.alive = True
        self.lastInput = None

    def run(self):
        global exitFlag
        while(self.alive):
            try:
                self.lastInput = input()
            except (EOFError):
                exitFlag = True
                self.alive = False
            
            #list of user inputs
            if(self.lastInput == 'l'):#list filenames
                print(str([p[0] for p in processes]))

            elif(self.lastInput == 'r'):#list process returncodes
                print(str([p[1].returncode for p in processes]))

            elif(self.lastInput == "exit"):#exit program without keyboardinterrupt
                exitFlag = True
                self.alive = False

            elif(self.lastInput == "th"):#print thread details for debugging purposes
                global threads
                print(threads)

            elif(self.lastInput == "p"):#print progress
                print(str(completed) + "/" + str(total) +" files complete")
           
            elif(self.lastInput == "t"):
                print(str(time.time()-startReduceTime) +"s since start")
            
            time.sleep(0.1)
        return

    def stop(self):
        self.alive = False


def main():
    atexit.register(cleanup)

    args = sys.argv[1:]
    #py file.py "path to folder" "fast" "5"
    path = os.path.join(args[0])
    preset = args[1]
    if(len(args) == 3):
        pmax = int(args[2])
    else:
        pmax = 5
    hevc = True
    global startReduceTime
    startReduceTime = time.time()

    if(os.path.isdir(path)):
        print("Beginning at " + time.strftime("%H:%M:%S", time.localtime()))
        statuses = reduceDir(path, True, preset, pmax)
    else:
        print("Invalid directory")
        return -1
    errs = []
    for s in statuses:
        if(s[0] != 0):
            errs.append(s)
    if(len(errs) > 0):
        print("Errors: " + str(errs))
    
    print("Finished " + str(len(statuses)) + " reductions in " + str(time.time()-startReduceTime)+ "s")



def reduceDir(path, hevc=True, preset='fast', pmax=5, hw = False):
    #set process priority to low so subprocess ffmpeg processes start as low.
    psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)

    global total, completed
    codes = []
    total = 0
    completed = 0

    #launch input handler thread
    inputThread = inputHandlerThread()
    threads.append(inputThread)
    inputThread.start()

    
    for file in os.listdir(path):
        if(file.endswith(".mp4")):
                total += 1
    for file in os.listdir(path):#beginning actual utility
            if(exitFlag):
                sys.exit(1)
            if(file.endswith(".mp4")):
                #print("Beginning " + file)
                #ffmpeg command construction
                outLevel = 'error'
                outputLevel = ['-loglevel', outLevel]
                inputArgs = ['-i', os.path.abspath(os.path.join(path, file))]
                codecArgs = ['-c:v', 'hevc_amf', '-c:a', 'copy'] if (hevc and hw) else ['-c:v', 'libx265', '-preset', preset, '-x265-params', 'log-level=error', '-c:a', 'copy']
                outputArgs = [os.path.abspath(os.path.join(path + '\out', file[0:file.rfind('.')])) + '-reduced_' + preset + '.mp4']
                argslist = [
                    'ffmpeg',
                    '-y',
                    '-hide_banner',
                    *outputLevel,
                    *inputArgs,
                    *codecArgs,
                    *outputArgs
                    ]
                
                processes.append([file, subprocess.Popen(argslist, stdin=subprocess.DEVNULL), time.time()])
            else:
                #dont need to iterate over non mp4 files
                continue

            while(len(processes) >= pmax and not exitFlag):
                for p in processes:
                    if(p[1].poll() != None):
                        if(p[1].returncode != 0):
                            codes.append([p[0],p[1].returncode])
                        else:
                            codes.append([p[1].returncode])
                        print(p[0] + " exited after " + str(time.time() - p[2])[:-13] + 's')
                        completed += 1
                        print(str(completed) + "/" + str(total) + " complete")
                        processes.remove(p)
                #reduce busy waiting
                time.sleep(.1)

    while(len(processes) > 0 and not exitFlag):
        for p in processes:
            if(p[1].poll() != None):
                if(p[1].returncode != 0):
                    codes.append([p[0],p[1].returncode])
                else:
                    codes.append([p[1].returncode])
                print(p[0] + " exited after " + str(time.time() - p[2])[:-13] + 's')
                completed += 1
                print(str(completed) + "/" + str(total) + " complete")
                processes.remove(p)
        time.sleep(.1)
    return codes


def cleanup():
    remain = len(processes)
    if(remain > 0):
        closed = 0
        print("interrupting ffmpeg subprocesses")
        for p in processes:
            if(p[1].poll() == None):
                p[1].terminate()
                p[1].wait()
            closed += 1
            print("%i/%i interrupted (name: %s)" % (closed, remain, p[0]))
    print("threads: ")
    for t in threads:
        print(t)
        if(t.is_alive()):
            print("thread " + t.name + " alive, stopping and joining")
            t.stop()
            t.join()
    return

if(__name__ == "__main__"):
    main()
