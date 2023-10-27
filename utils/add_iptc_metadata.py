# Copyright 2021 - 2023, Bill Kennedy (https://github.com/rbbrdckybk/dream-factory)
# SPDX-License-Identifier: MIT

# simple IPTC metadata utility
# usage help: python add_iptc_metadata.py --help

# example usage:

# This will overwrite any existing IPTC metadata for all .jpg images in C:\images with the specified example metadata:
# python add_iptc_metadata.py --dir "C:\images" --iptc_title "Example Title" -- --iptc_description "Example Description" --iptc_keywords "example, key, word" --iptc_copyright "Example Copyright"

# This will leave any existing metadata intact, but append the keywords "example, key, word" to the IPTC keywords field:
# python add_iptc_metadata.py --dir "C:\images" --append --iptc_keywords "example, key, word"


import sys
import argparse
import os
from os.path import exists

sys.path.insert(0, '../scripts')
import metadata


# entry point
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'IPTC metadata utility')
    parser.add_argument(
        "--append",
        action='store_true',
        help="append specified metadata fields instead of overwriting them"
    )
    parser.add_argument(
        "--iptc_title",
        default='',
        help="information to populate IPTC Title with"
    )
    parser.add_argument(
        "--iptc_description",
        default='',
        help="information to populate IPTC Description with"
    )
    parser.add_argument(
        "--iptc_keywords",
        default='',
        help="information to populate IPTC Keywords with (use commas to separate keywords)"
    )
    parser.add_argument(
        "--iptc_copyright",
        default='',
        help="information to populate IPTC Copyright with"
    )
    requiredNamed = parser.add_argument_group('required arguments')
    requiredNamed.add_argument(
        "--dir",
        required=True,
        help="input folder location (all .jpg files in this folder will processed)"
    )
    opt = parser.parse_args()

    if not exists(opt.dir):
        print('Specified input location does not exist, exiting!')
        exit(-1)
    else:
        keywords = []
        if opt.iptc_keywords != '':
            keys = opt.iptc_keywords.split(',')
            for k in keys:
                keywords.append(k.strip())
        count = 0
        files = [ f for f in os.listdir(opt.dir) if os.path.isfile(os.path.join(opt.dir,f)) ]
        for file in files:
            if file.lower().endswith('.jpg'):
                full_path = os.path.join(opt.dir, file)
                if not opt.append:
                    metadata.write_iptc_info(full_path,
                        opt.iptc_title,
                        opt.iptc_description,
                        keywords,
                        opt.iptc_copyright)
                else:
                    metadata.write_iptc_info_append(full_path,
                        opt.iptc_title,
                        opt.iptc_description,
                        keywords,
                        opt.iptc_copyright)
                count += 1

        print('\n Done - processed ' + str(count) + ' *.jpg images in ' + str(opt.dir) + '.')
