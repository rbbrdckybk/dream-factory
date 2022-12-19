# Changelog

Dream Factory release notes.

When updating to a new release, use the built-in setup.py script with the --update option to ensure all required repos are refreshed:
```
python setup.py --update
```
## [2022.12.18]

### Added
- Added the ability to specify multiple models with the !CKPT_FILE directive. When specifying multiple models, all of your prompts will be run against the first model, then the second, and so on. You can either use a comma-separated list (e.g. !CKPT_FILE = model01.ckpt, model02.ckpt, etc) or simply use '!CKPT_FILE = all' to specify that all of your models should be iterated through. In random mode, models will be switched every x prompts, where x can be defined with a new config.txt option (see RANDOM_QUEUE_SIZE in config-default.txt).

### Fixed
- Fixed an issue where GPU workers could appear to freeze on the status monitor page while new models were loading. 
- Fixed some malformed HTML on the status monitor page.

## [2022.12.15]

### Added
- Added support for wildcards in prompt files. See prompts/wildcards/colors.txt for an example.
- Added references to your available embeddings to the prompt editor's built-in help (if you have any).

### Fixed
- Fixed handling of 'PF_CKPT_FILE =' assignments in config.txt. Default model files set in config.txt will now be validated, and setting '!CKPT_FILE =' (e.g. setting the model to nothing) in prompt files will now properly default back to the validated config.txt setting.
- If you have '--autolaunch' set in your Auto1111 startup script, it will be ignored when starting Dream Factory (so it won't open a browser to the Auto1111 API).

### Changed
- Sorted the prompt file dropdown lists in both the prompt editor and control panel to appear in alphabetical order.
- Made significant improvements to the prompt editor's built-in help reference. Each help area now has its own button in the reference popup, and there is a bit of additional help context in each area regarding how to use models/wildcards/embeddings.

### Changed
- Sorted the reference samplers & models lists in the prompt editor to appear in alphabetical order.

## [2022.12.13]

### Fixed
- Fixed an that would cause no work to be queued if the active prompt file had an empty [prompts] section under certain conditions.
- Fixed an issue that would cause copying a sampler or model to the clipboard to fail from the prompt editor reference screen on non-https connections.

### Changed
- Sorted the reference samplers & models lists in the prompt editor to appear in alphabetical order.

## [2022.12.09]

If you're upgrading, you'll need to install **psutil**. You can either re-run setup.py, or just run this:
```
pip install psutil
```
### Added
- Added the ability to have Dream Factory automatically add the appropriate trigger word(s) to your prompts when using custom models. See **model-triggers.txt** in your dream-factory folder for more info (you'll need to run Dream Factory at least once after upgrading to generate this file). There is a new config.txt option that controls this behavior (see config-defaults.txt if you're upgrading).
- You can now put a 'catch-all' negative prompt in your config.txt file that will automatically be added to all new prompt files that you generate.

### Fixed
- Fixed an issue where the SD backend (auto1111) would leave child processes running in the background after Dream Factory was shut down.

## [2022.12.08]

### Added
- Added a model & sampler reference to the web GUI prompt editor. It shows a list of all samplers & models that are available to use; each item is clickable and will copy the appropriate prompt file directive to the clipboard. You can open it via the new button in the editor, or with ctrl+h.
- Added some additional error-handling around the txt2img and img2img workflows that should prevent Dream Factory from going into a state where it needs to be restarted due to GPU errors, or Auto1111 returning error responses.

### Fixed
- Fixed an issue where '.png' could be incorrectly appended to the seed value saved to image EXIF.

## [2022.12.06]
This is a major release; pretty much every piece of code has been touched and the entire backend has been re-done. **I highly recommend a fresh install!**

### Added
- Completely replaced the Stable Diffusion backend (which was previously a mix of my own SD repo and [basujindal's fork](https://github.com/basujindal/stable-diffusion), which seems to be mostly abandoned) with [Automatic1111's popular repo](https://github.com/AUTOMATIC1111/stable-diffusion-webui). This means that pretty much all of Automatic1111's [many features](https://github.com/AUTOMATIC1111/stable-diffusion-webui#features) are now available within Dream Factory! Some highlights:
  - Support for many more samplers.
  - Support for SD 2.0 models.
  - Support for [prompt weighting](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features#attentionemphasis) within prompt files.
  - Support for the [highres fix](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features#highres-fix), allowing for much more coherent images over 512x512.
  - Support for [prompt editing](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features#prompt-editing).
  - Support for [Codeformer](https://github.com/sczhou/CodeFormer) as a face enhancement/restoration option alongside GFPGAN.
- Added staggered GPU startup for multi-GPU systems to help prevent system RAM issues during initialization.
- Added a sampler and model reference to new prompt files created via the web interface.
- Added !UPSCALE_GFPGAN_AMOUNT and !UPSCALE_CODEFORMER_AMOUNT as prompt file directives, allowing you to specify the degree of face enhancement you want (from 0.0 to 1.0 for either or both options).

### Fixed
- Corrected many bugs with multi-GPU operation. Just spent the past 36 hours watching Dream Factory churn out images non-stop on a 3-GPU machine powered by a circa-2013 single-core AMD Sempron with 6GB of physical RAM (16GB with a swap file to get through model loads). Mostly confident that everything is working properly now, but report issues if you find them!
- Corrected a bug where setting **!INPUT_IMAGE =** in prompt files didn't properly clear an existing input image.

### Changed
- Models are now kept in memory on each GPU, instead of being discarded after each prompt call. This results in much faster performance.
- Dream Factory's setup script (setup.py) now installs far fewer python dependancies. Again, recommend a fresh install if you want to keep things clean.

### Removed
- !SD_LOW_MEMORY and !SD_LOW_MEM_TURBO have been removed as prompt file directives as they would no longer serve a purpose. Dream Factory will use whatever VRAM flags you've set for your Auto1111 installation, if any (most users won't need to worry about them).
- !UPSCALE_FACE_ENH has been removed as a prompt file directive, replaced by !UPSCALE_GFPGAN_AMOUNT and !UPSCALE_CODEFORMER_AMOUNT (see above).

## [2022.11.15]
### Fixed
- Corrected an issue with setup.py that was causing pytorch to be installed incorrectly.
- Corrected a bug that would throw an error when a single gpu id was manually specified in config.txt.

## [2022.10.20]
### Fixed
- Corrected a fomatting bug that would cause the control panel and status monitor to fail to load in the web UI when total completed jobs became greater than 999.
- Corrected an issue that wouldn't correctly enable webserver console logging in all cases when **WEBSERVER_CONSOLE_LOG = yes** was set in config.txt.

## [2022.10.15]
### Added
- Added negative prompt support, specify with **!NEG_PROMPT** directive in .prompt files.
- Added support for additional samplers. Specify with the **!SAMPLER** directive in .prompt files. Note that not all samplers are available in all modes currently - if you're using the low-memory-optimized mode with txt2img, you should have access to all of them (plms, ddim, lms, euler, euler_a, dpm2, dpm2_a, heun). 
- Added ability to specify a default model checkpoint file and sampler in global config.txt file; see config-default.txt for example.
- Added sampler, negative prompt, and model checkpoint (when not the default model.ckpt) to output EXIF, and display in internal web UI gallery.
- Updated example prompt files with **!CKPT_FILE**, **!SAMPLER**, and **!NEG_PROMPT** usage.

### Fixed
- Corrected a bug when specifying a custom seed with **!SEED**.
- Additional error-checking in setup.py for cases where required executables can't be located. Should handle gracefully now and prompt the user to re-run setup with a new **--shell** option.

## [2022.10.03]
### Added
- Added ability to specify which checkpoint to use in prompt files with **!CKPT_FILE** directive. If you use a relative path, it'll be relative from your /stable_diffusion subdirectory, hence the default is **!CKPT_FILE = models/ldm/stable-diffusion-v1/model.ckpt**. Useful if you've created your own .ckpt file(s) with DreamBooth or some other method and want to switch between them!

## [2022.10.02]
### Fixed
- Several UTF-8 character encoding issues with prompt file and EXIF metadata handling have been corrected.
- Quotation marks in prompts should no longer cause issues.
- Fixed an editor issue where it was possible to clear the entire document using by undo (ctrl-z) too many times.

## [2022.09.28]
### Added
- Initial soft release. Things should mostly work, but expect some issues.
