# Changelog

Dream Factory release notes.

When updating to a new release, use the built-in setup.py script with the --update option to ensure all required repos are refreshed:
```
python setup.py --update
```

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
