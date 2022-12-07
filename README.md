# Dream Factory

Multi-threaded GUI manager for mass creation of AI-generated art with support for multiple GPUs.

This is aimed at the user that wants to create a **lot** of AI artwork with minimal hands-on time. If you're looking for a repo that will allow you to spend hours tweaking a single image until it's perfect, [there are better options](https://github.com/AUTOMATIC1111/stable-diffusion-webui) (update 2022-12-06: Dream Factory now uses Automatic1111's repo on the backend so you'll get the best of both worlds!). If you have hundreds of prompt ideas and want to easily and quickly (well, as quickly as your GPUs can manage!) see them rendered in hundreds of different variations and/or styles, then this is for you.

To illustrate, I've had an RTX 3060, RTX 3080Ti, and Tesla M40 running Dream Factory 24/7 for a couple weeks now, and they churn out many thousands of images every day! Some samples (all straight out of Dream Factory other than some minor sharpening applied in Photoshop):  
<table>
 <tr>
  <td><img src="/images/01.jpg" width="152" height="152" alt="sample image 1" title="sample image 1"></td>
  <td><img src="/images/02.jpg" width="152" height="152" alt="sample image 2" title="sample image 2"></td>
  <td><img src="/images/03.jpg" width="152" height="152" alt="sample image 3" title="sample image 3"></td>
  <td><img src="/images/04.jpg" width="152" height="152" alt="sample image 4" title="sample image 4"></td>
 </tr>
 <tr>
  <td><img src="/images/05.jpg" width="152" height="152" alt="sample image 5" title="sample image 5"></td>
  <td><img src="/images/06.jpg" width="152" height="152" alt="sample image 6" title="sample image 6"></td>
  <td><img src="/images/07.jpg" width="152" height="152" alt="sample image 7" title="sample image 7"></td>
  <td><img src="/images/08.jpg" width="152" height="152" alt="sample image 8" title="sample image 8"></td>
 </tr>
 <tr>
  <td><img src="/images/09.jpg" width="152" height="152" alt="sample image 9" title="sample image 9"></td>
  <td><img src="/images/10.jpg" width="152" height="152" alt="sample image 10" title="sample image 10"></td>
  <td><img src="/images/11.jpg" width="152" height="152" alt="sample image 11" title="sample image 11"></td>
  <td><img src="/images/12.jpg" width="152" height="152" alt="sample image 12" title="sample image 12"></td>
 </tr>
</table>

Some UI screenshots:
<table>
 <tr>
  <td><img src="/images/screen_monitor.png" width="152" height="152" alt="UI: status monitor" title="UI: status monitor"></td>
  <td><img src="/images/screen_editor.png" width="152" height="152" alt="UI: prompt editor" title="UI: prompt editor"></td>
  <td><img src="/images/screen_gallery.png" width="152" height="152" alt="UI: gallery" title="UI: gallery"></td>
  <td><img src="/images/screen_gallery_image.png" width="152" height="152" alt="UI: image viewer" title="UI: image viewer"></td>
 </tr>
</table>

# Features

 * Based on [Stable Diffusion](https://stability.ai/blog/stable-diffusion-public-release).
 * Dream Factory acts as a powerful automation and management tool for the popular [Automatic1111 SD repo](https://github.com/AUTOMATIC1111/stable-diffusion-webui#features). Integration with Automatic1111's repo means full support for a rapidly-expanding feature set.
 * Multi-threaded engine capable of simultaneous, fast management of multiple GPUs. As far as I'm aware, Dream Factory is currently one of the only options for true multi-GPU support.
 * Powerful custom prompt file format that allows you to easily define compound prompt templates. Want to quickly create thousands of prompts from a template like "_photo of a **[adjective(s)] [animal]** as a **[profession]**, art by **[artist(s)]**, **[keyword(s)]**_" where each bracketed section needs to be filled in with dozens (or hundreds) of different items? No problem. Maybe you want your GPUs to create every possible combination, or maybe you want combinations to be picked randomly? Your choice. Maybe you want some items to be handled with different settings? Totally doable. Prompt files can be as complex or simple as you want — you can simply paste in a list of stand-alone prompts and go, too!
 * All prompt and creation settings are automatically embedded into output images as EXIF metadata (including the random seed used). Never wonder how you created an image again!
 * Easy web interface. Includes a built-in prompt file editor with context-sensitive highlighting, a gallery that displays your prompts and creation settings alongside your images, and at-a-glance information about the status of completed/ongoing work. Hate web interfaces? Turn it off via a configuration file — Dream Factory can be run completely via the command line if that's your thing!
 * Remote management. Access and fully manage your Dream Factory installation from anywhere (and easily download your created images in bulk as .zip files!). Can be configured to be accessible via LAN, WAN (internet), or just locally on the computer that Dream Factory is running on. Includes very basic HTTP-based authentication for WAN access.
 * Integrated optional [ESRGAN upscaling](https://github.com/xinntao/ESRGAN) with [GFPGAN face correction](https://xinntao.github.io/projects/gfpgan). 
 * Easy setup. If you can download a file and copy & paste a few lines ([see below](https://github.com/rbbrdckybk/dream-factory/edit/main/README.md#setup)), you can get this working. Uses Anaconda so Dream Factory will happily run alongside other Stable Diffusion repos without disturbing them.

# Requirements

You'll need at least one Nvidia GPU, preferably with a decent amount of VRAM. 3GB of VRAM should be enough to produce 512x512 images, but more GPU memory will allow you to create larger images (and/or create them faster).

You'll also need a working [Automatic1111 Stable Diffusion webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui#installation-and-running).

# Setup

These instructions were tested on several Windows 10 desktops with a variety of modern Nvidia GPUs ranging from 8-12GB VRAM, and also on an Ubuntu Server 20.04.3 system with an old Nvidia Tesla M40 GPU (24GB VRAM).

**[1]** Install [Anaconda](https://www.anaconda.com/products/individual), open the root terminal, and create a new environment (and activate it):
```
conda create --name dream-factory python=3.9
conda activate dream-factory
```

**[2]** Install a couple required Python packages:
```
conda install -c anaconda git urllib3
```

**[3]** Clone this repository and switch to its directory:
```
git clone https://github.com/rbbrdckybk/dream-factory
cd dream-factory
```

**[4]** Run the included setup script to finish the rest of your installation automatically:
```
python setup.py
```

**[5]** Edit your config.txt file to specify the full path to your Automatic1111 SD installation:
 * Look for the **SD_LOCATION =** entry near the top of the file.
 * On Windows, it should look something like **SD_LOCATION = C:\Applications\stable-diffusion-webui** when finished, depending on where you placed Automatic1111's webui.
 * On Linux, you'll want something like **SD_LOCATION = /home/[username]/stable-diffusion-webui**, where [username] is the linux user it was installed under, assuming you kept the default install location.

You're done! Ensure that your [Automatic1111 installation works properly](https://github.com/AUTOMATIC1111/stable-diffusion-webui#installation-and-running) before attempting to test Dream Factory.

Once you've verified that you can generate individual images with your Auto1111 installation, you can perform a test to make sure Dream Factory is working by running this (again, from the main **dream-factory** folder):
```
python dream-factory.py --prompt_file prompts/example-standard.prompts
```
This should start up the web interface with a simple example prompt file pre-loaded that your GPU(s) should start working on automatically. On the first run, several large files (~2GB total) will be downloaded automatically so it may take a few minutes before things start happening.

Eventually you should see images appearing in your **\output** folder (or you can click on the "Gallery" link within the web UI and watch for them there). If you're getting images, everything is working properly and you can move on to the next section.

# Usage

Full instructions coming soon. Quick version:

After installation, open **config.txt** and make any desired edits.

Start Dream Factory with:
```
python dream-factory.py
```
The web UI should open automatically, if not go to http://localhost:8080 (assuming you didn't change the port in config.txt) via your browser.

Browse to 'Control Panel' in the top nav and select one of the two example prompt files via the dropdown. Your GPU(s) should immediately start working on whichever one you choose. If you browse to 'Gallery' in the top nav you'll see images appearing as they're completed.

To create your own prompt files, browse to 'Prompt Editor' in the top nav and open one of the example files and read through the comments to see how they work. Experiment with creating your own via one of the 'New ...' buttons at the top of the page. To execute your new prompt file, go back to 'Control Panel' and select it from the drop down. 

You can update Dream Factory to the latest version by typing:
```
python setup.py --update
```


