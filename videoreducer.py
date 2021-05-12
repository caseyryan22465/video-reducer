import subprocess, atexit, threading
import os, sys, signal, argparse, time
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

            elif(self.lastInput == "?"):
                print("type p to list progress, t to list elapsed time, l to list current files, exit to shutdown the program, and ? to see this menu again")

            time.sleep(0.1)
        return

    def stop(self):
        self.alive = False


def main():
    parser = argparse.ArgumentParser(description="Batch-reduce filesize of video files in directory with ffmpeg")
    parser.add_argument('path', type=str, metavar="\"Path/To/Videos\"", help="Directory to read files from")
    parser.add_argument('-p', '--preset', type=str, dest="preset", default="fast", help="FFmpeg encoding speed preset")
    parser.add_argument('-n', '--number_processes', type=int, default=5, dest="pmax", help="Number of FFmpeg processes allowed to run concurrently")
    parser.add_argument('--hevc', default=False, action='store_true', help="Encode to HEVC codec?")
    parser.add_argument('--hw', default=False, action='store_true', help="Hardware Encoding enabled (AMD only)?")
    parser.add_argument('-v','--verbosity', type=int, default=1, choices=range(0,3), help="Verbosity of output, 0 = silent, 1 = normal, 2 = verbose")
    args = parser.parse_args()
    global startReduceTime
    startReduceTime = time.time()

    if(os.path.isdir(args.path)):
        if(args.verbosity > 0):
            print("Beginning at " + time.strftime("%H:%M:%S", time.localtime()))
        statuses = reduceDir(args.path, args.hevc, args.preset, args.pmax, args.hw, args.verbosity)
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



def reduceDir(path, hevc, preset, pmax, hw, ol):
    #set process priority to low so subprocess ffmpeg processes start as low.
    psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)

    global total, completed
    codes = []
    total = 0
    completed = 0

    atexit.register(cleanup, ol)

    #launch input handler thread
    inputThread = inputHandlerThread()
    threads.append(inputThread)
    inputThread.start()
    if(ol > 0):
        print("type p to list progress, t to list elapsed time, l to list current files, exit to shutdown the program, and ? to see this menu again")
    
    for file in os.listdir(path):
        if(file.endswith(".mp4")):
                total += 1
    for file in os.listdir(path):#beginning actual utility
            if(exitFlag):
                sys.exit(1)
            if(file.endswith(".mp4")):
                if(ol > 1):
                    print("Beginning " + file)
                #ffmpeg command construction
                outLevel = 'error'
                outputLevel = ['-loglevel', outLevel]
                inputArgs = ['-i', os.path.abspath(os.path.join(path, file))]
                codecArgs = ['-c:v']
                if(hw):
                    if(hevc):
                        codecArgs.append('hevc_amf')
                    else:
                        codecArgs.append('h264_amf')
                else:
                    if(hevc):
                        codecArgs.extend(['libx265','-preset', preset, '-x265-params', 'log-level=error'])
                    else:
                        codecArgs.extend(['libx264', '-preset', preset])
                codecArgs.extend(['-c:a', 'copy'])
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
                        completed += 1
                        if(ol > 1):
                            print(p[0] + " exited after " + str(time.time() - p[2])[:-13] + 's')
                        if(ol > 0):
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
                completed += 1
                if(ol > 1):
                    print(p[0] + " exited after " + str(time.time() - p[2])[:-13] + 's')
                if(ol > 0):
                    print(str(completed) + "/" + str(total) + " complete")
                processes.remove(p)
        time.sleep(.1)
    return codes


def cleanup(ol=1):
    remain = len(processes)
    if(remain > 0):
        closed = 0
        if(ol > 0):
            print("interrupting ffmpeg subprocesses")
        for p in processes:
            if(p[1].poll() == None):
                p[1].terminate()
                p[1].wait()
            closed += 1
            if(ol > 0):
                print("%i/%i interrupted (name: %s)" % (closed, remain, p[0]))
    for t in threads:
        if(t.is_alive()):
            if(ol > 0):
                print("thread " + t.name + " alive, stopping and joining")
            t.stop()
            t.join()
    return

if(__name__ == "__main__"):
    main()
