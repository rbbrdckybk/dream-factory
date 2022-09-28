# Dream Factory

Multi-threaded GUI manager for mass creation of AI-generated art with support for multiple GPUs.

This is aimed at the user that wants to create a **lot** of AI artwork with minimal hands-on time. If you're looking for a repo that will allow you to spend hours tweaking a single image until it's perfect, [there are better options](https://github.com/AUTOMATIC1111/stable-diffusion-webui). If you have hundreds of prompt ideas and want to easily and quickly (well, as quickly as your GPUs can manage!) see them rendered in hundreds of different variations and/or styles, then this is for you.

To illustrate, I've had an RTX 3060, RTX 3080Ti, and Tesla M40 running Dream Factory 24/7 for a couple weeks now, and they churn out roughly 5,000 images every day! Some samples (all straight out of Dream Factory other than some minor sharpening applied in Photoshop):  
<table>
<tr>
<td><img src="/images/01.jpg" width="160" height="160" alt="sample image 1" title="sample image 1"></td>
<td><img src="/images/02.jpg" width="160" height="160" alt="sample image 2" title="sample image 2"></td>
<td><img src="/images/03.jpg" width="160" height="160" alt="sample image 3" title="sample image 3"></td>
<td><img src="/images/04.jpg" width="160" height="160" alt="sample image 4" title="sample image 4"></td>
</tr>
<tr>
<td><img src="/images/05.jpg" width="148" height="148" alt="sample image 5" title="sample image 5"></td>
<td><img src="/images/06.jpg" width="148" height="148" alt="sample image 6" title="sample image 6"></td>
<td><img src="/images/07.jpg" width="148" height="148" alt="sample image 7" title="sample image 7"></td>
<td><img src="/images/08.jpg" width="148" height="148" alt="sample image 8" title="sample image 8"></td>
</tr>
<tr>
<td><img src="/images/09.jpg" width="148" height="148" alt="sample image 9" title="sample image 9"></td>
<td><img src="/images/10.jpg" width="148" height="148" alt="sample image 10" title="sample image 10"></td>
<td><img src="/images/11.jpg" width="148" height="148" alt="sample image 11" title="sample image 11"></td>
<td><img src="/images/12.jpg" width="148" height="148" alt="sample image 12" title="sample image 12"></td>
</tr>
</table>

# Features

 * Multi-threaded engine capable of simultaneous management of multiple GPUs.
 * Powerful custom prompt file format that allows you to easily define compound prompt templates. Want to quickly create thousands of prompts from a template like "_photo of a **[adjective(s)] [animal]** as a **[profession]**, art by **[artist(s)]**, **[keyword(s)]**_" where each bracketed section needs to be filled in with dozens (or hundreds) of different items? No problem. Maybe you want your GPUs to create every possible combination, or maybe you want combinations to be picked randomly? Your choice. Maybe you want some items to be handled with different settings? Totally doable. Prompt files can be as complex or simple as you want — you can simply paste in a list of stand-alone prompts and go, too!
 * All prompt and creation settings are automatically embedded into output images as EXIF metadata (including the random seed used). Never wonder how you created an image again!
 * Easy web interface. Includes a built-in prompt file editor with context-sensitive highlighting, a gallery that displays your prompts and creation settings alongside your images, and at-a-glance information about the status of completed/ongoing work. Hate web interfaces? Turn it off via a configuration file — Dream Factory can be run completely via the command line if that's your thing!
 * Remote management. Access and fully manage your Dream Factory installation from anywhere (and easily download your created images in bulk as .zip files!). Can be configured to be accessible via LAN, WAN (internet), or just locally on the computer that Dream Factory is running on. Includes very basic HTTP-based authentication for WAN access.
 * Integrated optional [ESRGAN upscaling](https://github.com/xinntao/ESRGAN) with [GFPGAN face correction](https://xinntao.github.io/projects/gfpgan). 
 * Easy setup. If you can download a file and copy & paste 6 lines ([see below](https://github.com/rbbrdckybk/dream-factory/edit/main/README.md#setup)), you can get this working. Uses Anaconda so Dream Factory will happily run alongside other Stable Diffusion repos without disturbing them.

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
