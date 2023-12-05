# Copyright 2021 - 2023, Bill Kennedy
# SPDX-License-Identifier: MIT
# Dream Factory setup script
# https://github.com/rbbrdckybk/dream-factory

import argparse
import datetime
import shlex
import subprocess
import shutil
import glob
import os
from os.path import exists, isdir, basename
from datetime import datetime as dt

# use this to give short messages summarizing what's
# happening when  verbose = False
def msg(text, verbose = False):
    if not verbose:
        print(text)

# execute subprocess
def exec(command, verbose = False, shell = False):
    if verbose:
        subprocess.run(shlex.split(command), shell=shell)
    else:
        subprocess.run(shlex.split(command), stdout=subprocess.DEVNULL, shell=shell)

# execute subprocess in another working dir
def exec_cwd(command, wd, verbose = False, shell = False):
    if verbose:
        subprocess.run(shlex.split(command), cwd=(wd), shell=shell)
    else:
        subprocess.run(shlex.split(command), cwd=(wd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=shell)

# grabs all required git repos
def clone_repos(verbose = False, shell = False):
    print('\nCloning all required repositories:')
    base = 'git clone https://github.com/'
    repos = [ \
        'CompVis/taming-transformers', \
        'openai/CLIP', \
        'rbbrdckybk/stable-diffusion', \
        'xinntao/Real-ESRGAN' \
    ]

    for repo in repos:
        msg('   fetching ' + repo + '...', verbose)
        exec(base+repo, verbose, shell)

# installs all dependancies via pip
def install_pytorch(verbose = False, shell = False):
    print('\nInstalling Pytorch (this may take several minutes - be patient do not abort!):')
    cmd = 'conda install -y pandas pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia'
    exec(cmd, verbose, shell)

# installs all dependancies via pip
def install_dependencies(verbose = False, shell = False):
    print('\nChecking for required dependencies:')
    base = 'pip install --no-input '
    packages = [ \
        #'transformers', \
        #'diffusers', \
        'cherrypy', \
        #'ftfy', \
        #'numpy', \
        'pillow', \
        #'omegaconf', \
        #'pytorch-lightning', \
        #'kornia', \
        #'imageio', \
        #'imageio-ffmpeg', \
        #'einops', \
        #'torch-fidelity', \
        #'opencv-python', \
        'datetime', \
        'psutil', \
        #'basicsr', \
        #'facexlib', \
        #'gfpgan', \
        'requests', \
        'IPTCInfo3'
    ]
    packages.sort()

    for package in packages:
        msg('   installing ' + package + '...', verbose)
        exec(base+package, verbose, shell)

# perform real-esrgan setup
def setup_esrgan(verbose = False, shell = False):
    print('\nSetting up Real-ESRGAN:')
    cmd = 'curl -L -o Real-ESRGAN/experiments/pretrained_models/RealESRGAN_x4plus.pth -C - https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth'
    msg('   downloading pre-trained models...', verbose)
    exec(cmd, verbose, shell)

    cwd = os.getcwd()
    cmd = 'python setup.py develop'
    msg('   running ESRGAN setup script...', verbose)
    exec_cwd(cmd, cwd + os.path.sep + 'Real-ESRGAN', verbose, shell)

# for debugging
def test(verbose = False, shell = False):
    print('\nTesting dummy call:')
    base = 'thiswillfail'
    exec(base, verbose, shell)

# create config.txt file
def create_config():
    if not os.path.exists('config.txt'):
        print('\nCreating config.txt containing default settings...')
        shutil.copy2('config-default.txt', 'config.txt')
    else:
        print('\nExisting config.txt found, leaving it intact...')

# updates these repos to the latest version
def update(shell = False):
    print('\nChecking for updates:')
    cmd = 'git pull'
    cwd = os.getcwd()

    try:
        print('updating dream-factory...')
        exec(cmd, True, shell)
        #print('updating stable-diffusion...')
        #exec_cwd(cmd, cwd + os.path.sep + 'stable-diffusion', True, shell)
        install_dependencies(False, shell)

    except FileNotFoundError:
        print('\nUnable to find git executable - try re-running update with the --shell option, e.g.:')
        print('   python setup.py --shell --update\n')
        exit(-1)

# entry point
if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--verbose",
        action='store_true',
        help="display all output from subprocesses"
    )

    parser.add_argument(
        "--force",
        action='store_true',
        help="force setup to run over a previous install"
    )

    parser.add_argument(
        "--shell",
        action='store_true',
        help="enable shell calls; try this if setup cannot find your executables"
    )

    parser.add_argument(
        "--update",
        action='store_true',
        help="updates a previous installation"
    )

    opt = parser.parse_args()
    verbose = opt.verbose
    shell = opt.shell

    if opt.update:
        if os.path.exists('logs'):
            # user is requesting an update
            update(shell)
        else:
            print('\nNo previous installation detected; aborting update.')
            print('Run without the --update switch first.\n')
    else:
        if opt.force or not os.path.exists('stable-diffusion'):
            # either no previous installation or the user is forcing re-install
            try:
                #clone_repos(verbose, shell)
                install_pytorch(verbose, shell)
                install_dependencies(verbose, shell)
                #setup_esrgan(verbose, shell)
            except FileNotFoundError:
                print('\nUnable to find executable - try re-running setup with the --shell option, e.g.:')
                print('   python setup.py --shell --force\n')
                exit(-1)

            create_config()
            #checkpoint_path = 'stable-diffusion\models\ldm\stable-diffusion-v1'
            #if not os.path.exists(checkpoint_path):
            #    os.makedirs(checkpoint_path)

            #print('\n\nAll done - don\'t forget to place your model.ckpt file in this directory! : ')
            #print(checkpoint_path + '\n')
            if not os.path.exists('output'):
                os.makedirs('output')

            print('\n\nAll done! - don\'t forget to add your automatic1111 repo location to config.txt!')

        else:
            print('\nPrevious installation detected; aborting setup.')
            print('If you really want to run setup again, use the --force switch.')
            print('If you want to update this installation, use the --update switch.\n')
