# Copyright 2021 - 2022, Bill Kennedy
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
        with open(self.control.prompt_file) as f:
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
                    # save PromptSection
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
        with open(self.control.prompt_file) as f:
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
        self.config = {
            'mode' : "standard",
            'sd_low_memory' : self.control.config['sd_low_memory'],
            'sd_low_mem_turbo' : self.control.config['sd_low_mem_turbo'],
            'seed' : -1,
            'width' : self.control.config['width'],
            'height' : self.control.config['height'],
            'steps' : self.control.config['steps'],
            'scale' : self.control.config['scale'],
            'min_scale' : 7.5,
            'max_scale' : 7.5,
            'samples' : self.control.config['samples'],
            'batch_size' : 1,
            'input_image' : "",
            'random_input_image_dir' : "",
            'strength' : 0.75,
            'min_strength' : 0.75,
            'max_strength' : 0.75,
            'delim' : " ",
            'use_upscale' : self.control.config['use_upscale'],
            'upscale_amount' : self.control.config['upscale_amount'],
            'upscale_face_enh' : self.control.config['upscale_face_enh'],
            'upscale_keep_org' : self.control.config['upscale_keep_org'],
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
                    print("*** WARNING: specified 'WIDTH' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'width' : value})

        elif command == 'height':
            if value != '':
                try:
                    int(value)
                except:
                    print("*** WARNING: specified 'HEIGHT' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'height' : value})

        elif command == 'seed':
            if value != '':
                try:
                    int(value)
                except:
                    print("*** WARNING: specified 'SEED' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'seed' : value})

        elif command == 'steps':
            if value != '':
                try:
                    int(value)
                except:
                    print("*** WARNING: specified 'STEPS' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'steps' : value})

        elif command == 'scale':
            if value != '':
                try:
                    float(value)
                except:
                    print("*** WARNING: specified 'SCALE' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'scale' : value})
                    self.config.update({'min_scale' : value})
                    self.config.update({'max_scale' : value})

        elif command == 'min_scale':
            if value != '':
                try:
                    float(value)
                except:
                    print("*** WARNING: specified 'MIN_SCALE' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'min_scale' : value})

        elif command == 'max_scale':
            if value != '':
                try:
                    float(value)
                except:
                    print("*** WARNING: specified 'MAX_SCALE' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'max_scale' : value})

        elif command == 'samples':
            if value != '':
                try:
                    int(value)
                except:
                    print("*** WARNING: specified 'SAMPLES' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'samples' : value})

        elif command == 'batch_size':
            if value != '':
                try:
                    int(value)
                except:
                    print("*** WARNING: specified 'BATCH_SIZE' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'batch_size' : value})

        elif command == 'strength':
            if value != '':
                try:
                    float(value)
                except:
                    print("*** WARNING: specified 'STRENGTH' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'strength' : value})
                    self.config.update({'min_strength' : value})
                    self.config.update({'max_strength' : value})

        elif command == 'min_strength':
            if value != '':
                try:
                    float(value)
                except:
                    print("*** WARNING: specified 'MIN_STRENGTH' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'min_strength' : value})

        elif command == 'max_strength':
            if value != '':
                try:
                    float(value)
                except:
                    print("*** WARNING: specified 'MAX_STRENGTH' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'max_strength' : value})

        elif command == 'sd_low_memory':
            if value == 'yes' or value == 'no':
                self.config.update({'sd_low_memory' : value})

        elif command == 'sd_low_mem_turbo':
            if value == 'yes' or value == 'no':
                self.config.update({'sd_low_mem_turbo' : value})

        elif command == 'use_upscale':
            if value == 'yes' or value == 'no':
                self.config.update({'use_upscale' : value})

        elif command == 'upscale_amount':
            if value != '':
                try:
                    float(value)
                except:
                    print("*** WARNING: specified 'UPSCALE_AMOUNT' is not a valid number; it will be ignored!")
                else:
                    self.config.update({'upscale_amount' : value})

        elif command == 'upscale_face_enh':
            if value == 'yes' or value == 'no':
                self.config.update({'upscale_face_enh' : value})

        elif command == 'upscale_keep_org':
            if value == 'yes' or value == 'no':
                self.config.update({'upscale_keep_org' : value})

        elif command == 'mode':
            if value == 'random' or value == 'standard':
                self.config.update({'mode' : value})

        elif command == 'input_image':
            if value != '':
                self.config.update({'input_image' : value})

        elif command == 'random_input_image_dir':
            if value != '':
                self.config.update({'random_input_image_dir' : value})

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
                    print("*** WARNING: prompt file command DELIM value (" + value + ") not understood (make sure to put quotes around it)! ***")
                    time.sleep(1.5)

        else:
            print("*** WARNING: prompt file command not recognized: " + command.upper() + " (it will be ignored)! ***")
            time.sleep(1.5)


    # update config variables if there were changes in the prompt file [config]
    def handle_config(self):
        if len(self.conf) > 0:
            for line in self.conf:
                # check for lines that start with '!' and contain '='
                ss = re.search('!(.+?)=', line)
                if ss:
                    command = ss.group(1).lower().strip()
                    value = line.split("=",1)[1].lower().strip()
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
                    value = fragment.split("=",1)[1].lower().strip()
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
                prompt_work_queue.append(work.copy())

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
            with open(filename) as f:
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

    py_command = "python scripts_mod/txt2img.py"
    if command.get('sd_low_memory') == "yes":
        py_command = "python scripts_mod/optimized_txt2img.py"

    if command.get('input_image') != "":
        py_command = "python scripts_mod/img2img.py"
        if command.get('sd_low_memory') == "yes":
            py_command = "python scripts_mod/optimized_img2img.py"

    if command.get('sd_low_memory') == "yes" and command.get('sd_low_mem_turbo') == "yes":
        py_command += " --turbo"

    # if this isn't happening on the default gpu, specify the device
    if "cuda:" in gpu_id and gpu_id != "cuda:0":
        py_command += " --device \"" + gpu_id + "\""

    py_command += " --skip_grid" \
        + " --n_iter " + str(command.get('samples')) \
        + " --n_samples " + str(command.get('batch_size')) \
        + " --prompt \"" + str(command.get('prompt')).replace('\"', '') + "\"" \
        + " --ddim_steps " + str(command.get('steps')) \
        + " --scale " + str(command.get('scale'))

    if command.get('input_image') != "":
        py_command += " --init-img \"../" + str(command.get('input_image')) + "\"" + " --strength " + str(command.get('strength'))
    else:
        py_command += " --W " + str(command.get('width')) + " --H " + str(command.get('height'))

    py_command += " --seed " + str(command.get('seed'))

    py_command += " --outdir \"../" + output_folder + "\""

    return py_command


# extracts SD parameters from the full command
def extract_params_from_command(command):
    params = {
        'prompt' : "",
        'seed' : "",
        'width' : "",
        'height' : "",
        'steps' : "",
        'scale' : "",
        'input_image' : "",
        'strength' : ""
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

        elif '"' in command:
            params.update({'prompt' : command.split('"', 1)[0]})
            command = command.split('"', 1)[1]

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

        if '--init-img' in command:
            temp = command.split('--init-img', 1)[1]
            if '--' in temp:
                temp = temp.split('--', 1)[0]
            temp = temp.replace('../', '').strip().strip('"')
            temp = filename_from_abspath(temp)
            params.update({'input_image' : temp})

        if '--strength' in command:
            temp = command.split('--strength', 1)[1]
            if '--' in temp:
                temp = temp.split('--', 1)[0]
            params.update({'strength' : temp.strip()})

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
    command += " -i ..//" + dir + " -o ..//" + dir

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
