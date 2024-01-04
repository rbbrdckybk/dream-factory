# Copyright 2021 - 2024, Bill Kennedy (https://github.com/rbbrdckybk/dream-factory)
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
import copy
import math
from PIL import Image
from io import BytesIO
import scripts.utils as utils
import scripts.metadata as metadata
import scripts.civitai as civitai
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
        command = ''
        original_filename = ''
        original_exif = {}
        original_iptc = {}
        original_command = {}
        process_mode = False
        if not int(self.command.get('seed')) > 0:
            self.command['seed'] = -1
        else:
            # increment seed if we've finished one or more complete loops
            if control.models != []:
                # multiple models in queue, only increment for each time we use all of them
                complete = math.floor(control.loops / len(control.models))
                seed = int(self.command.get('seed')) + complete
                self.command['seed'] = seed
            else:
                seed = int(self.command.get('seed')) + control.loops
                self.command['seed'] = seed

        # check for ADetailer params
        use_adetailer = False
        if control.sdi_adetailer_available and self.command.get('adetailer_use') and self.command.get('adetailer_model') != '':
            use_adetailer = True
            if '<prompt>' in self.command.get('adetailer_prompt'):
                self.command['adetailer_prompt'] = self.command.get('adetailer_prompt').replace('<prompt>', self.command.get('prompt'))

        # if this is a process-mode prompt, skip past image generation stuff
        if self.command.get('mode') != 'process':

            # handle IPTC metadata history stuff
            if self.command['iptc_title_history']:
                for key in self.command['iptc_title_history']:
                    self.command['iptc_title'] += self.command['iptc_title_history'][key][-1]

            if self.command['iptc_description_history']:
                for key in self.command['iptc_description_history']:
                    self.command['iptc_description'] += self.command['iptc_description_history'][key][-1]

            if self.command['iptc_keywords_history']:
                for key in self.command['iptc_keywords_history']:
                    for k in self.command['iptc_keywords_history'][key][-1]:
                        if k not in self.command['iptc_keywords']:
                            self.command['iptc_keywords'].append(k)

            # if this is a random prompt, settle on random values
            if self.command.get('mode') == 'random':
                if float(self.command.get('min_scale')) > 0 and float(self.command.get('max_scale')) > 0:
                    self.command['scale'] = round(random.uniform(float(self.command.get('min_scale')), float(self.command.get('max_scale'))), 1)
                if float(self.command.get('min_strength')) > 0 and float(self.command.get('max_strength')) > 0:
                    self.command['strength'] = round(random.uniform(float(self.command.get('min_strength')), float(self.command.get('max_strength'))), 2)
                if self.command.get('random_input_image_dir') != "":
                    self.command['input_image'] = utils.InputManager(self.command.get('random_input_image_dir')).pick_random()

            # settle on random values for ranges specified in scale directive
            if '-' in str(self.command['scale']):
                try:
                    values = str(self.command['scale']).split('-', 1)
                    first = float(values[0].strip())
                    second = float(values[1].strip())
                    if second >= first:
                        self.command['scale'] = round(random.uniform(first, second), 1)
                    else:
                        self.command['scale'] = round(random.uniform(second, first), 1)
                except:
                    pass

            # settle on random values for ranges specified in strength directive
            if '-' in str(self.command['strength']):
                try:
                        values = str(self.command['strength']).split('-', 1)
                        first = float(values[0].strip())
                        second = float(values[1].strip())
                        if second >= first:
                            self.command['strength'] = round(random.uniform(first, second), 2)
                        else:
                            self.command['strength'] = round(random.uniform(second, first), 2)
                except:
                    pass

            # settle on random values for ranges specified in steps directive
            if '-' in str(self.command['steps']):
                try:
                        values = str(self.command['steps']).split('-', 1)
                        first = int(values[0].strip())
                        second = int(values[1].strip())
                        if second >= first:
                            self.command['steps'] = random.randint(first, second)
                        else:
                            self.command['steps'] = random.randint(second, first)
                except:
                    pass

            # settle of random styles if necessary
            if len(self.command['styles']) > 0:
                if self.command['styles'][0].startswith('random'):
                    num = 1
                    styles = []
                    temp = self.command['styles'][0].split(' ')
                    if len(temp) > 1:
                        num = int(temp[1])
                    # pick random styles
                    if control.sdi_styles != None and control.sdi_styles != []:
                        if len(control.sdi_styles) > num:
                            work = copy.deepcopy(control.sdi_styles)
                            while num > 0:
                                pick = random.randint(0, len(work)-1)
                                styles.append(work[pick]['name'])
                                work.pop(pick)
                                num = num - 1
                        else:
                            # user asked for more random styles than exist; use all of them
                            for s in control.sdi_styles:
                                styles.append(s)
                    # update command with random styles
                    self.command['styles'] = styles

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

            if self.command.get('prompt').strip() == '.':
                self.command['prompt'] = ''
            else:
                # clean up potentially dangerous prompt content:
                while '--' in self.command.get('prompt'):
                     self.command['prompt'] = self.command.get('prompt').replace('--', '-')

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
                        elif 'keyword:' in self.command.get('auto_insert_model_trigger'):
                            keyword = self.command.get('auto_insert_model_trigger')
                            keyword = keyword.split('keyword:', 1)[1].strip()
                            if keyword in p:
                                # the keyword we need to replace with the trigger is in the prompt, replace it
                                self.command['prompt'] = p.replace(keyword, trigger)

                # check to see if the hi-res model we're using has an associated trigger if necessary
                # BK 2023-10-29
                if self.command.get('highres_ckpt_file') != '':
                    if control.model_trigger_words.get(self.command.get('highres_ckpt_file')) != None:
                        trigger = control.model_trigger_words.get(self.command.get('highres_ckpt_file'))
                        p = self.command.get('highres_prompt')
                        if p.strip() == '':
                            p = self.command.get('prompt')
                        if trigger not in p:
                            # trigger word isn't in highres prompt, we need to add it
                            if self.command.get('auto_insert_model_trigger') == 'first_comma':
                                if ',' in p:
                                    self.command['highres_prompt'] = p.split(',', 1)[0] + ', ' + trigger + ',' + p.split(',', 1)[1]
                                else:
                                    self.command['highres_prompt'] = p + ', ' + trigger
                            elif self.command.get('auto_insert_model_trigger') == 'end':
                                self.command['highres_prompt'] = p + ', ' + trigger
                            elif self.command.get('auto_insert_model_trigger') == 'start':
                                self.command['highres_prompt'] = trigger + ', ' + p
                            elif 'keyword:' in self.command.get('auto_insert_model_trigger'):
                                keyword = self.command.get('auto_insert_model_trigger')
                                keyword = keyword.split('keyword:', 1)[1].strip()
                                if keyword in p:
                                    # the keyword we need to replace with the trigger is in the prompt, replace it
                                    self.command['highres_prompt'] = p.replace(keyword, trigger)

            # check for wildcard replacements
            p = self.command.get('prompt')
            #print('before wildcard replace: ' + self.command['prompt'])
            for k, v in control.wildcards.items():
                key = '__' + k.lower() + '__'
                if key in p.lower():
                    vcopy = v.copy()
                    # check if any of the values are wildcard keys themselves
                    key_replacements = 1
                    while key_replacements > 0:
                        key_replacements = 0
                        for v in vcopy:
                            #print('Checking ' + v)
                            check_key = v[2:][:-2].lower()
                            if check_key in control.wildcards.keys():
                                key_replacements += 1
                                #print('\n\nFound nested wildcard: ' + v)
                                #print('\nList before replacement: ' + str(vcopy))
                                vcopy.extend(control.wildcards[check_key])
                                vcopy.remove(v)
                                #print('\nList after replacement: ' + str(vcopy) + '\n\n')

                    # this will handle multiple replacements of the same key
                    while key in p.lower():
                        replace_all = False
                        if len(vcopy) > 0:
                            # pick a random value & remove it from the copied list
                            x = random.randint(0, len(vcopy)-1)
                            replace = vcopy.pop(x)
                        else:
                            # not enough values to make all replacements, sub '' instead
                            replace_all = True
                            replace = ''

                        # make the replacement(s)
                        p = utils.wildcard_replace(p, key, replace, replace_all)
                        # check IPTC metadata and make the same replacement if necessary
                        self.command['iptc_title'] = utils.wildcard_replace(self.command.get('iptc_title'), key, replace, replace_all)
                        self.command['iptc_description'] = utils.wildcard_replace(self.command.get('iptc_description'), key, replace, replace_all)
                        self.command['iptc_keywords'] = utils.wildcard_replace_list(self.command.get('iptc_keywords'), key, replace, replace_all)
                        self.command['iptc_copyright'] = utils.wildcard_replace(self.command.get('iptc_copyright'), key, replace, replace_all)

            # handle special hard-coded prompt directive wildcards
            if '__!iptc_title__' in p.lower():
                p = utils.wildcard_replace(p, '__!iptc_title__', self.command.get('iptc_title'), True)
            if '__!iptc_description__' in p.lower():
                p = utils.wildcard_replace(p, '__!iptc_description__', self.command.get('iptc_description'), True)
            if '__!iptc_keywords__' in p.lower():
                p = utils.wildcard_replace_list(p, '__!iptc_keywords__', self.command.get('iptc_keywords'), True)

            self.command['prompt'] = p
            #print('after wildcard replace: ' + self.command['prompt'])

            # check for auto-dimensions
            orig_size = [self.command.get('width'), self.command.get('height')]
            if self.command.get('auto_size') == 'match_controlnet_image_size':
                if self.command.get('controlnet_input_image') != '':
                    new_size = utils.get_image_size(self.command.get('controlnet_input_image'))
                    if new_size != []:
                        self.command['width'] = new_size[0]
                        self.command['height'] = new_size[1]

            elif self.command.get('auto_size') == 'match_input_image_size':
                if self.command.get('input_image') != '':
                    new_size = utils.get_image_size(self.command.get('input_image'))
                    if new_size != []:
                        self.command['width'] = new_size[0]
                        self.command['height'] = new_size[1]

            elif self.command.get('auto_size') == 'match_controlnet_image_aspect_ratio':
                if self.command.get('controlnet_input_image') != '':
                    new_size = utils.match_image_aspect_ratio(self.command.get('controlnet_input_image'), orig_size)
                    if new_size != []:
                        self.command['width'] = new_size[0]
                        self.command['height'] = new_size[1]

            elif self.command.get('auto_size') == 'match_input_image_aspect_ratio':
                if self.command.get('input_image') != '':
                    new_size = utils.match_image_aspect_ratio(self.command.get('input_image'), orig_size)
                    if new_size != []:
                        self.command['width'] = new_size[0]
                        self.command['height'] = new_size[1]

            elif "resize_longest_dimension:" in self.command.get('auto_size'):
                new_long_dim = self.command.get('auto_size').split(':', 1)[1].strip()
                new_size = utils.resize_based_on_longest_dimension(new_long_dim, orig_size)
                if new_size != []:
                    self.command['width'] = new_size[0]
                    self.command['height'] = new_size[1]

            # check for ControlNet params
            use_controlnet = False
            scribble_mode = False
            cn_params = [64, 64, 64]
            img2img = False
            if control.sdi_controlnet_available and self.command.get('controlnet_input_image') != '' and (self.command.get('controlnet_model') != '' or 'reference' in self.command.get('controlnet_pre')):
                use_controlnet = True
                if self.command.get('input_image') != '':
                    img2img = True

                # encode CN image
                encoded = base64.b64encode(open(self.command.get('controlnet_input_image'), "rb").read())
                encodedString = str(encoded, encoding='utf-8')
                cn_img_payload = 'data:image/png;base64,' + encodedString

                # get preprocessor params
                if len(self.command.get('controlnet_pre')) >= 3:
                    found = False
                    for p in control.sdi_controlnet_preprocessors:
                        #if self.command.get('controlnet_pre').lower() == p[0]:
                        #    self.command['controlnet_pre'] = p[0]
                        #    cn_params = p[1]
                        #    break
                        if self.command.get('controlnet_pre').lower() == p.lower():
                            self.command['controlnet_pre'] = p
                            # these are the openpose defaults; not sure if these are needed
                            # TODO: investigate
                            cn_params = [512, 64, 64]
                            found = True
                            break
                    if not found:
                        self.command['controlnet_pre'] = 'none'
                else:
                    self.command['controlnet_pre'] = 'none'

                # check for auto-model from filename
                auto = self.command.get('controlnet_model').lower().strip()
                if auto.startswith('auto'):
                    cn_img = self.command.get('controlnet_input_image')
                    cn_img = utils.filename_from_abspath(cn_img)
                    auto_model = ''
                    # attempt to extract controlnet model from cn input file
                    if '-' in cn_img:
                        auto_model = cn_img.split('-', 1)[0]
                        validated = False
                        if len(auto_model) >= 3 and control.sdi_controlnet_models != None:
                            for m in control.sdi_controlnet_models:
                                if auto_model.lower() in m.lower():
                                    auto_model = m
                                    validated = True
                                    break
                            if not validated:
                                auto_model = ''
                        else:
                            auto_model = ''

                    if auto_model == '':
                        # couldn't get model from filename, check for default
                        if ',' in auto:
                            auto_model = auto.rsplit(',', 1)[1].strip()
                            validated = False
                            if len(auto_model) >= 3 and control.sdi_controlnet_models != None:
                                for m in control.sdi_controlnet_models:
                                    if auto_model.lower() in m.lower():
                                        auto_model = m
                                        validated = True
                                        break
                                if not validated:
                                    auto_model = ''
                            else:
                                auto_model = ''
                    if auto_model == '':
                        # failed to get model or default, disable CN
                        use_controlnet = False
                        self.print('WARNING: automatic ControlNet model specified, but unable to determine valid CN model from input image filename: ' + cn_img + '; disabling ControlNet!')
                    else:
                        # we have a valid model, use it
                        self.command['controlnet_model'] = auto_model

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
                  "tiling": self.command.get('tiling'),
                  "negative_prompt": str(self.command.get('neg_prompt')),
                  "alwayson_scripts": {}
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
                  "tiling": self.command.get('tiling'),
                  "negative_prompt": str(self.command.get('neg_prompt')),
                  "alwayson_scripts": {}
                }

                if self.command['highres_fix'] == 'yes':
                    if self.command.get('highres_upscaler') != '':
                        payload["hr_upscaler"] = str(self.command.get('highres_upscaler'))
                    if self.command.get('highres_ckpt_file') != '':
                        payload["hr_checkpoint_name"] = str(self.command.get('highres_ckpt_file'))
                    if self.command.get('highres_sampler') != '':
                        payload["hr_sampler_name"] = str(self.command.get('highres_sampler'))
                    if self.command.get('highres_prompt') != '':
                        if self.command.get('highres_prompt').lower().strip() == '<remove loras>':
                            # use the main prompt with loras/hypernets stripped out
                            mp = str(self.command.get('prompt'))

                            while '<lora:' in mp and '>' in mp:
                                p = mp
                                before = p.split('<lora:', 1)[0]
                                after = p.split('<lora:', 1)[1]
                                if '>' in after:
                                    after = after.split('>', 1)[1]
                                    mp = (before + after).strip()
                                else:
                                    mp = before.strip()

                            while '<hypernet:' in mp and '>' in mp:
                                p = mp
                                before = p.split('<hypernet:', 1)[0]
                                after = p.split('<hypernet:', 1)[1]
                                if '>' in after:
                                    after = after.split('>', 1)[1]
                                    mp = (before + after).strip()
                                else:
                                    mp = before.strip()

                            payload["hr_prompt"] = str(mp)
                        else:
                            if '<prompt>' in self.command.get('highres_prompt'):
                                self.command['highres_prompt'] = self.command.get('highres_prompt').replace('<prompt>', self.command.get('prompt'))
                            payload["hr_prompt"] = str(self.command.get('highres_prompt'))
                    if self.command.get('highres_neg_prompt') != '':
                        if '<neg_prompt>' in self.command.get('highres_neg_prompt'):
                            self.command['highres_neg_prompt'] = self.command.get('highres_neg_prompt').replace('<neg_prompt>', self.command.get('neg_prompt'))
                        payload["hr_negative_prompt"] = str(self.command.get('highres_neg_prompt'))
                    if self.command.get('highres_steps') != '':
                        payload["hr_second_pass_steps"] = self.command.get('highres_steps')
                    # add upscaling factor if necessary
                    if control.config.get('hires_fix_mode') == 'advanced':
                        if self.command.get('highres_scale_factor') == '':
                            # set default so we'll have it in metadata
                            self.command['highres_scale_factor'] = 2.0
                        payload["hr_scale"] = self.command.get('highres_scale_factor')
                else:
                    # remove these so they don't go into metadata when HR fix is disabled
                    self.command['highres_scale_factor'] = ''
                    self.command['highres_upscaler'] = ''
                    self.command['highres_ckpt_file'] = ''
                    self.command['highres_sampler'] = ''
                    self.command['highres_steps'] = ''
                    self.command['highres_prompt'] = ''
                    self.command['highres_neg_prompt'] = ''

            # add styles to payload if present
            if self.command.get('styles') != None and len(self.command.get('styles')) > 0:
                payload["styles"] = self.command.get('styles')

            # add refiner to payload if present
            if self.command.get('refiner_ckpt_file') != '':
                payload["refiner_checkpoint"] = str(self.command.get('refiner_ckpt_file'))
                if self.command.get('refiner_switch') != '':
                    payload["refiner_switch_at"] = self.command.get('refiner_switch')

            # add CN params to existing payload if ControlNet is enabled
            # https://github.com/Mikubill/sd-webui-controlnet/wiki/API
            if use_controlnet:
                cn_payload = {
                    "ControlNet": {
                        "args": [{
                            "input_image": cn_img_payload,
                            "mask": "",
                            "module": str(self.command.get('controlnet_pre')),
                            "model": str(self.command.get('controlnet_model')),
                            "weight": 1,
                            #"resize_mode": "Scale to Fit (Inner Fit)",
                            "lowvram": self.command.get('controlnet_lowvram'),
                            #"processor_res": cn_params[0],
                            #"threshold_a": cn_params[1],
                            #"threshold_b": cn_params[2],
                            "guidance_start": 0,
                            "guidance_end": 1,
                            "control_mode": str(self.command.get('controlnet_controlmode')),
                            "pixel_perfect": self.command.get('controlnet_pixelperfect')
                            #"guessmode": self.command.get('controlnet_guessmode')  # removed in CN extension v 1.1.09
                        }]
                    }
                }
                #payload["alwayson_scripts"] = cn_payload
                payload["alwayson_scripts"].update(cn_payload)

            # add ADetailer params to existing payload if ADetailer is enabled
            # https://github.com/Bing-su/adetailer/wiki/API
            if use_adetailer:
                ad_payload = utils.build_adetailer_payload(self.command)
                payload["alwayson_scripts"].update(ad_payload)

            # handle override settings here: clip_skip, vae, etc
            override_settings = {}
            if self.command.get('clip_skip') != '':
                override_settings["CLIP_stop_at_last_layers"] = int(self.command.get('clip_skip'))

            if self.command.get('input_image') == '' and self.command['highres_fix'] == 'yes' and self.command.get('highres_vae') != '':
                # BK 2023-09-26 revert, no separate Auto1111 VAE API setting
                #override_settings["sd_vae"] = str(self.command.get('highres_vae'))
                pass
            else:
                if self.command.get('vae') != '':
                    override_settings["sd_vae"] = self.command.get('vae')
                self.command['highres_vae'] = ''

            if override_settings != {}:
                payload["override_settings"] = override_settings

        else:
            # !MODE=process -specific stuff here
            process_mode = True
            original_exif = metadata.read_exif(self.command.get('input_image'))
            original_iptc = metadata.read_iptc(self.command.get('input_image'))

            if self.command['use_upscale'] == 'yes' and (self.command['upscale_model'] == 'sd' or self.command['upscale_model'] == 'ultimate'):
                # get original image parameters if we're doing a SD upscale
                original_details = ''
                if original_exif != None:
                    try:
                        original_details = original_exif[0x9c9c].decode('utf16')
                    except KeyError as e:
                        pass
                    else:
                        original_command = utils.extract_params_from_command(original_details)

            original_filename = utils.filename_from_abspath(self.command.get('input_image')).lower().strip()
            # remove extension
            original_filename = original_filename[:-4]

            # check for !OUTPUT_DIR, create if necessary
            if self.command.get('output_dir') != '':
                if not os.path.exists(self.command.get('output_dir')):
                    try:
                        # attempt to create output directory
                        Path(self.command.get('output_dir')).mkdir(parents=True, exist_ok=True)
                    except:
                        # error creating specified output_dir, fallback to default
                        self.print("Specified OUTPUT_DIR could not be created: " + self.command.get('output_dir'))
                        self.print("Using default output directory instead...")
                        self.command['output_dir'] = ''

        # !MODE = process enters here:
        command = utils.create_command(self.command, self.command.get('prompt_file'), self.worker['id'])
        if not process_mode:
            self.print("starting job #" + str(self.worker['jobs_done']+1) + ": " + command)
        else:
            self.print("starting job #" + str(self.worker['jobs_done']+1) + ": batch processing...")

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
        if control.config.get('debug_test_mode') and not process_mode:
            # simulate SD work
            work_time = round(random.uniform(2, 6), 2)
            time.sleep(work_time)
        else:
            # invoke SD
            if not process_mode:
                if self.command.get('input_image') != '':
                    if use_controlnet:
                        #self.worker['sdi_instance'].do_controlnet_img2img(payload, samples_dir)
                        self.worker['sdi_instance'].do_img2img(payload, samples_dir)
                    else:
                        self.worker['sdi_instance'].do_img2img(payload, samples_dir)
                else:
                    if use_controlnet:
                        #self.worker['sdi_instance'].do_controlnet_txt2img(payload, samples_dir)
                        self.worker['sdi_instance'].do_txt2img(payload, samples_dir)
                    else:
                        self.worker['sdi_instance'].do_txt2img(payload, samples_dir)
                while self.worker['sdi_instance'].busy and self.worker['sdi_instance'].isRunning:
                    time.sleep(0.25)

        # upscale here if requested
        if (self.worker['sdi_instance'].last_job_success or process_mode) and self.worker['sdi_instance'].isRunning:
            # only if we're not shutting down
            use_upscale = False
            if self.command['use_upscale'] == 'yes':
                use_upscale = True

            if use_upscale or use_adetailer:
                if use_upscale:
                    self.worker['work_state'] = 'upscaling'
                elif use_adetailer:
                    self.worker['work_state'] = 'adetailer'
                else:
                    self.worker['work_state'] = 'processing'
                gpu_id = self.worker['id'].replace("cuda:", "")

                if control.config.get('debug_test_mode'):
                    # simulate upscaling work
                    work_time = round(random.uniform(0.5, 2), 2)
                    time.sleep(work_time)
                else:
                    new_files = []
                    if not process_mode:
                        # upscale all newly-generated images for non-process mode
                        new_files = os.listdir(samples_dir)
                    else:
                        # if process mode, upscale the designated image
                        new_files.append(self.command.get('input_image'))
                    if len(new_files) > 0:
                        # invoke ESRGAN on entire directory
                        #utils.upscale(self.command['upscale_amount'], samples_dir, self.command['upscale_face_enh'], gpu_id)

                        # upscale each image
                        if not process_mode:
                            self.worker['sdi_instance'].log('upscaling images...')
                        else:
                            if use_upscale:
                                self.worker['sdi_instance'].log('upscaling ' + self.command.get('input_image') + '...')
                            elif use_adetailer:
                                self.worker['sdi_instance'].log('adetailer: ' + self.command.get('input_image') + '...')
                            else:
                                self.worker['sdi_instance'].log('processing ' + self.command.get('input_image') + '...')
                        for file in new_files:
                            encoded = None
                            if not process_mode:
                                encoded = base64.b64encode(open(os.path.join(samples_dir, file), "rb").read())
                            else:
                                # this whole process_mode thread is pretty hacky...
                                encoded = base64.b64encode(open(self.command.get('input_image'), "rb").read())
                            encodedString = str(encoded, encoding='utf-8')
                            img_payload = 'data:image/png;base64,' + encodedString
                            if use_upscale:
                                if self.command['upscale_model'] != 'sd' and self.command['upscale_model'] != 'ultimate':
                                    # normal upscale
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
                                        "upscaler_1": self.command['upscale_model'],
                                        #"upscaler_2": "None",
                                        #"extras_upscaler_2_visibility": 0,
                                        #"upscale_first": false,
                                        "image": img_payload
                                    }
                                    self.worker['sdi_instance'].do_upscale(payload, samples_dir)
                                else:
                                    # SD upscale uses img2img
                                    # use whatever params we can find in original image

                                    sd_sampler = str(self.command.get('sampler'))
                                    if "sampler" in original_command:
                                        sd_sampler = original_command['sampler']
                                        # validate sampler in case we're upscaling very old images
                                        if control.prompt_manager != None:
                                            # TODO: should instantiate new prompt_manager if we don't have one yet
                                            sd_sampler = control.prompt_manager.validate_sampler(sd_sampler, True)

                                    sd_vae = str(self.command.get('vae'))
                                    if "vae" in original_command:
                                        sd_vae = original_command['vae']

                                    sd_prompt = str(self.command.get('prompt'))
                                    if "prompt" in original_command:
                                        sd_prompt = original_command['prompt']

                                    sd_neg_prompt = str(self.command.get('neg_prompt'))
                                    if "neg_prompt" in original_command:
                                        sd_neg_prompt = original_command['neg_prompt']

                                    sd_seed = str(self.command.get('seed'))
                                    if "seed" in original_command:
                                        try:
                                            sd_seed = int(original_command['seed'])
                                        except:
                                            pass

                                    sd_steps = self.command.get('steps')
                                    if "steps" in original_command:
                                        try:
                                            sd_steps = int(original_command['steps'])
                                        except:
                                            pass

                                    sd_scale = self.command.get('scale')
                                    if "scale" in original_command:
                                        try:
                                            sd_scale = float(original_command['scale'])
                                        except:
                                            pass

                                    sd_tiling = self.command.get('tiling')
                                    if "tiling" in original_command:
                                        if original_command['tiling'] == 'yes':
                                            sd_tiling = True
                                        else:
                                            sd_tiling = False

                                    # grab styles from original command and put into list
                                    styles = []
                                    if "styles" in original_command:
                                        if original_command['styles'] != '':
                                            temp = original_command['styles'].split(',')
                                            for t in temp:
                                                styles.append(t.strip())

                                    # calculate max output size for sd_upscale
                                    orig_width = 0
                                    orig_height = 0
                                    sd_width = 512
                                    sd_height = 512
                                    if self.command['upscale_model'] == 'sd':
                                        with Image.open(self.command.get('input_image')) as img:
                                            orig_width, orig_height = img.size

                                        set_max_output_size = control.config.get('max_output_size')

                                        # check for overrides in process mode directives
                                        if self.command.get('override_max_output_size') != 0:
                                            set_max_output_size = int(self.command.get('override_max_output_size'))
                                        new_dimensions = utils.get_largest_possible_image_size([orig_width, orig_height], set_max_output_size, True)

                                        if new_dimensions != []:
                                            sd_width = new_dimensions[0]
                                            sd_height = new_dimensions[1]
                                            self.command['width'] = sd_width
                                            self.command['height'] = sd_height
                                        else:
                                            control.print('Error: SD upscale unable to find appropriate upscale size under MAX_OUTPUT_SIZE for ' + str(self.command.get('input_image')) + '!')

                                    if self.command.get('override_steps') != 0:
                                        sd_steps = self.command.get('override_steps')

                                    if self.command.get('override_sampler') != '':
                                        sd_sampler = self.command.get('override_sampler')

                                    # check if a model change is needed before upscaling
                                    sd_model = str(self.command.get('ckpt_file'))
                                    if "ckpt_file" in original_command:
                                        sd_model = original_command['ckpt_file']
                                        sd_model = control.validate_model(sd_model)

                                        # check if we're overriding the model for upscaling
                                        override_model = ''
                                        if self.command.get('override_ckpt_file') != '':
                                            override_model = control.validate_model(self.command.get('override_ckpt_file'))
                                            if override_model != '':
                                                sd_model = override_model

                                        # check if a refiner model is available if necessary
                                        if override_model == '':
                                            if control.config.get('auto_use_refiner'):
                                                refiner_model = original_command['ckpt_file'].replace('.safetensors', '').replace('.ckpt', '')
                                                if '[' in refiner_model:
                                                    refiner_model = refiner_model.split('[', 1)[0].strip()
                                                refiner_model = refiner_model + '_refiner'
                                                refiner_model = control.validate_model(refiner_model)
                                                if refiner_model != '':
                                                    sd_model = refiner_model

                                    if sd_model != '' and (sd_model != self.worker['sdi_instance'].model_loaded):
                                        self.worker['sdi_instance'].load_model(sd_model)
                                        while self.worker['sdi_instance'].options_change_in_progress:
                                            # wait for model change to complete
                                            time.sleep(0.25)

                                    payload = {
                                      "init_images": [img_payload],
                                      "sampler_index": str(sd_sampler),
                                      #"resize_mode": 0,
                                      "denoising_strength": self.command.get('upscale_sd_strength'),
                                      "prompt": str(sd_prompt),
                                      "seed": str(sd_seed),
                                      "batch_size": 1,
                                      "n_iter": 1,
                                      "steps": sd_steps,
                                      "cfg_scale": sd_scale,
                                      "width": sd_width,
                                      "height": sd_height,
                                      #"restore_faces": False,
                                      "tiling": sd_tiling,
                                      "negative_prompt": sd_neg_prompt,
                                      "alwayson_scripts": {}
                                    }

                                    # add styles to payload if present
                                    if styles != []:
                                        payload["styles"] = styles

                                    override_settings = {}
                                    if self.command.get('clip_skip') != '':
                                        override_settings["CLIP_stop_at_last_layers"] = int(self.command.get('clip_skip'))

                                    if self.command.get('override_vae') != '':
                                        override_settings["sd_vae"] = self.command.get('override_vae')
                                    else:
                                        if override_model == '':
                                            if sd_vae != '':
                                                override_settings["sd_vae"] = sd_vae

                                    if override_settings != {}:
                                        payload["override_settings"] = override_settings

                                    # add additional sd_ultimate_upscale params if necessary
                                    if self.command['upscale_model'] == 'ultimate':
                                        up_index = control.get_upscale_model_index(self.command['upscale_ult_model'])
                                        if up_index == -1:
                                            up_index = control.get_upscale_model_index('ESRGAN_4x')
                                            if up_index == -1:
                                                up_index = 0

                                        custom_scale = 2.0
                                        if 'upscale_amount' in self.command and float(self.command['upscale_amount']) > 1.0:
                                            custom_scale = self.command['upscale_amount']
                                        custom_scale = float(custom_scale)

                                        # docs: https://github.com/Coyote-A/ultimate-upscale-for-automatic1111
                                        payload["script_name"] = "ultimate sd upscale"
                                        payload["script_args"] = [
                                        	"",            # (not used)
                                        	512,           # tile_width
                                        	512,           # tile_height
                                        	8,             # mask_blur
                                        	32,            # padding
                                        	64,            # seams_fix_width
                                        	0.35,          # seams_fix_denoise
                                        	32,            # seams_fix_padding
                                        	up_index,      # upscaler_index
                                        	True,          # save_upscaled_image a.k.a Upscaled
                                        	0,             # redraw_mode
                                        	False,         # save_seams_fix_image a.k.a Seams fix
                                        	8,             # seams_fix_mask_blur
                                        	0,             # seams_fix_type
                                        	2,             # target_size_type (0 = From img2img2 settings, 1 = Custom size, 2 = Scale from image size)
                                        	2048,          # custom_width
                                        	2048,          # custom_height
                                        	custom_scale   # custom_scale
                                        ]

                                    # add adetailer if specified
                                    if use_adetailer:
                                        ad_payload = utils.build_adetailer_payload(self.command, True)
                                        payload["alwayson_scripts"].update(ad_payload)

                                    self.worker['sdi_instance'].do_img2img(payload, samples_dir)
                            else:
                                # We're just doing ADetailer; no upscale...
                                payload = {
                                  "init_images": [img_payload],
                                  "alwayson_scripts": {}
                                }
                                ad_payload = utils.build_adetailer_payload(self.command, True)
                                payload["alwayson_scripts"].update(ad_payload)
                                self.worker['sdi_instance'].do_img2img(payload, samples_dir)

                            while self.worker['sdi_instance'].busy and self.worker['sdi_instance'].isRunning:
                                time.sleep(0.25)

                        # remove originals if upscaled version present
                        if not process_mode:
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
                new_files = []
                if exists(samples_dir):
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
                            if self.command['upscale_model'] == 'sd':
                                upscale_text += 'via SD upscale: to ' + str(sd_width) + 'x' + str(sd_height) + ' @ ' + str(self.command.get('upscale_sd_strength')) + ' strength)'
                            elif self.command['upscale_model'] == 'ultimate':
                                upscale_text += 'via SD ultimate upscale: ' + str(self.command.get('upscale_amount')) + 'x using ' + self.command['upscale_ult_model'] + ' @ ' + str(self.command.get('upscale_sd_strength')) + ' strength)'
                            else:
                                upscale_text += str(self.command['upscale_amount']) + "x via " + self.command['upscale_model'] + ")"

                        ad_text = ""
                        if use_adetailer:
                            ad_text = " (ADetailer applied: "
                            ad_text += str(self.command.get('adetailer_model')) + ' @ ' + str(self.command.get('adetailer_strength')) + ' strength)'


                        pngImage = PngImageFile(samples_dir + "/" + f)
                        im = pngImage.convert('RGB')
                        exif = None
                        if not process_mode:
                            exif = im.getexif()
                            exif[0x9286] = meta_prompt
                            exif[0x9c9c] = meta_prompt.encode('utf16')
                            exif[0x0131] = "https://github.com/rbbrdckybk/dream-factory"
                        else:
                            exif = original_exif
                        exif[0x9c9d] = ('AI art' + upscale_text + ad_text).encode('utf16')

                        newfilename = ''
                        if self.command['filename'] != '':
                            # user specified custom filename format

                            model = self.command.get('ckpt_file')
                            model = model.split('[', 1)[0].strip()
                            if '\\' in model:
                                model = model.rsplit('\\', 1)[1].strip()
                            if '/' in model:
                                model = model.rsplit('/', 1)[1].strip()
                            if '.' in model:
                                model = model.rsplit('.', 1)[0].strip()

                            cn_model = ''
                            if self.command.get('controlnet_model') != '':
                                cn_model = self.command.get('controlnet_model')
                                cn_model = cn_model.split('[', 1)[0].strip()
                                if '.' in cn_model:
                                    cn_model = cn_model.rsplit('.', 1)[0].strip()

                            cn_img = ''
                            if self.command.get('controlnet_input_image') != '':
                                cn_img = self.command.get('controlnet_input_image')
                                cn_img = utils.filename_from_abspath(cn_img)[:-4]

                            input_img = ''
                            if self.command.get('input_image') != '':
                                input_img = self.command.get('input_image')
                                input_img = utils.filename_from_abspath(input_img)[:-4]

                            hr_model = ''
                            if self.command.get('highres_ckpt_file') != '':
                                hr_model = self.command.get('highres_ckpt_file')
                                hr_model = hr_model.split('[', 1)[0].strip()
                                if '\\' in hr_model:
                                    hr_model = hr_model.rsplit('\\', 1)[1].strip()
                                if '/' in hr_model:
                                    hr_model = hr_model.rsplit('/', 1)[1].strip()
                                if '.' in hr_model:
                                    hr_model = hr_model.rsplit('.', 1)[0].strip()

                            ad_model = ''
                            if self.command.get('adetailer_model') != '':
                                ad_model = self.command.get('adetailer_model')
                                ad_model = ad_model.split('[', 1)[0].strip()
                                if '\\' in ad_model:
                                    ad_model = ad_model.rsplit('\\', 1)[1].strip()
                                if '/' in ad_model:
                                    ad_model = ad_model.rsplit('/', 1)[1].strip()
                                if '.' in ad_model:
                                    ad_model = ad_model.rsplit('.', 1)[0].strip()

                            styles = ''
                            style_count = 0
                            if len(self.command.get('styles')) > 0:
                                for style in self.command.get('styles'):
                                    if style_count > 0:
                                        styles += '_'
                                    styles += style.replace('Style: ', '').strip()
                                    style_count += 1

                            newfilename = self.command['filename']
                            if not process_mode:
                                try:
                                    newfilename = re.sub('<prompt>', self.command.get('prompt'), newfilename, flags=re.IGNORECASE)
                                    newfilename = re.sub('<neg-prompt>', self.command.get('neg_prompt'), newfilename, flags=re.IGNORECASE)
                                except:
                                    pass
                                newfilename = re.sub('<scale>', str(self.command.get('scale')), newfilename, flags=re.IGNORECASE)
                                newfilename = re.sub('<strength>', str(self.command.get('strength')), newfilename, flags=re.IGNORECASE)
                                newfilename = re.sub('<seed>', str(self.command.get('seed')), newfilename, flags=re.IGNORECASE)
                                newfilename = re.sub('<steps>', str(self.command.get('steps')), newfilename, flags=re.IGNORECASE)
                                newfilename = re.sub('<width>', str(self.command.get('width')), newfilename, flags=re.IGNORECASE)
                                newfilename = re.sub('<height>', str(self.command.get('height')), newfilename, flags=re.IGNORECASE)
                                newfilename = re.sub('<sampler>', self.command.get('sampler'), newfilename, flags=re.IGNORECASE)
                                newfilename = re.sub('<model>', model, newfilename, flags=re.IGNORECASE)
                                newfilename = re.sub('<cn-img>', cn_img, newfilename, flags=re.IGNORECASE)
                                newfilename = re.sub('<cn-model>', cn_model, newfilename, flags=re.IGNORECASE)
                                newfilename = re.sub('<hr-model>', hr_model, newfilename, flags=re.IGNORECASE)
                                newfilename = re.sub('<styles>', styles, newfilename, flags=re.IGNORECASE)
                            else:
                                # these are only applicable to upscale process jobs
                                newfilename = re.sub('<upscale-model>', self.command.get('upscale_model'), newfilename, flags=re.IGNORECASE)
                                newfilename = re.sub('<upscale-sd-strength>', str(self.command.get('upscale_sd_strength')), newfilename, flags=re.IGNORECASE)

                            newfilename = re.sub('<date>', dt.now().strftime('%Y%m%d'), newfilename, flags=re.IGNORECASE)
                            newfilename = re.sub('<time>', dt.now().strftime('%H%M%S'), newfilename, flags=re.IGNORECASE)
                            newfilename = re.sub('<date-year>', dt.now().strftime('%Y'), newfilename, flags=re.IGNORECASE)
                            newfilename = re.sub('<date-month>', dt.now().strftime('%m'), newfilename, flags=re.IGNORECASE)
                            newfilename = re.sub('<date-day>', dt.now().strftime('%d'), newfilename, flags=re.IGNORECASE)
                            newfilename = re.sub('<input-img>', input_img, newfilename, flags=re.IGNORECASE)
                            if str(self.command.get('adetailer_strength')) != '':
                                newfilename = re.sub('<ad-strength>', str(self.command.get('adetailer_strength')), newfilename, flags=re.IGNORECASE)
                            if ad_model != '':
                                newfilename = re.sub('<ad-model>', ad_model, newfilename, flags=re.IGNORECASE)

                            # remove all unrecognized variables
                            #opening_braces = '<'
                            #closing_braces = '>'
                            #non_greedy_wildcard = '.*?'
                            #re.sub(f'[{opening_braces}]{non_greedy_wildcard}[{closing_braces}]', '', newfilename)

                            # limit filename length
                            newfilename = newfilename[:200]

                            # make the final name filesystem-safe
                            newfilename = utils.slugify(newfilename)

                            x = 0
                            testname = newfilename
                            while exists(output_dir + "/" + testname + ".jpg"):
                                testname = newfilename + '-' + str(x)
                                x += 1
                            newfilename = testname
                        else:
                            # use default filename format
                            newfilename = dt.now().strftime('%Y%m%d-%H%M%S-') + str(nf_count)
                            nf_count += 1

                        quality = control.config.get('jpg_quality')
                        #output_fn = output_dir + "/" + newfilename + ".jpg"
                        output_fn = os.path.join(output_dir, newfilename + ".jpg")
                        if process_mode and self.command.get('output_dir') != '':
                            output_fn =os.path.join(self.command.get('output_dir'), newfilename + ".jpg")

                        try:
                            im.save(output_fn, exif=exif, quality=quality)
                        except:
                            self.print("OS error when attempting to save output image!")

                        iptc_append = False
                        if process_mode:
                            # re-attach original iptc info
                            metadata.attach_iptc_info(output_fn, original_iptc)
                            if self.command.get('iptc_append'):
                                iptc_append = True

                        # add IPTC metadata if necesary
                        if (self.command.get('iptc_title') != ''
                                or self.command.get('iptc_description') != ''
                                or self.command.get('iptc_keywords') != []
                                or self.command.get('iptc_copyright') != ''):

                            if not iptc_append:
                                metadata.write_iptc_info(output_fn,
                                    self.command.get('iptc_title'),
                                    self.command.get('iptc_description'),
                                    self.command.get('iptc_keywords'),
                                    self.command.get('iptc_copyright'))
                            else:
                                metadata.write_iptc_info_append(output_fn,
                                    self.command.get('iptc_title'),
                                    self.command.get('iptc_description'),
                                    self.command.get('iptc_keywords'),
                                    self.command.get('iptc_copyright'))

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
        self.upscale_work_queue = deque()           # higher-priority queue for upscales, never cleared
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
        #self.sdi_setup_request_made = False        # made this worker-level
        self.sdi_sampler_request_made = False
        self.sdi_samplers = None
        self.models_filename = 'model-triggers.txt'
        self.model_trigger_words = None
        self.sdi_model_request_made = False
        self.sdi_models = None                      # 2023-05-30 changed to list of dicts
        self.sdi_hypernetwork_request_made = False
        self.sdi_hypernetworks = None               # 2023-05-30 changed to list of dicts
        self.sdi_lora_request_made = False
        self.sdi_loras = None                       # replaced self.loras with this, list of dicts
        self.sdi_VAE_request_made = False
        self.sdi_VAEs = None                        # list of dicts
        self.sdi_style_request_made = False
        self.sdi_styles = None                      # list of dicts
        self.embeddings = []                        # 2023-05-30 changed to list of dicts
        self.poses = []                             # [ path, [filename, str(WxH img dimensions), str(preview ext: '', 'jpg', 'png')] ]
        self.sdi_upscaler_request_made = False
        self.sdi_upscalers = None
        self.sdi_controlnet_available = False
        self.sdi_controlnet_request_made = False
        self.sdi_controlnet_pre_request_made = False
        self.sdi_controlnet_models = None
        self.sdi_controlnet_preprocessors = None
        self.sdi_script_request_made = False
        self.sdi_txt2img_scripts = None
        self.sdi_img2img_scripts = None
        self.sdi_ultimate_upscale_available = False
        self.sdi_adetailer_available = False
        self.wildcards = None
        self.default_model_validated = False
        self.max_output_size = 0
        self.civitai_startup_done = False
        self.civitai_new_stage = False
        self.civitai_startup_stage = 0
        # for queuing multiple models to apply to prompt files
        self.models = []
        self.model_index = 0
        self.highres_models = []
        self.highres_model_index = 0

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

        # do an initial read of user-installed files
        self.read_wildcards()
        self.read_embeddings()
        #self.read_loras()          # 2023-05-30 API call now available for this
        self.init_controlnet()


    # clean up empty output dirs
    def clean_output_subdirs(self, directory):
        for entry in os.scandir(directory):
            if os.path.isdir(entry.path) and not os.listdir(entry.path):
                try:
                    # try to remove an entry output sub-dir
                    os.rmdir(entry.path)
                except:
                    pass


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
        if self.config['wildcard_location'] != '' and os.path.exists(self.config['wildcard_location']):
            for x in os.listdir(self.config['wildcard_location']):
                if x.endswith('.txt'):
                    key = x.replace('.txt', '').strip()
                    #print(key) + ' :'
                    # read the contents of the wildcard file
                    with open(os.path.join(self.config['wildcard_location'], x), encoding = 'utf-8') as f:
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
        self.embeddings = []
        embed_dir = os.path.join(self.config['sd_location'], 'embeddings')
        if os.path.exists(embed_dir):
            # get root dir files
            for x in os.listdir(embed_dir):
                if x.endswith('.pt') or x.endswith('.bin') or x.endswith('.safetensors'):
                    dict = {}
                    dict['name'] = x.replace('.pt', '').replace('.bin', '').replace('.safetensors', '')
                    dict['path'] = os.path.join(embed_dir, x)
                    self.embeddings.append(dict)

            # 2023-06-04 get subdir files
            for entry in os.scandir(embed_dir):
                if entry.is_dir():
                    subdir = os.path.join(embed_dir, entry.name)
                    for subdir_entry in os.scandir(subdir):
                       if subdir_entry.is_file():
                           x = subdir_entry.name.lower()
                           if x.endswith('.pt') or x.endswith('.bin') or x.endswith('.safetensors'):
                               dict = {}
                               dict['name'] = x.replace('.pt', '').replace('.bin', '').replace('.safetensors', '')
                               dict['path'] = os.path.join(subdir, subdir_entry.name)
                               self.embeddings.append(dict)

        #self.embeddings.sort()
        self.embeddings = sorted(self.embeddings, key=lambda d: d['name'].lower())


    # checks for user lora files in Auto1111 embeddings dir
    # 2023-02-28 BK there is no API request for these; doing this instead
    # 2023-05-30 BK API call now available, no longer using this
    def read_loras(self):
        self.loras = []
        lora_dir = os.path.join(self.config['sd_location'], 'models')
        lora_dir = os.path.join(lora_dir, 'Lora')
        if os.path.exists(lora_dir):
            for x in os.listdir(lora_dir):
                if x.endswith('.pt') or x.endswith('.bin') or x.endswith('.safetensors'):
                    self.loras.append(x)
        self.loras.sort()


    # if civitai_integration is enabled in config,
    # handle calculating hashes of all embeddings, loras, models, hypernets
    # use hashes to perform lookups on civitai.com & cache info for each
    # runs on background threads while GPUs do work
    def civitai_startup(self):
        if self.config['civitai_use']:
            cache_dir = 'cache'

            # do LoRA hashes
            if self.civitai_startup_stage == 0:
                # build list of loras that exist but aren't in hash cache
                loras = []
                for l in self.sdi_loras:
                    if 'path' in l:
                        loras.append(l['path'])
                missing_loras = self.missing_models(loras, os.path.join(cache_dir, 'hashes-lora.txt'))

                # start a worker to calculate hashes for missing models and add to cache
                if len(missing_loras) > 0:
                    self.print('Starting background hash calculations for ' + str(len(missing_loras)) + ' LoRA files without cache file entries...')
                    worker = civitai.BackgroundWorker(self, self.config['debug_civitai'], 'LoRA')
                    worker.hashcalc_start(missing_loras)
                else:
                    self.civitai_startup_stage += 1
                    self.civitai_new_stage = True

            # do embedding hashes
            elif self.civitai_startup_stage == 1:
                embeddings = []
                embed_dir = os.path.join(self.config['sd_location'], 'embeddings')
                for e in self.embeddings:
                    #filename = os.path.basename(e['path'])
                    #embeddings.append(os.path.join(embed_dir, filename))
                    embeddings.append(e['path'])
                missing_embeddings = self.missing_models(embeddings, os.path.join(cache_dir, 'hashes-embedding.txt'))

                # start a worker to calculate hashes for missing models and add to cache
                if len(missing_embeddings) > 0:
                    self.print('Starting background hash calculations for ' + str(len(missing_embeddings)) + ' embedding files without cache file entries...')
                    worker = civitai.BackgroundWorker(self, self.config['debug_civitai'], 'embedding')
                    worker.hashcalc_start(missing_embeddings)
                else:
                    self.civitai_startup_stage += 1
                    self.civitai_new_stage = True

            # do model hashes
            elif self.civitai_startup_stage == 2:
                models = []
                model_dir = os.path.join(self.config['sd_location'], 'models')
                model_dir = os.path.join(model_dir, 'Stable-diffusion')
                for m in self.sdi_models:
                    short_name = m['name']
                    if '[' in short_name:
                        short_name = short_name.split('[', 1)[0].strip()
                    models.append(os.path.join(model_dir, short_name))
                missing_models = self.missing_models(models, os.path.join(cache_dir, 'hashes-model.txt'))

                # check model-triggers.txt for hashes that Auto1111 has already calculated
                if exists('model-triggers.txt'):
                    # in case the user has no loras or embeddings but does have a model-triggers file
                    skip = False
                    if not os.path.exists('cache'):
                        try:
                            Path('cache').mkdir(parents=True, exist_ok=True)
                        except:
                            skip = True

                    # proceed if there were no issues creating cache directory
                    if not skip:
                        cache_file = os.path.join(cache_dir, 'hashes-model.txt')
                        lines = ""
                        with open('model-triggers.txt', 'r', encoding="utf-8") as f:
                            lines = f.readlines()

                        found_models = []
                        for x in missing_models:
                            filename = os.path.basename(x)
                            found = False
                            for line in lines:
                                if filename in line:
                                    if '[' in line and ']' in line:
                                        # retrieve hash and insert into cache
                                        hash = line.split('[', 1)[1].strip()
                                        hash = hash.split(']', 1)[0].strip()

                                        with open(cache_file, 'a', encoding="utf-8") as f:
                                            f.write(filename + ', ' + hash + '\n')

                                        # save so we can remove when we're done iterating
                                        found_models.append(x)
                                        break

                    # remove founds from list of missing models
                    for m in found_models:
                        missing_models.remove(m)

                # start a worker to calculate hashes for missing models and add to cache
                if len(missing_models) > 0:
                    self.print('Starting background hash calculations for ' + str(len(missing_models)) + ' model files without cache file entries...')
                    worker = civitai.BackgroundWorker(self, self.config['debug_civitai'], 'model')
                    worker.hashcalc_start(missing_models)
                else:
                    self.civitai_startup_stage += 1
                    self.civitai_new_stage = True

            # do hypernet hashes
            elif self.civitai_startup_stage == 3:
                hypernets = []
                for h in self.sdi_hypernetworks:
                    if 'path' in h:
                        hypernets.append(h['path'])
                missing_hypernets = self.missing_models(hypernets, os.path.join(cache_dir, 'hashes-hypernet.txt'))

                # start a worker to calculate hashes for missing models and add to cache
                if len(missing_hypernets) > 0:
                    self.print('Starting background hash calculations for ' + str(len(missing_hypernets)) + ' hypernet files without cache file entries...')
                    worker = civitai.BackgroundWorker(self, self.config['debug_civitai'], 'hypernetwork')
                    worker.hashcalc_start(missing_hypernets)
                else:
                    self.civitai_startup_stage += 1
                    self.civitai_new_stage = True


            # do lora civitai lookups
            elif self.civitai_startup_stage == 4:
                # build list of lora hashes that exist but aren't in civitai lookup cache
                hashes = self.fetch_hashes(os.path.join(cache_dir, 'hashes-lora.txt'))
                missing_hashes = self.missing_hashes(hashes, os.path.join(cache_dir, 'civitai-lora.txt'))

                # start a worker to perform lookups on civitai.com for missing hashes
                if len(missing_hashes) > 0:
                    self.print('Starting background civitai.com lookups for ' + str(len(missing_hashes)) + ' LoRA hashes without cache file entries...')
                    worker = civitai.BackgroundWorker(self, self.config['debug_civitai'], 'LoRA')
                    worker.civitai_lookup_start(missing_hashes)
                else:
                    self.civitai_startup_stage += 1
                    self.civitai_new_stage = True

            # do embedding civitai lookups
            elif self.civitai_startup_stage == 5:
                hashes = self.fetch_hashes(os.path.join(cache_dir, 'hashes-embedding.txt'))
                missing_hashes = self.missing_hashes(hashes, os.path.join(cache_dir, 'civitai-embedding.txt'))

                # start a worker to perform lookups on civitai.com for missing hashes
                if len(missing_hashes) > 0:
                    self.print('Starting background civitai.com lookups for ' + str(len(missing_hashes)) + ' embedding hashes without cache file entries...')
                    worker = civitai.BackgroundWorker(self, self.config['debug_civitai'], 'embedding')
                    worker.civitai_lookup_start(missing_hashes)
                else:
                    self.civitai_startup_stage += 1
                    self.civitai_new_stage = True

            # do model civitai lookups
            elif self.civitai_startup_stage == 6:
                hashes = self.fetch_hashes(os.path.join(cache_dir, 'hashes-model.txt'))
                missing_hashes = self.missing_hashes(hashes, os.path.join(cache_dir, 'civitai-model.txt'))

                # start a worker to perform lookups on civitai.com for missing hashes
                if len(missing_hashes) > 0:
                    self.print('Starting background civitai.com lookups for ' + str(len(missing_hashes)) + ' model hashes without cache file entries...')
                    worker = civitai.BackgroundWorker(self, self.config['debug_civitai'], 'model')
                    worker.civitai_lookup_start(missing_hashes)
                else:
                    self.civitai_startup_stage += 1
                    self.civitai_new_stage = True

            # do hypernet civitai lookups
            elif self.civitai_startup_stage == 7:
                hashes = self.fetch_hashes(os.path.join(cache_dir, 'hashes-hypernet.txt'))
                missing_hashes = self.missing_hashes(hashes, os.path.join(cache_dir, 'civitai-hypernet.txt'))

                # start a worker to perform lookups on civitai.com for missing hashes
                if len(missing_hashes) > 0:
                    self.print('Starting background civitai.com lookups for ' + str(len(missing_hashes)) + ' hypernetwork hashes without cache file entries...')
                    worker = civitai.BackgroundWorker(self, self.config['debug_civitai'], 'hypernetwork')
                    worker.civitai_lookup_start(missing_hashes)
                else:
                    self.civitai_startup_stage += 1
                    self.civitai_new_stage = True

            # all hashing/lookups are complete;
            # load all civitai info back into appropriate dictionaries
            else:
                self.load_civitai_info_from_cache("model", self.sdi_models)
                self.load_civitai_info_from_cache("lora", self.sdi_loras)
                self.load_civitai_info_from_cache("hypernet", self.sdi_hypernetworks)
                self.load_civitai_info_from_cache("embedding", self.embeddings)

                # all civitai work complete
                self.civitai_new_stage = False
                self.civitai_startup_stage = 999

        else:
            self.civitai_new_stage = False
            self.civitai_startup_stage = 999
            self.print('Civitai integration disabled via config.txt; skipping civitai.com lookup checks...')


    # returns the short subdir of a given model path
    # e.g. full path minus the base path of SD
    def model_subdir(self, full_path):
        sd_path = self.config['sd_location']
        path = full_path.replace(sd_path, '')

        if '\\models\\lora\\' in path.lower():
            path = re.sub('\\\\models\\\\lora\\\\', '', path, flags=re.IGNORECASE)
        if '/models/lora/' in path.lower():
            path = re.sub('/models/lora/', '', path, flags=re.IGNORECASE)

        if '\\models\\hypernetworks\\' in path.lower():
            path = re.sub('\\\\models\\\\hypernetworks\\\\', '', path, flags=re.IGNORECASE)
        if '/models/hypernetworks/' in path.lower():
            path = re.sub('/models/hypernetworks/', '', path, flags=re.IGNORECASE)

        if '\\embeddings\\' in path.lower():
            path = re.sub('\\\\embeddings\\\\', '', path, flags=re.IGNORECASE)
        if '/embeddings/' in path.lower():
            path = re.sub('/embeddings/', '', path, flags=re.IGNORECASE)

        return path


    # loads civitai info from cache directory
    # model_type_desc is "model", "lora", "hypernet", "embedding"
    # list_ref corresponds to the list of dicts for that model_type_desc
    def load_civitai_info_from_cache(self, model_type_desc, list_ref, suppress_warnings=False):
        cache_dir = 'cache'
        hash_file = 'hashes-' + model_type_desc + '.txt'
        cache_file = 'civitai-' + model_type_desc + '.txt'
        hash_path = os.path.join(cache_dir, hash_file)
        cache_path = os.path.join(cache_dir, cache_file)
        passed = True
        if not exists(hash_path):
            if not suppress_warnings:
                self.print('warning: ' + model_type_desc + ' hash file not found!')
            passed = False
        if not exists(cache_path):
            if not suppress_warnings:
                self.print('warning: ' + model_type_desc + ' cache file not found!')
            passed = False

        if passed:
            # read hash and cache files into memory
            hash_lines = ''
            with open(hash_path, encoding = 'utf-8') as f:
                hash_lines = f.readlines()
            cache_lines = ''
            with open(cache_path, encoding = 'utf-8') as f:
                cache_lines = f.readlines()

            # iterate through each file in ref list and look for hash in hash file
            for x in list_ref:
                list_name = x['name']
                if model_type_desc.lower() == 'model':
                    if '[' in list_name:
                        list_name = list_name.split('[', 1)[0].strip()

                name = os.path.basename(list_name)
                for line in hash_lines:
                    if name in line:
                        # found line containing hash info
                        hash = line.split(',', 1)[1].strip()
                        x['hash'] = hash
                        break

            # iterate through each file in ref list and try to match
            # assigned hash with entry in civitai cache file
            for x in list_ref:
                if 'hash' in x:
                    hash = x['hash']
                    for line in cache_lines:
                        if hash in line:
                            # found line containing cache info
                            if ';' in line:
                                info = line.split(';')
                                # try to read info into list_ref dict
                                try:
                                    x['civitai_id'] = info[1].strip()
                                    x['civitai_title'] = info[2].strip()
                                    x['civitai_base_model'] = info[3].strip()
                                    x['civitai_nsfw'] = False
                                    if info[4].lower().strip() == 'nsfw':
                                        x['civitai_nsfw'] = True
                                    x['civitai_triggers'] = []
                                    if info[5].strip() != '':
                                         triggers = info[5].split(',')
                                         for t in triggers:
                                             t = t.replace('\n', '').strip()
                                             x['civitai_triggers'].append(t)
                                    if 'lora' in model_type_desc.lower() or 'hypernet' in model_type_desc.lower():
                                        x['civitai_weight'] = info[6].replace('\n', '').strip()
                                except:
                                    pass
                            break


    # returns list of models that exist but aren't in hash cache
    # full_list is a list of filenames (can be full paths, will be shortened)
    # cache_location is path to corresponding cache file
    def missing_models(self, full_list, cache_location):
        missing = []
        if exists(cache_location):
            lines = ""
            with open(cache_location, 'r', encoding="utf-8") as f:
                lines = f.readlines()
            for x in full_list:
                filename = os.path.basename(x)
                found = False
                for line in lines:
                    if filename in line:
                        found = True
                        break
                if not found:
                    missing.append(x)
        else:
            # no cache, assume everything is missing
            missing = full_list
        return missing

    # returns list of hashes that exist but aren't in hash cache
    # full_list is a list of hashes
    # cache_location is path to corresponding cache file
    def missing_hashes(self, full_list, cache_location):
        missing = []
        if exists(cache_location):
            lines = ""
            with open(cache_location, 'r', encoding="utf-8") as f:
                lines = f.readlines()
            for x in full_list:
                found = False
                for line in lines:
                    if x in line:
                        found = True
                        break
                if not found:
                    missing.append(x)
        else:
            # no cache, assume everything is missing
            missing = full_list
        return missing

    # get list of hashes from specified cache file
    def fetch_hashes(self, cache_location):
        hashes = []
        if exists(cache_location):
            lines = ""
            with open(cache_location, 'r', encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines:
                if ',' in line:
                    hash = line.split(',', 1)[1].strip()
                    hashes.append(hash)
        return hashes

    # checks for presense of controlnet extension
    def init_controlnet(self):
        cn_dir = os.path.join(self.config['sd_location'], 'extensions')
        cn_dir = os.path.join(cn_dir, 'sd-webui-controlnet')
        if os.path.exists(cn_dir):
            # controlnet extension appears to be installed
            self.sdi_controlnet_available = True
            self.print('ControlNet extension found; enabling ControlNet functionality...')

            # 2023-04-16 API now supports this
            # build preprocesor list manually - no API call for this currently
            #pre = []
            #pre.append(['none', [64, 64, 64]])
            #pre.append(['canny', [512, 100, 200]])
            #pre.append(['depth', [384, 64, 64]])
            #pre.append(['hed', [512, 64, 64]])
            #pre.append(['mlsd', [512, 0.1, 0.1]])
            #pre.append(['normal_map', [512, 0.4, 64]])
            #pre.append(['openpose', [512, 64, 64]])
            #pre.append(['scribble', [512, 64, 64]])
            #pre.append(['segmentation', [512, 64, 64]])
            #self.sdi_controlnet_preprocessors = pre

            # read/init pose files
            if os.path.exists('poses'):
                self.poses = []
                root_files = []
                for entry in os.scandir('poses'):
                    if entry.is_dir() and entry.name != 'previews':
                        # scan subdirs
                        files = []
                        subdir = os.path.join('poses', entry.name)
                        for entry in os.scandir(subdir):
                           if entry.is_file() and (entry.name.lower().endswith('.png') or entry.name.lower().endswith('.jpg')):
                               size = ''
                               try:
                                   with Image.open(os.path.join(subdir, entry.name)) as img:
                                       width, height = img.size
                                       size = str(width) + 'x' + str(height)
                               except:
                                   size = ''
                               if size != '':
                                   preview = ''
                                   preview_dir = os.path.join(subdir, 'previews')
                                   if os.path.exists(os.path.join(preview_dir, entry.name[:-3] + 'jpg')):
                                       preview = 'jpg'
                                   elif os.path.exists(os.path.join(preview_dir, entry.name[:-3] + 'png')):
                                       preview = 'png'
                                   files.append([entry.name, size, preview])
                        if len(files) > 0:
                            files.sort()
                            self.poses.append([subdir, files])

                    else:
                        # scan root
                        if entry.is_file() and (entry.name.lower().endswith('.png') or entry.name.lower().endswith('.jpg')):
                            size = ''
                            try:
                               with Image.open(os.path.join('poses', entry.name)) as img:
                                   width, height = img.size
                                   size = str(width) + 'x' + str(height)
                            except:
                               size = ''
                            if size != '':
                                preview = ''
                                preview_dir = os.path.join('poses', 'previews')
                                if os.path.exists(os.path.join(preview_dir, entry.name[:-3] + 'jpg')):
                                   preview = 'jpg'
                                elif os.path.exists(os.path.join(preview_dir, entry.name[:-3] + 'png')):
                                   preview = 'png'
                                root_files.append([entry.name, size, preview])
            if len(root_files) > 0:
                root_files.sort()
                self.poses.append(['poses', root_files])

            self.poses.sort()

            #for x in self.poses:
            #    print(x[0])
            #    for f in x[1]:
            #        print('   ' + f[0] + ' (' + f[1] + '), ' + str(f[2]))

        else:
            # controlnet extension not available
            self.sdi_controlnet_available = False
            self.print('ControlNet extension not found; disabling ControlNet functionality...')


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
            'wildcard_location' : 'prompts/wildcards',
            'output_location' : 'output',
            'use_gpu_devices' : 'auto',
            'webserver_use' : True,
            'civitai_use' : True,
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
            'debug_civitai' : False,
            'random_queue_size' : 50,
            'editor_max_styling_chars' : 80000,
            'jpg_quality' : 88,
            'max_output_size' : 0,
            'auto_use_refiner' : True,
            'hires_fix_mode' : 'simple',

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
            'upscale_sd_strength' : 0.3,
            'upscale_override_ckpt_file' : '',
            'upscale_model' : "ESRGAN_4x",
            'ckpt_file' : "",
            'filename' : "",

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
                            #value = value.replace('/', os.path.sep)
                            #value = value.replace('\\', os.path.sep)
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

                    elif command == 'civitai_integration':
                        if value == 'yes' or value == 'no':
                            if value == 'yes':
                                self.config.update({'civitai_use' : True})
                            else:
                                self.config.update({'civitai_use' : False})

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

                    elif command == 'editor_max_styling_chars':
                        try:
                            int(value)
                        except:
                            print("*** WARNING: specified 'EDITOR_MAX_STYLING_CHARS' is not a valid number; it will be ignored!")
                        else:
                            self.config.update({'editor_max_styling_chars' : int(value)})

                    elif command == 'jpg_quality':
                        try:
                            int(value)
                        except:
                            print("*** WARNING: specified 'JPG_QUALITY' is not a valid number; it will be ignored!")
                        else:
                            if int(value) > 0 and int(value) <= 100:
                                self.config.update({'jpg_quality' : int(value)})
                            else:
                                print("*** WARNING: specified 'JPG_QUALITY' value must be between 1-100!")

                    elif command == 'hires_fix_mode':
                        value = value.lower()
                        if value == 'simple' or value == 'advanced':
                            self.config.update({'hires_fix_mode' : value})
                        else:
                            print("*** WARNING: specified 'HIRES_FIX_MODE' value not recognized; defaulting to simple!")
                            self.config.update({'hires_fix_mode' : 'simple'})

                    elif command == 'max_output_size':
                        value = value.replace(',', '').strip()
                        if value != '':
                            try:
                                int(value)
                            except:
                                print("*** WARNING: specified 'MAX_OUTPUT_SIZE' is not a valid number; it will be ignored!")
                            else:
                                if int(value) > 262144:
                                    self.config.update({'max_output_size' : int(value)})
                                else:
                                    print("*** WARNING: specified 'MAX_OUTPUT_SIZE' is too low; it will be ignored!")

                    elif command == 'auto_use_refiner':
                        if value == 'yes' or value == 'no':
                            if value == 'yes':
                                self.config.update({'auto_use_refiner' : True})
                            else:
                                self.config.update({'auto_use_refiner' : False})

                    elif command == 'debug_test_mode':
                        if value == 'yes' or value == 'no':
                            if value == 'yes':
                                self.config.update({'debug_test_mode' : True})
                            else:
                                self.config.update({'debug_test_mode' : False})

                    elif command == 'debug_civitai':
                        if value == 'yes' or value == 'no':
                            if value == 'yes':
                                self.config.update({'debug_civitai' : True})
                            else:
                                self.config.update({'debug_civitai' : False})

                    elif command == 'pf_auto_insert_model_trigger':
                        if value == 'start' or value == 'end' or value == 'first_comma' or value == 'off' or 'keyword:' in value:
                            self.config.update({'auto_insert_model_trigger' : value})

                    elif command == 'pf_neg_prompt':
                        self.config.update({'neg_prompt' : value})

                    elif command == 'pf_highres_fix':
                        if value == 'yes' or value == 'no':
                            self.config.update({'highres_fix' : value})

                    elif command == 'random_queue_size':
                        try:
                            int(value)
                        except:
                            print("*** WARNING: specified 'RANDOM_QUEUE_SIZE' is not a valid number; it will be ignored!")
                        else:
                            # shouldn't need to queue more than this ever
                            if int(value) > 1000:
                                value = '1000'
                            self.config.update({'random_queue_size' : int(value)})

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

                    elif command == 'pf_upscale_sd_strength':
                        try:
                            float(value)
                        except:
                            print("*** WARNING: specified 'PF_UPSCALE_SD_STRENGTH' is not a valid number; it will be ignored!")
                        else:
                            self.config.update({'upscale_sd_strength' : float(value)})

                    elif command == 'pf_upscale_keep_org':
                        if value == 'yes' or value == 'no':
                            self.config.update({'upscale_keep_org' : value})

                    elif command == 'pf_upscale_model':
                        # this is validated after we receive valid upscalers from the server
                        self.config.update({'upscale_model' : value})

                    elif command == 'pf_ckpt_file':
                        # this is validated after we receive valid models from the server
                        self.config.update({'ckpt_file' : value})

                    elif command == 'pf_upscale_override_ckpt_file':
                        # this is validated after we receive valid models from the server
                        self.config.update({'upscale_override_ckpt_file' : value})

                    elif command == 'pf_filename':
                        self.config.update({'filename' : value})

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

            # clean up empty output subdirs
            self.clean_output_subdirs(self.config.get('output_location'))

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
                'sdi_setup_request_made' : False, \
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
                'sdi_setup_request_made' : True, \
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

        # check for a multiple models scenario
        # BK 2023-10-30
        check_main = False
        if len(self.highres_models) > 0:
            # we have multiple high-res models, iterate through all of them
            # before switching main model
            if self.highres_model_index < len(self.highres_models)-1:
                self.highres_model_index += 1
            else:
                self.highres_model_index = 0
                check_main = True
            new_model = self.highres_models[self.highres_model_index]
            self.prompt_manager.config['highres_ckpt_file'] = new_model
        else:
            check_main = True

        if check_main and len(self.models) > 0:
            # a models list was preserved, need to switch to next ckpt
            # move to next model
            if self.model_index < len(self.models)-1:
                self.model_index += 1
            else:
                self.model_index = 0
            new_model = self.models[self.model_index]
            self.prompt_manager.config['ckpt_file'] = new_model
        else:
            if self.model_index < 0:
                # handle start case when both are at -1 and main won't be checked
                self.model_index = 0

        # process mode
        if self.prompt_manager.config.get('mode') == 'process':
            self.work_queue = self.prompt_manager.build_process_work()
            self.orig_work_queue_size = len(self.work_queue)

        # random mode; queue up a few random prompts
        elif self.prompt_manager.config.get('mode') == 'random':
            for i in range(self.config['random_queue_size']):
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
        # if we haven't validated models/etc, defer loading
        if not self.default_model_validated:
            self.print("Waiting for model initialization to finish before loading requested prompt file...")
            opt.prompt_file = new_file
        else:
            if self.prompt_file != '':
                # clean up empty output subdirs on every prompt file switch
                self.clean_output_subdirs(self.config.get('output_location'))

            # clear model queues
            self.models = []
            self.model_index = 0
            self.highres_models = []
            self.highres_model_index = 0

            self.clear_work_queue()

            self.read_wildcards()
            self.prompt_file = new_file
            self.prompt_manager = utils.PromptManager(self)

            self.prompt_manager.handle_config()
            self.input_manager = utils.InputManager(self.prompt_manager.config.get('random_input_image_dir'))

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
        buffer += "!SAMPLER = " + str(self.config['sampler']) + "             # sampler to use; press ctrl+h for reference\n"
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

        if self.config['ckpt_file'] != '':
            buffer += "!CKPT_FILE = " + str(self.config['ckpt_file']) +	"   # config.txt default; press ctrl+h for reference\n"
        else:
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
        web_path = web_path.replace('%20', ' ')
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


    # upscale a gallery image
    def upscale_gallery_img(self, web_path):
        # lazy copy paste from delete_gallery_img ...
        web_path = web_path.replace('%20', ' ')
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
            actual_file = os.path.basename(actual_path)
            if self.config['max_output_size'] > 0:
                upscale_dir = os.path.join(self.config['output_location'], "upscaled")
                if not os.path.exists(os.path.join(upscale_dir, actual_file)):
                    # check if this file is already queued for upscaling
                    found = False
                    for w in self.upscale_work_queue:
                        f = os.path.basename(w['input_image'])
                        if f == actual_file:
                            found = True
                            break
                    # check if a worker is already working on this
                    for w in self.workers:
                        if w["job_prompt_info"] != '':
                            f = os.path.basename(str(w["job_prompt_info"].get('input_image')))
                            if f == actual_file:
                                if w["job_prompt_info"].get('prompt') == 'df_gallery_upscale':
                                    found = True
                                    break
                    if not found:
                        # queue the actual upscale
                        prompt_manager = utils.PromptManager(self, False)
                        work = prompt_manager.config.copy()
                        work['prompt_file'] = ''
                        work['mode'] = 'process'
                        work['input_image'] = actual_path
                        work['use_upscale'] = 'yes'
                        work['override_ckpt_file'] = self.config['upscale_override_ckpt_file']
                        work['upscale_model'] = 'sd'
                        work['output_dir'] = upscale_dir
                        work['filename'] = '<input-img>'
                        work['prompt'] = 'df_gallery_upscale'
                        self.upscale_work_queue.append(work.copy())
                        response = actual_file + " queued for upscaling!"
                        if self.is_paused:
                            self.is_paused = False
                    else:
                        response = actual_file + " is already queued for upscaling!"
                else:
                    response = actual_file + " has already been upscaled!"
            else:
                response = "Upscale not enabled; set MAX_OUTPUT_SIZE in config.txt!"
        else:
            # shouldn't happen
            response = "Error: " + actual_file + " not found!"
        return response


    # checks for updated model strings from server
    # non-empty return value indicates the local txt file should be updated
    def hash_check(self, old_model, new_model):
        retval = ''
        if ',' in old_model:
            pre_old = old_model.split(',', 1)[0]
            post_old = old_model.split(',', 1)[1]

            if pre_old != new_model:
                #print('Models do not match!: ' + pre_old + ', ' + new_model)
                retval = new_model + ',' + post_old
                #print(' -> Should be updated to: ' + retval)
            else:
                #print('Models match: ' + pre_old + ', ' + new_model)
                pass

        return retval

    # sets the list of SD models available
    # also creates/updates the model/trigger file
    def update_models(self, models):
        self.sdi_models = models
        if exists(self.models_filename):
            # already exists, check the models we already have in the file
            with open(self.models_filename, 'r', encoding="utf-8") as f:
                lines = f.readlines()

            # scan to see if any on the server are missing from the file
            missing = []
            updates = []
            for m in models:
                found = False
                for line in lines:
                    # remove hash from m if present for compare
                    compare_m = m['name']
                    if '[' in m['name'] and ']' in m['name']:
                        compare_m = m['name'].split('[', 1)[0].strip()
                    if compare_m in line:
                        found = True
                        new_line = self.hash_check(line, m['name'])
                        if new_line != '':
                            updates.append([line, new_line])
                        break
                if not found:
                    missing.append(m['name'])

            # handle updates if necessary
            if len(updates) > 0:
                # first make a backup of the existing model-triggers.txt file
                try:
                    if exists(self.models_filename + '.bak'):
                        os.remove(self.models_filename + '.bak')
                    os.rename(self.models_filename, self.models_filename + '.bak')
                except:
                    print('Error creating backup of model-triggers.txt!')

                with open(self.models_filename, 'w', encoding="utf-8") as f:
                    for line in lines:
                        found = False
                        for update in updates:
                            if update[0] == line:
                                found = True
                                f.write(update[1])
                                break
                        if not found:
                            f.write(line)

            # append missing models to file
            with open(self.models_filename, 'a', encoding="utf-8") as f:
                for new_m in missing:
                    pass
                    f.write(new_m + ', \n')

        else:
            # creating for the first time
            with open(self.models_filename, 'w', encoding="utf-8") as f:
                f.write('# Dream Factory model-trigger.txt file\n')
                f.write('# This contains a list of all SD models available for use in Dream Factory.\n')
                f.write('# Append the trigger word/phrase after the comma following each model to\n')
                f.write('# allow Dream Factory to automatically add it to your prompts when using the model!\n\n')
                for m in models:
                    f.write(m + ', \n')

        # build trigger words dict
        self.model_trigger_words = {}
        with open(self.models_filename, 'r', encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            if not line.startswith('#') and line.strip() != '' and line.strip() != '\n':
                model = line.split(',', 1)[0].strip()
                trigger = line.split(',', 1)[1].strip()
                if trigger != '':
                    self.model_trigger_words[model] = trigger

        # validate default override upscale model if there is one:
        if self.config['upscale_override_ckpt_file'] != '':
            model = self.config['upscale_override_ckpt_file']
            validated_model = self.validate_model(model)
            if validated_model != '':
                self.config['upscale_override_ckpt_file'] = validated_model
                self.print('[controller] >>> default upscale override model validated: ' + self.config['upscale_override_ckpt_file'])
            else:
                self.config['upscale_override_ckpt_file'] = ''
                self.print("*** WARNING: config.txt file command PF_UPSCALE_OVERRIDE_CKPT_FILE value (" + model + ") doesn't match any server values; ignoring it! ***")

        # validate default model if there is one:
        if self.config['ckpt_file'] != '':
            model = self.config['ckpt_file']
            validated_model = self.validate_model(model)
            if validated_model != '':
                self.config['ckpt_file'] = validated_model
                self.print('[controller] >>> default model validated: ' + self.config['ckpt_file'])
            else:
                self.config['ckpt_file'] = ''
                self.print("*** WARNING: config.txt file command PF_CKPT_FILE value (" + model + ") doesn't match any server values; ignoring it! ***")
        self.default_model_validated = True


    def check_default_upscaler(self):
        # validate default upscaler if there is one:
        if self.config['upscale_model'] != 'ESRGAN_4x':
            model = self.config['upscale_model']
            validated_model = self.validate_upscale_model(model)
            if validated_model != '':
                self.config['upscale_model'] = validated_model
                self.print('[controller] >>> default upscaler validated: ' + self.config['upscale_model'])
            else:
                self.config['upscale_model'] = 'ESRGAN_4x'
                self.print("*** WARNING: config.txt file command PF_UPSCALE_MODEL value (" + model + ") doesn't match any server values; ignoring it! ***")


    # passing models must be exactly what SD expects; use this to make sure
    # user-supplied model is ok - otherwise revert to default
    def validate_model(self, model):
        validated_model = ''
        if len(model) > 5:
            if self.sdi_models != None:
                for m in self.sdi_models:
                    if model.lower() in m['name'].lower():
                        # case-insensitive partial match; use the exact casing from the server
                        validated_model = m['name']
                        break
        return validated_model


    # passing VAEs must be exactly what SD expects; use this to make sure
    # user-supplied model is ok - otherwise revert to default
    def validate_VAE(self, model):
        validated_model = ''
        if len(model) > 3:
            if self.sdi_VAEs != None:
                for m in self.sdi_VAEs:
                    if model.lower() in m['name'].lower():
                        # case-insensitive partial match; use the exact casing from the server
                        validated_model = m['name']
                        break
        return validated_model


    # passing styles must be exactly what SD expects; use this to make sure
    # user-supplied style is ok - otherwise revert to default
    def validate_style(self, style):
        validated_style = ''
        if len(style) > 1:
            if self.sdi_styles != None:
                for s in self.sdi_styles:
                    if style.lower() in s['name'].lower():
                        # case-insensitive partial match; use the exact casing from the server
                        validated_style = s['name']
                        break
        return validated_style


    # passing models must be exactly what SD expects; use this to make sure
    # user-supplied model is ok - otherwise revert to default
    def validate_upscale_model(self, model):
        validated_model = ''
        if len(model) >= 3:
            if model.lower() == 'ultimate':
                if self.sdi_ultimate_upscale_available:
                    validated_model = 'ultimate'
                else:
                    self.print("*** WARNING: You may not use !UPSCALE_MODEL = ULTIMATE unless the sd_ultimate_upscale extension is installed in Auto1111! ***")
            elif self.sdi_upscalers != None:
                for m in self.sdi_upscalers:
                    if model.lower() in m.lower():
                        # case-insensitive partial match; use the exact casing from the server
                        validated_model = m
                        break
        elif model.lower() == 'sd':
            # allow 'sd' for SD upscaling if the user has specified a max output size
            if self.config['max_output_size'] > 0:
                validated_model = 'sd'
            else:
                self.print("*** WARNING: You may not use !UPSCALE_MODEL = SD without setting MAX_OUTPUT_SIZE in your Dream Factory config.txt first! ***")
        return validated_model


    # same as above, only validates actual server values - for sd_ultimate_upscale
    def validate_ultimate_upscale_model(self, model):
        validated_model = ''
        if len(model) >= 3:
            if self.sdi_upscalers != None:
                for m in self.sdi_upscalers:
                    if model.lower() in m.lower():
                        # case-insensitive partial match; use the exact casing from the server
                        validated_model = m
                        break
        return validated_model


    # gets the server index of a given upscaler - for sd_ultimate_upscale
    # should only be passing previously validated model names here
    def get_upscale_model_index(self, model):
        index = -1
        if self.sdi_upscalers != None:
            try:
                index = self.sdi_upscalers.index(model)
            except:
                index = -1
        return index


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

    # main work loop
    while not control.work_done:
        # check for un-initialized workers
        for worker in control.workers:
            if not worker['sdi_instance'].init:
                if control.current_active_inits() < control.config['gpu_init_stagger']:
                    # init this worker as long as we're not already at the init limit
                    worker['sdi_instance'].initialize()

        # do background civitai hash/lookup work
        if not control.civitai_startup_done \
                and control.default_model_validated \
                and control.sdi_hypernetworks is not None \
                and control.sdi_loras is not None:
            # start background hashes and civitai lookups if civitai integration is enabled
            control.civitai_startup_done = True
            control.civitai_new_stage = False

            # do an initial cache load, another will be done after all lookups complete
            control.load_civitai_info_from_cache("model", control.sdi_models, True)
            control.load_civitai_info_from_cache("lora", control.sdi_loras, True)
            control.load_civitai_info_from_cache("hypernet", control.sdi_hypernetworks, True)
            control.load_civitai_info_from_cache("embedding", control.embeddings, True)

            control.civitai_startup()

        if control.civitai_startup_done and control.civitai_new_stage and control.civitai_startup_stage <= 20:
            # work through various stages of background work for civitai integration
            # stages are incremented via callbacks as worker threads finish the prior stage
            control.civitai_new_stage = False
            control.civitai_startup()

        # check for idle workers
        worker = control.get_idle_gpu_worker()
        skip = False

        if worker != None:
            #if not control.sdi_setup_request_made:
            if not worker['sdi_setup_request_made']:
                # sets initial config options necessary for Dream Factory to operate
                worker['sdi_instance'].set_initial_options(control.config.get('hires_fix_mode'))
                worker['sdi_setup_request_made'] = True
                skip = True

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

            if not control.sdi_lora_request_made:
                # get available loras from the server
                # when the first worker is ready
                #worker['sdi_instance'].update_server_loras()
                worker['sdi_instance'].get_server_loras()
                control.sdi_lora_request_made = True
                skip = True

            if not control.sdi_VAE_request_made:
                # get available VAEs from the server
                # when the first worker is ready
                worker['sdi_instance'].get_server_VAEs()
                control.sdi_VAE_request_made = True
                skip = True

            if not control.sdi_style_request_made:
                # get available styles from the server
                # when the first worker is ready
                worker['sdi_instance'].get_server_styles()
                control.sdi_style_request_made = True
                skip = True

            if not control.sdi_script_request_made:
                # get available scripts from the server
                # when the first worker is ready
                worker['sdi_instance'].get_server_scripts()
                control.sdi_script_request_made = True
                skip = True

            if not control.sdi_upscaler_request_made:
                # get available upscalers from the server
                # when the first worker is ready
                worker['sdi_instance'].get_server_upscalers()
                control.sdi_upscaler_request_made = True
                skip = True

            if not control.sdi_controlnet_request_made and control.sdi_controlnet_available:
                # get available controlnet models from the server
                # when the first worker is ready
                worker['sdi_instance'].get_server_controlnet_models()
                control.sdi_controlnet_request_made = True
                skip = True

            if not control.sdi_controlnet_pre_request_made and control.sdi_controlnet_available:
                # get available controlnet modules from the server
                # when the first worker is ready
                worker['sdi_instance'].get_server_controlnet_modules()
                control.sdi_controlnet_pre_request_made = True
                skip = True

            # worker is idle, start some work
            if not control.is_paused and not skip and control.default_model_validated:
                # load initial prompt file if specified
                if opt.prompt_file != "":
                    if exists(opt.prompt_file):
                        control.new_prompt_file(opt.prompt_file)
                    else:
                        control.print("ERROR: specified prompt file '" + opt.prompt_file + "' does not exist - load one from the control panel instead!")
                    opt.prompt_file = ""

                if len(control.upscale_work_queue) > 0:
                    # check for gallery upscale jobs in the queue
                    new_work = control.upscale_work_queue.popleft()
                    control.do_work(worker, new_work)
                elif len(control.work_queue) > 0:
                    # get a new prompt or setting directive from the queue
                    new_work = control.work_queue.popleft()
                    control.do_work(worker, new_work)
                else:
                    # if we're in random prompts mode, re-fill the queue
                    if control.prompt_manager != None and control.prompt_manager.config.get('mode') == 'random':
                        control.print('adding more random prompts to the work queue...')
                        control.init_work_queue()
                    else:
                        should_stop = False
                        # check for multiple model scenario, should go through all once
                        if not control.repeat_jobs:
                            if len(control.models) > 0:
                                if control.model_index == len(control.models)-1:
                                    # we've reached the end of the models list
                                    # check that we've also reached the end of the highres list if present
                                    if len(control.highres_models) > 0:
                                        if control.highres_model_index == len(control.highres_models)-1:
                                            should_stop = True
                                    else:
                                        should_stop = True
                            elif len(control.highres_models) > 0:
                                if control.highres_model_index == len(control.highres_models)-1:
                                    should_stop = True
                            else:
                                # not running multiple models, stop here
                                should_stop = True

                        if should_stop:
                            # check if user specified a prompt file to load upon completion
                            if control.prompt_manager != None and control.prompt_manager.config.get('next_prompt_file') != "":
                                fname = utils.filename_from_abspath(control.prompt_manager.config.get('next_prompt_file'))
                                control.print("all work done; loading next specified prompt file: " + str(fname))
                                control.new_prompt_file(control.prompt_manager.config.get('next_prompt_file'))
                            else:
                                # all work done and no follow-up prompt file specified
                                control.is_paused = True
                                # no more jobs, wait for all workers to finish
                                if control.jobs_done > 0:
                                    control.print('No more work in queue; waiting for all workers to finish...')
                                while control.num_workers_working() > 0:
                                    time.sleep(.05)
                                if control.jobs_done > 0:
                                    control.print('All work done; pausing server - add some more work via the control panel!')
                                else:
                                    control.print('Startup complete; GPU worker(s) ready - queue some work via the control panel!')
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
