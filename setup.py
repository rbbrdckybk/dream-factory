# Copyright 2021 - 2022, Bill Kennedy
# SPDX-License-Identifier: MIT
# Dream Factory setup script
# https://github.com/rbbrdckybk/dream-factory

import argparse
import datetime
import shlex
import subprocess
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
def exec(command, verbose = False):
    if verbose:
        subprocess.call(command)
    else:
        subprocess.call(command, stdout=subprocess.DEVNULL)

# execute subprocess in another working dir
def exec_cwd(command, wd, verbose = False):
    if verbose:
        subprocess.call(command, cwd=(wd))
    else:
        subprocess.call(command, cwd=(wd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# grabs all required git repos
def clone_repos(verbose = False):
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
        exec(base+repo, verbose)

# installs all dependancies via pip
def install_pytorch(verbose = False):
    print('\nInstalling Pytorch (this may take a few minutes):')
    cmd = 'conda install -y pandas pytorch torchvision torchaudio cudatoolkit=11.3 -c pytorch'
    exec(cmd, verbose)

# installs all dependancies via pip
def install_dependencies(verbose = False):
    print('\nInstalling all required dependencies:')
    base = 'pip install --no-input '
    packages = [ \
        'transformers', \
        'diffusers', \
        'cherrypy', \
        'ftfy', \
        'numpy', \
        'pillow', \
        'omegaconf', \
        'pytorch-lightning', \
        'kornia', \
        'imageio', \
        'imageio-ffmpeg', \
        'einops', \
        'torch-fidelity', \
        'opencv-python', \
        'datetime', \
        'basicsr', \
        'facexlib', \
        'gfpgan'
    ]
    packages.sort()

    for package in packages:
        msg('   installing ' + package + '...', verbose)
        exec(base+package, verbose)

# perform real-esrgan setup
def setup_esrgan(verbose = False):
    print('\nSetting up Real-ESRGAN:')
    cmd = 'curl -L -o Real-ESRGAN/experiments/pretrained_models/RealESRGAN_x4plus.pth -C - \"https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth\"'
    msg('   downloading pre-trained models...', verbose)
    exec(cmd, verbose)

    cwd = os.getcwd()
    cmd = 'python setup.py develop'
    msg('   running ESRGAN setup script...', verbose)
    exec_cwd(cmd, cwd + os.path.sep + 'Real-ESRGAN', verbose)

# updates these repos to the latest version
def update():
    print('\nChecking for updates:')
    cmd = 'git pull'
    cwd = os.getcwd()

    print('updating dream-factory...')
    exec(cmd, True)

    print('updating stable-diffusion...')
    exec_cwd(cmd, cwd + os.path.sep + 'stable-diffusion', True)

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
        "--update",
        action='store_true',
        help="updates a previous installation"
    )

    opt = parser.parse_args()
    verbose = opt.verbose

    if opt.update:
        if os.path.exists('stable-diffusion'):
            # user is requesting an update
            update()
        else:
            print('\nNo previous installation detected; aborting update.')
            print('Run without the --update switch first.\n')
    else:
        if opt.force or not os.path.exists('stable-diffusion'):
            # either no previous installation or the user is forcing re-install
            clone_repos(verbose)
            install_pytorch(verbose)
            install_dependencies(verbose)
            setup_esrgan(verbose)

            checkpoint_path = 'stable-diffusion\models\ldm\stable-diffusion-v1'
            if not os.path.exists(checkpoint_path):
                os.makedirs(checkpoint_path)

            print('\n\nAll done - don\'t forget to place your model.ckpt file in this directory! : ')
            print(checkpoint_path + '\n')
        else:
            print('\nPrevious installation detected; aborting setup.')
            print('If you really want to run setup again, use the --force switch.')
            print('If you want to update this installation, use the --update switch.\n')
