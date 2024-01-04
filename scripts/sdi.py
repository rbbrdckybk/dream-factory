# Copyright 2021 - 2024, Bill Kennedy (https://github.com/rbbrdckybk/dream-factory)
# SPDX-License-Identifier: MIT

import json
import requests
import io
import base64
import os
import shlex
import subprocess
import time
import sys
import signal
import threading
import platform
import shutil
import atexit
import psutil
from os.path import exists
from PIL import Image, PngImagePlugin
from pprint import pprint


# for making txt2img requests
class Txt2ImgRequest(threading.Thread):
    def __init__(self, sdi_ref, payload, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref
        self.callback = callback
        self.payload = payload

    def run(self):
        response = requests.post(url=f'{self.sdi_ref.url}/sdapi/v1/txt2img', json=self.payload)
        self.callback(response)


# for making img2img requests
class Img2ImgRequest(threading.Thread):
    def __init__(self, sdi_ref, payload, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref
        self.callback = callback
        self.payload = payload

    def run(self):
        response = requests.post(url=f'{self.sdi_ref.url}/sdapi/v1/img2img', json=self.payload)
        self.callback(response)


# for making ControlNet txt2img requests
class ControlNet_Txt2ImgRequest(threading.Thread):
    def __init__(self, sdi_ref, payload, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref
        self.callback = callback
        self.payload = payload

    def run(self):
        response = requests.post(url=f'{self.sdi_ref.url}/controlnet/txt2img', json=self.payload)
        self.callback(response)


# for making ControlNet img2img requests
class ControlNet_Img2ImgRequest(threading.Thread):
    def __init__(self, sdi_ref, payload, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref
        self.callback = callback
        self.payload = payload

    def run(self):
        response = requests.post(url=f'{self.sdi_ref.url}/controlnet/img2img', json=self.payload)
        self.callback(response)


# for making upscale requests
class UpscaleRequest(threading.Thread):
    def __init__(self, sdi_ref, payload, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref
        self.callback = callback
        self.payload = payload

    def run(self):
        response = requests.post(url=f'{self.sdi_ref.url}/sdapi/v1/extra-single-image', json=self.payload)
        self.callback(response)


# for fetching valid samplers
class GetSamplersRequest(threading.Thread):
    def __init__(self, sdi_ref, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref
        self.callback = callback

    def run(self):
        response = requests.get(url=f'{self.sdi_ref.url}/sdapi/v1/samplers')
        self.callback(response)


# for fetching valid model checkpoints
class GetModelsRequest(threading.Thread):
    def __init__(self, sdi_ref, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref
        self.callback = callback

    def run(self):
        response = requests.get(url=f'{self.sdi_ref.url}/sdapi/v1/sd-models')
        self.callback(response)


# for fetching hypernetworks
class GetHyperNetworksRequest(threading.Thread):
    def __init__(self, sdi_ref, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref
        self.callback = callback

    def run(self):
        response = requests.get(url=f'{self.sdi_ref.url}/sdapi/v1/hypernetworks')
        self.callback(response)


# for fetching styles
class GetStylesRequest(threading.Thread):
    def __init__(self, sdi_ref, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref
        self.callback = callback

    def run(self):
        response = requests.get(url=f'{self.sdi_ref.url}/sdapi/v1/prompt-styles')
        self.callback(response)


# for fetching VAEs
class GetVAEsRequest(threading.Thread):
    def __init__(self, sdi_ref, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref
        self.callback = callback

    def run(self):
        response = requests.get(url=f'{self.sdi_ref.url}/sdapi/v1/sd-vae')
        self.callback(response)


# for fetching loras
class GetLorasRequest(threading.Thread):
    def __init__(self, sdi_ref, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref
        self.callback = callback

    def run(self):
        response = requests.get(url=f'{self.sdi_ref.url}/sdapi/v1/loras')
        self.callback(response)


# for updating loras
class LoraRefreshRequest(threading.Thread):
    def __init__(self, sdi_ref, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref
        self.callback = callback

    def run(self):
        response = requests.post(url=f'{self.sdi_ref.url}/sdapi/v1/refresh-loras')
        self.callback(response)


# for fetching scripts
class GetScriptsRequest(threading.Thread):
    def __init__(self, sdi_ref, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref
        self.callback = callback

    def run(self):
        response = requests.get(url=f'{self.sdi_ref.url}/sdapi/v1/scripts')
        self.callback(response)


# for fetching upscalers
class GetUpscalersRequest(threading.Thread):
    def __init__(self, sdi_ref, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref
        self.callback = callback

    def run(self):
        response = requests.get(url=f'{self.sdi_ref.url}/sdapi/v1/upscalers')
        self.callback(response)


# for fetching ControlNet models
class ControlNet_GetModelsRequest(threading.Thread):
    def __init__(self, sdi_ref, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref
        self.callback = callback

    def run(self):
        response = requests.get(url=f'{self.sdi_ref.url}/controlnet/model_list')
        self.callback(response)


# for fetching ControlNet modules
class ControlNet_GetModulesRequest(threading.Thread):
    def __init__(self, sdi_ref, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref
        self.callback = callback

    def run(self):
        response = requests.get(url=f'{self.sdi_ref.url}/controlnet/module_list')
        self.callback(response)


# for changing server options, including model swaps
class SetOptionsRequest(threading.Thread):
    def __init__(self, sdi_ref, payload, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref
        self.callback = callback
        self.payload = payload

    def run(self):
        response = requests.post(url=f'{self.sdi_ref.url}/sdapi/v1/options', json=self.payload)
        self.callback(response, self.payload)


# for fetching valid model checkpoints
class InterruptRequest(threading.Thread):
    def __init__(self, sdi_ref, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref

    def run(self):
        response = requests.post(url=f'{self.sdi_ref.url}/sdapi/v1/interrupt', json={})


# for checking if the server is alive / ready for requests
class AliveRequest(threading.Thread):
    def __init__(self, sdi_ref, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref
        self.callback = callback

    def run(self):
        response_code = self.check_alive()
        self.callback(response_code)

    def check_alive(self):
        code = -1
        try:
            response = requests.get(self.sdi_ref.url + '/docs', timeout = 300)
            code = response.status_code
        except:
            code = 999
        return code


# for monitoring SD server status
class Monitor(threading.Thread):
    def __init__(self, sdi_ref, callback=lambda: None, *args):
        threading.Thread.__init__(self)
        self.sdi_ref = sdi_ref
        self.callback = callback


    def run(self):
        #print("Monitor for GPU " + str(self.sdi_ref.gpu_id) + " starting!")
        self.sdi_ref.log("waiting for SD instance to be ready...", True)
        alive_check = AliveRequest(self.sdi_ref, self.alive_check_callback)
        alive_check.start()

        while self.sdi_ref.isRunning:
            # monitor progress here
            time.sleep(1)
        self.callback()

    # callback for alive check; whether or not server is ready for requests
    def alive_check_callback(self, response_code):
        #self.sdi_ref.log(str(response_code))
        if response_code == 200:
            self.sdi_ref.ready = True
            self.sdi_ref.log("SD instance finished initialization; ready for work!")
        else:
            # not ready yet; check again
            time.sleep(0.25)
            alive_check = AliveRequest(self.sdi_ref, self.alive_check_callback)
            alive_check.start()


# Stable Diffusion Interface
# manages the relationship between a GPU and an SD instance
class SDI:
    def __init__(self, gpu_id, port, path_to_sd, control_ref, worker_name):
        os.makedirs('logs', exist_ok=True)

        self.control_ref = control_ref
        self.worker_name = worker_name
        self.gpu_id = gpu_id
        self.platform = platform.system().lower()
        self.path_to_sd = path_to_sd
        self.command = 'webui-user.bat'
        self.target_command = 'df-start-gpu-' + str(gpu_id) + '.bat'
        self.sd_port = port
        self.url = 'http://localhost:' + str(self.sd_port)
        self.isRunning = True
        self.logfilename = os.path.join('logs', 'gpu-' + str(self.gpu_id) + '-log.txt')
        self.errorfilename = os.path.join('logs', 'gpu-' + str(self.gpu_id) + '-errors.txt')
        self.logfile = open(self.logfilename, 'w')
        self.errorfile = open(self.errorfilename, 'w')
        self.monitor = None
        self.process = None
        self.init = False           # has init() been run?
        self.ready = False          # is our associated server ready (e.g. has init() finished)?
        self.busy = False           # is this instance in the process of making a request?
        self.status = ''            # TODO fill in % done here
        self.request_count = 0
        self.output_dir = ''
        self.options_change_in_progress = False
        self.model_loaded = ''
        self.model_loading_now = ''
        self.last_job_success = True

        if self.platform == 'linux':
            self.command = 'webui-user.sh'
            self.target_command = 'df-start-gpu-' + str(gpu_id) + '.sh'

    #waits for SD APIs to be ready and returning expected information
    def wait_for_server(self, url, api_endpoint, timeout=300):
        start_time = time.time()

        while True:
            try:
                response = requests.get(url + api_endpoint)
                response.raise_for_status()  # Raises stored HTTPError, if one occurred.

                data = response.json()
                if 'detail' in data and data['detail'] == 'Not Found':
                    # If we get 'detail': 'Not Found', the API is not ready.
                    pass
                else:
                    # If we don't get 'detail': 'Not Found', the API is ready.
                    break

            except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, KeyError):
                pass

            if time.time() - start_time > timeout:
                raise TimeoutError(f'Server at {url} not responding after {timeout} seconds')

            time.sleep(5)  # Wait before trying again

    # starts up a new SD instance
    def initialize(self):
        self.init = True
        full_target = os.path.join(self.path_to_sd, self.target_command)

        # we don't have a startup script for this gpu; make one
        #if not exists(full_target):
        self.create_startup_batch_file()

        self.log('starting new SD instance via: ' + full_target, True)

        self.process = subprocess.Popen(full_target, \
            cwd=self.path_to_sd, \
            #stdout=subprocess.PIPE, \
            stdout=self.logfile, \
            stderr=self.errorfile, \
            bufsize=0, \
            universal_newlines=True
        )

        atexit.register(self.kill_sd_process)

        # start monitoring the SD subprocess's piped output
        self.monitor = Monitor(self, self.monitor_done_callback)
        self.monitor.start()

        # Wait for server to be ready
        self.wait_for_server(self.url, "/sdapi/v1/samplers")


    # creates a suitable startup .bat/.sh for this gpu
    def create_startup_batch_file(self):
        original_file = os.path.join(self.path_to_sd, self.command)
        if exists(original_file):
            # make a copy of the original
            dst = os.path.join(self.path_to_sd, self.target_command)
            shutil.copyfile(original_file, dst)
            # modify the copy to suit our needs
            with open(dst, 'r+') as f:
                lines = f.readlines()
                f.truncate(0)
                f.seek(0)

                for line in lines:
                    if line.startswith('set COMMANDLINE_ARGS='):
                        # modify Windows .bat file
                        line = line.replace('--autolaunch ', '')
                        line = line.replace('--autolaunch', '')
                        line = line.replace('\n', '')
                        if not '--api' in line:
                            line += ' --api'
                        # 2023-06-08 there is a bug in Auto1111 that prevents loras from activating when --nowebui is present
                        # https://github.com/AUTOMATIC1111/stable-diffusion-webui/issues/11016
                        #if not '--nowebui' in line:
                        #    line += ' --nowebui'

                        # ignore existing --device-id
                        if '--device-id' in line:
                            start = line.split('--device-id', 1)[0]
                            end = line.split('--device-id', 1)[1]
                            if '--' in end:
                                end = '--' + end.split('--', 1)[1]
                            else:
                                end = ''
                            line = start + end

                        # ignore existing --port
                        if '--port' in line:
                            start = line.split('--port', 1)[0]
                            end = line.split('--port', 1)[1]
                            if '--' in end:
                                end = '--' + end.split('--', 1)[1]
                            else:
                                end = ''
                            line = start + end

                        line += ' --port ' + str(self.sd_port)
                        line += ' --device-id ' + str(self.gpu_id)
                        line += '\n'

                    elif line.startswith('#export COMMANDLINE_ARGS=') or line.startswith('export COMMANDLINE_ARGS='):
                        # modify Linux .sh script
                        if line.startswith('export COMMANDLINE_ARGS='):
                            # Dream Factory won't work with the original line uncommented under Linux as
                            # it will override any changes we define here. Need to re-comment and inform user
                            with open(original_file, 'r+') as o:
                                ls = o.readlines()
                                o.truncate(0)
                                o.seek(0)
                                for l in ls:
                                    if l.startswith('export COMMANDLINE_ARGS='):
                                        print("\nNotice: found uncommented COMMANDLINE_ARGS in your webui-user.sh script.")
                                        print("Dream Factory requires its own COMMANDLINE_ARGS to be set, and an uncommented")
                                        print("line here will override the settings that Dream Factory needs to work.")
                                        print("The following change has been made to " + original_file + " :\n")
                                        print("old:   " + l)
                                        l = '#' + l
                                        print("new:   " + l)
                                        print("You'll need to uncomment this line if you wish to use Automatic1111 webui with the environment settings above.")
                                        print("It will be re-commented automatically each time Dream Factory starts (and you'll receive this message again).\n")
                                    o.write(l)

                        line = line.replace('#export COMMANDLINE_ARGS=', 'export COMMANDLINE_ARGS=')
                        line = line.replace('\n', '')
                        line = line.replace('--autolaunch', '')
                        addQuote = False
                        if line.endswith('"'):
                            line = line[:-1]
                            addQuote = True

                        if not '--api' in line:
                            line += ' --api'
                        # 2023-06-08 there is a bug in Auto1111 that prevents loras from activating when --nowebui is present
                        # https://github.com/AUTOMATIC1111/stable-diffusion-webui/issues/11016
                        #if not '--nowebui' in line:
                        #    line += ' --nowebui'

                        #if not '--lowram' in line:
                        #    line += ' --lowram'
                        line += ' --port ' + str(self.sd_port)
                        line += ' --device-id ' + str(self.gpu_id)

                        if addQuote:
                            line += '"'
                        line += '\n'

                    f.write(line)

                # add a call to start the webui under Linux
                if self.platform == 'linux':
                    f.write('source webui.sh')

            # give the script execute permission on Linux
            if self.platform == 'linux':
                os.chmod(dst, 0o777)

        else:
            print('\nError - Stable Diffusion not found at the following location: ' + self.path_to_sd)
            print('Make sure to set \'SD_LOCATION =\' in your config.txt with the path to your Automatic1111 SD repo installation!')
            print('\nExiting...')
            exit(0)


    # callback for log monitor when finished
    def monitor_done_callback(self, *args):
        #self.log("monitor for GPU " + str(self.gpu_id) + " shutting down!", True)
        pass


    # make a txt2img request
    def do_txt2img(self, payload, output_dir = ''):
        self.busy = True
        self.output_dir = output_dir
        #self.log('Making a txt2img request!')
        txt2img = Txt2ImgRequest(self, payload, self.handle_response)
        txt2img.start()


    # make a img2img request
    def do_img2img(self, payload, output_dir = ''):
        self.busy = True
        self.output_dir = output_dir
        #self.log('Making a img2img request!')
        img2img = Img2ImgRequest(self, payload, self.handle_response)
        img2img.start()


    # make a controlnet txt2img request
    def do_controlnet_txt2img(self, payload, output_dir = ''):
        self.busy = True
        self.output_dir = output_dir
        txt2img = ControlNet_Txt2ImgRequest(self, payload, self.handle_response)
        txt2img.start()


    # make a controlnet img2img request
    def do_controlnet_img2img(self, payload, output_dir = ''):
        self.busy = True
        self.output_dir = output_dir
        img2img = ControlNet_Img2ImgRequest(self, payload, self.handle_response)
        img2img.start()


    # make an upscale request
    def do_upscale(self, payload, output_dir = ''):
        self.busy = True
        self.output_dir = output_dir
        #self.log('Making an upscale request!')
        upscale = UpscaleRequest(self, payload, self.handle_upscale_response)
        upscale.start()


    # gets valid samplers from server
    def get_server_samplers(self):
        self.busy = True
        #self.log('Fetching samplers from server...')
        self.log('querying SD for available samplers...', True)
        query = GetSamplersRequest(self, self.sampler_response)
        query.start()

    # handle server sampler response
    def sampler_response(self, response):
        r = response.json()

        samplers = []
        sampler_str = ''
        for i in r:
            samplers.append(i['name'])
            sampler_str += '   - ' + i['name'] + '\n'

        #self.log('Server indicates the following samplers are available for use:\n' + sampler_str)
        self.log('received sampler query response: SD indicates ' + str(len(samplers)) + ' samplers available for use...', True)
        samplers.sort()
        self.control_ref.sdi_samplers = samplers

        # reload prompt file if we have one to validate it against samplers
        if self.control_ref.prompt_file != '':
            self.control_ref.new_prompt_file(self.control_ref.prompt_file)

        self.busy = False


    # gets valid controlnet models from server
    def get_server_controlnet_models(self):
        self.busy = True
        #self.log('Fetching models from server...')
        self.log('querying SD for available ControlNet models...', True)
        query = ControlNet_GetModelsRequest(self, self.controlnet_model_response)
        query.start()


    # handle server controlnet model response
    def controlnet_model_response(self, response):
        try:
            r = response.json()
            models = []
            for i in r['model_list']:
                models.append(i)

            if len(models) > 0:
                self.log('received ControlNet query response: SD indicates ' + str(len(models)) + ' ControlNet models available for use...', True)
                self.control_ref.sdi_controlnet_models = models
            else:
                self.log('received ControlNet query response: SD indicates no ControlNet models available; disabling ControlNet functionality (install at least one model)!', True)
                self.control_ref.sdi_controlnet_available = False
        except:
            self.log('*** Error: received invalid ControlNet model response (is your ControlNet extension installed properly?); disabling ControlNet functionality!', True)
            self.control_ref.sdi_controlnet_available = False

        self.busy = False


    # gets valid controlnet modules from server
    def get_server_controlnet_modules(self):
        self.busy = True
        #self.log('Fetching modules from server...')
        self.log('querying SD for available ControlNet preprocessors...', True)
        query = ControlNet_GetModulesRequest(self, self.controlnet_module_response)
        query.start()


    # handle server controlnet module response
    def controlnet_module_response(self, response):
        try:
            r = response.json()
            modules = []
            for i in r['module_list']:
                modules.append(i)

            if len(modules) > 0:
                self.log('received ControlNet query response: SD indicates ' + str(len(modules)) + ' ControlNet preprocessors available for use...', True)
                self.control_ref.sdi_controlnet_preprocessors = modules
            else:
                self.log('received ControlNet query response: SD indicates no ControlNet preprocessors available (is your ControlNet extension installed properly?)!', True)
                #self.control_ref.sdi_controlnet_available = False
        except:
            self.log('*** Error: received invalid ControlNet preprocessor response (is your ControlNet extension up to date?)!', True)

        self.busy = False


    # gets valid hypernetworks from server
    def get_server_hypernetworks(self):
        self.busy = True
        self.log('querying SD for available hypernetworks...', True)
        query = GetHyperNetworksRequest(self, self.hypernetwork_response)
        query.start()


    # gets valid styles from server
    def get_server_styles(self):
        self.busy = True
        self.log('querying SD for available styles...', True)
        query = GetStylesRequest(self, self.style_response)
        query.start()


    # gets valid VAEs from server
    def get_server_VAEs(self):
        self.busy = True
        self.log('querying SD for available VAEs...', True)
        query = GetVAEsRequest(self, self.VAE_response)
        query.start()


    # gets valid loras from server
    def get_server_loras(self):
        self.busy = True
        self.log('querying SD for available LoRAs...', True)
        query = GetLorasRequest(self, self.lora_response)
        query.start()


    # update loras on server
    def update_server_loras(self):
        #self.busy = True       # don't wait for response before starting work
        #self.log('asking SD to refresh LoRAs...', True)
        query = LoraRefreshRequest(self, self.lora_refresh_response)
        query.start()


    # gets valid scripts from server
    def get_server_scripts(self):
        self.busy = True
        self.log('querying SD for available scripts...', True)
        query = GetScriptsRequest(self, self.script_response)
        query.start()


    # gets valid upscalers from server
    def get_server_upscalers(self):
        self.busy = True
        self.log('querying SD for available upscalers...', True)
        query = GetUpscalersRequest(self, self.upscaler_response)
        query.start()


    # handle server hypernetwork response
    def hypernetwork_response(self, response):
        r = response.json()
        networks = []
        for i in r:
            if 'name' in i:
                network = {}
                network['name'] = i['name']
                if 'path' in i:
                    network['path'] = i['path']
                networks.append(network)

        self.log('received hypernetwork query response: SD indicates ' + str(len(networks)) + ' hypernetworks available for use...', True)
        networks = sorted(networks, key=lambda d: d['name'].lower())
        self.control_ref.sdi_hypernetworks = networks
        self.busy = False


    # handle server style response
    def style_response(self, response):
        r = response.json()
        styles = []
        for i in r:
            if 'name' in i:
                style = {}
                style['name'] = i['name']
                if 'prompt' in i:
                    style['prompt'] = i['prompt']
                if 'negative_prompt' in i:
                    style['negative_prompt'] = i['negative_prompt']
                if style['name'] != None and style['prompt'] != None and style['negative_prompt'] != None:
                    styles.append(style)

        self.log('received style query response: SD indicates ' + str(len(styles)) + ' styles available for use...', True)
        styles = sorted(styles, key=lambda d: d['name'].lower())
        self.control_ref.sdi_styles = styles
        self.busy = False


    # handle server VAE response
    def VAE_response(self, response):
        r = response.json()
        vaes = []
        for i in r:
            if 'model_name' in i:
                vae = {}
                vae['name'] = i['model_name']
                if 'filename' in i:
                    vae['path'] = i['filename']
                vaes.append(vae)

        self.log('received VAE query response: SD indicates ' + str(len(vaes)) + ' VAEs available for use...', True)
        vaes = sorted(vaes, key=lambda d: d['name'].lower())
        self.control_ref.sdi_VAEs = vaes
        self.busy = False


    # handle server lora response
    def lora_response(self, response):
        r = response.json()
        loras = []
        for i in r:
            if 'name' in i:
                lora = {}
                lora['name'] = i['name']
                if 'path' in i:
                    lora['path'] = i['path']
                loras.append(lora)

        self.log('received LoRA query response: SD indicates ' + str(len(loras)) + ' LoRAs available for use...', True)
        loras = sorted(loras, key=lambda d: d['name'].lower())
        self.control_ref.sdi_loras = loras
        self.busy = False


    # handle server lora response
    def lora_refresh_response(self, response):
        r = response.json()
        #self.log('received LoRA refresh response...', True)
        #self.busy = False


    # handle server script response
    def script_response(self, response):
        r = response.json()
        txt2img_scripts = []
        img2img_scripts = []

        for i in r['txt2img']:
            txt2img_scripts.append(i)
        for i in r['img2img']:
            img2img_scripts.append(i)

        rtxt = 'is not'
        if 'ultimate sd upscale' in img2img_scripts:
            self.control_ref.sdi_ultimate_upscale_available = True
            rtxt = 'is'
        self.log('received script query response: SD indicates \'Ultimate SD Upscale script\' ' + rtxt + ' available for use...', True)

        rtxt = 'is not'
        if 'adetailer' in img2img_scripts:
            self.control_ref.sdi_adetailer_available = True
            rtxt = 'is'
        self.log('received script query response: SD indicates \'ADetailer script\' ' + rtxt + ' available for use...', True)

        self.control_ref.sdi_txt2img_scripts = txt2img_scripts
        self.control_ref.sdi_img2img_scripts = img2img_scripts
        self.busy = False


    # handle server upscaler response
    def upscaler_response(self, response):
        r = response.json()
        upscalers = []
        for i in r:
            upscalers.append(i['name'])

        self.log('received upscaler query response: SD indicates ' + str(len(upscalers)) + ' upscalers available for use...', True)
        self.control_ref.sdi_upscalers = upscalers
        self.control_ref.check_default_upscaler()
        self.busy = False


    # gets valid models from server
    def get_server_models(self):
        self.busy = True
        #self.log('Fetching models from server...')
        self.log('querying SD for available models...', True)
        query = GetModelsRequest(self, self.model_response)
        query.start()


    # handle server model response
    def model_response(self, response):
        r = response.json()
        models = []
        for i in r:
            if 'title' in i:
                model = {}
                model['name'] = i['title']
                if 'filename' in i:
                    model['path'] = i['filename']
                models.append(model)

        self.log('received model query response: SD indicates ' + str(len(models)) + ' models available for use...', True)

        # send models to controller
        #models.sort()
        models = sorted(models, key=lambda d: d['name'].lower())
        self.control_ref.update_models(models)

        # reload prompt file if we have one to validate it against models
        if self.control_ref.prompt_file != '':
            self.control_ref.new_prompt_file(self.control_ref.prompt_file)

        self.busy = False


    # handle upscale responses
    def handle_upscale_response(self, response):
        # only handle if we're not already shutting down
        if self.isRunning:
            #self.log('Handling response from server...')
            try:
                r = response.json()
                os.makedirs(self.output_dir, exist_ok=True)

                i = r['image']
                image = Image.open(io.BytesIO(base64.b64decode(i)))

                png_payload = {
                    "image": "data:image/png;base64," + i
                }
                response2 = requests.post(url=f'{self.url}/sdapi/v1/png-info', json=png_payload)

                pnginfo = PngImagePlugin.PngInfo()
                pnginfo.add_text("parameters", response2.json().get("info"))

                seed = '0'
                # get the actual seed used
                if 'Seed:' in response2.json().get("info"):
                    temp = response2.json().get("info").split('Seed:', 1)
                    temp = temp[1].split(',', 1)
                    seed = temp[0].strip()

                filename = 'seed_' + seed + '_u.png'
                image.save(os.path.join(self.output_dir, filename), pnginfo=pnginfo)
                #self.log(filename + ' created!')
            except KeyError:
                self.log('*** Error response received during upscaling! *** : ' + str(r['detail']), True)
                time.sleep(1)
            except:
                #e = sys.exc_info()[0]
                #self.log('*** Error response received! *** : ' + str(e), True)
                self.log('*** Error response received during upscaling! *** : if this persists, try lowering your settings', True)
                time.sleep(1)

            self.request_count += 1
            self.busy = False


    # handle SD responses, callback for server requests
    def handle_response(self, response):
        # only handle if we're not already shutting down
        if self.isRunning:
            #self.log('Handling response from server...')
            self.last_job_success = True
            try:
                r = response.json()
                os.makedirs(self.output_dir, exist_ok=True)

                for i in r['images']:
                    image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))

                    png_payload = {
                        "image": "data:image/png;base64," + i
                    }
                    response2 = requests.post(url=f'{self.url}/sdapi/v1/png-info', json=png_payload)

                    pnginfo = PngImagePlugin.PngInfo()
                    pnginfo.add_text("parameters", response2.json().get("info"))

                    seed = '0'
                    # get the actual seed used
                    if 'Seed:' in response2.json().get("info"):
                        temp = response2.json().get("info").split('Seed:', 1)
                        temp = temp[1].split(',', 1)
                        seed = temp[0].strip()

                    filename = 'seed_' + seed + '.png'
                    image.save(os.path.join(self.output_dir, filename), pnginfo=pnginfo)
                    #self.log(filename + ' created!')
            except KeyError:
                self.log('*** Error response received! *** : ' + str(r['detail']), True)
                time.sleep(1)
                self.last_job_success = False
            except:
                #e = sys.exc_info()[0]
                #self.log('*** Error response received! *** : ' + str(e), True)
                self.log('*** Error response received! *** : if this persists, try lowering your settings', True)
                time.sleep(1)
                self.last_job_success = False

            self.request_count += 1
            self.busy = False


    # tells the SD instance to load the indicated model
    def load_model(self, new_model):
        self.options_change_in_progress = True
        self.model_loading_now = new_model
        self.log("requesting a new model load: " + new_model, True)
        payload = {
            "sd_model_checkpoint": new_model
        }
        model_req = SetOptionsRequest(self, payload, self.handle_options_response)
        model_req.start()


    # tells the SD instance to use the legacy highres_fix behavior or current new method
    def set_initial_options(self, hires_fix_mode):
        self.options_change_in_progress = True
        self.log("passing initial setup options to SD instance...", True)
        if hires_fix_mode == 'advanced':
            payload = {
                "use_old_hires_fix_width_height": False
            }
        else:
            payload = {
                "use_old_hires_fix_width_height": True
            }
        model_req = SetOptionsRequest(self, payload, self.handle_options_response)
        model_req.start()


    # handle option change responses
    def handle_options_response(self, response, payload):
        if response.status_code == 200:
            # no errors
            if "sd_model_checkpoint" in str(payload):
                self.model_loaded = self.model_loading_now
                self.model_loading_now = ''
                self.log('new model successfully loaded!', True)
            else:
                pass
                # TODO uncomment this if used beyond initial setup
                #self.log('options successfully changed!', True)
        else:
            # TODO handle error reporting
            #r = response.json()
            #print('unexpected handle_options_response: ' + str(response.status_code))
            pass

        self.options_change_in_progress = False


    # shutdown and clean up
    def cleanup(self):
        self.isRunning = False
        if self.busy:
            # if we're busy, send an interrupt request
            self.log("terminating current task...", True)
            int = InterruptRequest(self)
            int.start()

        self.logfile.close()
        self.errorfile.close()

        # the atexit call should get this, but will check here also
        self.kill_sd_process()

        # cleanup gpu working dir
        if self.output_dir != '':
            if os.path.exists(self.output_dir):
                shutil.rmtree(self.output_dir)


    # kill the SD child process
    def kill_sd_process(self):
        if self.process != None:
            #print("attempting to kill SD")
            try:
                #self.process.terminate()
                #self.process.kill()
                # this should kill all child processes spawned this SD instance
                parent = psutil.Process(self.process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
            except:
                # we're exiting anyway
                pass


    # logging function
    # set webserver = True to also send it to the web UI log
    def log(self, line, webserver = False):
        #pre = '[GPU ' + str(self.gpu_id) + '] >>> '
        pre = '[' + self.worker_name + '] >>> '
        print(pre + line)
        if webserver:
            self.control_ref.output_buffer.append(pre + line + '\n')
