# Dream Factory

Multi-threaded GUI manager for mass creation of AI-generated art with support for multiple GPUs.

# Features

 * Multi-threaded engine capable of simultaneous management of multiple GPUs.
 * Powerful custom prompt file format that allows you to easily define compound prompt templates. Want to quickly create thousands of prompts from a template like "_photo of a **[adjective(s)] [animal]** as a **[profession]**, art by **[artist(s)]**, **[keyword(s)]**_" where each bracketed section needs to be filled in with dozens (or hundreds) of different items? No problem. Maybe you want your GPUs to create every possible combination, or maybe you want combinations to be picked randomly? Your choice. Maybe you want some items to be handled with different settings? Totally doable.
 * 

# Requirements

You'll need at least one Nvidia GPU, preferably with a decent amount of VRAM. 3GB of VRAM should be enough to produce 512x512 images, but more GPU memory will allow you to create larger images (and/or create them faster).

# Setup

These instructions were tested on several Windows 10 desktops with a variety of modern Nvidia GPUs ranging from 8-12GB VRAM, and also on an Ubuntu Server 20.04.3 system with an old Nvidia Tesla M40 GPU (24GB VRAM).

**[1]** Install [Anaconda](https://www.anaconda.com/products/individual), open the root terminal, and create a new environment (and activate it):
```
conda create --name dream-factory python=3.9
conda activate dream-factory
```

**[2]** Clone this repository and switch to its directory:
```
git clone https://github.com/rbbrdckybk/dream-factory
cd dream-factory
```

**[3]** Install a couple required Python packages:
```
conda install -c anaconda git urllib3
```

**[4]** Run the included setup script to finish the rest of your installation automatically:
```
python setup.py
```

**[5]** Download the Stable Diffusion pre-trained checkpoint file:
 * First register [here](https://huggingface.co/CompVis) (only requires email and name)
 * Then [download the v1.4 checkpoint file](https://huggingface.co/CompVis/stable-diffusion-v-1-4-original/resolve/main/sd-v1-4.ckpt) (or [browse here](https://huggingface.co/CompVis) for a newer checkpoint file)
  * After downloading the checkpoint file, you'll need to rename it to **model.ckpt** and place it into the following directory:
```
\stable-diffusion\models\ldm\stable-diffusion-v1
```
This directory is located off the main **dream-factory** folder that you ran the setup script from in the previous step.

You're done! You can perform a test to make sure everything is working by running this (again, from the main **dream-factory** folder):
```
python dream-factory.py --prompt_file prompts/example-standard.prompts
```
This should start up the web interface with a simple example prompt file pre-loaded that your GPU(s) should start working on automatically. On the first run, several large files (~2GB total) will be downloaded automatically so it may take a few minutes before things start happening.

Eventually you should see images appearing in your **\output** folder (or you can click on the "Gallery" link within the web UI and watch for them there). If you're getting images, everything is working properly and you can move on to the next section.

If you're on Windows and see these errors appearing in the console:
```
OSError: Windows requires Developer Mode to be activated, or to run Python as an administrator, in order to create symlinks.
```
You'll need to [enable developer mode](https://www.howtogeek.com/292914/what-is-developer-mode-in-windows-10/) to get things working. I tested installations on several different Windows desktops, and only one gave me this error. Not sure what causes it, but enabling developer mode fixed it for me.

# Usage

TODO
