# Copyright 2021 - 2023, Bill Kennedy (https://github.com/rbbrdckybk/dream-factory)
# SPDX-License-Identifier: MIT

# Civitai.com prompt scraper utility
# checks your model-triggers.txt for installed models (you need to have loaded
# them at least once to calculate the hash) and scrapes all associated prompts,
# then saves them as a Dream Factory .prompts file (1 per model).

# usage: python civitai.py

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

class Civitai:
    def __init__(self):
        self.browser = playwright.chromium.launch(headless = True)
        self.use_auth = False
        self.url = ""
        self.metadata = None
        self.hashes = []
        self.hashmap = {}

        self.flush_metadata_buffer()
        self.get_trigger_hashes()

        if os.path.exists('civitai-auth.json'):
            self.use_auth = True


    def flush_metadata_buffer(self):
        self.metadata = []

    def get_trigger_hashes(self):
        triggers_filename = os.path.join('..', 'model-triggers.txt')
        if os.path.exists(triggers_filename):
            with open(triggers_filename, 'r', encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                if not line.strip().startswith('#'):
                    if '[' in line and ']' in line:
                        hash = line.split('[', 1)[1]
                        hash = hash.split(']', 1)[0].strip()
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

    # scrapes the specified URL
    def scrape(self, playwright: Playwright, url = '') -> None:
        if url != '':
            self.url = url
        if self.url != "":
            tries = 0
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
                    page.goto(self.url, wait_until="networkidle")
                except:
                    print('Error connecting to ' + self.url + '; re-trying in 5 seconds...')
                    tries += 1
                    time.sleep(5)
                else:
                    success = True
            page.keyboard.down('End')
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
                            if "meta" in image and image["meta"] is not None:
                                if "prompt" in image["meta"]:
                                    p = image["meta"]["prompt"]
                                    found = False
                                    for i in self.metadata:
                                        if p == i['prompt']:
                                            found = True
                                            break
                                    if not found:
                                        total_images += 1
                                        self.metadata.append(image["meta"])
                    #print('Post ID ' + str(post["postId"]) + ' -> number of images: ' + str(image_count))
            print('Found ' + str(count) + ' posts with ' + str(total_images) + ' images containing metadata...')

    # writes output .prompts file from given list of image metadata
    def write(self, hash, model_name, metadata = []):
        if metadata == []:
            metadata = self.metadata

        filename = 'civitai-' + model_name + '.prompts'
        with open(filename, 'w', encoding="utf-8") as f:
            f.write('[config]\n\n!MODE = standard\n!REPEAT = yes\n\n!WIDTH = 1408\n!HEIGHT = 1408\n')
            f.write('!HIGHRES_FIX = yes\n!STRENGTH = 0.68\n!FILENAME = <model>-<date>-<time>\n')
            f.write('!AUTO_INSERT_MODEL_TRIGGER = end\n\n!CKPT_FILE = ' + hash)
            f.write('\n\n[prompts]\n')

            for image in metadata:
                prompt = image["prompt"].replace('\n', '')
                if prompt.startswith('['):
                    prompt = 'image of ' + prompt
                if prompt.endswith(','):
                    prompt = prompt[:-1]
                negPrompt = ""
                sampler = ""
                scale = -1
                steps = 20
                if "negativePrompt" in image:
                    negPrompt = image["negativePrompt"].replace('\n', '')
                    f.write('\n!NEG_PROMPT = ' + negPrompt + '\n')
                if "sampler" in image:
                    sampler = image["sampler"]
                    f.write('!SAMPLER = ' + sampler + '\n')
                if "cfgScale" in image:
                    scale = image["cfgScale"]
                    f.write('!SCALE = ' + str(scale) + '\n')
                if "steps" in image:
                    steps = image["steps"]
                    f.write('!STEPS = ' + str(steps) + '\n')
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


# entry point
if __name__ == '__main__':

    count = 0
    all_data = {}

    with sync_playwright() as playwright:
        civitai = Civitai()

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
                civitai.scrape(playwright, url)
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


    # write all to a single file
    filename = 'civitai-all.prompts'
    with open(filename, 'w', encoding="utf-8") as f:
        f.write('[config]\n\n!MODE = standard\n!REPEAT = yes\n\n!WIDTH = 1408\n!HEIGHT = 1408\n')
        f.write('!HIGHRES_FIX = yes\n!STRENGTH = 0.68\n!FILENAME = <model>-<date>-<time>\n')
        f.write('!AUTO_INSERT_MODEL_TRIGGER = end\n\n[prompts]\n')

        for key, metadata in all_data.items():
            f.write('\n\n#########################\n!CKPT_FILE = ' + civitai.get_hash_from_civitai_id(key) + '\n#########################\n\n')
            for image in metadata:
                prompt = image["prompt"].replace('\n', '')
                if prompt.startswith('['):
                    prompt = 'image of ' + prompt
                if prompt.endswith(','):
                    prompt = prompt[:-1]
                negPrompt = ""
                sampler = ""
                scale = -1
                steps = 20
                if "negativePrompt" in image:
                    negPrompt = image["negativePrompt"].replace('\n', '')
                    f.write('\n!NEG_PROMPT = ' + negPrompt + '\n')
                if "sampler" in image:
                    sampler = image["sampler"]
                    f.write('!SAMPLER = ' + sampler + '\n')
                if "cfgScale" in image:
                    scale = image["cfgScale"]
                    f.write('!SCALE = ' + str(scale) + '\n')
                if "steps" in image:
                    steps = image["steps"]
                    f.write('!STEPS = ' + str(steps) + '\n')
                f.write(prompt + '\n\n')
