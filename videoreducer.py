import subprocess
import os, sys, getopt, time
import psutil

#https://stackoverflow.com/questions/9319317/quick-and-easy-file-dialog-in-python
#add gui and make it a real not command line project?

def main():
    args = sys.argv[1:]

    path = os.path.join(args[0])
    preset = args[1]
    if(len(args) == 3):
        pmax = int(args[2])
    else:
        pmax = 5
    hevc = True

    startReduceTime = time.time()

    if(os.path.isdir(path)):
        print("Beginning at " + time.strftime("%H:%M:%S", time.localtime()))
        statuses = reduceDir(path, True, preset, pmax)
    else:
        print("Invalid directory")
        return -1
    print(statuses)
    print("Finished " + str(len(statuses)) + " reductions in " + str(time.time()-startReduceTime)+ "s")
    
def reduceDir(path, hevc=True, preset='fast', pmax=5):
    #https://stackoverflow.com/questions/46849574/start-process-with-low-priority-popen
    #set process priority to low so subprocess ffmpeg processes start as low.
    psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)

    processes = []
    codes = []
    hw = False
    for file in os.listdir(path):
            if(file.endswith(".mp4")):
                #start = time.strftime("%H:%M:%S" ,time.localtime())
                #print("starting conversion for: " + file + ", time started: " + start)
                print("Beginning " + file)
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
                processes.append([file, subprocess.Popen(argslist), time.time()])

                #had lines 65-69 up here too to not only check for when len(p) > pmax, but all the time. However I don't know if checking all processes for finish every time a new one is created is useful or cheaper than just waiting til needed.

            #could use multithreading to constantly check for finished processes, only checking when processes>pmax might be wasteful/bottleneck
            while(len(processes) >= pmax):
                for p in processes:
                    if(p[1].poll() == 0):
                        codes.append(p[1].returncode)
                        print(p[0] + " exited after " + str(time.time() - p[2])[:-13] + 's')
                        processes.remove(p)
                #reduce busy waiting?
                time.sleep(.1)

    #program gets here very early on. wasteful
    while(len(processes) > 0):
        for p in processes:
            if(p[1].poll() == 0):
                codes.append(p[1].returncode)
                print(p[0] + " exited after " + str(time.time() - p[2])[:-13] + 's')
                processes.remove(p)
        time.sleep(.1)
    return codes

#def reduceVideo(filePath, outName, hevc = True, preset='slow'):
if __name__ == "__main__":
    main()
