# Copyright 2021 - 2022, Bill Kennedy (https://github.com/rbbrdckybk/dream-factory)
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
import shutil
import base64
import json
from PIL import Image
from io import BytesIO
import scripts.utils as utils
from os.path import exists
from datetime import datetime as dt
from datetime import date
from pathlib import Path
from collections import deque
from PIL.PngImagePlugin import PngImageFile, PngInfo
from torch.cuda import get_device_name, device_count
from scripts.server import ArtServer
from scripts.sdi import SDI

# environment setup
cwd = os.getcwd()
python_path = ""
env_paths = [ \
    os.path.join(cwd, 'taming-transformers'),
    os.path.join(cwd, 'CLIP')
]

for path in env_paths:
    python_path += os.pathsep + path
#os.environ['PYTHONPATH'] = python_path


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
        if not int(self.command.get('seed')) > 0:
            self.command['seed'] = -1

        # if this is a random prompt, settle on random values
        if self.command.get('mode') == 'random':
            self.command['scale'] = round(random.uniform(float(self.command.get('min_scale')), float(self.command.get('max_scale'))), 1)
            self.command['strength'] = round(random.uniform(float(self.command.get('min_strength')), float(self.command.get('max_strength'))), 2)
            if self.command.get('random_input_image_dir') != "":
                self.command['input_image'] = utils.InputManager(self.command.get('random_input_image_dir')).pick_random()

        # check if a model change is needed
        if self.command.get('ckpt_file') != '' and (self.command.get('ckpt_file') != self.worker['sdi_instance'].model_loaded):
            self.worker['sdi_instance'].load_model(self.command.get('ckpt_file'))
            while self.worker['sdi_instance'].options_change_in_progress:
                # wait for model change to complete
                time.sleep(0.25)
        elif self.command.get('ckpt_file') == '':
            # revert to default config.txt model if necessary
            if control.config.get('ckpt_file') != '' and control.default_model_validated and (control.config.get('ckpt_file') != self.worker['sdi_instance'].model_loaded):
                self.worker['sdi_instance'].load_model(control.config.get('ckpt_file'))
                while self.worker['sdi_instance'].options_change_in_progress:
                    # wait for model change to complete
                    time.sleep(0.25)

        # check for auto-insertion of model trigger word
        if (control.model_trigger_words != None) and (self.command.get('auto_insert_model_trigger') != 'off'):
            # check to see if the model we're using has an associated trigger
            if control.model_trigger_words.get(self.command.get('ckpt_file')) != None:
                trigger = control.model_trigger_words.get(self.command.get('ckpt_file'))
                p = self.command.get('prompt')
                if trigger not in p:
                    # trigger word isn't in prompt, we need to add it
                    if self.command.get('auto_insert_model_trigger') == 'first_comma':
                        if ',' in p:
                            self.command['prompt'] = p.split(',', 1)[0] + ', ' + trigger + ',' + p.split(',', 1)[1]
                        else:
                            self.command['prompt'] = p + ', ' + trigger
                    elif self.command.get('auto_insert_model_trigger') == 'end':
                        self.command['prompt'] = p + ', ' + trigger
                    elif self.command.get('auto_insert_model_trigger') == 'start':
                        self.command['prompt'] = trigger + ', ' + p

        # check for wildcard replacements
        p = self.command.get('prompt')
        #print('before wildcard replace: ' + self.command['prompt'])
        for k, v in control.wildcards.items():
            key = '__' + k.lower() + '__'
            if key in p.lower():
                vcopy = v.copy()
                # this will handle multiple replacements of the same key
                while key in p.lower():
                    if len(vcopy) > 0:
                        # pick a random value & remove it from the copied list
                        x = random.randint(0, len(vcopy)-1)
                        replace = vcopy.pop(x)
                        # replace the first occurence with the chosen value
                        p = re.sub(key, replace, p, 1, flags=re.IGNORECASE)
                    else:
                        # not enough values to make all replacements, sub '' instead
                        p = re.sub(key, '', p, flags=re.IGNORECASE)
        self.command['prompt'] = p
        #print('after wildcard replace: ' + self.command['prompt'])

        command = utils.create_command(self.command, self.command.get('prompt_file'), self.worker['id'])
        self.print("starting job #" + str(self.worker['jobs_done']+1) + ": " + command)

        # parameters to pass to SD instance
        payload = {}
        if self.command.get('input_image') != '':
            #img2img
            encoded = base64.b64encode(open(self.command.get('input_image'), "rb").read())
            encodedString = str(encoded, encoding='utf-8')
            img_payload = 'data:image/png;base64,' + encodedString

            payload = {
              "init_images": [img_payload],
              "sampler_index": str(self.command.get('sampler')),
              #"resize_mode": 0,
              "denoising_strength": self.command.get('strength'),
              "prompt": str(self.command.get('prompt')),
              "seed": self.command.get('seed'),
              "batch_size": self.command.get('batch_size'),     # gpu makes this many at once
              "n_iter": self.command.get('samples'),            # number of iterations to run
              "steps": self.command.get('steps'),
              "cfg_scale": self.command.get('scale'),
              "width": self.command.get('width'),
              "height": self.command.get('height'),
              #"restore_faces": False,
              #"tiling": False,
              "negative_prompt": str(self.command.get('neg_prompt'))
            }
        else:
            # txt2img
            payload = {
              "enable_hr": self.command.get('highres_fix'),
              "denoising_strength": self.command.get('strength'),
              "sampler_index": str(self.command.get('sampler')),
              "prompt": str(self.command.get('prompt')),
              "seed": self.command.get('seed'),
              "batch_size": self.command.get('batch_size'),     # gpu makes this many at once
              "n_iter": self.command.get('samples'),            # number of iterations to run
              "steps": self.command.get('steps'),
              "cfg_scale": self.command.get('scale'),
              "width": self.command.get('width'),
              "height": self.command.get('height'),
              #"restore_faces": False,
              #"tiling": False,
              "negative_prompt": str(self.command.get('neg_prompt'))
            }

        start_time = time.time()
        self.worker['job_start_time'] = start_time
        self.worker['job_prompt_info'] = self.command

        output_dir = command.split(" --outdir ",1)[1].strip('\"')
        #output_dir = output_dir.replace("../","")

        if "cuda:" in self.worker['id']:
            gpu_id = self.worker['id'].replace('cuda:', '')
        else:
            gpu_id = self.worker['id']

        #samples_dir = os.path.join(output_dir, "gpu_" + str(gpu_id))
        samples_dir = output_dir + '/' + "gpu_" + str(gpu_id)

        #self.worker['sdi_instance'].last_job_success = True
        if control.config.get('debug_test_mode'):
            # simulate SD work
            work_time = round(random.uniform(2, 6), 2)
            time.sleep(work_time)
        else:
            # invoke SD
            #wd = cwd + os.path.sep + 'stable-diffusion'
            #subprocess.call(shlex.split(command), cwd=(wd))
            if self.command.get('input_image') != '':
                self.worker['sdi_instance'].do_img2img(payload, samples_dir)
            else:
                self.worker['sdi_instance'].do_txt2img(payload, samples_dir)
            while self.worker['sdi_instance'].busy and self.worker['sdi_instance'].isRunning:
                time.sleep(0.25)

        # upscale here if requested
        if self.worker['sdi_instance'].last_job_success and self.worker['sdi_instance'].isRunning:
            # only if we're not shutting down
            if self.command['use_upscale'] == 'yes':
                self.worker['work_state'] = 'upscaling'
                gpu_id = self.worker['id'].replace("cuda:", "")

                if control.config.get('debug_test_mode'):
                    # simulate upscaling work
                    work_time = round(random.uniform(0.5, 2), 2)
                    time.sleep(work_time)
                else:
                    new_files = os.listdir(samples_dir)
                    if len(new_files) > 0:
                        # invoke ESRGAN on entire directory
                        #utils.upscale(self.command['upscale_amount'], samples_dir, self.command['upscale_face_enh'], gpu_id)

                        # upscale each image
                        self.worker['sdi_instance'].log('upscaling generated images...')
                        for file in new_files:
                            encoded = base64.b64encode(open(os.path.join(samples_dir, file), "rb").read())
                            encodedString = str(encoded, encoding='utf-8')
                            img_payload = 'data:image/png;base64,' + encodedString
                            payload = {
                                #"resize_mode": 0,
                                #"show_extras_results": true,
                                "gfpgan_visibility": self.command['upscale_gfpgan_amount'],
                                "codeformer_visibility": self.command['upscale_codeformer_amount'],
                                #"codeformer_weight": 0,
                                "upscaling_resize": self.command['upscale_amount'],
                                #"upscaling_resize_w": 512,
                                #"upscaling_resize_h": 512,
                                #"upscaling_crop": true,
                                "upscaler_1": "ESRGAN_4x",
                                #"upscaler_2": "None",
                                #"extras_upscaler_2_visibility": 0,
                                #"upscale_first": false,
                                "image": img_payload
                            }
                            self.worker['sdi_instance'].do_upscale(payload, samples_dir)
                            while self.worker['sdi_instance'].busy and self.worker['sdi_instance'].isRunning:
                                time.sleep(0.25)


                        # remove originals if upscaled version present
                        new_files = os.listdir(samples_dir)
                        for f in new_files:
                            if (".png" in f):
                                basef = f.replace(".png", "")
                                if basef[-2:] == "_u":
                                    # this is an upscaled image, delete the original
                                    # or save it in /original if desired
                                    if exists(samples_dir + "/" + basef[:-2] + ".png"):
                                        if self.command['upscale_keep_org'] == 'yes':
                                            # move the original to /original
                                            orig_dir = output_dir + "/original"
                                            Path(orig_dir).mkdir(parents=True, exist_ok=True)
                                            os.replace(samples_dir + "/" + basef[:-2] + ".png", \
                                                orig_dir + "/" + basef[:-2] + ".png")
                                        else:
                                            os.remove(samples_dir + "/" + basef[:-2] + ".png")


        # find the new image(s) that SD created: re-name, process, and move them
        if self.worker['sdi_instance'].last_job_success and self.worker['sdi_instance'].isRunning:
            # only if we're not shutting down
            self.worker['work_state'] = "+exif data"
            if control.config.get('debug_test_mode'):
                # simulate metadata work
                work_time = round(random.uniform(1, 2), 2)
                time.sleep(work_time)
            else:
                new_files = os.listdir(samples_dir)
                nf_count = 0
                for f in new_files:
                    if (".png" in f):
                        # save just the essential prompt params to metadata
                        meta_prompt = command.split(" --prompt ",1)[1]
                        meta_prompt = meta_prompt.split(" --outdir ",1)[0]

                        if 'seed_' in f:
                            # grab seed from filename
                            # filename = seed_3542762265.png or seed_3542762265_u.png
                            actual_seed = f.replace('seed_', '')
                            actual_seed = actual_seed.replace('_u', '')
                            actual_seed = actual_seed.split('.', 1)[0]

                            # replace the seed in the command with the actual seed used
                            pleft = meta_prompt.split(" --seed ",1)[0]
                            pright = meta_prompt.split(" --seed ",1)[1].strip()
                            meta_prompt = pleft + " --seed " + actual_seed

                        upscale_text = ""
                        if self.command['use_upscale'] == 'yes':
                            upscale_text = " (upscaled "
                            upscale_text += str(self.command['upscale_amount']) + "x via ESRGAN"

                        pngImage = PngImageFile(samples_dir + "/" + f)
                        im = pngImage.convert('RGB')
                        exif = im.getexif()
                        exif[0x9286] = meta_prompt
                        exif[0x9c9c] = meta_prompt.encode('utf16')
                        exif[0x9c9d] = ('AI art' + upscale_text).encode('utf16')
                        exif[0x0131] = "https://github.com/rbbrdckybk/dream-factory"
                        newfilename = dt.now().strftime('%Y%m-%d%H-%M%S-') + str(nf_count)
                        nf_count += 1
                        im.save(output_dir + "/" + newfilename + ".jpg", exif=exif, quality=88)
                        if exists(samples_dir + "/" + f):
                            os.remove(samples_dir + "/" + f)


        self.worker['work_state'] = ""
        # remove the samples dir to flush any unfinished work
        try:
            # os.rmdir only removes empty directories
            #os.rmdir(samples_dir)
            shutil.rmtree(samples_dir)
        except OSError as e:
            pass

        exec_time = time.time() - start_time
        if self.worker['sdi_instance'].last_job_success:
            self.print("finished job #" + str(self.worker['jobs_done']+1) + " in " + str(round(exec_time, 2)) + " seconds.")
        else:
            self.print("job #" + str(self.worker['jobs_done']+1) + " failed after " + str(round(exec_time, 2)) + " seconds.")
        self.callback(self.worker)


    def print(self, text):
        out_txt = "[" + self.worker['id'] + "] >>> " + text
        with print_lock:
            print(out_txt)

        # also write to buffer for webserver use
        if self.output_buffer != None:
            self.output_buffer.append(out_txt + '\n')


# controller manages worker thread(s) and user input
class Controller:
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = {}
        self.prompt_file = ""
        self.prompt_editor_file = ""
        self.temp_path = ""
        self.prompt_manager = None
        self.input_manager = None
        self.output_buffer = deque([], maxlen=300)
        self.work_queue = deque()
        self.workers = []
        self.work_done = False
        self.is_paused = False
        self.loops = 0
        self.orig_work_queue_size = 0
        self.jobs_done = 0
        self.total_jobs_done = 0
        self.repeat_jobs = False
        self.server = None
        self.server_startup_time = time.time()
        self.shutting_down = False
        self.sdi_ports_assigned = 0
        self.sdi_sampler_request_made = False
        self.sdi_samplers = None
        self.models_filename = 'model-triggers.txt'
        self.model_trigger_words = None
        self.sdi_model_request_made = False
        self.sdi_models = None
        self.sdi_hypernetwork_request_made = False
        self.sdi_hypernetworks = None
        self.wildcards = None
        self.default_model_validated = False
        self.embeddings = []

        # read config options
        self.init_config()

        if self.config['sd_location'] == '':
            print('\nERROR: path to stable diffusion not specified in config file! ')
            print('Make sure to set \'SD_LOCATION =\' in your config.txt with the path to your Automatic1111 SD repo installation!')
            print('\nExiting...')
            exit(0)


        # start the webserver if enabled
        if self.config.get('webserver_use'):
            x = threading.Thread(target=self.start_server, args=(), daemon=True)
            x.start()
        else:
            # cherrypy would otherwise catch ctrl-break for us
            self.register_handlers()

        # create temp folder for backups/zips/etc - needs to be webserver-accessible
        self.temp_path = os.path.join('server', 'temp')
        if not os.path.exists(self.temp_path):
            os.makedirs(self.temp_path)

        if not self.config.get('debug_test_mode'):
            # initialize GPU(s)
            self.init_gpu_workers()
        else:
            # create some dummy devices for testing
            self.init_dummy_workers()

        # do an initial read of user wildcard files
        self.read_wildcards()

        # do an initial read of user embedding files
        self.read_embeddings()


    # returns the current operation mode (standard or random)
    def get_mode(self):
        if self.prompt_manager != None:
            return self.prompt_manager.config.get('mode')
        else:
            return None


    # reads user-create wildcard files into a dictionary for use with prompting
    # dict key is filename, value is list of lines in file
    def read_wildcards(self):
        self.wildcards = {}
        if self.config['wildcard_location'] != '':
            for x in os.listdir(self.config['wildcard_location']):
                if x.endswith('.txt'):
                    key = x.replace('.txt', '').strip()
                    #print(key) + ' :'
                    # read the contents of the wildcard file
                    with open(os.path.join(self.config['wildcard_location'], x)) as f:
                        lines = f.readlines()
                    # store the contents into a list
                    vals = []
                    for line in lines:
                        line = line.strip().split('#', 1)
                        line = line[0]
                        if len(line) > 0:
                            vals.append(line.replace('\n', '').strip())
                    # save the filename & contents as a dict entry
                    self.wildcards[key] = vals
        #self.print_wildcards()


    # checks for user embedding files in Auto1111 embeddings dir
    def read_embeddings(self):
        embed_dir = os.path.join(self.config['sd_location'], 'embeddings')
        if os.path.exists(embed_dir):
            for x in os.listdir(embed_dir):
                if x.endswith('.pt') or x.endswith('.bin'):
                    self.embeddings.append(x)
        self.embeddings.sort()


    # for debugging
    def print_wildcards(self):
        print('\nWildcard entries:')
        for k, v in self.wildcards.items():
            print('\n   ' + k + ' :')
            for i in v:
                print('      ' + i)
        print('\n')


    # reads the config file
    def init_config(self):
        # set defaults
        self.config = {
            'prompts_location' : 'prompts',
            'wildcard_location' : 'prompts\wildcards',
            'output_location' : 'output',
            'use_gpu_devices' : 'auto',
            'webserver_use' : True,
            'webserver_port' : 80,
            'webserver_network_accessible' : False,
            'webserver_use_authentication' : False,
            'webserver_auth_username' : 'admin',
            'webserver_auth_password' : 'password',
            'gallery_max_images' : 100,
            'gallery_refresh' : 30,
            'gallery_user_folder' : '',
            'gallery_user_folder_alias' : '',
            'gallery_current' : 'recent',
            'webserver_open_browser' : True,
            'webserver_console_log' : False,
            'debug_test_mode' : False,

            'auto_insert_model_trigger' : 'start',
            'neg_prompt' : '',
            'highres_fix' : "no",
            'width' : 512,
            'height' : 512,
            'sampler' : 'Euler',
            'steps' : 50,
            'scale' : 7.5,
            'samples' : 1,
            'use_upscale' : "no",
            'upscale_amount' : 2.0,
            'upscale_keep_org' : "no",
            'upscale_codeformer_amount' : 0.0,
            'upscale_gfpgan_amount' : 0.0,
            'ckpt_file' : "",

            'sd_location' : "",
            'sd_port' : 7861,
            'gpu_init_stagger' : 1
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

                    elif command == 'wildcard_location':
                        if value != '':
                            value = value.replace('/', os.path.sep)
                            value = value.replace('\\', os.path.sep)
                            self.config.update({'wildcard_location' : value})

                    elif command == 'output_location':
                        if value != '':
                            self.config.update({'output_location' : value})

                    elif command == 'use_gpu_devices':
                        if value != '':
                            self.config.update({'use_gpu_devices' : value})

                    elif command == 'sd_location':
                        if value != '':
                            self.config.update({'sd_location' : value})

                    elif command == 'sd_port':
                        try:
                            int(value)
                        except:
                            print("*** WARNING: specified 'SD_PORT' is not a valid number; it will be ignored!")
                        else:
                            self.config.update({'sd_port' : int(value)})

                    elif command == 'gpu_init_stagger':
                        try:
                            int(value)
                        except:
                            print("*** WARNING: specified 'GPU_INIT_STAGGER' is not a valid number; it will be ignored!")
                        else:
                            self.config.update({'gpu_init_stagger' : int(value)})

                    elif command == 'webserver_use':
                        if value == 'yes' or value == 'no':
                            if value == 'yes':
                                self.config.update({'webserver_use' : True})
                            else:
                                self.config.update({'webserver_use' : False})

                    elif command == 'webserver_port':
                        try:
                            int(value)
                        except:
                            print("*** WARNING: specified 'WEBSERVER_PORT' is not a valid number; it will be ignored!")
                        else:
                            self.config.update({'webserver_port' : int(value)})

                    elif command == 'webserver_network_accessible':
                        if value == 'yes' or value == 'no':
                            if value == 'yes':
                                self.config.update({'webserver_network_accessible' : True})
                            else:
                                self.config.update({'webserver_network_accessible' : False})

                    elif command == 'webserver_use_authentication':
                        if value == 'yes' or value == 'no':
                            if value == 'yes':
                                self.config.update({'webserver_use_authentication' : True})
                            else:
                                self.config.update({'webserver_use_authentication' : False})

                    elif command == 'webserver_auth_username':
                        if value != '':
                            self.config.update({'webserver_auth_username' : value})

                    elif command == 'webserver_auth_password':
                        if value != '':
                            self.config.update({'webserver_auth_password' : value})

                    elif command == 'gallery_max_images':
                        try:
                            int(value)
                        except:
                            print("*** WARNING: specified 'GALLERY_MAX_IMAGES' is not a valid number; it will be ignored!")
                        else:
                            self.config.update({'gallery_max_images' : int(value)})

                    elif command == 'gallery_refresh':
                        try:
                            int(value)
                        except:
                            print("*** WARNING: specified 'GALLERY_REFRESH' is not a valid number; it will be ignored!")
                        else:
                            self.config.update({'gallery_refresh' : int(value)})

                    elif command == 'gallery_user_folder':
                        if value != '':
                            self.config.update({'gallery_user_folder' : value})

                    elif command == 'gallery_user_folder_alias':
                        if value != '':
                            self.config.update({'gallery_user_folder_alias' : value})

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

                    elif command == 'debug_test_mode':
                        if value == 'yes' or value == 'no':
                            if value == 'yes':
                                self.config.update({'debug_test_mode' : True})
                            else:
                                self.config.update({'debug_test_mode' : False})

                    elif command == 'pf_auto_insert_model_trigger':
                        if value == 'start' or value == 'end' or value == 'first_comma' or value == 'off':
                            self.config.update({'auto_insert_model_trigger' : value})

                    elif command == 'pf_neg_prompt':
                        self.config.update({'neg_prompt' : value})

                    elif command == 'pf_highres_fix':
                        if value == 'yes' or value == 'no':
                            self.config.update({'highres_fix' : value})

                    elif command == 'pf_width':
                        try:
                            int(value)
                        except:
                            print("*** WARNING: specified 'PF_WIDTH' is not a valid number; it will be ignored!")
                        else:
                            self.config.update({'width' : int(value)})

                    elif command == 'pf_height':
                        try:
                            int(value)
                        except:
                            print("*** WARNING: specified 'PF_HEIGHT' is not a valid number; it will be ignored!")
                        else:
                            self.config.update({'height' : int(value)})

                    elif command == 'pf_sampler':
                        # TODO validate this
                        if value != '':
                            self.config.update({'sampler' : value})

                    elif command == 'pf_steps':
                        try:
                            int(value)
                        except:
                            print("*** WARNING: specified 'PF_STEPS' is not a valid number; it will be ignored!")
                        else:
                            self.config.update({'steps' : int(value)})

                    elif command == 'pf_scale':
                        try:
                            float(value)
                        except:
                            print("*** WARNING: specified 'PF_SCALE' is not a valid number; it will be ignored!")
                        else:
                            self.config.update({'scale' : float(value)})

                    elif command == 'pf_samples':
                        try:
                            int(value)
                        except:
                            print("*** WARNING: specified 'PF_SAMPLES' is not a valid number; it will be ignored!")
                        else:
                            self.config.update({'samples' : int(value)})

                    elif command == 'pf_use_upscale':
                        if value == 'yes' or value == 'no':
                            self.config.update({'use_upscale' : value})

                    elif command == 'pf_upscale_amount':
                        try:
                            float(value)
                        except:
                            print("*** WARNING: specified 'PF_UPSCALE_AMOUNT' is not a valid number; it will be ignored!")
                        else:
                            self.config.update({'upscale_amount' : float(value)})

                    elif command == 'pf_upscale_codeformer_amount':
                        try:
                            float(value)
                        except:
                            print("*** WARNING: specified 'PF_UPSCALE_CODEFORMER_AMOUNT' is not a valid number; it will be ignored!")
                        else:
                            self.config.update({'upscale_codeformer_amount' : float(value)})

                    elif command == 'pf_upscale_gfpgan_amount':
                        try:
                            float(value)
                        except:
                            print("*** WARNING: specified 'PF_UPSCALE_GFPGAN_AMOUNT' is not a valid number; it will be ignored!")
                        else:
                            self.config.update({'upscale_gfpgan_amount' : float(value)})

                    elif command == 'pf_upscale_keep_org':
                        if value == 'yes' or value == 'no':
                            self.config.update({'upscale_keep_org' : value})

                    elif command == 'pf_ckpt_file':
                        # this is validated after we receive valid models from the server
                        self.config.update({'ckpt_file' : value})

                    else:
                        self.print("warning: config file command not recognized: " + command.upper() + " (it will be ignored)!")


        else:
            self.print("configuration file '" + self.config_file + "' doesn't exist; using defaults...")


    # starts the webserver
    def start_server(self):
        addr = "http://localhost"
        if self.config['webserver_port'] != 80:
            addr += ':' + str(self.config['webserver_port']) + '/'
        self.print("starting webserver (" + addr + ") as a background process...")
        if self.config.get('webserver_open_browser'):
            webbrowser.open(addr)
        self.server = ArtServer()
        self.server.start(self)


    # if we're not running the webserver we'll use these
    def register_handlers(self):
        if sys.platform == "win32" or os.name == 'nt':
            signal.signal(signal.SIGBREAK, self.sigterm_handler)
        signal.signal(signal.SIGINT, self.sigterm_handler)
        signal.signal(signal.SIGTERM, self.sigterm_handler)


    # handle graceful cleanup here
    def sigterm_handler(self, *args):
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
        if not self.shutting_down:
            self.shutting_down = True
            self.print("Server shutdown requested; cleaning up and shutting down...")
            if self.server != None:
                # stop the webserver if it's running
                self.server.stop()

            # clean up gpu sd instance threads
            for worker in self.workers:
                worker['sdi_instance'].cleanup()

            # clean up temp directory
            temp = os.path.join('server', 'temp')
            if os.path.exists(temp):
                shutil.rmtree(temp)

            self.is_paused = True
            self.work_done = True


    # adds a GPU to the list of workers
    def add_gpu_worker(self, id, name, dummy = False):
        sdi_gpu_id = id.replace('cuda:', '')
        sdi_port = self.config['sd_port'] + self.sdi_ports_assigned
        self.sdi_ports_assigned += 1

        if not dummy:
            self.workers.append({'id': id, \
                'name': name, \
                'work_state': "", \
                'jobs_done': 0, \
                'job_prompt_info': '', \
                'job_start_time': float(0), \
                'idle': True, \
                'sdi_instance': SDI(sdi_gpu_id, sdi_port, self.config['sd_location'], self, id) \
            })
        else:
            # TODO fix dummy workers to work in sim mode
            self.workers.append({'id': id, \
                'name': name, \
                'work_state': "", \
                'jobs_done': 0, \
                'job_prompt_info': '', \
                'job_start_time': float(0), \
                'idle': True, \
                'sdi_instance': None \
            })

        self.print("initialized worker '" + id + "': " + name)


    # build a list of gpu workers
    def init_gpu_workers(self):
        if self.config['use_gpu_devices'] == "auto":
            # attempt to auto-detect GPUs
            self.print("detected " + str(device_count()) + " total GPU device(s)...")
            for i in range(device_count()):
                name = ""
                worker = "cuda:" + str(i)
                try:
                    name = get_device_name(worker)
                except AssertionError:
                    self.print("unable to initialize device '" + worker + "'; removing it as a GPU candidate...")

                # if we can see the gpu name, add it to the list of workers
                if name != '':
                    self.add_gpu_worker(worker, name)

        elif ',' in self.config['use_gpu_devices']:
            # we're specifying multiple GPUs
            gpus = self.config['use_gpu_devices'].split(',')
            for gpu in gpus:
                name = ""
                worker = "cuda:" + gpu.strip()
                try:
                    name = get_device_name(worker)
                except AssertionError:
                    self.print("unable to initialize device '" + worker + "'; removing it as a GPU candidate...")

                # if we can see the gpu name, add it to the list of workers
                if name != '':
                    self.add_gpu_worker(worker, name)

        else:
            # add exactly 1 gpu
            gpu = -1
            try:
                gpu = int(self.config['use_gpu_devices'].strip())
            except ValueError:
                self.print("ERROR: can't understand USE_GPU_DEVICES configuration: " + self.config['use_gpu_devices'])

            if gpu > -1:
                name = ""
                worker = "cuda:" + str(gpu)
                try:
                    name = get_device_name(worker)
                except AssertionError:
                    self.print("unable to initialize device '" + worker + "'; removing it as a GPU candidate...")

                # if we can see the gpu name, add it to the list of workers
                if name != '':
                    self.add_gpu_worker(worker, name)


    # build a list of dummy workers for debugging/testing
    def init_dummy_workers(self):
        worker_list = []
        worker_list.append("cuda:0")
        worker_list.append("cuda:1")
        worker_list.append("cuda:2")
        #worker_list.append("cuda:3")
        #worker_list.append("cpu")

        for worker in worker_list:
            worker = worker.lower().strip()
            name = ''
            if ':' in worker:
                if worker.split(':' ,1)[0] == 'cuda':
                    try:
                        name = get_device_name(worker)
                    except AssertionError:
                        name = "Dummy GPU Device"

            elif worker == 'cpu':
                name = platform.processor()

            # if we're able to see the device, add it to the worker queue
            if name != '':
                self.add_gpu_worker(worker, name, True)


    # returns the first idle gpu worker if there is one, otherwise returns None
    def get_idle_gpu_worker(self):
        for worker in self.workers:
            if ':' in worker["id"]:
                if worker["id"].split(':' ,1)[0] == 'cuda':
                    # this is a gpu worker
                    if worker['sdi_instance'].ready and not worker['sdi_instance'].busy:
                        # the worker has been initialized and isn't performing tasks
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


    # start a new worker thread
    def do_work(self, worker, command):
        worker['idle'] = False
        thread = Worker(command, self.work_done_callback, worker, self.output_buffer)
        thread.start()


    # callback for worker threads when finished
    def work_done_callback(self, *args):
        self.jobs_done += 1
        self.total_jobs_done += 1
        # args[0] contains worker data; set this worker back to idle
        args[0]['idle'] = True
        args[0]['work_state'] = ""
        args[0]['jobs_done'] += 1
        args[0]['job_start_time'] = 0
        args[0]['job_prompt_info'] = ''


    def clear_work_queue(self):
        self.print("clearing work queue...")
        self.work_queue.clear()
        self.loops = 0
        self.jobs_done = 0
        self.orig_work_queue_size = 0


    # build a work queue with the specified prompt and style files
    def init_work_queue(self):
        # random mode; queue up a few random prompts
        if self.prompt_manager.config.get('mode') == 'random':
            for i in range(50):
                #work = "Test work item #" + str(i+1)
                work = self.prompt_manager.config.copy()
                work['prompt'] = self.prompt_manager.pick_random()
                work['prompt_file'] = self.prompt_file
                self.work_queue.append(work)

        # standard mode, grab all possible combos
        else:
            self.work_queue = self.prompt_manager.build_combinations()
            self.orig_work_queue_size = len(self.work_queue)

        self.print("queued " + str(len(self.work_queue)) + " work items.")


    # loads a new prompt file
    # note that new_file is an absolute path reference
    def new_prompt_file(self, new_file):
        # TODO validate everything is ok before making the switch

        self.read_wildcards()
        self.prompt_file = new_file
        self.prompt_manager = utils.PromptManager(self)

        self.prompt_manager.handle_config()
        self.input_manager = utils.InputManager(self.prompt_manager.config.get('random_input_image_dir'))

        self.clear_work_queue()
        self.init_work_queue()


    # sets a new active editor file
    # note that new_file is an absolute path reference
    def new_prompt_editor_file(self, new_file):
        self.prompt_editor_file = new_file


    # saves the currently open prompt editor file with the new
    # text supplied by the user via the editor
    def save_prompt_editor_file(self, new_text):
        result = True
        if self.prompt_editor_file != "":
            # create backup in case anything goes wrong
            backup_file = os.path.join(self.temp_path, utils.filename_from_abspath(self.prompt_editor_file))
            shutil.copy2(self.prompt_editor_file, backup_file)
            try:
                with open(self.prompt_editor_file, 'w', encoding = 'utf-8') as f:
                    f.write(new_text)
            except:
                result = False
                # restore backup
                shutil.copy2(backup_file, self.prompt_editor_file)
            else:
                # success
                result = True
                # if the saved prompt file is the actively-running one, reload it
                if utils.filename_from_abspath(self.prompt_editor_file) == utils.filename_from_abspath(self.prompt_file):
                    self.print("active prompt file edited; reloading it...")
                    self.new_prompt_file(self.prompt_editor_file)

        return result


    # renames currently open prompt editor file
    def rename_prompt_editor_file(self, new_name):
        result = True
        if self.prompt_editor_file != "":
            # create backup in case anything goes wrong
            backup_file = os.path.join(self.temp_path, utils.filename_from_abspath(self.prompt_editor_file))
            shutil.copy2(self.prompt_editor_file, backup_file)
            new_file = os.path.join(self.config['prompts_location'], new_name + '.prompts')
            try:
                os.rename(self.prompt_editor_file, new_file)
            except:
                result = False
            else:
                # success; update the prompt file with the new name
                self.prompt_editor_file = new_file
                result = True

        return result


    # deletes currently selected prompt file
    def delete_prompt_file(self):
        result = True
        if self.prompt_editor_file != "":
            if os.path.exists(self.prompt_editor_file):
                # create backup in case anything goes wrong
                backup_file = os.path.join(self.temp_path, utils.filename_from_abspath(self.prompt_editor_file))
                shutil.copy2(self.prompt_editor_file, backup_file)
                try:
                    os.remove(self.prompt_editor_file)
                except:
                    result = False
                else:
                    # success; clear the prompt file
                    self.prompt_editor_file = ""
                    result = True

        return result


    # creates a new prompt file of the specified type
    # types may be 'standard' or 'random'
    def create_prompt_editor_file(self, type):
        mode_desc = '							# random mode; queue random prompts from [prompts] sections below'
        if (type != 'random'):
            mode_desc = '                       # standard mode; queue all possible combinations of [prompts] below'
            type = 'standard'

        newfilename = dt.now().strftime('%Y-%m-%d-') + 'prompts-' + type
        new_file = os.path.join(self.config['prompts_location'], newfilename + '.prompts')

        # make sure we have a unique file name
        count = 0
        while os.path.exists(new_file):
            temp = newfilename + '-' + str(count)
            new_file = os.path.join(self.config['prompts_location'], temp + '.prompts')
            count += 1

        # create a simple template
        buffer = "# *****************************************************************************************************\n"
        buffer += "# Dream Factory " + type + " prompt file\n"
        create_stamp = dt.now().strftime('%Y-%m-%d') + " at " + dt.now().strftime('%H:%M:%S')
        buffer += "# created " + create_stamp + " via the integrated prompt editor\n"
        buffer += "# *****************************************************************************************************\n"

        buffer += "# these are the default configuration parameters set in your config.txt file\n"
        buffer += "# you may override anything in this section if you wish, otherwise skip down to the [prompts] section(s) below\n"
        buffer += "[config]\n\n"
        buffer += "!MODE = " + type + mode_desc + "\n"
        buffer += "!DELIM = \" \"							# delimiter to use between prompt sections, default is space\n"
        if type == "standard":
            buffer += "!REPEAT = yes							# repeat when all work finished (yes/no)?\n\n"
            buffer += "# in standard mode, you may put also embed any of the following config directives into \n"
            buffer += "# the [prompt] sections below; they'll affect all prompts that follow the directive\n\n"

        buffer += "!WIDTH = " + str(self.config['width']) + "							# output image width\n"
        buffer += "!HEIGHT = " + str(self.config['height']) + "							# output image height\n"
        buffer += "!HIGHRES_FIX = " + self.config['highres_fix'] + "				        # fix for images significantly larger than 512x512, if enabled uses !STRENGTH setting\n"
        buffer += "!STEPS = " + str(self.config['steps']) + "							# number of steps, more may improve image but increase generation time\n"
        buffer += "!SAMPLER = " + str(self.config['sampler']) + "                      # sampler to use; press ctrl+h for reference\n"
        buffer += "!SAMPLES = " + str(self.config['samples']) + "					      	# number of images to generate per prompt\n"

        if type == "standard":
            buffer += "!SCALE = " + str(self.config['scale']) + "							# guidance scale, increase for stricter prompt adherence\n"
            buffer += "!INPUT_IMAGE = 						# specify an input image to use as a generation starting point\n"
            buffer += "!STRENGTH = 0.75						# strength of input image influence (0-1, with 1 corresponding to least influence)\n"
        else:
            buffer += "!MIN_SCALE = " + str(self.config['scale']) + "						# minimum guidance scale, default = 7.5\n"
            buffer += "!MAX_SCALE = " + str(self.config['scale']) + "						# maximum guidance scale, set min and max to same number for no variance\n"
            buffer += "!RANDOM_INPUT_IMAGE_DIR =				# specify directory of images here; a random image will be picked per prompt \n"
            buffer += "!MIN_STRENGTH = 0.75					# min strength of starting image influence, (0-1, 1 is lowest influence)\n"
            buffer += "!MAX_STRENGTH = 0.75					# max strength of start image, set min and max to same number for no variance\n"

        buffer += "!CKPT_FILE = " + str(self.config['ckpt_file']) +	"                          # model to load, press ctrl+h for reference\n"

        buffer += "\n# optional integrated upscaling\n\n"
        buffer += "!USE_UPSCALE = " + self.config['use_upscale'] + "						# upscale output images?\n"
        buffer += "!UPSCALE_AMOUNT = " + str(self.config['upscale_amount']) + "					# upscaling factor\n"
        buffer += "!UPSCALE_CODEFORMER_AMOUNT = " + str(self.config['upscale_codeformer_amount']) + "		# how visible codeformer enhancement is, 0-1\n"
        buffer += "!UPSCALE_GFPGAN_AMOUNT = " + str(self.config['upscale_gfpgan_amount']) + "			# how visible gfpgan enhancement is, 0-1\n"
        buffer += "!UPSCALE_KEEP_ORG = " + self.config['upscale_keep_org'] + "				# keep the original non-upscaled image (yes/no)?\n"

        buffer += "\n# optional negative prompt\n\n"
        buffer += "!NEG_PROMPT = " + self.config['neg_prompt'] + '\n'

        buffer += "\n# *****************************************************************************************************\n"
        buffer += "# prompt section\n"
        buffer += "# *****************************************************************************************************\n"
        buffer += "[prompts]\n"
        buffer += "\n# put your prompts here; one per line\n"
        buffer += "# you may also add additional [prompt] sections below, see 'example-" + type + ".prompts' for details\n"

        # write the buffer to a new file and return it
        with open(new_file, 'w', encoding = 'utf-8') as f:
            f.write(buffer)

        self.prompt_editor_file = new_file
        buffer = utils.filename_from_abspath(new_file).replace('.prompts', '') + '|' + buffer

        return buffer


    # delete an image
    def delete_gallery_img(self, web_path):
        web_path = web_path.replace('/', os.path.sep)
        web_path = web_path.replace('\\', os.path.sep)
        response = ""
        actual_path = ""
        if (os.path.sep + 'user_gallery') in web_path:
            div = os.path.sep + 'user_gallery' + os.path.sep
            actual_path = web_path.split(div, 1)[1]
            actual_path = os.path.join(self.config['gallery_user_folder'], actual_path)
        else:
            div = os.path.sep + 'output' + os.path.sep
            actual_path = web_path.split(div, 1)[1]
            actual_path = os.path.join(self.config['output_location'], actual_path)

        if os.path.exists(actual_path):
            # move the 'deleted' file to the server /temp directory
            # it will be deleted permanently when the server shuts down
            temp = os.path.join(self.temp_path, utils.filename_from_abspath(actual_path))
            try:
                os.replace(actual_path, temp)
            except:
                try:
                    shutil.move(actual_path, temp)
                except:
                    pass
            else:
                # if the moves failed, just delete the file
                if os.path.exists(actual_path):
                    os.remove(actual_path)
        else:
            response = "image not found"

        return response


    # sets the list of SD models available
    # also creates/updates the model/trigger file
    def update_models(self, models):
        self.sdi_models = models
        if exists(self.models_filename):
            # already exists, check the models we already have in the file
            with open(self.models_filename, 'r') as f:
                lines = f.readlines()

            # scan to see if any on the server are missing from the file
            missing = []
            for m in models:
                found = False
                for line in lines:
                    if m in line:
                        found = True
                        break
                if not found:
                    missing.append(m)

            # append missing models to file
            with open(self.models_filename, 'a') as f:
                for new_m in missing:
                    f.write(new_m + ', \n')

        else:
            # creating for the first time
            with open(self.models_filename, 'w') as f:
                f.write('# Dream Factory model-trigger.txt file\n')
                f.write('# This contains a list of all SD models available for use in Dream Factory.\n')
                f.write('# Append the trigger word/phrase after the comma following each model to\n')
                f.write('# allow Dream Factory to automatically add it to your prompts when using the model!\n\n')
                for m in models:
                    f.write(m + ', \n')

        # build trigger words dict
        self.model_trigger_words = {}
        with open(self.models_filename, 'r') as f:
            lines = f.readlines()

        for line in lines:
            if not line.startswith('#') and line.strip() != '' and line.strip() != '\n':
                model = line.split(',', 1)[0].strip()
                trigger = line.split(',', 1)[1].strip()
                if trigger != '':
                    self.model_trigger_words[model] = trigger

        # validate default model if there is one:
        if self.config['ckpt_file'] != '':
            model = self.config['ckpt_file']
            validated_model = self.validate_model(model)
            if validated_model != '':
                self.config['ckpt_file'] = validated_model
                print('[controller] >>> default model validated: ' + self.config['ckpt_file'])
            else:
                self.config['ckpt_file'] = ''
                print("*** WARNING: config.txt file command PF_CKPT_FILE value (" + model + ") doesn't match any server values; ignoring it! ***")
        self.default_model_validated = True


    # passing models must be exactly what SD expects; use this to make sure
    # user-supplied model is ok - otherwise revert to default
    def validate_model(self, model):
        validated_model = ''
        if len(model) > 5:
            if self.sdi_models != None:
                for m in self.sdi_models:
                    if model.lower() in m.lower():
                        # case-insensitive partial match; use the exact casing from the server
                        validated_model = m
                        break
        return validated_model


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


    # returns how many worker inits are happening right now,
    # used for staggered GPU startup
    def current_active_inits(self):
        active_inits = 0
        for worker in self.workers:
            if worker['sdi_instance'].init and not worker['sdi_instance'].ready:
                # we started init but it isn't ready, therefore in process of init
                active_inits += 1
        return active_inits


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

    parser.add_argument(
        "--prompt_file",
        type=str,
        nargs="?",
        default="",
        help="initial prompt file to load"
    )

    opt = parser.parse_args()
    control = Controller(opt.config)
    if len(control.workers) == 0:
        control.print("ERROR: unable to initialize any GPUs for work; exiting!")
        exit()

    # load initial prompt file if specified
    if (opt.prompt_file) != "":
        if exists(opt.prompt_file):
            control.new_prompt_file(opt.prompt_file)
        else:
            control.print("ERROR: specified prompt file '" + opt.prompt_file + "' does not exist - load one from the control panel instead!")

    # main work loop
    while not control.work_done:
        # check for un-initialized workers
        for worker in control.workers:
            if not worker['sdi_instance'].init:
                if control.current_active_inits() < control.config['gpu_init_stagger']:
                    # init this worker as long as we're not already at the init limit
                    worker['sdi_instance'].initialize()

        # check for idle workers
        worker = control.get_idle_gpu_worker()
        skip = False

        if worker != None:

            if not control.sdi_sampler_request_made:
                # get available samplers from the server
                # when the first worker is ready
                worker['sdi_instance'].get_server_samplers()
                control.sdi_sampler_request_made = True
                skip = True

            if not control.sdi_model_request_made:
                # get available models from the server
                # when the first worker is ready
                worker['sdi_instance'].get_server_models()
                control.sdi_model_request_made = True
                skip = True

            if not control.sdi_hypernetwork_request_made:
                # get available hypernetworks from the server
                # when the first worker is ready
                worker['sdi_instance'].get_server_hypernetworks()
                control.sdi_hypernetwork_request_made = True
                skip = True

            # worker is idle, start some work
            if not control.is_paused and not skip:
                if len(control.work_queue) > 0:
                    # get a new prompt or setting directive from the queue
                    new_work = control.work_queue.popleft()
                    control.do_work(worker, new_work)
                else:
                    # if we're in random prompts mode, re-fill the queue
                    if control.prompt_manager != None and control.prompt_manager.config.get('mode') == 'random':
                        control.print('adding more random prompts to the work queue...')
                        control.init_work_queue()
                    else:
                        if not control.repeat_jobs:
                            control.is_paused = True
                            # no more jobs, wait for all workers to finish
                            control.print('No more work in queue; waiting for all workers to finish...')
                            while control.num_workers_working() > 0:
                                time.sleep(.05)
                            control.print('All work done; pausing server - add some more work via the control panel!')
                        else:
                            # flag to repeat work enabled, re-load work queue
                            control.loops += 1
                            control.jobs_done = 0
                            control.init_work_queue()
            else:
                time.sleep(.1)

        else:
            time.sleep(.05)

    print('\nShutting down...')
    if control and control.total_jobs_done > 0:
        print("\nTotal jobs done: " + str(control.total_jobs_done))
        #control.print_worker_report()

    exit()
