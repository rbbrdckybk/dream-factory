# Copyright 2021 - 2023, Bill Kennedy (https://github.com/rbbrdckybk/dream-factory)
# SPDX-License-Identifier: MIT

# simple civitai.com image prompt scraper utility
# usage: python civitai-image-scraper.py [options]
# examples:
# python civitai-image-scraper.py
# python civitai-image-scraper.py --remove_loras --no-neg

# or for help/options: python civitai-image-scraper.py --help

# This requires Playwright, which can be installed with these commands:
# pip3 install playwright
# playwright install

from playwright.sync_api import Playwright, sync_playwright
from datetime import datetime
import time
import json
import argparse
import os
import re
from os.path import exists

url = "https://www.civitai.com/images"
search = 'image.getInfinite'

searchFound = False
outdir = ''
header = ''
footer = ''
neg_prompts = True
remove_loras = False
query_mode = False

# entry point
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--outdir",
        default='',
        help="output folder location (must exist!)"
    )
    parser.add_argument(
        "--header",
        default='',
        help=".txt file containing text to prepend output .prompts file with"
    )
    parser.add_argument(
        "--footer",
        default='',
        help=".txt file containing text to append output .prompts file with"
    )
    parser.add_argument(
        "--no_neg",
        action='store_true',
        help="do not include negative prompts"
    )
    parser.add_argument(
        "--remove_loras",
        action='store_true',
        help="remove all lora/hypernet references from prompts"
    )
    opt = parser.parse_args()
    outdir = opt.outdir
    header = opt.header
    footer = opt.footer
    if opt.no_neg == True:
        neg_prompts = False
    if opt.remove_loras == True:
        remove_loras = True


def create_output(json):
    global outdir
    global header
    global footer
    global neg_prompts
    global remove_loras

    r = json
    count = 0
    prompts = []
    prompts_unique = []

    if r["result"]["data"]["json"]["items"]:
        for job in r["result"]["data"]["json"]["items"]:
            if "meta" in job and job["meta"] is not None and "prompt" in job["meta"] and job["meta"]["prompt"] is not None:
                count += 1
                id = ''
                if "id" in job and job["id"] is not None:
                    id = str(job["id"])

                prompt = job["meta"]["prompt"].replace('\n', '').strip()
                if prompt.startswith('['):
                    prompt = 'image of ' + prompt
                while prompt.endswith(','):
                    prompt = prompt[:-1]
                while prompt.startswith('*'):
                    prompt = prompt[1:]

                # remove loras/hypernets if necessary
                if opt.remove_loras:
                    while '<lora:' in prompt and '>' in prompt:
                        p = prompt
                        before = p.split('<lora:', 1)[0]
                        after = p.split('<lora:', 1)[1]
                        after = after.split('>', 1)[1]
                        prompt = (before + after).strip()

                    while '<hypernet:' in prompt and '>' in prompt:
                        p = prompt
                        before = p.split('<hypernet:', 1)[0]
                        after = p.split('<hypernet:', 1)[1]
                        after = after.split('>', 1)[1]
                        prompt = (before + after).strip()

                    while '<ti:' in prompt and '>' in prompt:
                        p = prompt
                        before = p.split('<ti:', 1)[0]
                        after = p.split('<ti:', 1)[1]
                        after = after.split('>', 1)[1]
                        prompt = (before + after).strip()

                while '  ' in prompt:
                    prompt = prompt.replace('  ', ' ')
                prompt = prompt.strip()

                if prompt not in prompts_unique:
                    prompts_unique.append(prompt)
                    if neg_prompts == True:
                        neg = ''
                        if "negativePrompt" in job["meta"] and job["meta"]["negativePrompt"] is not None:
                            neg = job["meta"]["negativePrompt"].replace('\n', '').strip()
                            while '  ' in neg:
                                neg = neg.replace('  ', ' ')
                        neg = '!NEG_PROMPT = ' + neg + '\n\n'
                        prompt = neg + prompt

                        if id != '':
                            prompt = '# ' + url + '/' + id + '\n' + prompt

                    prompts.append(prompt)

        prompts = list(set(prompts))
        prompts.sort()

        date = datetime.today().strftime('%Y-%m-%d')
        filename = 'civitai-images-' + date + '.prompts'
        if outdir != '':
            if os.path.exists(outdir):
                filename = os.path.join(outdir, filename)
            else:
                print('Output directory (' + outdir + ') does not exist; defaulting to execution location!')

        with open(filename, 'w', encoding="utf-8") as f:
            # write header if necessary
            if header != '':
                if os.path.exists(header):
                    lines = ''
                    with open(header, 'r', encoding="utf-8") as h:
                        lines = h.readlines()
                    for line in lines:
                        f.write(line)
                else:
                    print('Header file (' + header + ') does not exist; ignoring it!')

            # write scraped prompts
            f.write('\n[prompts]\n\n')
            f.write('\n#######################################################################################################\n')
            f.write('# Created with utils\civitai-image-scraper.py\n')
            f.write('# ' + str(len(prompts)) + ' unique prompts from https://www.civitai.com/images' + '\n')
            f.write('#######################################################################################################\n\n')
            for prompt in prompts:
                f.write(prompt + '\n\n')

            # write footer if necessary
            if footer != '':
                if os.path.exists(footer):
                    lines = ''
                    with open(footer, 'r', encoding="utf-8") as h:
                        lines = h.readlines()
                    for line in lines:
                        f.write(line)
                else:
                    print('Footer file (' + footer + ') does not exist; ignoring it!')

        print('Done! Wrote ' + filename)


def run(playwright: Playwright) -> None:
    # headless = True will result in being flagged as a bot
    browser = playwright.chromium.launch(headless = False)
    context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36')

    s = """
    navigator.webdriver = false
    Object.defineProperty(navigator, 'webdriver', {
    get: () => false
    })
    """

    # Open new page
    page = context.new_page()
    page.add_init_script(s)
    page.on("response", handle_response)
    try:
        page.goto(url, wait_until="networkidle")
    except Exception as e:
        print('Encountered an error, aborting...')
        print('Error details: ')
        print(e)
    else:
        page.keyboard.down('End')
    page.context.close()
    browser.close()

with sync_playwright() as playwright:
    def handle_response(response):
        global search
        global searchFound

        if (search in response.url):
            if response.ok:
                searchFound = True
                r = response.json()
                create_output(r)
            else:
                print('Error: civitai.com returned a non-OK response (code: ' + str(response.status) + ') (possible bot detection)!')

    run(playwright)
    if not searchFound:
        print('Error: no response with "' + search + '" in the URL!')
