# Copyright 2021 - 2023, Bill Kennedy (https://github.com/rbbrdckybk/dream-factory)
# SPDX-License-Identifier: MIT

# Dream Factory extract_prompts utility
# Extracts prompt metadata from images created with Dream Factory and saves to prompts.txt
# Usage: python extract_prompts.py --imgdir [directory containing images]
# For additional options, use: python extract_prompts.py --help

import argparse
import time
import datetime as dt
from datetime import date
import shlex
import subprocess
import sys
import unicodedata
import re
import random
import os
from os.path import exists
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS

# populate this with phrases you want to be stripped from prompts
# example: user_remove_words = ['charliebo artstyle', 'holliemengert artstyle']
user_remove_words = []

# found prompts should be completely discarded if they contain any of the words
# contained in filter_words, defined below
# example: filter_words = ['nsfw']
filter_words = []

# define any manual replacements you want to make in found prompts here
# example: manual_replacements = [ ['cottage cheese', 'swiss cheese'] ]
# would replace all occurances of 'cottage cheese' with 'swiss cheese' in found prompts
manual_replacements = []

# checks model_triggers.txt for any trigger/token phrases
def get_filter_words_from_trigger_file(filepath):
    filter_words = []
    if exists(filepath):
        with open(filepath, 'r') as f:
            lines = f.readlines()
        for line in lines:
            if ',' in line:
                word = line.split(',', 1)[1].strip()
                if word != '' and word != '\n':
                    filter_words.append(word)
    # de-dupe & arrange longest phrases first
    filter_words = [*set(filter_words)]
    filter_words.sort(key=len, reverse=True)
    return filter_words


# gets images found within specified dir, ignores subdirs
def get_images_from_dir(dir):
    images = []
    for f in os.scandir(dir):
        if f.path.lower().endswith(".jpg"):
            images.append(f.path)
    images.sort()
    return images


# gets found within specified dir and all sub-dirs
def get_images_from_tree(root_dir):
    images = []
    for root, dirs, files in os.walk(root_dir, topdown=False):
        for name in files:
            if name.lower().endswith('.jpg'):
                full_file_path = os.path.join(root, name)
                images.append(full_file_path)

        for name in dirs:
            full_dir_path = os.path.join(root, name)

    images.sort()
    return images


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
        'strength' : "",
        'neg_prompt' : "",
        'model' : "",
        'sampler' : ""
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
            temp = temp.strip()
            if temp[-1] == '\"':
                temp = temp[:-1]
            temp = temp.replace('\\', '')
            params.update({'prompt' : temp})

        if '--neg_prompt' in command:
            temp = command.split('--neg_prompt', 1)[1]
            if '--' in temp:
                temp = temp.split('--', 1)[0]
            params.update({'neg_prompt' : temp.strip().strip('"')})

        if '--ckpt' in command:
            temp = command.split('--ckpt', 1)[1]
            if '--' in temp:
                temp = temp.split('--', 1)[0]
            params.update({'model' : temp.strip().strip('"')})

        if '--sampler' in command:
            temp = command.split('--sampler', 1)[1]
            if '--' in temp:
                temp = temp.split('--', 1)[0]
            params.update({'sampler' : temp.strip()})

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
            head, tail = os.path.split(temp)
            if tail == '':
                tail = temp
            params.update({'input_image' : tail})

        if '--strength' in command:
            temp = command.split('--strength', 1)[1]
            if '--' in temp:
                temp = temp.split('--', 1)[0]
            params.update({'strength' : temp.strip()})

    return params

# entry point
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--imgdir",
        type=str,
        required=True,
        help="the base directory containing images"
    )
    parser.add_argument(
        "--keep_triggers",
        action='store_true',
        help="don't strip model trigger/token phrases from prompts"
    )
    parser.add_argument(
        "--ignore_subdirs",
        action='store_true',
        help="don't search sub-directories for images"
    )
    parser.add_argument(
        "--extract_neg_prompts",
        action='store_true',
        help="include negative prompts in the output"
    )
    parser.add_argument(
        "--extract_cfg_scale",
        action='store_true',
        help="include config scale setting in the output"
    )
    parser.add_argument(
        "--extract_models",
        action='store_true',
        help="include original model(s) in the output"
    )
    opt = parser.parse_args()

    prompts = {}
    if not opt.extract_models:
        prompts['all'] = []

    if opt.imgdir != '':
        print('\nStarting...')

        # build a list of images
        if not opt.ignore_subdirs:
            images = get_images_from_tree(opt.imgdir)
            print('Found ' + str(len(images)) + ' images in ' + opt.imgdir + ' and all sub-directories...')
        else:
            images = get_images_from_dir(opt.imgdir)
            print('Found ' + str(len(images)) + ' images in ' + opt.imgdir + '...')

        # look for dream factory exif tags in images
        if len(images) > 0:

            # get trigger/token phrases to strip if necessary
            remove_words = []
            if not opt.keep_triggers:
                print('Checking your model-triggers.txt file for trigger/token phrases to remove from prompts...')
                remove_words = get_filter_words_from_trigger_file('..\model-triggers.txt')
                if len(remove_words) > 0:
                    print('   Found ' + str(len(remove_words)) + ' trigger words in model-triggers.txt; these will be filtered from prompts...')
                else:
                    print('   No trigger/token phrases found in model-triggers.txt...')

            # add additional user-specified words to remove
            for word in user_remove_words:
                remove_words.append(word)
            remove_words = [*set(remove_words)]
            remove_words.sort(key=len, reverse=True)

            print('Looking for metadata in images.', end='', flush=True)
            count = 0
            for img in images:
                count += 1
                if count > 500:
                    print('.', end='', flush=True)
                    count = 0
                # try to extract exif
                details = ''
                exif = read_exif_from_image(img)
                if exif != None:
                    try:
                        details = exif[0x9c9c].decode('utf16')
                    except KeyError as e:
                        pass

                if details != '':
                    # if the image has exif data, investigate
                    params = extract_params_from_command(details)
                    if params['prompt'] != '':
                        # we found a prompt, add it if this wasn't img2img
                        if params['input_image'] == "":
                            # check if made with Auto1111, strip extra metadata if so
                            if '\nNegative prompt:' in params['prompt'] or '\nSteps:' in params['prompt']:
                                # grab neg prompt
                                if '\nNegative prompt:' in params['prompt']:
                                    params['neg_prompt'] = params['prompt'].split('\nNegative prompt:', 1)[1].strip()
                                    params['neg_prompt'] = params['neg_prompt'].split('\nSteps:', 1)[0].strip()
                                    #print(params['neg_prompt'])

                                # grab prompt
                                if '\nNegative prompt' in params['prompt']:
                                    params['prompt'] = params['prompt'].split('\nNegative prompt', 1)[0]
                                if '\nSteps' in params['prompt']:
                                    params['prompt'] = params['prompt'].split('\nSteps', 1)[0]
                                params['prompt'] = params['prompt'].replace('\n', '')

                            # check for filter words
                            found_fw = False
                            for fw in filter_words:
                                if fw in params['prompt']:
                                    found_fw = True
                                    break

                            # only add if filter words don't appear in prompt
                            if not found_fw:
                                # check for manual manual_replacements
                                for replacement in manual_replacements:
                                    if len(replacement) >= 2:
                                        params['prompt'] = params['prompt'].replace(replacement[0], replacement[1])

                                # check for words to be removed
                                for rw in remove_words:
                                    if rw in params['prompt']:
                                        params['prompt'] = params['prompt'].replace(rw, '')

                                # remove leading spaces and commas
                                while params['prompt'].startswith(' ') or params['prompt'].startswith(','):
                                    params['prompt'] = params['prompt'][1:]

                                # remove trailing spaces and commas
                                while params['prompt'].endswith(' ') or params['prompt'].endswith(','):
                                    params['prompt'] = params['prompt'][:-1]
                                # fix double commas & other misc issues
                                if params['prompt'].endswith('.'):
                                    params['prompt'] = params['prompt'][:-1].strip()
                                params['prompt'] = params['prompt'].replace('|', ',')
                                params['prompt'] = params['prompt'].replace(',,', ',')
                                params['prompt'] = params['prompt'].replace(', ,', ',')
                                params['prompt'] = params['prompt'].replace(' ,', ',')
                                params['prompt'] = params['prompt'].replace(',  style,', ',')
                                params['prompt'] = params['prompt'].strip('\"').strip(",").strip()

                                if params['prompt'].strip() != '':
                                    temp = params['prompt']
                                    if opt.extract_neg_prompts:
                                        temp = '!NEG_PROMPT = ' + params['neg_prompt'] + '\n\n' + temp
                                    if opt.extract_cfg_scale:
                                        temp = '!SCALE = ' + params['scale'] + '\n' + temp
                                    if opt.extract_models:
                                        model = params['model']
                                        model = model.split('[', 1)[0].strip()
                                        if '\\' in model:
                                            model = model.rsplit('\\', 1)[1].strip()
                                        if '/' in model:
                                            model = model.rsplit('/', 1)[1].strip()
                                        if model not in prompts:
                                            prompts[model] = []
                                        prompts[model].append(temp)
                                    else:
                                        prompts['all'].append(temp)


            length = 0
            for key in prompts:
                length += len(prompts[key])
            print(' found ' + str(length) + ' prompts.')

            # de-dupe and sort
            length = 0
            for key in prompts:
                prompts[key] = [*set(prompts[key])]
                prompts[key].sort()
                length += len(prompts[key])

            print('After removing dupes, there are ' + str(length) + ' unique prompts.')

            print('Writing these to prompts.txt...')

            f = open('prompts.txt', 'w', encoding = 'utf-8')
            f.write('#######################################################################################################\n')
            f.write('# Created with utils\extract_prompts.py\n')
            f.write('# ' + str(length) + ' unique prompts from images in ' + opt.imgdir + '\n')
            f.write('# Copy and paste these into any Dream Factory .prompt file.\n')
            f.write('#######################################################################################################\n\n')
            #for p in final:
            #    f.write(p + '\n\n')
            for key in prompts:
                if opt.extract_models:
                    if key != '':
                        f.write('\n!CKPT_FILE = ' + key + '\n\n')
                    else:
                        f.write('\n# no model specified for the following prompts\n\n')
                for p in prompts[key]:
                    f.write(p + '\n\n')
            f.close()

        print('Done!')
