# Copyright 2021 - 2023, Bill Kennedy (https://github.com/rbbrdckybk/dream-factory)
# SPDX-License-Identifier: MIT

# Dream Factory chain.py utility
# Simple utility that will chain a bunch of .prompts files together by adding
# !NEXT_PROMPT_FILE directives to each file. Allows you to run many prompt prompt
# files unattended. Note this should only be used on standard (not random or process)
# prompt files! You may want to back up your .prompts files before running this, as
# edits will be made directly to your files.
# Usage:
# python chain.py --dir [directory containing .prompts files to chain together]
# For additional options, use: python chain.py --help

import os
import argparse

# entry point
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dir",
        type=str,
        default='',
        help="the directory containing the .prompts files you want to chain together"
    )
    parser.add_argument(
        "--resize",
        type=int,
        default=0,
        help="additionally enable !AUTO_RESIZE (to the specified longest dimension) for each prompt file"
    )
    opt = parser.parse_args()

    prompt_files = []
    if opt.dir != '' and os.path.exists(opt.dir):
        for root, dirs, files in os.walk(opt.dir):
            for file in files:
                if file.lower().endswith('.prompts'):
                    full_path = os.path.join(root, file)
                    prompt_files.append(full_path)

    i = 0
    for file in prompt_files:
        # read prompt file
        lines = ''
        with open(file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # make edits
        edited_lines = ''
        found_config = False
        finished = False
        for line in lines:
            #print(line)
            if line.lower().strip().startswith('[config]'):
                found_config = True
            if found_config:
                if line.lower().strip().startswith('[prompts]'):
                    finished = True
                    next_file = ''
                    if i+1 >= len(prompt_files):
                        next_file = os.path.basename(prompt_files[0])
                    else:
                        next_file = os.path.basename(prompt_files[i+1])
                    pre = '# added by chain.py\n# note these will override any settings above'
                    pre += '\n!REPEAT = no\n!NEXT_PROMPT_FILE = ' + next_file

                    if opt.resize > 0:
                        line = pre + '\n!AUTO_SIZE = resize_longest_dimension: ' + str(opt.resize) + '\n\n' + line
                    else:
                        line = pre + '\n\n' + line

                if not finished:
                    if '!repeat' in line.lower():
                        #line = '#' + line
                        pass
                    if '!next_prompt_file' in line.lower():
                        #line = '#' + line
                        pass
            edited_lines += line

        if not found_config:
            print(file + ' does not have a [config] section; no edits made!')
        else:
            with open(file, 'w', encoding='utf-8') as f:
                f.write(edited_lines)

        i += 1
