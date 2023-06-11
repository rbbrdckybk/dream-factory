@echo off
REM ********************* civitai.com scraper example *********************
REM You must have already run Dream Factory with Civitai integration enabled!
REM (CIVITAI_INTEGRATION = yes in your Dream Factory config.txt file)
REM You can change the --type flag to be lora, hypernet, or embedding

cls
echo This will build .prompts files for all of your custom models, using the example images on civitai.com.
echo Images tagged nsfw will be excluded, and images will be scaled so that their longest dimension is 1024 pixels.
echo Output files will be "chained" together so that Dream Factory will run them in sequence, one after the other.
pause

python civitai-scraper.py --max_steps 65 --resolution 1024 --nsfw exclude --type model
python chain.py --dir civitai-scraper

echo All done - output .prompts files should be in a civitai-scraper sub-folder!
pause