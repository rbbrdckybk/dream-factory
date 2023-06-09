# Copyright 2021 - 2023, Bill Kennedy (https://github.com/rbbrdckybk/dream-factory)
# SPDX-License-Identifier: MIT

import os
import sys
import time
import threading
import requests
from os.path import exists
import hashlib as hashlib
from pathlib import Path


# for civitai.com model lookups in a background thread
class CivitaiFetcher(threading.Thread):
    def __init__(self, hashlist, model_type_desc, callback=lambda: None, debug=False, *args):
        threading.Thread.__init__(self)
        self.URL = "https://civitai.com/api/v1/model-versions/by-hash/"
        self.debug = debug
        self.callback = callback
        self.hashlist = hashlist
        self.model_type_desc = model_type_desc.lower()
        self.print_lock = threading.Lock()
        self.lookup_count = 0
        self.data_file = ""

        dir = 'cache'
        self.data_file = os.path.join(dir, 'civitai-model.txt')
        if 'lora' in self.model_type_desc:
            self.data_file = os.path.join(dir, 'civitai-lora.txt')
        elif 'embedding' in self.model_type_desc:
            self.data_file = os.path.join(dir, 'civitai-embedding.txt')
        elif 'hypernet' in self.model_type_desc:
            self.data_file = os.path.join(dir, 'civitai-hypernet.txt')

    def run(self):
        self.lookup_hashes(self.hashlist, self.data_file)
        self.callback(self.lookup_count)

    # looks up list of hashes on civitai.com
    # writes data to specified filename
    def lookup_hashes(self, hash_list, filename):
        URL = self.URL
        cache = []
        for hash in hash_list:
            self.print('Working on model hash ' + hash + '...')
            skip = False
            self.lookup_count += 1
            hashinfo = requests.get(URL + hash.upper())
            try:
                data = hashinfo.json()
            except:
                self.print('Error attempting to lookup model hash ' + hash + ' on civitai.com; skipping...')
                self.lookup_count -= 1
                skip = True
            if not skip:
                if 'model' in data and 'name' in data['model']:
                    info = hash + ';'
                    model_name = data['model']['name'].replace(';', ',').strip()
                    model_id = data['modelId']
                    version_name = data['name'].replace(';', ',').strip()
                    triggers = data['trainedWords']
                    baseModel = data['baseModel'].strip()
                    nsfw = 'sfw'
                    if data['model']['nsfw']:
                        nsfw = 'nsfw'
                    #description = data['description']
                    self.print('Found hash ' + hash + ': ' + str(model_id) + ': ' + model_name + ' (' + version_name + ')')

                    # remove non-triggers (e.g. '<lora:xxx:xxx>')
                    # grab default weight if possible
                    lora_weight = '1.0'
                    bad_triggers = []
                    for t in triggers:
                        if '<' in t and '>' in t:
                            bad_triggers.append(t)
                            trig = t.split('<', 1)[1]
                            trig = trig.split('>', 1)[0]
                            if ':' in trig:
                                weight = trig.rsplit(':', 1)[1]
                                try:
                                    float(weight)
                                except ValueError:
                                    pass
                                else:
                                    if float(weight) > 0 and float(weight) < 1:
                                        lora_weight = str(weight)

                    for t in bad_triggers:
                        triggers.remove(t)

                    # write info to cache file
                    #info += str(model_id) + ';' + model_name + ';' + version_name + ';' + baseModel + ';' + nsfw
                    info += str(model_id) + ';' + model_name + ';' + baseModel + ';' + nsfw + ';'

                    tw = ''
                    count = 0
                    for trig in triggers:
                        if count > 0:
                            tw += ','
                        tw += trig.strip()
                        count += 1
                    info += tw

                    # add default weight for loras
                    if 'lora' in self.model_type_desc.lower() or 'hypernet' in self.model_type_desc.lower():
                        info += ';' + lora_weight

                    if info not in cache:
                        with open(filename, 'a', encoding="utf-8") as f:
                            f.write(info + '\n')
                        cache.append(info)
                else:
                    self.print('Hash ' + hash + ' not found on civitai.com!')
                    if hash not in cache:
                        with open(filename, 'a', encoding="utf-8") as f:
                            f.write(hash + '\n')
                        cache.append(hash)

    # for debugging
    def print(self, text, force=False):
        if self.debug or force:
            out_txt = "[CivitaiFetcher thread] >>> " + text
            with self.print_lock:
                print(out_txt)


# for calculating autov2 hashes of models in a background thread
class HashCalc(threading.Thread):
    def __init__(self, filelist, model_type_desc, callback=lambda: None, debug=False, *args):
        threading.Thread.__init__(self)
        self.files = filelist
        self.callback = callback
        self.debug = debug
        self.startup_errors = False
        self.print_lock = threading.Lock()
        self.lora_cache_file = ""
        self.embedding_cache_file = ""
        self.model_cache_file = ""
        self.hypernet_cache_file = ""
        self.hash_calc_count = 0
        self.model_type_desc = model_type_desc.lower()
        self.startup()

    def run(self):
        if not self.startup_errors:
            # calculate hashes
            hashes = []
            cache_file = self.model_cache_file
            if 'lora' in self.model_type_desc:
                cache_file = self.lora_cache_file
            elif 'embedding' in self.model_type_desc:
                cache_file = self.embedding_cache_file
            elif 'hypernet' in self.model_type_desc:
                cache_file = self.hypernet_cache_file
            for file in self.files:
                self.print('Calculating hash for: ' + file + '...')
                hash = self.model_hash(file)
                self.print('Calculated AutoV2 hash: ' + hash + '...')
                short_file = os.path.basename(file)
                hashes.append(short_file + ', ' + hash)
                # write to cache file
                with open(cache_file, 'a', encoding="utf-8") as f:
                    f.write(short_file + ', ' + hash + '\n')
                self.hash_calc_count += 1

        else:
            self.print('Aborted hash calculations due to startup errors!', True)

        self.callback(self.hash_calc_count)

    # returns autov2 hash for the specified file
    def model_hash(self, filename):
        hash = ""
        sha256_hash = hashlib.sha256()
        with open(filename, "rb") as f:
            for block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(block)
            hash = sha256_hash.hexdigest()
        # take first 10 digits for autov2
        return hash[0:10]

    # ensure cache directory exists, etc
    # errors here will abort entire process
    def startup(self):
        dir = 'cache'
        if not os.path.exists(dir):
            try:
                Path(dir).mkdir(parents=True, exist_ok=True)
            except:
                self.print('Error: cache directory could not be created!', True)
                self.startup_errors = True

        self.lora_cache_file = os.path.join(dir, 'hashes-lora.txt')
        if not exists(self.lora_cache_file):
            try:
                with open(self.lora_cache_file, 'w', encoding="utf-8") as f:
                    # create empty file
                    pass
            except:
                self.print('Error: lora cache file could not be created!', True)
                self.startup_errors = True

        self.embedding_cache_file = os.path.join(dir, 'hashes-embedding.txt')
        if not exists(self.embedding_cache_file):
            try:
                with open(self.embedding_cache_file, 'w', encoding="utf-8") as f:
                    # create empty file
                    pass
            except:
                self.print('Error: embedding cache file could not be created!', True)
                self.startup_errors = True

        self.model_cache_file = os.path.join(dir, 'hashes-model.txt')
        if not exists(self.model_cache_file):
            try:
                with open(self.model_cache_file, 'w', encoding="utf-8") as f:
                    # create empty file
                    pass
            except:
                self.print('Error: model cache file could not be created!', True)
                self.startup_errors = True

        self.hypernet_cache_file = os.path.join(dir, 'hashes-hypernet.txt')
        if not exists(self.hypernet_cache_file):
            try:
                with open(self.hypernet_cache_file, 'w', encoding="utf-8") as f:
                    # create empty file
                    pass
            except:
                self.print('Error: hypernet cache file could not be created!', True)
                self.startup_errors = True

    # for debugging
    def print(self, text, force=False):
        if self.debug or force:
            out_txt = "[HashCalc thread] >>> " + text
            with self.print_lock:
                print(out_txt)


# manages background work threads
class BackgroundWorker():
    def __init__(self, control_ref, debug=False, model_type_desc='model'):
        self.control_ref = control_ref
        self.working = False
        self.debug = debug
        self.model_type_desc = model_type_desc
        self.print_lock = threading.Lock()

    # do civitai lookup work in the background
    def civitai_lookup_start(self, file_list):
        self.working = True
        self.print('CivitaiFetcher work starting!')
        thread = CivitaiFetcher(file_list, self.model_type_desc, self.civitai_lookup_finished, self.debug)
        thread.start()

    # callback for civitai lookup worker threads when finished
    def civitai_lookup_finished(self, count, *args):
        desc = self.model_type_desc + ' hash'
        if count > 1:
            desc += 'es'
        self.control_ref.print('Finished background civitai.com lookups for ' + str(count) + ' uncached ' + desc + '...')
        self.control_ref.civitai_startup_stage += 1
        self.control_ref.civitai_new_stage = True
        self.working = False


    # do hash calculation work in the background
    def hashcalc_start(self, file_list):
        self.working = True
        self.print('HashCalc work starting!')
        thread = HashCalc(file_list, self.model_type_desc, self.hashcalc_finished, self.debug)
        thread.start()

    # callback for hashcalc worker threads when finished
    def hashcalc_finished(self, count, *args):
        desc = self.model_type_desc
        if count > 1:
            desc += 's'
        self.control_ref.print('Finished background hash calculations for ' + str(count) + ' uncached ' + desc + '...')
        self.control_ref.civitai_startup_stage += 1
        self.control_ref.civitai_new_stage = True
        self.working = False

    # for debugging
    def print(self, text, force=False):
        if self.debug or force:
            out_txt = "[Background Worker] >>> " + text
            with self.print_lock:
                print(out_txt)
