# Copyright 2021 - 2023, Bill Kennedy (https://github.com/rbbrdckybk/dream-factory)
# SPDX-License-Identifier: MIT

# Civitai.com prompt scraper utility
# checks your model-triggers.txt for installed models (you need to have loaded
# them at least once to calculate the hash) and scrapes all associated prompts,
# then saves them as a Dream Factory .prompts file (1 per model).

# usage: python civitai-scraper.py --help

# This requires Playwright, which can be installed with these commands:
# pip3 install playwright
# playwright install

# This will not return any data for NSFW models on civitai.com unless you use
# civitai-auth.py (see instructions in that file) to authenticate with your
# civitai credentials once first, and ensure that NSFW models aren't hidden
# in your personal civitai.com browsing settings.

from playwright.sync_api import Playwright, sync_playwright
import requests
import time
import json
import os.path
import copy
import unicodedata
import re
import argparse
from pathlib import Path

resize = 0
max_steps = 0
sizes = 'include'


class Civitai:
    def __init__(self, type='model', nsfw='exclude'):
        self.browser = playwright.chromium.launch(headless = True)
        self.use_auth = False
        self.url = ""
        self.auto1111_path = ""
        self.metadata = None
        self.hashes = []
        self.hashmap = {}
        self.current_hash = ''
        self.output_dir = 'civitai-scraper'

        type = type.lower()
        if not (type == 'model' or type == 'lora' or type == 'hypernet' or type == 'embedding'):
            print('Invalid --type specified, defaulting to model...')
            type = 'model'

        nsfw = nsfw.lower()
        if not (nsfw == 'include' or nsfw == 'exclude' or nsfw == 'only'):
            print('Invalid --nsfw specified, defaulting to exclude...')
            nsfw = 'exclude'

        self.type = type
        self.nsfw = nsfw

        self.flush_metadata_buffer()
        self.get_trigger_hashes(self.type)

        if os.path.exists('civitai-auth.json'):
            self.use_auth = True

        # create output dir
        if not os.path.exists(self.output_dir):
            try:
                Path(self.output_dir).mkdir(parents=True, exist_ok=True)
            except:
                print('Error: output directory could not be created!')
                self.output_dir = ''

    def flush_metadata_buffer(self):
        self.metadata = []

    def get_auto1111_path(self):
        config_filename = os.path.join('..', 'config.txt')
        if os.path.exists(config_filename):
            with open(config_filename, 'r', encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                if not line.strip().startswith('#'):
                    if 'SD_LOCATION =' in line:
                        loc = line.split('=', 1)[1].strip()
                        loc = os.path.join(loc, 'models')
                        loc = os.path.join(loc, 'Stable-diffusion')
                        if os.path.exists(loc):
                            self.auto1111_path = loc
                        break

    def get_trigger_hashes(self, type='model'):
        self.get_auto1111_path()
        #triggers_filename = os.path.join('..', 'model-triggers.txt')
        triggers_filename = os.path.join('..', 'cache')
        triggers_filename = os.path.join(triggers_filename, 'hashes-' + type + '.txt')
        if os.path.exists(triggers_filename):
            with open(triggers_filename, 'r', encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                if not line.strip().startswith('#'):
                    if ',' in line:
                        hash = line.split(',', 1)[1].strip()
                        if hash not in self.hashes:
                            self.hashes.append(hash)

    # returns a dict, key is civitai ID, value is list of image metadata
    def lookup_hash(self, hash):
        data = {}
        images = []
        hash = hash.upper()
        model_name = ""

        URL = "https://civitai.com/api/v1/model-versions/by-hash/"
        modelinfo = requests.get(URL + hash)
        modeldata = modelinfo.json()

        if 'model' in modeldata and 'name' in modeldata['model']:
            model_id = modeldata['modelId']
            model_name = modeldata['model']['name']
            #version_name = modeldata['name']
            self.hashmap[hash] = model_id

            #for version in modeldata['modelVersions']:
                #print(version['name'])
                #for image in version['images']:

            for image in modeldata['images']:
                #print(image['url'])
                meta = image['meta']
                if not meta is None:
                    if 'nsfw' in image:
                        meta['nsfw'] = image['nsfw']
                    images.append(meta)
            data[model_id] = images
        else:
            #print('   Hash ' + hash + ' not found!')
            pass

        return [data, model_name]

    def get_civitai_id_from_hash(self, hash):
        id = -1
        hash = hash.upper()
        if hash in self.hashmap:
            id = self.hashmap[hash]
        return id

    def get_hash_from_civitai_id(self, id):
        hash = ""
        for key, value in self.hashmap.items():
            if value == id:
                hash = key
                break
        return hash

    def get_filename_from_hash(self, hash):
        filename = ''
        triggers_filename = os.path.join('..', 'cache')
        triggers_filename = os.path.join(triggers_filename, 'hashes-' + type + '.txt')
        if os.path.exists(triggers_filename):
            with open(triggers_filename, 'r', encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                if not line.strip().startswith('#'):
                    if ',' in line and hash in line:
                        filename = line.split(',', 1)[0].strip()
                        break
        return filename

    def get_weight_from_hash(self, hash):
        weight = '1'
        triggers_filename = os.path.join('..', 'cache')
        triggers_filename = os.path.join(triggers_filename, 'civitai-' + type + '.txt')
        if os.path.exists(triggers_filename):
            with open(triggers_filename, 'r', encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                if not line.strip().startswith('#'):
                    if ';' in line and hash in line:
                        weight = line.rsplit(';', 1)[1].strip()
                        break
        return weight

    # scrapes the specified URL
    def scrape(self, playwright: Playwright, url = '', hash = '') -> None:
        if url != '':
            self.url = url
        if self.url != "":
            if hash != '':
                self.current_hash = hash
            tries = 0
            delay = 5
            success = False
            page = None

            if self.use_auth:
                context = self.browser.new_context(storage_state="civitai-auth.json")
                page = context.new_page()
            else:
                page = self.browser.new_page()

            page.on("response", self.handle_response)
            while not success:
                try:
                    # allow 2 mins for response
                    page.goto(self.url, wait_until="networkidle", timeout=120000)
                except Exception as e:
                    print(e)
                    print('Error connecting to ' + self.url + '; re-trying in ' + str(delay) + ' seconds...')
                    tries += 1
                    time.sleep(delay)
                    delay += 15
                else:
                    success = True
            #page.keyboard.down('End')
            page.context.close()
        else:
            print('Error: call to run with no URL set!')

    # handles the response from civitai.com, returns list of image metadata posts
    def handle_response(self, response):
        if ("image.getImagesAsPostsInfinite?" in response.url):
            r = response.json()
            count = 0
            total_images = 0

            if r["result"]["data"]["json"]["items"]:
                for post in r["result"]["data"]["json"]["items"]:
                    count += 1
                    image_count = 0
                    if post["images"]:
                        for image in post["images"]:
                            image_count += 1
                            nsfw_tag = ''
                            if "nsfw" in image:
                                nsfw_tag = image["nsfw"].lower()

                            if "meta" in image and image["meta"] is not None:
                                if "prompt" in image["meta"]:
                                    p = image["meta"]["prompt"]
                                    found = False

                                    # ensure lora is in the prompt
                                    if self.type == 'lora' or self.type == 'hypernet':
                                        filename = self.get_filename_from_hash(self.current_hash)
                                        if filename != '':
                                            search = '<' + self.type + ':' + filename + ':'
                                            if search not in p:
                                                weight = self.get_weight_from_hash(self.current_hash)
                                                p += ' <' + self.type + ':' + filename + ':' + weight + '>'
                                                image["meta"]["prompt"] = p

                                    for i in self.metadata:
                                        if p == i['prompt']:
                                            found = True
                                            break
                                    if not found:
                                        total_images += 1
                                        image["meta"]["nsfw"] = nsfw_tag
                                        self.metadata.append(image["meta"])

                    #print('Post ID ' + str(post["postId"]) + ' -> number of images: ' + str(image_count))
            print('Found ' + str(count) + ' posts with ' + str(total_images) + ' images containing metadata...')

    # writes output .prompts file from given list of image metadata
    def write(self, hash, model_name, metadata = []):
        global resize
        global sizes
        if metadata == []:
            metadata = self.metadata

        filename = 'civitai-' + model_name + '.prompts'
        filename = os.path.join(self.output_dir, filename)
        with open(filename, 'w', encoding="utf-8") as f:
            resize_txt = '!AUTO_SIZE = off'
            if int(resize) > 0:
                resize_txt = '!AUTO_SIZE = resize_longest_dimension: ' + str(resize)
            f.write('[config]\n\n!MODE = standard\n!REPEAT = yes\n\n' + str(resize_txt) + '\n')
            f.write('!HIGHRES_FIX = yes\n!STRENGTH = 0.68\n!FILENAME = <model>-<date>-<time>\n')
            f.write('!AUTO_INSERT_MODEL_TRIGGER = end\n\n')
            if self.type == 'model':
                filename = self.get_filename_from_hash(hash)
                if filename != '':
                    f.write('# model hash: ' + hash + '\n')
                    f.write('!CKPT_FILE = ' + filename)
                else:
                    f.write('!CKPT_FILE = ' + hash)
            else:
                f.write('!CKPT_FILE = # fill in your model(s) here')

            f.write('\n\n[prompts]\n')

            for image in metadata:
                # handle nsfw filter option
                include = True
                image_nsfw = False
                nsfw_tag = ''
                if "nsfw" in image:
                    nsfw_tag = image['nsfw'].lower()
                    if nsfw_tag != '':
                        if nsfw_tag != 'none':
                            image_nsfw = True

                    if self.nsfw == 'exclude' and image_nsfw:
                        include = False
                    if self.nsfw == 'only' and not image_nsfw:
                        include = False

                if include and "prompt" in image:
                    prompt = image["prompt"].replace('\n', '')
                    if prompt.startswith('['):
                        prompt = 'image of ' + prompt
                    while prompt.endswith(','):
                        prompt = prompt[:-1]
                    prompt = prompt.strip()
                    negPrompt = ""
                    sampler = ""
                    scale = -1
                    steps = 20
                    if "negativePrompt" in image:
                        negPrompt = image["negativePrompt"].replace('\n', '').strip()
                        f.write('\n!NEG_PROMPT = ' + negPrompt + '\n')
                    if "sampler" in image:
                        sampler = image["sampler"]
                        f.write('!SAMPLER = ' + sampler + '\n')
                    if "cfgScale" in image:
                        scale = image["cfgScale"]
                        f.write('!SCALE = ' + str(scale) + '\n')
                    if "steps" in image:
                        steps = image["steps"]
                        steps = check_steps(steps, max_steps)
                        f.write('!STEPS = ' + str(steps) + '\n')

                    if sizes != 'exclude':
                        if "Size" in image:
                            if "x" in image["Size"]:
                                meta_size = image["Size"].split('x', 1)
                                f.write('!WIDTH = ' + str(meta_size[0]) + '\n')
                                f.write('!HEIGHT = ' + str(meta_size[1]) + '\n')
                    if "Clip skip" in image:
                        clip_skip = image["Clip skip"]
                        f.write('!CLIP_SKIP = ' + str(clip_skip) + '\n')
                    else:
                        f.write('!CLIP_SKIP = 1\n')
                    if "nsfw" in image:
                        #f.write('# ' + str(nsfw_tag) + '\n')
                        pass
                    f.write(prompt + '\n\n')


    def cleanup(self):
        if self.browser != None:
            self.browser.close()



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

def check_steps(value, max):
    new_value = value
    if max > 0:
        try:
            int(value)
        except:
            pass
        else:
            if int(value) > max:
                new_value = max
    return new_value

# entry point
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max_steps",
        type=int,
        default=0,
        help="step values higher than this will be set to this; leave at zero to disable (default)"
    )
    parser.add_argument(
        "--resolution",
        type=int,
        default=0,
        help="auto-resize longest image dimension to this size (aspect ratio will be maintained); leave at zero to disable (default)"
    )
    parser.add_argument(
        "--type",
        default='model',
        help="type of resource to scrape: model (default), lora, hypernet, or embedding"
    )
    parser.add_argument(
        "--nsfw",
        default='exclude',
        help="include/exclude nsfw images: exclude (default), include, or only"
    )
    parser.add_argument(
        "--sizes",
        default='include',
        help="include/exclude image size info: include (default), or exclude"
    )

    opt = parser.parse_args()
    resize = opt.resolution
    max_steps = opt.max_steps
    type = opt.type.lower()
    nsfw = opt.nsfw.lower()
    sizes = opt.sizes.lower()

    count = 0
    all_data = {}

    with sync_playwright() as playwright:
        civitai = Civitai(type, nsfw)

        for hash in civitai.hashes:
            print('\nLooking up hash ' + hash + '...')
            fulldata = civitai.lookup_hash(hash)
            data = fulldata[0]
            if len(data) > 0:
                count += 1
                c_id = civitai.get_civitai_id_from_hash(hash)
                url = "https://civitai.com/models/" + str(c_id)
                print('  -> Hash ' + hash + ' maps to civitai.com ID ' + str(c_id) + '...')
                print('  -> Scraping ' + url + ' for user image metadata...')
                civitai.flush_metadata_buffer()
                civitai.scrape(playwright, url, hash)
                # deep copy because we're constantly purging main obj
                user_images = copy.deepcopy(civitai.metadata)
                all_data[c_id] = copy.deepcopy(data[c_id])
                all_data[c_id].extend(user_images)
                # write .prompts file
                civitai.write(hash, slugify(fulldata[1]), all_data[c_id])
            else:
                print('  -> Hash ' + hash + ' not found on civitai.com...')

            #if count > 1:
            #    break
            time.sleep(2)

        civitai.cleanup()
