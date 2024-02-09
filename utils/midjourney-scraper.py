# Copyright 2021 - 2023, Bill Kennedy (https://github.com/rbbrdckybk/dream-factory)
# SPDX-License-Identifier: MIT

# simple Midjourney showcase prompt scraper utility
# usage: python midjourney-scraper.py

# This requires Playwright, which can be installed with these commands:
# pip3 install playwright
# playwright install

from playwright.sync_api import Playwright, sync_playwright
from datetime import datetime
import time
import json
import argparse
import os
from os.path import exists

url = "https://www.midjourney.com/showcase"
search = 'recent-jobs?amount=50&page=0'
json_file = ''

top = False
searchFound = False
outdir = ''
outname = ''
header = ''
footer = ''

# entry point
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--top",
        action='store_true',
        help="fetch the top showcase instead of recent"
    )
    parser.add_argument(
        "--file",
        default='',
        help="use this .json file instead of scraping midjourney.com"
    )
    parser.add_argument(
        "--outdir",
        default='',
        help="output folder location (must exist!)"
    )
    parser.add_argument(
        "--outname",
        default='midjourney',
        help="output filename (date will be appended automatically); default is 'midjourney'"
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
    opt = parser.parse_args()
    top = opt.top
    json_file = opt.file
    outdir = opt.outdir
    outname = opt.outname
    header = opt.header
    footer = opt.footer


def create_output(json):
    global outdir
    global outname
    global header
    global footer

    r = json
    count = 0
    prompts = []

    if r["jobs"]:
        for job in r["jobs"]:
            if "full_command" in job and job["full_command"] is not None:
                count += 1
                prompt = job["full_command"].replace('\n', '').strip()
                if prompt.startswith('['):
                    prompt = 'image of ' + prompt
                if '--ar' in prompt:
                    prompt = prompt.split('--ar', 1)[0].strip()
                while prompt.endswith(','):
                    prompt = prompt[:-1]
                while prompt.startswith('*'):
                    prompt = prompt[1:]
                if prompt.lower().startswith('/imagine'):
                    prompt = prompt[8:].strip()
                if '<<<' in prompt and '>>>' in prompt:
                    start = prompt.split('<<<', 1)[0]
                    end = prompt.split('>>>', 1)[1]
                    prompt = start + ' ' + end
                prompt = prompt.strip()
                prompts.append(prompt)

        prompts = list(set(prompts))
        prompts.sort()

        date = datetime.today().strftime('%Y-%m-%d')
        filename = outname + '-' + date + '.prompts'
        if top:
            filename = outname + '-showcase-top.prompts'
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

            f.write('[prompts]\n\n')
            f.write('#####################################################################################################################################\n')
            f.write('### Dream Factory standard .prompts file\n')
            f.write('### Created with midjourney-scraper.py on ' + str(date) + '\n')
            f.write('### ' + str(len(prompts)) + ' unqiue prompts scraped from: ' + url.replace(' ', '+') + '\n')
            f.write('#####################################################################################################################################\n\n')

            # write scraped prompts
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
        global top
        global search
        global searchFound
        # the endpoint we are insterested in
        #print(response.url)

        if top:
            search = 'top.json'
        if (search in response.url):
            #resp = json.dumps(response.json(), indent=2)
            #with open('midjourney.json', 'w') as f:
            #    f.write(resp)

            if response.ok:
                searchFound = True
                r = response.json()
                create_output(r)
            else:
                print('Error: midjourney.com returned a non-OK response (code: ' + str(response.status) + ') (possible bot detection)!')
                #print(response.text())


    # we're scraping from midjourney.com
    if json_file == '':
        run(playwright)
        if not searchFound:
            print('Error: no response with "' + search + '" in the URL!')

    # we have a .json file
    else:
        lines = ''
        with open(json_file, 'r', encoding="utf-8") as f:
            json_data = json.load(f)
        create_output(json_data)
