#!/usr/bin/env python
from __future__ import print_function, division, absolute_import
import argparse, os, threading, subprocess, sys, StringIO, time
pjoin = os.path.join

__version__ = 0.1

def parse_args():
    parser = argparse.ArgumentParser(description="A simple script to help run a benchmark")
    parser.add_argument('--precommand', type=str, help="A command to run before the benchmark starts")
    parser.add_argument('--command', type=str, required=True, nargs=argparse.REMAINDER, help="The benchmark command to run")
    parser.add_argument('--results', type=str, required=True, help="The directory in which to store the results")
    parser.add_argument('--timeformat', type=str, default="[%c] <%s> ", help="The timeformat to append to each line")
    parser.add_argument('--version', action='version', version='%(prog)s (version {0})'.format(__version__))
    parser.add_argument('--interval', type=int, default=15, help="Time interval for collecting system data")

    return parser.parse_args()

def getargs():
    args = parse_args()
    args.results = pjoin(os.getcwd(), args.results)
    args.command = " ".join(args.command)
    return args

class Runner(threading.Thread):
    def __init__(self, command, filename, timeformat, echo=True):
        super(Runner, self).__init__()

        self.command = command
        self.filename = filename
        self.file = open(filename, "w")
        self.timeformat = timeformat
        self.echo = echo
        self.active = True

    def raw_write(self, data):
        self.file.write(data)
        if self.echo:
            sys.stdout.write(data)
            sys.stdout.flush()

    def stopsignal(self):
        self.active = False

    def write(self, data):
        prefix = time.strftime(self.timeformat)
        self.raw_write(prefix + data)

    def run(self):
        proc = subprocess.Popen(self.command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        text = "-"
        while (proc.poll() is None or text != "") and self.active:
            text = proc.stdout.readline()
            self.write(text)
        self.raw_write("\n")
        self.file.close()

        if not self.active: proc.kill()

class Collector:
    def __init__(self, interval, timeformat):
        self.interval = interval
        self.timeformat = timeformat

        self.measurables = []
        self.cmd = "while true; do {c}; sleep {i}; done"

    def add(self, command, filename):
        self.measurables.append(Runner(self.cmd.format(c=command, i=self.interval), filename, timeformat=self.timeformat, echo=False))

    def start(self):
        for m in self.measurables:
            m.start()

    def stop(self):
        for m in self.measurables:
            m.stopsignal()

        for m in self.measurables:
            m.join()

def quickrun(command, filename):
    Runner(command, filename, timeformat="", echo=False).run()

def main():
    args = getargs()

    if os.path.exists(args.results):
        print("{0} already exists - will not overwrite data!".format(args.results))
        sys.exit(1)

    os.mkdir(args.results)
    quickrun("hostname", pjoin(args.results, "hostname"))
    quickrun("cat /proc/cpuinfo", pjoin(args.results, "cpuinfo"))
    quickrun("uname -a", pjoin(args.results, "kernel"))
    quickrun("env", pjoin(args.results, "env"))

    if args.precommand:
        quickrun(args.precommand, pjoin(args.results, "precommand"))

    with open(pjoin(args.results, "command"), "w") as f:
        f.write(" ".join(sys.argv) + "\n")

    collector = Collector(args.interval, args.timeformat)
    collector.add("sensors", pjoin(args.results, "sensors"))
    collector.add("free -m", pjoin(args.results, "memory"))
    collector.start()

    cmd = Runner(args.command, pjoin(args.results, "output"), timeformat=args.timeformat)
    cmd.start()
    cmd.join()

    collector.stop()
if __name__ == "__main__":
    main()
