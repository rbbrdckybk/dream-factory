# Copyright 2021 - 2023, Bill Kennedy (https://github.com/rbbrdckybk/dream-factory)
# SPDX-License-Identifier: MIT

# Dream Factory lexica_scraper utility
# Queries lexica.art for specified search term(s) and saves to lexica-[search term]-prompts.txt
# Usage:
# python lexica_scraper.py --search [search term]
# python lexica_scraper.py --file [path/name to text file containing multiple search terms]
# running with no arguments will simply return the current top prompts on lexica.art.
# For additional options, use: python lexica_scraper.py --help

import argparse
import json
import time
import traceback
import urllib.parse
from collections import deque
from urllib.request import urlopen
from string import printable

# entry point
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--search",
        type=str,
        default="top",
        help="the term to search for"
    )
    parser.add_argument(
        "--no_nsfw",
        action='store_true',
        help="ignore prompts marked as nsfw"
    )
    parser.add_argument(
        "--file",
        type=str,
        default="",
        help="pass in a text file of inputs, one per line"
    )

    opt = parser.parse_args()
    images = []

    if opt.file == '':
        if (opt.search == 'top'):
            print('Grabbing top results from lexica.art...')
        else:
            print('Grabbing results from lexica.art that match: ' + opt.search + '...')

        URL = "https://lexica.art/api/v1/search?q=" + urllib.parse.quote_plus(opt.search)
        page = urlopen(URL)
        strpage = page.read().decode('utf-8')
        prompts = json.loads(strpage)

        # first insert to a list so we can sanitize and de-dupe
        for prompt in prompts["images"]:
            if opt.no_nsfw and prompt["nsfw"]:
                pass
            else:
                fp = prompt["prompt"].strip()
                # remove trailing spaces and commas
                while fp.endswith(' ') or fp.endswith(','):
                    fp = fp[:-1]
                # fix double commas
                fp = fp.replace(',,', ',')
                images.append(fp)

    else:
        opt.search = 'multiple'
        search_queue = deque()
        first = True

        with open(opt.file, 'r') as f:
            lines = f.readlines()

        for line in lines:
            if line.strip() != '' and line.strip() != '\n':
                if line.startswith('['):
                    line = line.replace('[', '')
                    line = line.replace(']', '')
                search_queue.append(line)

        while len(search_queue) > 0:

            if first:
                first = False
            else:
                time.sleep(1)

            # lazy copy/paste of above, make a function if this is going to be re-usable
            line = ''
            try:
                line = search_queue.popleft()
                print('Grabbing results from lexica.art that match: ' + line + '...')
                URL = "https://lexica.art/api/v1/search?q=" + urllib.parse.quote_plus(line)
                page = urlopen(URL)
                strpage = page.read().decode('utf-8')
                prompts = json.loads(strpage)

                # first insert to a list so we can sanitize and de-dupe
                for prompt in prompts["images"]:
                    if opt.no_nsfw and prompt["nsfw"]:
                        pass
                    else:
                        fp = prompt["prompt"].strip()
                        # remove trailing spaces and commas
                        while fp.endswith(' ') or fp.endswith(','):
                            fp = fp[:-1]
                        # fix double commas
                        fp = fp.replace(',,', ',')
                        images.append(fp)
            except Exception:
                print("Got a rate-limit exception; waiting 90 seconds between continuing...")
                # put the item back at the head of the queue and wait
                search_queue.appendleft(line)
                time.sleep(90)


    # de-dupe
    final = [*set(images)]

    # now write final list to file
    f = open('lexica-' + opt.search + '-prompts.txt', 'w', encoding = 'utf-8')
    for prompt in final:
        f.write(prompt + '\n\n')
    f.close()

    print('Done - lexica-' + opt.search + '-prompts.txt saved!')
