# Copyright 2021 - 2022, Bill Kennedy (https://github.com/rbbrdckybk/ai-art-generator)
# SPDX-License-Identifier: MIT

import threading
import time
import datetime
import shlex
import subprocess
import sys
import unicodedata
import re
import random
import os
import platform
import signal
import webbrowser
import argparse
import scripts.utils as utils
from os.path import exists
from datetime import datetime as dt
from datetime import date
from pathlib import Path
from collections import deque
from PIL.PngImagePlugin import PngImageFile, PngInfo
from torch.cuda import get_device_name
from scripts.server import ArtServer

# environment setup
cwd = os.getcwd()

if sys.platform == "win32" or os.name == 'nt':
    import keyboard
    os.environ['PYTHONPATH'] = os.pathsep + (cwd + "\latent-diffusion") + os.pathsep + (cwd + "\\taming-transformers") + os.pathsep + (cwd + "\CLIP")
else:
    os.environ['PYTHONPATH'] = os.pathsep + (cwd + "/latent-diffusion") + os.pathsep + (cwd + "/taming-transformers") + os.pathsep + (cwd + "/CLIP")

# Prevent threads from printing at same time.
print_lock = threading.Lock()


# worker thread executes specified shell command
class Worker(threading.Thread):
    def __init__(self, command, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.command = command
        self.callback = callback

        # grab the worker info from the args
        self.worker = args[0]

        # grab the output buffer
        self.output_buffer = None
        if len(args) > 1:
            self.output_buffer = args[1]

    def run(self):
        self.print("starting job #" + str(self.worker['jobs_done']+1) + ":")
        self.print("command: " + self.command)

        start_time = time.time()
        self.worker['job_start_time'] = start_time
        self.worker['job_prompt_info'] = self.command

        work_time = round(random.uniform(1, 5), 2)
        time.sleep(work_time)
        exec_time = time.time() - start_time

        self.print("finished job #" + str(self.worker['jobs_done']+1) + " in " + str(round(exec_time, 2)) + " seconds.")
        self.callback(self.worker)


    def print(self, text):
        out_txt = "[" + self.worker['id'] + "] >>> " + text
        with print_lock:
            print(out_txt)

        # also write to buffer for webserver use
        if self.output_buffer != None:
            self.output_buffer.append(out_txt + '\n')


# controller manages worker thread(s) and user input
# TODO change worker_idle to array of bools to manage multiple threads/gpus
class Controller:
    def __init__(self, config_file):

        self.config_file = config_file
        self.config = {}
        self.prompt_file = ""
        self.output_buffer = deque([], maxlen=200)
        self.work_queue = deque()
        self.workers = []
        self.work_done = False
        self.is_paused = False
        self.total_jobs_done = 0
        self.repeat_jobs = False
        self.server = None
        self.server_startup_time = time.time()

        signal.signal(signal.SIGINT, self.sigterm_handler)
        signal.signal(signal.SIGBREAK, self.sigterm_handler)
        signal.signal(signal.SIGTERM, self.sigterm_handler)

        # read config options
        self.init_config()

        # start the webserver if enabled
        if self.config.get('webserver_use'):
            x = threading.Thread(target=self.start_server, args=(), daemon=True)
            x.start()

        worker_list = []
        worker_list.append("cuda:0")
        worker_list.append("cuda:1")
        worker_list.append("cuda:2")
        worker_list.append("cpu")

        self.init_workers(worker_list)
        self.init_work_queue()


    # reads the config file
    def init_config(self):
        # set defaults
        self.config = {
            'prompts_location' : 'prompts',
            'output_location' : 'output',
            'webserver_use' : True,
            'webserver_open_browser' : True,
            'webserver_console_log' : False
        }

        file = utils.TextFile(self.config_file)
        if file.lines_remaining() > 0:
            self.print("reading configuration from " + self.config_file + "...")
            while file.lines_remaining() > 0:
                line = file.next_line()

                # update config values for found directives
                if '=' in line:
                    line = line.split('=', 1)
                    command = line[0].lower().strip()
                    value = line[1].strip()

                    if command == 'prompts_location':
                        if value != '':
                            self.config.update({'prompts_location' : value})

                    elif command == 'output_location':
                        if value != '':
                            self.config.update({'output_location' : value})

                    elif command == 'webserver_use':
                        if value == 'yes' or value == 'no':
                            if value == 'yes':
                                self.config.update({'webserver_use' : True})
                            else:
                                self.config.update({'webserver_use' : False})

                    elif command == 'webserver_open_browser':
                        if value == 'yes' or value == 'no':
                            if value == 'yes':
                                self.config.update({'webserver_open_browser' : True})
                            else:
                                self.config.update({'webserver_open_browser' : False})

                    elif command == 'webserver_console_log':
                        if value == 'yes' or value == 'no':
                            if value == 'yes':
                                self.config.update({'webserver_console_log' : True})
                            else:
                                self.config.update({'webserver_console_log' : False})

                    else:
                        self.print("warning: config file command not recognized: " + command.upper() + " (it will be ignored)!")


        else:
            self.print("configuration file '" + self.config_file + "' doesn't exist; using defaults...")


    # starts the webserver
    def start_server(self):
        self.print("starting webserver (http://localhost:8080/) as a background process...")
        if self.config.get('webserver_open_browser'):
            webbrowser.open('http://localhost:8080/')
        self.server = ArtServer()
        self.server.start(self)


    # handle graceful cleanup here
    def sigterm_handler(self, signal, frame):
        # save the state here or do whatever you want
        self.print('********** Exiting; handling clean up ***************')
        self.shutdown()
        sys.exit(0)


    # resizes the output_buffer
    def resize_buffer(self, new_length):
        self.output_buffer = deque([], maxlen=new_length)


    def pause(self):
        if not self.is_paused:
            self.is_paused = True
            self.print("Pause requested; workers will finish current work and then wait...")


    def unpause(self):
        if self.is_paused:
            self.is_paused = False
            self.print("Un-pausing; workers will resume working...")


    def shutdown(self):
        self.print("Server shutdown requested; cleaning up and shutting down...")
        if self.server != None:
            # stop the webserver if it's running
            self.server.stop()
        self.is_paused = True
        self.work_done = True


    # build a list of gpu workers
    def init_workers(self, worker_list):
        for worker in worker_list:
            worker = worker.lower().strip()
            name = ''
            if ':' in worker:
                if worker.split(':' ,1)[0] == 'cuda':
                    try:
                        name = get_device_name(worker)
                    except AssertionError:
                        self.print("ERROR: unable to find device '" + worker + "'; removing it as a potential worker...")
                        name = "Dummy Test Device"
                        time.sleep(1.5)
            elif worker == 'cpu':
                name = platform.processor()
            else:
                self.print("ERROR: unrecognized device format: '" + worker + "'; removing it as a potential worker...")
                time.sleep(1.5)

            # if we're able to see the device, add it to the worker queue
            # TODO uncomment
            #if name != '':
            self.workers.append({'id': worker, \
                'name': name, \
                'jobs_done': 0, \
                'job_prompt_info': '', \
                'job_start_time': float(0), \
                'idle': True})

        for worker in self.workers:
            self.print("initialized worker '" + worker["id"] + "': " + worker["name"])


    # returns the first idle gpu worker if there is one, otherwise returns None
    def get_idle_gpu_worker(self):
        for worker in self.workers:
            if ':' in worker["id"]:
                if worker["id"].split(':' ,1)[0] == 'cuda':
                    # this is a gpu worker
                    if worker["idle"]:
                        # worker is idle, return it
                        return worker

        # none of the gpu workers are idle
        return None


    # returns the current number of working workers
    def num_workers_working(self):
        working = 0
        for worker in self.workers:
            if not worker["idle"]:
                working += 1
        return working


    # build a work queue with the specified prompt and style files
    def init_work_queue(self):
        for i in range(20):
            work = "Test work item #" + str(i+1)
            self.work_queue.append(work)

        self.print("queued " + str(len(self.work_queue)) + " work items.")

    # start a new worker thread
    def do_work(self, worker, command):
        worker['idle'] = False
        thread = Worker(command, self.work_done_callback, worker, self.output_buffer)
        thread.start()


    # callback for worker threads when finished
    def work_done_callback(self, *args):
        self.total_jobs_done += 1
        # args[0] contains worker data; set this worker back to idle
        args[0]['idle'] = True
        args[0]['jobs_done'] += 1
        args[0]['job_start_time'] = 0
        args[0]['job_prompt_info'] = ''


    # loads a new prompt file
    # note that new_file is an absolute path reference
    def new_prompt_file(self, new_file):

        # TODO validate prompt file
        # create work queue
        # handle both combination/random prompt files

        self.prompt_file = new_file


    # for debugging; prints a report of current worker status
    def print_worker_report(self):
        i = 0
        self.print("*** Worker Report ***")
        for worker in self.workers:
            i += 1
            self.print("Worker #" + str(i) + ":")
            for k, v in worker.items():
                if isinstance(v, str):
                    self.print("   " + k + ": '" + str(v) + "'")
                else:
                    self.print("   " + k + ": " + str(v))

    def print(self, text):
        out_txt = "[controller] >>> " + text
        with print_lock:
            print(out_txt)
        # also write to buffer for webserver use
        self.output_buffer.append(out_txt + '\n')


# entry point
if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        type=str,
        nargs="?",
        default="config.txt",
        help="the server configuration file"
    )

    opt = parser.parse_args()

    control = Controller(opt.config)

    # main work loop
    while not control.work_done:
        # check for idle workers
        worker = control.get_idle_gpu_worker()
        if worker != None:
            # worker is idle, start some work
            if not control.is_paused:
                if len(control.work_queue) > 0:
                    # get a new prompt or setting directive from the queue
                    new_work = control.work_queue.popleft()
                    control.do_work(worker, new_work)
                else:
                    if not control.repeat_jobs:
                        control.is_paused = True
                        # no more jobs, wait for all workers to finish
                        control.print('No more work in queue; waiting for all workers to finish...')
                        while control.num_workers_working() > 0:
                            time.sleep(.01)
                        control.print('All work done; pausing server - add some more work via the control panel!')
                    else:
                        # flag to repeat work enabled, re-load work queue
                        control.init_work_queue()

        else:
            time.sleep(.01)

    print('\nShutting down...')
    if control and control.total_jobs_done > 0:
        print("\nTotal jobs done: " + str(control.total_jobs_done))
        #control.print_worker_report()

    exit()
