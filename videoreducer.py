import subprocess
import os, sys, getopt, time

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
        statuses = reduceDir(path, True, 'fast', pmax)
    else:
        print("Need directory")
        return -1
    print(statuses)
    print("Finished " + str(len(statuses)) + " reductions in " + str(time.time()-startReduceTime)+ "s")
    
def reduceDir(path, hevc=True, preset='fast', pmax=5):
    processes = []
    codes = []
    for file in os.listdir(path):
            if(file.endswith(".mp4")):
                #start = time.strftime("%H:%M:%S" ,time.localtime())
                #print("starting conversion for: " + file + ", time started: " + start)
                print("Beginning " + file)
                processes.append([file, subprocess.Popen(['ffmpeg','-y','-hide_banner', '-loglevel', 'error', '-i', os.path.abspath(os.path.join(path, file)), '-c:v','libx265', '-x265-params', 'log-level=error', '-preset', preset, '-c:a', 'copy', os.path.abspath(os.path.join(path + '\out', file[0:file.rfind('.')])) + '-reduced_' + preset + '.mp4'])])
    
            while(len(processes) >= pmax):
                #waits for the shortest one every time. should make object that instead stores name, path, popen, time started, and size. Wait strategically (some function of time started and size)
                for p in processes:
                    if(p[1].poll() == 0):
                        codes.append(p[1].returncode)
                        print("conversion " + p[0] + " exited")
                        processes.remove(p)
    
                minSize = os.path.getsize(path + '\\' + processes[0][0])
                waitTarget = processes[0]
                for p in processes:
                    if(os.path.getsize(path + '\\' + p[0]) < minSize):
                        waitTarget = p
                #print(str(len(processes)) + " processes greater than limit "+ str(pmax) + ", waiting for " + p[0] + " to finish")
                #try:
                #print(waitTarget)
                codes.append(waitTarget[1].wait())
                #except:
                print("finished " + waitTarget[0])
                processes.remove(waitTarget)
                #print(str(len(processes)) + " processes active")
                
    for p in processes:
        codes.append(p[1].wait())
        print("finished " + p[0])

    return codes

#def reduceVideo(filePath, outName, hevc = True, preset='slow'):
if __name__ == "__main__":
    main()
