# Copyright 2021 - 2023, Bill Kennedy (https://github.com/rbbrdckybk/dream-factory)
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
import glob
import os
import itertools
import copy
from zipfile import ZipFile
from os.path import exists, isdir, basename
from datetime import datetime as dt
from datetime import date
from pathlib import Path
from collections import deque
from PIL import Image
from PIL.PngImagePlugin import PngImageFile, PngInfo


# maintains the info in each input file [prompt] section
class PromptSection():
    def __init__(self, tokens, min_pick, max_pick, delim):
        self.tokens = tokens
        self.min_pick = min_pick
        self.max_pick = max_pick
        self.delim = delim

    def debug_print(self):
        print("\n*** Printing contents of PromptSection: ***")
        print("min pick: " + str(self.min_pick))
        print("max pick: " + str(self.max_pick))
        print("delim: (" + self.delim + ')')
        if len(self.tokens) > 0:
            print("tokens:")
            for x in self.tokens:
                print(">> " + x)
        else:
            print("tokens list is empty")
        print('\n')

# for easy management of input files
# input_path is the directory of the input images to use
class InputManager():
    def __init__(self, input_path):
        # a list of all the files we're using as inputs
        self.files = list()
        self.input_path = ""

        if input_path != "":
            self.input_path = input_path

            # populate the list with the given init directory
            for x in os.listdir(self.input_path):
                if x.endswith('.jpg') or x.endswith('.png'):
                    self.files.append(x)

    # pick a random file from the list
    def pick_random(self):
        if len(self.files) > 0:
            x = random.randint(0, len(self.files)-1)
            full_path = os.path.join(self.input_path, self.files[x])
            return full_path
        else:
            return ""

    def debug_print_files(self):
        if len(self.files) > 0:
            print("Listing " + str(len(self.files)) + " total files in '" + self.input_directory + "':")
            for x in self.files:
                print(x)
        else:
            print("Input image directory '" + self.input_directory + "' is empty; input images will not be used.")

# for easy management of prompts
class PromptManager():
    def __init__(self, control_ref):
        # reference to control obj, lazy but it'll do for now
        self.control = control_ref

        # dictionary of config info w/ initial defaults
        self.config = {}
        self.reset_config_defaults()

        # list for config info
        self.conf = list()
        # list of PromptSection
        self.prompts = list()

        self.__init_config(self.conf, "config")
        self.__init_prompts(self.prompts, "prompts")

        #self.debug_print()

    # init the prompts list
    def __init_prompts(self, which_list, search_text):
        with open(self.control.prompt_file, encoding = 'utf-8') as f:
            lines = f.readlines()

            found_header = False
            search_header = '[' + search_text

            tokens = list()
            ps = PromptSection(tokens, 1, 1, self.config.get('delim'))

            # find the search text and read until the next search header
            for line in lines:
                # ignore comments and strip whitespace
                line = line.strip().split('#', 1)
                line = line[0]

                # if we already found the header we want and we see another header,
                if found_header and len(line) > 0 and line.startswith('['):
                    # save PromptSection if not empty
                    if len(ps.tokens) > 0:
                        which_list.append(ps)

                    # start a new PS
                    tokens = list()
                    ps = PromptSection(tokens, 1, 1,self.config.get('delim'))

                    # look for next prompt section
                    found_header = False

                # found the search header
                if search_header.lower() in line.lower() and line.endswith(']'):
                    found_header = True

                    # check for optional args
                    args = line.strip(search_header).strip(']').strip()
                    vals = shlex.split(args, posix=False)

                    # grab min/max args
                    if len(vals) > 0:
                        if '-' in vals[0]:
                            minmax = vals[0].split('-')
                            if len(minmax) > 0:
                                ps.min_pick = minmax[0].strip()
                                if len(minmax) > 1:
                                    ps.max_pick = minmax[1].strip()
                        else:
                            ps.min_pick = vals[0]
                            ps.max_pick = vals[0]

                        # grab delim arg
                        if len(vals) > 1:
                            if vals[1].startswith('\"') and vals[1].endswith('\"'):
                                ps.delim = vals[1].strip('\"')

                    line = ""

                if len(line) > 0 and found_header:
                    ps.tokens.append(line)

            # save final PromptSection if not empty
            if len(ps.tokens) > 0:
                which_list.append(ps)


    # init the config list
    def __init_config(self, which_list, search_text):
        with open(self.control.prompt_file, encoding = 'utf-8') as f:
            lines = f.readlines()

            search_header = '[' + search_text + ']'
            found_header = False

            # find the search text and read until the next search header
            for line in lines:
                # ignore comments and strip whitespace
                line = line.strip().split('#', 1)
                line = line[0]

                # if we already found the header we want and we see another header, stop
                if found_header and len(line) > 0 and line[0] == '[':
                    break

                # found the search header
                if search_header.lower() == line.lower():
                    found_header = True
                    line = ""

                if len(line) > 0 and found_header:
                    #print(search_header + ": " + line)
                    which_list.append(line)


    # resets config options back to defaults
    def reset_config_defaults(self):
        self.control.repeat_jobs = False
        self.config = {
            'mode' : "standard",
            'seed' : -1,
            'width' : self.control.config['width'],
            'height' : self.control.config['height'],
            'auto_size' : 'off',
            'steps' : self.control.config['steps'],
            'scale' : self.control.config['scale'],
            'min_scale' : 7.5,
            'max_scale' : 7.5,
            'samples' : self.control.config['samples'],
            'batch_size' : 1,
            'input_image' : "",
            'random_input_image_dir' : "",
            'controlnet_input_image' : "",
            'controlnet_pre' : "none",
            'controlnet_model' : "",
            'controlnet_lowvram' : False,
            'strength' : 0.75,
            'min_strength' : 0.75,
            'max_strength' : 0.75,
            'delim' : " ",
            'next_prompt_file' : "",
            'iptc_title' : "",
            'iptc_title_history' : {},
            'iptc_description' : "",
            'iptc_description_history' : {},
            'iptc_keywords' : [],
            'iptc_keywords_history' : {},
            'iptc_copyright' : "",
            'iptc_append' : False,
            'clip_skip' : "",
            'ckpt_file' : self.control.config['ckpt_file'],
            'sampler' : self.control.config['sampler'],
            'neg_prompt' : "",
            'neg_prompt' : self.control.config['neg_prompt'],
            'highres_fix' : self.control.config['highres_fix'],
            'auto_insert_model_trigger' : self.control.config['auto_insert_model_trigger'],
            'use_upscale' : self.control.config['use_upscale'],
            'upscale_amount' : self.control.config['upscale_amount'],
            'upscale_codeformer_amount' : self.control.config['upscale_codeformer_amount'],
            'upscale_gfpgan_amount' : self.control.config['upscale_gfpgan_amount'],
            'upscale_keep_org' : self.control.config['upscale_keep_org'],
            'upscale_model' : self.control.config['upscale_model'],
            'filename' : self.control.config['filename'],
            'output_dir' : '',
            'outdir' : self.control.config['output_location']
        }

    def debug_print(self):
        if len(self.prompts) > 0:
            print("\nPS contents:\n")
            for x in self.prompts:
                x.debug_print()
        else:
            print("prompts list is empty")


    # handle prompt file config directives
    def handle_directive(self, command, value):
        if command == 'width':
            if value != '':
                try:
                    int(value)
                except:
                    self.control.print("*** WARNING: specified 'WIDTH' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'width' : value})

        elif command == 'height':
            if value != '':
                try:
                    int(value)
                except:
                    self.control.print("*** WARNING: specified 'HEIGHT' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'height' : value})

        elif command == 'auto_size':
            value = value.lower().strip()
            if value == 'off' or value == '':
                self.config.update({'auto_size' : 'off'})
            elif value == 'match_controlnet_image_size' or value == 'match_controlnet_image_aspect_ratio':
                self.config.update({'auto_size' : value})
            elif value == 'match_input_image_size' or value == 'match_input_image_aspect_ratio':
                self.config.update({'auto_size' : value})
            elif 'resize_longest_dimension:' in value:
                dimension = value.split(':', 1)[1].strip()
                try:
                    int(dimension)
                except:
                    self.control.print("*** WARNING: invalid dimension supplied (" + value + ") for !AUTO_SIZE; it will be ignored!")
                else:
                    self.config.update({'auto_size' : value})
            else:
                self.control.print("*** WARNING: specified 'AUTO_SIZE' value (" + value + ") not understood; it will be ignored!")

        elif command == 'auto_insert_model_trigger':
            if value == 'start' or value == 'end' or value == 'first_comma' or value == 'off' or 'keyword:' in value:
                self.config.update({'auto_insert_model_trigger' : value})

        elif command == 'highres_fix':
            if value == 'yes' or value == 'no':
                self.config.update({'highres_fix' : value})

        elif command == 'seed':
            if value != '':
                try:
                    int(value)
                except:
                    self.control.print("*** WARNING: specified 'SEED' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'seed' : value})

        elif command == 'steps':
            if value != '':
                try:
                    int(value)
                except:
                    self.control.print("*** WARNING: specified 'STEPS' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'steps' : value})

        elif command == 'scale':
            if value != '':
                try:
                    float(value)
                except:
                    self.control.print("*** WARNING: specified 'SCALE' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'scale' : value})
                    self.config.update({'min_scale' : value})
                    self.config.update({'max_scale' : value})

        elif command == 'min_scale':
            if value != '':
                try:
                    float(value)
                except:
                    self.control.print("*** WARNING: specified 'MIN_SCALE' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'min_scale' : value})

        elif command == 'max_scale':
            if value != '':
                try:
                    float(value)
                except:
                    self.control.print("*** WARNING: specified 'MAX_SCALE' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'max_scale' : value})

        elif command == 'samples':
            if value != '':
                try:
                    int(value)
                except:
                    self.control.print("*** WARNING: specified 'SAMPLES' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'samples' : value})

        elif command == 'batch_size':
            if value != '':
                try:
                    int(value)
                except:
                    self.control.print("*** WARNING: specified 'BATCH_SIZE' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'batch_size' : value})

        elif command == 'strength':
            if value != '':
                try:
                    float(value)
                except:
                    self.control.print("*** WARNING: specified 'STRENGTH' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'strength' : value})
                    self.config.update({'min_strength' : value})
                    self.config.update({'max_strength' : value})

        elif command == 'min_strength':
            if value != '':
                try:
                    float(value)
                except:
                    self.control.print("*** WARNING: specified 'MIN_STRENGTH' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'min_strength' : value})

        elif command == 'max_strength':
            if value != '':
                try:
                    float(value)
                except:
                    self.control.print("*** WARNING: specified 'MAX_STRENGTH' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'max_strength' : value})

        elif command == 'use_upscale':
            if value == 'yes' or value == 'no':
                self.config.update({'use_upscale' : value})

        elif command == 'upscale_amount':
            if value != '':
                try:
                    float(value)
                except:
                    self.control.print("*** WARNING: specified 'UPSCALE_AMOUNT' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'upscale_amount' : value})

        elif command == 'upscale_codeformer_amount':
            if value != '':
                try:
                    float(value)
                except:
                    self.control.print("*** WARNING: specified 'UPSCALE_CODEFORMER_AMOUNT' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'upscale_codeformer_amount' : value})

        elif command == 'upscale_gfpgan_amount':
            if value != '':
                try:
                    float(value)
                except:
                    self.control.print("*** WARNING: specified 'UPSCALE_GFPGAN_AMOUNT' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'upscale_gfpgan_amount' : value})

        elif command == 'upscale_keep_org':
            if value == 'yes' or value == 'no':
                self.config.update({'upscale_keep_org' : value})

        elif command == 'upscale_model':
            if value != '':
                upscale_model = self.control.validate_upscale_model(value.strip())
                if upscale_model != '':
                    self.config.update({'upscale_model' : upscale_model})
                else:
                    self.control.print("*** WARNING: !UPSCALE_MODEL value (" + value.strip() + ") doesn't match any server values; ignoring it! ***")
            else:
                self.config.update({'upscale_model' : 'ESRGAN_4x'})

        elif command == 'mode':
            if value == 'random' or value == 'standard' or value == 'process':
                self.config.update({'mode' : value})

        elif command == 'input_image':
            if value != '':
                if os.path.exists(value):
                    self.config.update({'input_image' : value})
                else:
                    self.control.print("*** WARNING: specified 'INPUT_IMAGE' (" + value + ") does not exist; it will be ignored!")
            else:
                self.config.update({'input_image' : ''})

        elif command == 'random_input_image_dir':
            if value != '':
                if os.path.exists(value):
                    self.config.update({'random_input_image_dir' : value})
                else:
                    self.control.print("*** WARNING: specified 'RANDOM_INPUT_IMAGE_DIR' (" + value + ") does not exist; it will be ignored!")

        elif command == 'output_dir':
            if value != '':
                #if os.path.exists(value):
                self.config.update({'output_dir' : value})
                #else:
                #    self.control.print("*** WARNING: specified 'OUTPUT_DIR' (" + value + ") does not exist; it will be ignored!")

        elif command == 'controlnet_input_image':
            if value != '':
                if os.path.exists(value):
                    self.config.update({'controlnet_input_image' : value})
                else:
                    self.control.print("*** WARNING: specified 'CONTROLNET_INPUT_IMAGE' (" + value + ") does not exist; it will be ignored!")
            else:
                self.config.update({'controlnet_input_image' : ''})

        elif command == 'controlnet_pre':
            if value != '':
                self.config.update({'controlnet_pre' : value})
            else:
                self.config.update({'controlnet_pre' : 'none'})

        elif command == 'controlnet_model':
            if value != '':
                cn_model = self.validate_controlnet_model(value)
                self.config.update({'controlnet_model' : cn_model})
            else:
                self.config.update({'controlnet_model' : ''})

        elif command == 'controlnet_lowvram':
            if value == 'yes' or value == 'on':
                self.config.update({'controlnet_lowvram' : True})
            elif value == 'no' or value == 'off':
                self.config.update({'controlnet_lowvram' : False})

        elif command == 'repeat':
            if value == 'yes':
                self.control.repeat_jobs = True
            elif value == 'no':
                self.control.repeat_jobs = False

        elif command == 'delim':
            if value != '':
                if value.startswith('\"') and value.endswith('\"'):
                    self.config.update({'delim' : value.strip('\"')})
                    #print("New delim: \"" + self.config.get('delim')  + "\"")
                else:
                    self.control.print("*** WARNING: prompt file command DELIM value (" + value + ") not understood (make sure to put quotes around it)! ***")
                    time.sleep(1.5)

        elif command == 'next_prompt_file':
            match = False
            if value != '':
                value = value.lower().replace('.prompts', '').strip()
                files = os.listdir(self.control.config.get('prompts_location'))
                for f in files:
                    if f.lower().endswith('.prompts'):
                        file = f.lower().replace('.prompts', '')
                        if value == file:
                            match = True
                            value += '.prompts'
                            value = os.path.join(os.path.abspath(self.control.config.get('prompts_location')), value)
                            self.config.update({'next_prompt_file' : value})
                            break
            if not match:
                self.control.print("*** WARNING: prompt file command NEXT_PROMPT_FILE value (" + value + ") is not a valid prompt file and will be ignored! ***")
                time.sleep(1.5)

        elif command == 'iptc_title':
            if value != '':
                if len(value) > 0 and value[0] == '+':
                    # check for [identifier]
                    if '<' in value and '>' in value:
                        # get the key within the first []
                        key = value.split('<', 1)[1].strip()
                        key = key.split('>', 1)[0].strip()
                        # the actual value is everything that follows the []
                        value = value.split('>', 1)[1]
                        # add the key/value pair to the history
                        if key in self.config['iptc_title_history']:
                            self.config['iptc_title_history'][key].append(value)
                        else:
                            self.config['iptc_title_history'][key] = [value]
                    else:
                        self.config['iptc_title'] += value[1:]
                else:
                    self.config.update({'iptc_title' : value})
            else:
                self.config.update({'iptc_title' : ''})

        elif command == 'iptc_description':
            if value != '':
                if len(value) > 0 and value[0] == '+':
                    # check for [identifier]
                    if '<' in value and '>' in value:
                        # get the key within the first []
                        key = value.split('<', 1)[1].strip()
                        key = key.split('>', 1)[0].strip()
                        # the actual value is everything that follows the []
                        value = value.split('>', 1)[1]
                        # add the key/value pair to the history
                        if key in self.config['iptc_description_history']:
                            self.config['iptc_description_history'][key].append(value)
                        else:
                            self.config['iptc_description_history'][key] = [value]
                    else:
                        self.config['iptc_description'] += value[1:]
                else:
                    self.config.update({'iptc_description' : value})
            else:
                self.config.update({'iptc_description' : ''})

        elif command == 'iptc_keywords':
            if value != '':
                addon = False
                history = False
                key = ''
                # check for [identifier]
                if value.strip()[0] == '+':
                    addon = True
                    if '<' in value and '>' in value:
                        # get the key within the first []
                        key = value.split('<', 1)[1].strip()
                        key = key.split('>', 1)[0].strip()
                        # the actual value is everything that follows the []
                        value = value.split('>', 1)[1]
                        history = True

                keywords = []
                kw = value.split(',')
                for k in kw:
                    keywords.append(k.strip())

                if len(keywords) > 0:
                    if addon:
                        if history:
                            # add the key/value pair to the history
                            if key in self.config['iptc_keywords_history']:
                                self.config['iptc_keywords_history'][key].append(keywords)
                            else:
                                self.config['iptc_keywords_history'][key] = [keywords]
                        else:
                            #keywords[0] = keywords[0][1:]
                            for k in keywords:
                                if k not in self.config['iptc_keywords']:
                                    self.config['iptc_keywords'].append(k)
                    else:
                        self.config.update({'iptc_keywords' : keywords})
            else:
                self.config.update({'iptc_keywords' : []})

        elif command == 'iptc_copyright':
            if value != '':
                self.config.update({'iptc_copyright' : value})
            else:
                self.config.update({'iptc_copyright' : ''})

        elif command == 'iptc_append':
            if value == 'yes' or value == 'on':
                self.config.update({'iptc_append' : True})
            elif value == 'no' or value == 'off':
                self.config.update({'iptc_append' : False})

        elif command == 'clip_skip':
            if value != '':
                try:
                    int(value)
                except:
                    self.control.print("*** WARNING: specified 'CLIP_SKIP' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'clip_skip' : value})
            else:
                self.config.update({'clip_skip' : ''})

        elif command == 'ckpt_file':
            model = ''
            if value != '':
                if value == 'all':
                    # we're queueing all the models; copy the validated model list
                    if self.control.sdi_models != None and len(self.control.sdi_models) > 0:
                        self.control.models = self.control.sdi_models.copy()
                        model = self.control.models[0]
                        # this is lazy but should always be incremented to zero on the first loop
                        self.control.model_index = -1
                    else:
                        self.control.print("*** WARNING: unable to validate 'CKPT_FILE = all' (has your GPU finished initializing?)! ***")
                elif ',' in value:
                    # we're queuing multiple models
                    models = value.split(',')
                    validated_models = []
                    for m in models:
                        v = self.control.validate_model(m.strip())
                        if v != '':
                            validated_models.append(v)
                        else:
                            self.control.print("*** WARNING: ckpt in model list of !CKPT_FILE value (" + m.strip() + ") doesn't match any server values; ignoring it! ***")
                    if len(validated_models) > 0:
                        # we have at least one valid model, start with the first one
                        # store list with the controller
                        self.control.models = validated_models
                        model = self.control.models[0]
                        # this is lazy but should always be incremented to zero on the first loop
                        self.control.model_index = -1
                else:
                    model = self.control.validate_model(value)
                    if model == '':
                        self.control.print("*** WARNING: prompt file command CKPT_FILE value (" + value + ") doesn't match any server values; ignoring it! ***")
                    else:
                        # to cover cases where there are multiple !CKPT_FILE directives in a single prompt file
                        self.control.models = []
                        self.control.model_index = 0
            self.config.update({'ckpt_file' : model})

        elif command == 'sampler':
            sampler = self.validate_sampler(value)
            self.config.update({'sampler' : sampler})

        elif command == 'neg_prompt':
            self.config.update({'neg_prompt' : value})

        elif command == 'filename':
            self.config.update({'filename' : value})

        else:
            self.control.print("*** WARNING: prompt file command not recognized: " + command.upper() + " (it will be ignored)! ***")
            time.sleep(1.5)


    # passing samplers is case-sensitive; use this to make sure user-supplied
    # sampler name is ok - otherwise use a default
    def validate_sampler(self, sampler):
        validated_sampler = sampler
        validated = False
        if self.control.sdi_samplers != None:
            for s in self.control.sdi_samplers:
                if sampler.lower() == s.lower():
                    # case-insensitive match; use the exact casing from the server
                    validated_sampler = s
                    validated = True
                    break

            if not validated:
                # user-supplied sampler doesn't closely match anything on server list
                # use default
                validated_sampler = 'Euler'
                self.control.print("*** WARNING: prompt file command SAMPLER value (" + sampler + ") doesn't match any server values; defaulting to Euler! ***")

        return validated_sampler


    # validate user-supplied controlnet model
    def validate_controlnet_model(self, model):
        validated_model = ''
        validated = False
        if model.lower().strip().startswith('auto'):
            # the user wants to extract the model from the input img later
            validated_model = model
            validated = True
        elif len(model) >= 3 and self.control.sdi_controlnet_models != None:
            for m in self.control.sdi_controlnet_models:
                if model.lower() in m.lower():
                    validated_model = m
                    validated = True
                    break

        if not validated:
            # user-supplied CN model doesn't closely match anything on server list
            self.control.print("*** WARNING: prompt file command CONTROLNET_MODEL value (" + model + ") doesn't match any server values; ignoring it! ***")

        return validated_model


    # update config variables if there were changes in the prompt file [config]
    def handle_config(self):
        if len(self.conf) > 0:
            for line in self.conf:
                # check for lines that start with '!' and contain '='
                ss = re.search('!(.+?)=', line)
                if ss:
                    command = ss.group(1).lower().strip()
                    #value = line.split("=",1)[1].lower().strip()
                    value = line.split("=",1)[1].strip()
                    self.handle_directive(command, value)


    # return a list of all possible PromptSection combinations
    def build_combinations(self):
        prompt_work_queue = deque()

        # convert PromptSections to simple lists so they're iterable
        all_prompts = list()
        for ps in self.prompts:
            prompts = list()
            prompts = ps.tokens
            all_prompts.append(prompts)

        # get all possible combos
        prompt_combos = itertools.product(*all_prompts)

        # associate a copy of config info with each prompt
        for prompt in prompt_combos:
            #work = self.config.copy()
            # switched to deep copy here to handle IPTC metadata history stuff
            work = copy.deepcopy(self.config)

            work['prompt_file'] = self.control.prompt_file
            str_prompt = ""
            fragments = 0
            is_directive = False

            for fragment in prompt:
                # handle embedded command directives
                ss = re.search('!(.+?)=', fragment)
                if ss:
                    # this is a directive, handle it and ignore this combination
                    command = ss.group(1).lower().strip()
                    #value = fragment.split("=",1)[1].lower().strip()
                    value = fragment.split("=",1)[1].strip()
                    self.handle_directive(command, value)
                    is_directive = True
                    break

                if fragments > 0:
                    if not (fragment.startswith(',') or fragment.startswith(';')):
                        str_prompt += self.config.get('delim')
                str_prompt += fragment
                fragments += 1

            if not is_directive:
                work['prompt'] = str_prompt

                # check for input/controlnet input images that are directories
                # if found, iterate over contained files, submit work for each
                subdir_processed = False
                if os.path.isdir(work['input_image']) and os.path.isdir(work['controlnet_input_image']):
                    # need to add combination of input/control files
                    input_files = get_images_in_dir(work['input_image'])
                    controlnet_files = get_images_in_dir(work['controlnet_input_image'])
                    if len(input_files) > 0 and len(controlnet_files) > 0:
                        subdir_processed = True
                        for i in input_files:
                            for c in controlnet_files:
                                work['input_image'] = i
                                work['controlnet_input_image'] = c
                                prompt_work_queue.append(work.copy())
                    #else:
                        # one or both directories are empty, fall through to below and handle

                if not subdir_processed and os.path.isdir(work['input_image']):
                    # input image is a directory, add a work item for each file
                    files = get_images_in_dir(work['input_image'])
                    if len(files) > 0:
                        subdir_processed = True
                        for f in files:
                            # queue each image in the input dir
                            work['input_image'] = f
                            prompt_work_queue.append(work.copy())
                    else:
                        self.control.print("*** WARNING: prompt file command INPUT_IMAGE refers to an empty directory (" + work['input_image'] + "); ignoring it! ***")
                        work['input_image'] = ''

                if not subdir_processed and os.path.isdir(work['controlnet_input_image']):
                    # ControlNet input image is a directory, add a work item for each file
                    files = get_images_in_dir(work['controlnet_input_image'])
                    if len(files) > 0:
                        subdir_processed = True
                        for f in files:
                            # queue each image in the input dir
                            work['controlnet_input_image'] = f
                            prompt_work_queue.append(work.copy())
                    else:
                        self.control.print("*** WARNING: prompt file command CONTROLNET_INPUT_IMAGE refers to an empty directory (" + work['controlnet_input_image'] + "); ignoring it! ***")
                        work['controlnet_input_image'] = ''

                if not subdir_processed:
                    prompt_work_queue.append(work.copy())

        return prompt_work_queue


    # for !MODE = process
    # return a list of the first PromptSection w/ some additional processing/checks
    # this is a lazy copy/paste of build_combinations with minimum work done
    # to make it work for !MODE=process; come back and clean this up later
    def build_process_work(self):
        prompt_work_queue = deque()
        go_cmds = 0

        if len(self.prompts) > 0:
            # ignore everything after first prompt section for !MODE = process
            all_prompts = list()
            ps = self.prompts[0]
            prompts = list()
            prompts = ps.tokens
            all_prompts.append(prompts)
            prompt_combos = itertools.product(*all_prompts)
        else:
            prompt_combos = []

        if len(self.prompts) > 1:
            self.control.print("*** WARNING: loading a '!MODE=process' prompt file with more than 1 [prompts] section; ignoring extras! ***")

        # associate a copy of config info with each prompt
        for prompt in prompt_combos:
            work = self.config.copy()
            work['prompt_file'] = self.control.prompt_file
            str_prompt = ""
            fragments = 0
            is_directive = False

            for fragment in prompt:
                # handle embedded command directives
                ss = re.search('!(.+?)=', fragment)
                if ss:
                    # this is a directive, handle it and ignore this combination
                    command = ss.group(1).lower().strip()
                    #value = fragment.split("=",1)[1].lower().strip()
                    value = fragment.split("=",1)[1].strip()
                    self.handle_directive(command, value)
                    is_directive = True
                    break

                if fragments > 0:
                    if not (fragment.startswith(',') or fragment.startswith(';')):
                        str_prompt += self.config.get('delim')
                str_prompt += fragment
                fragments += 1

            if not is_directive:
                if str_prompt.lower().strip() == 'go':
                    work['prompt'] = str_prompt
                    go_cmds += 1

                    # check for input images that are directories
                    # if found, iterate over contained files, submit work for each
                    subdir_processed = False
                    if os.path.isdir(work['input_image']):
                        # input image is a directory, add a work item for each file
                        files = get_images_in_dir(work['input_image'])
                        if len(files) > 0:
                            subdir_processed = True
                            for f in files:
                                # queue each image in the input dir
                                work['input_image'] = f
                                prompt_work_queue.append(work.copy())
                        else:
                            self.control.print("*** WARNING: prompt file command INPUT_IMAGE refers to an empty directory (" + work['input_image'] + "); ignoring it! ***")
                            work['input_image'] = ''

                    if not subdir_processed:
                        # process mode requires an input image
                        # verify that we have a valid input image before queueing work
                        # existence was already checked when prompt file was read
                        if work['input_image'] != '':
                            prompt_work_queue.append(work.copy())

                else:
                    self.control.print("*** WARNING: !MODE=process prompt file doesn't accept normal prompts: " + str_prompt + "! ***")

        if go_cmds == 0:
            self.control.print("*** WARNING: loading a !MODE=process prompt file with no 'go' keywords in first [prompts] section; no work will be done! ***")
        return prompt_work_queue


    # create a random prompt from the information in the prompt file
    def pick_random(self):
        fragments = 0
        full_prompt = ""
        tokens = list()

        if len(self.prompts) > 0:
            # iterate through each PromptSection to build the prompt
            for ps in self.prompts:
                fragment = ""
                picked = 0
                # decide how many tokens to pick
                x = random.randint(int(ps.min_pick), int(ps.max_pick))

                # pick token(s)
                if len(ps.tokens) >= x:
                    tokens = ps.tokens.copy()
                    for i in range(x):
                        z = random.randint(0, len(tokens)-1)
                        if picked > 0:
                            fragment += ps.delim
                        fragment += tokens[z]
                        del tokens[z]
                        picked += 1
                else:
                    # not enough tokens to take requested amount, take all
                    for t in ps.tokens:
                        if picked > 0:
                            fragment += ps.delim
                        fragment += t
                        picked += 1

                # add this fragment to the overall prompt
                if fragment != "":
                    if fragments > 0:
                        if not (fragment.startswith(',') or fragment.startswith(';')):
                            full_prompt += self.config.get('delim')
                    full_prompt += fragment
                    fragments += 1

        full_prompt = full_prompt.replace(",,", ",")
        full_prompt = full_prompt.replace(", ,", ",")
        full_prompt = full_prompt.replace(" and,", ",")
        full_prompt = full_prompt.replace(" by and ", " by ")
        full_prompt = full_prompt.strip().strip(',')

        return full_prompt


# for easy reading of prompt/config files
class TextFile():
    def __init__(self, filename):
        self.lines = deque()
        if exists(filename):
            with open(filename, encoding = 'utf-8') as f:
                l = f.readlines()

            for x in l:
                # remove newline and whitespace
                x = x.strip('\n').strip();
                # remove comments
                x = x.split('#', 1)[0].strip();
                if x != "":
                    # these lines are actual prompts
                    self.lines.append(x)

    def next_line(self):
        return self.lines.popleft()

    def lines_remaining(self):
        return len(self.lines)


# Taken from https://github.com/django/django/blob/master/django/utils/text.py
# Using here to make filesystem-safe directory names
def slugify(value, allow_unicode=False):
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    value = re.sub(r'[-\s]+', '-', value).strip('-_')
    # added in case of very long filenames due to multiple prompts
    return value[0:180]


# gets just filename from absolute path
def filename_from_abspath(fpath):
    filename = fpath
    if '\\' in fpath:
        filename = fpath.rsplit('\\', 1)[1]
    elif '/' in fpath:
        filename = fpath.rsplit('/', 1)[1]
    return filename

# gets just path from absolute path + filename
def path_from_abspath(fpath):
    path = fpath
    if '\\' in fpath:
        path = fpath.rsplit('\\', 1)[0]
    elif '/' in fpath:
        path = fpath.rsplit('/', 1)[0]
    return path


# creates the full command to invoke SD with our specified params
# and selected prompt + input image
def create_command(command, output_dir_ext, gpu_id):
    output_dir_ext = filename_from_abspath(output_dir_ext)
    if '.' in output_dir_ext:
        output_dir_ext = output_dir_ext.split('.', 1)[0]
    output_folder = command.get('outdir') + '/' + str(date.today()) + '-' + str(output_dir_ext)

    #py_command = "python scripts/txt2img.py"
    py_command = 'txt2img:'
    if command.get('controlnet_input_image') != '' and command.get('controlnet_model') != '':
        py_command = 'txt2img with ControlNet:'

    if command.get('input_image') != '':
        #py_command = "python scripts/img2img.py"
        if command.get('controlnet_input_image') != '' and command.get('controlnet_model') != '':
            py_command = 'img2img with ControlNet:'
        else:
            py_command = 'img2img:'

    # if this isn't happening on the default gpu, specify the device
    if "cuda:" in gpu_id and gpu_id != "cuda:0":
        py_command += " --device \"" + gpu_id + "\""

    prompt = str(command.get('prompt')).replace('\"', '\\"')
    neg_prompt = str(command.get('neg_prompt')).replace('\"', '\\"')

    py_command += " --skip_grid" \
        + " --n_iter " + str(command.get('samples')) \
        + " --n_samples " + str(command.get('batch_size')) \
        + " --prompt \"" + prompt + "\"" \
        + " --ddim_steps " + str(command.get('steps')) \
        + " --scale " + str(command.get('scale'))

    if neg_prompt != "":
        py_command += " --neg_prompt \"" + neg_prompt + "\"" \

    if command.get('controlnet_input_image') != "" and command.get('controlnet_model') != "":
        py_command += " --cn-img \"" + str(command.get('controlnet_input_image')) + "\"" + " --cn-model \"" + str(command.get('controlnet_model')) + "\""

    if command.get('input_image') != "":
        #py_command += " --init-img \"../" + str(command.get('input_image')) + "\"" + " --strength " + str(command.get('strength'))
        py_command += " --init-img \"" + str(command.get('input_image')) + "\"" + " --strength " + str(command.get('strength'))

    if command.get('clip_skip') != "":
        py_command += " --clip-skip " + str(command.get('clip_skip'))

    if command.get('width') != "":
        py_command += " --W " + str(command.get('width')) + " --H " + str(command.get('height'))

    if command.get('ckpt_file') != '':
        py_command += " --ckpt \"" + str(command.get('ckpt_file')) + "\""

    # with img2img only ddim is supported so don't pass sampler options
    py_command += " --sampler " + str(command.get('sampler'))
    #if command.get('input_image') == "":
    #    if command.get('sampler') != '' and command.get('sd_low_memory') == "yes":
    #        py_command += " --sampler " + str(command.get('sampler'))
    #    elif command.get('sampler') == 'plms' and command.get('sd_low_memory') == "no":
    #        py_command += " --plms"

    # the seed below, and everything before this point will be saved to metadata
    # excluding anything that precedes the actual prompt
    py_command += " --seed " + str(command.get('seed'))

    py_command += " --outdir \"" + output_folder + "\""

    return py_command


# extracts SD parameters from the full command
def extract_params_from_command(command):
    params = {
        'prompt' : "",
        'neg_prompt' : "",
        'seed' : "",
        'width' : "",
        'height' : "",
        'steps' : "",
        'sampler' : "ddim",
        'scale' : "",
        'input_image' : "",
        'strength' : "",
        'ckpt_file' : "",
        'controlnet_model' : "",
        'controlnet_input_image' : "",
        'clip_skip' : ""
    }

    if command != "":
        command = command.strip('"')

        # need this because of old format w/ upscale info included
        if '(upscaled' in command:
            command = command.split('(upscaled', 1)[0]
            command = command.replace('(upscaled', '')

        if '--prompt' in command:
            temp = command.split('--prompt', 1)[1]
            if '--' in temp:
                temp = temp.split('--', 1)[0]
            params.update({'prompt' : temp.strip().strip('"')})

        else:
            # we'll assume anything before --ddim_steps is the prompt
            temp = command.split('--ddim_steps', 1)[0]
            if len(temp) > 2:
                temp = temp.strip()
                if temp[-1] == '\"':
                    temp = temp[:-1]
                temp = temp.replace('\\', '')
            else:
                temp = ''
            params.update({'prompt' : temp})
            #command = command.split('"', 1)[1]

        #elif '"' in command:
        #    params.update({'prompt' : command.split('"', 1)[0]})
        #    command = command.split('"', 1)[1]

        if '--neg_prompt' in command:
            temp = command.split('--neg_prompt', 1)[1]
            if '--' in temp:
                temp = temp.split('--', 1)[0]
            params.update({'neg_prompt' : temp.strip().strip('"')})

        if '--ddim_steps' in command:
            temp = command.split('--ddim_steps', 1)[1]
            if '--' in temp:
                temp = temp.split('--', 1)[0]
            params.update({'steps' : temp.strip()})

        if '--scale' in command:
            temp = command.split('--scale', 1)[1]
            if '--' in temp:
                temp = temp.split('--', 1)[0]
            params.update({'scale' : temp.strip()})

        if '--seed' in command:
            temp = command.split('--seed', 1)[1]
            if '--' in temp:
                temp = temp.split('--', 1)[0]
            params.update({'seed' : temp.strip()})

        if '--W' in command:
            temp = command.split('--W', 1)[1]
            if '--' in temp:
                temp = temp.split('--', 1)[0]
            params.update({'width' : temp.strip()})

        if '--H' in command:
            temp = command.split('--H', 1)[1]
            if '--' in temp:
                temp = temp.split('--', 1)[0]
            params.update({'height' : temp.strip()})

        if '--clip-skip' in command:
            temp = command.split('--clip-skip', 1)[1]
            if '--' in temp:
                temp = temp.split('--', 1)[0]
            params.update({'clip_skip' : temp.strip()})

        if '--init-img' in command:
            temp = command.split('--init-img', 1)[1]
            if '--' in temp:
                temp = temp.split('--', 1)[0]
            temp = temp.replace('../', '').strip().strip('"')
            temp = filename_from_abspath(temp)
            params.update({'input_image' : temp})

        if '--cn-img' in command:
            temp = command.split('--cn-img', 1)[1]
            if '--' in temp:
                temp = temp.split('--', 1)[0]
            temp = temp.replace('../', '').strip().strip('"')
            temp = filename_from_abspath(temp)
            params.update({'controlnet_input_image' : temp})

        if '--strength' in command:
            temp = command.split('--strength', 1)[1]
            if '--' in temp:
                temp = temp.split('--', 1)[0]
            params.update({'strength' : temp.strip()})

        if '--plms' in command:
            # non-optimized version, ddim is default unless --plms specified
            params.update({'sampler' : 'plms'})
        else:
            # optimized version
            if '--sampler' in command:
                temp = command.split('--sampler', 1)[1]
                if '--' in temp:
                    temp = temp.split('--', 1)[0]
                params.update({'sampler' : temp.strip()})

        if '--ckpt' in command:
            temp = command.split('--ckpt', 1)[1]
            if '--' in temp:
                temp = temp.split('--', 1)[0]
            temp = temp.replace('\"', '')
            temp = filename_from_abspath(temp)
            params.update({'ckpt_file' : temp.strip()})

        if '--cn-model' in command:
            temp = command.split('--cn-model', 1)[1]
            if '--' in temp:
                temp = temp.split('--', 1)[0]
            temp = temp.replace('\"', '')
            temp = filename_from_abspath(temp)
            params.update({'controlnet_model' : temp.strip()})


    return params


# ESRGAN/GFPGAN upscaling:
# scale - upscale by this amount, default is 2.0x
# dir - upscale all images in this folder
# do_face_enhance - True/False use GFPGAN (for faces)
def upscale(scale, dir, do_face_enhance, gpu_id):
    command = "python inference_realesrgan.py -n RealESRGAN_x4plus --suffix u -s "

    # check that scale is a valid float, otherwise use default scale of 2
    try :
        float(scale)
        command += str(scale)
    except :
        command += "2"

    # append the input/output dir
    #command += " -i ..//" + dir + " -o ..//" + dir
    command += " -i " + dir + " -o " + dir

    # whether to use GFPGAN for faces
    if do_face_enhance:
        command += " --face_enhance"

    # specify gpu
    if gpu_id != "":
        if "cuda:" in gpu_id:
            gpu_id = gpu_id.replace("cuda:", "")
        command += " -g " + gpu_id

    cwd = os.getcwd()
    print("Invoking Real-ESRGAN: " + command)

    # invoke Real-ESRGAN
    if sys.platform == "win32" or os.name == 'nt':
        subprocess.call(shlex.split(command), cwd=(cwd + '\Real-ESRGAN'), stderr=subprocess.DEVNULL)
    else:
        subprocess.call(shlex.split(command), cwd=(cwd + '/Real-ESRGAN'), stderr=subprocess.DEVNULL)


# returns the exif data of the specified image
def read_exif_from_image(abs_path_to_img):
    exif = None
    if exists(abs_path_to_img):
        if abs_path_to_img.lower().endswith('.jpg'):
            try:
                im = Image.open(abs_path_to_img)
                exif = im.getexif()
                im.close()
            except:
                pass
    return exif


# gets the most recently modified images found within the SUBDIRs of dir
# will return up to max_files images
def get_recent_images(dir, max_files):
    count = 0
    images = []
    subdirs = []

    # first get a list of directories in most-recently-modified order
    for f in os.scandir(dir):
        if f.is_dir():
            subdirs.append(f.path)

    # contains a list of subdirs in most-recently-modified order
    subdirs.sort(key=os.path.getmtime, reverse=True)

    # iterate through sorted subdirs, sorting images within each by
    # most-recently-modified, then adding images until we have max_files
    for d in subdirs:
        tmp_images = []
        for f in os.scandir(d):
            if f.path.lower().endswith(".jpg"):
                tmp_images.append(f.path)
        tmp_images.sort(key=os.path.getmtime, reverse=True)

        for img in tmp_images:
            images.append(img)
            count += 1
            if count >= max_files:
                break

        if count >= max_files:
            break

    return images


# gets the most recently modified images found within specified dir
# will return up to max_files images
def get_images_from_dir(dir, max_files):
    count = 0
    images = []
    tmp_images = []

    for f in os.scandir(dir):
        if f.path.lower().endswith(".jpg"):
            tmp_images.append(f.path)
    tmp_images.sort(key=os.path.getmtime, reverse=True)

    for img in tmp_images:
        images.append(img)
        count += 1
        if count >= max_files:
            break

    return images


# creates a .zip of the files in the specified directory
def create_zip(dir):
    # make sure server/temp exists
    zip_path = os.path.join('server', 'temp')
    if not os.path.exists(zip_path):
        os.makedirs(zip_path)

    filename = filename_from_abspath(dir) + '.zip'
    zip_path = os.path.join(zip_path, filename)
    print("creating " + zip_path + " for download at user request...")

    with ZipFile(zip_path, 'w') as zipObj:
        for f in os.scandir(dir):
           if f.path.lower().endswith('.jpg'):
               zipObj.write(f.path, basename(f.path))

    return zip_path


# returns an image's size dimensions in [w, h] format
# output dimensions will be divisible by 64 (orig dimensions rounded down if necessary)
# returns [] if image doesn't exist or isn't a valid format
def get_image_size(filepath):
    size = []
    if os.path.exists(filepath):
        try:
           with Image.open(filepath) as img:
               width, height = img.size
               size = [width, height]
        except:
           size = []

        if len(size) == 2:
            if size[0] % 64 != 0:
                size[0] = int((size[0] // 64) * 64)
            if size[1] % 64 != 0:
                size[1] = int((size[1] // 64) * 64)

    return size

# given an image (filepath) and orignal dimensions,
# returns new dimensions with the same aspect ratio as the image
# the longest original dimension will match the longest matched AR dimension
# output dimensions will be divisible by 64
# returns dimensions as [w, h], or [] if there was an issue
def match_image_aspect_ratio(filepath, original_dimensions):
    input_dimensions = get_image_size(filepath)
    output_dimensions = []
    if input_dimensions != [] and len(original_dimensions) == 2:
        # first get the longest original dimension
        longest_original_dimension = 0
        if original_dimensions[0] >= original_dimensions[1]:
            longest_original_dimension = int(original_dimensions[0])
        else:
            longest_original_dimension = int(original_dimensions[1])

        # determine which side of the input image is longer
        # and calculate the input image's aspect ratio
        width_longest = True
        aspect_ratio = 0
        if input_dimensions[0] >= input_dimensions[1]:
            width_longest = True
            aspect_ratio = input_dimensions[0] / input_dimensions[1]
        else:
            width_longest = False
            aspect_ratio = input_dimensions[1] / input_dimensions[0]

        # calculate the short dimension of output image
        new_short_dimension = longest_original_dimension / aspect_ratio

        # ensure result is divisible by 64; round down to nearest 64 if not
        if new_short_dimension % 64 != 0:
            new_short_dimension = (new_short_dimension // 64) * 64

        # build return dimensions
        if width_longest:
            output_dimensions = [int(longest_original_dimension), int(new_short_dimension)]
        else:
            output_dimensions = [int(new_short_dimension), int(longest_original_dimension)]

    return output_dimensions


# given a new longest-side dimension, and original dimensions,
# return new dimenions where the longest side matches new_long_dimension
# and the original aspect ratio is maintained (divisble by 64)
def resize_based_on_longest_dimension(new_long_dimension, original_dimensions):
    output_dimensions = []
    if len(original_dimensions) == 2:
        # ensure result is divisible by 64; round down to nearest 64 if not
        new_long_dimension = int(new_long_dimension)
        if new_long_dimension % 64 != 0:
            new_long_dimension = (new_long_dimension // 64) * 64

        # first get the longest original dimension
        longest_original_dimension = 0
        if int(original_dimensions[0]) >= int(original_dimensions[1]):
            longest_original_dimension = int(original_dimensions[0])
        else:
            longest_original_dimension = int(original_dimensions[1])

        # determine which side of the original image is longer
        # and calculate the original image's aspect ratio
        width_longest = True
        aspect_ratio = 0
        if int(original_dimensions[0]) >= int(original_dimensions[1]):
            width_longest = True
            aspect_ratio = int(original_dimensions[0]) / int(original_dimensions[1])
        else:
            width_longest = False
            aspect_ratio = int(original_dimensions[1]) / int(original_dimensions[0])

        # calculate the short dimension of output image
        new_short_dimension = new_long_dimension / aspect_ratio

        # ensure result is divisible by 64; round down to nearest 64 if not
        if new_short_dimension % 64 != 0:
            new_short_dimension = (new_short_dimension // 64) * 64

        # build return dimensions
        if width_longest:
            output_dimensions = [int(new_long_dimension), int(new_short_dimension)]
        else:
            output_dimensions = [int(new_short_dimension), int(new_long_dimension)]

    return output_dimensions


# returns a list of .jpg and .png images in the given directory
def get_images_in_dir(path):
    files = []
    if os.path.exists(path):
        for entry in os.scandir(path):
            if entry.is_file() and (entry.name.lower().endswith('.png') or entry.name.lower().endswith('.jpg')):
                file = os.path.join(path, entry.name)
                files.append(file)
    return files


# check a string for potential wildcard replacement; make at most 1
# unless all=True (make all replacements)
def wildcard_replace(str, key, replace, all=False):
    if str != None and len(str) > 0:
        if not all:
            str = re.sub(key, replace, str, 1, flags=re.IGNORECASE)
        else:
            str = re.sub(key, replace, str, flags=re.IGNORECASE)
    return str


# check a list for potential wildcard replacement; make at most 1
# unless all=True (make all replacements)
def wildcard_replace_list(list, key, replace, all=False):
    replace_list = []
    made_replacement = False
    if list != None and len(list) > 0:
        for str in list:
            if not made_replacement and key.lower() in str.lower():
                if not all:
                    str = re.sub(key, replace, str, 1, flags=re.IGNORECASE)
                    made_replacement = True
                else:
                    str = re.sub(key, replace, str, flags=re.IGNORECASE)
            replace_list.append(str)
    else:
        replace_list = list
    return replace_list
