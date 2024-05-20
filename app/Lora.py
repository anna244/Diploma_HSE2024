#https://github.com/huggingface/notebooks/blob/main/diffusers/SDXL_DreamBooth_LoRA_.ipynb
#https://medium.com/@dminhk/how-to-fine-tune-dreambooth-lora-for-stable-diffusion-xl-sdxl-in-amazon-sagemaker-notebook-7ce6726ebca9
import gc
import glob
import json
import locale
import os
import pathlib
from datetime import datetime

import torch
from diffusers import AutoencoderKL, DiffusionPipeline
from PIL import Image
from transformers import AutoProcessor, BlipForConditionalGeneration


class DreamBoth_LoRA():
    def __init__(self,  model_dir: str, cache_dir: str, prompt: str, type_person :str):
        self.model_dir = pathlib.Path(model_dir)
        self.image_dir = pathlib.Path(model_dir) / "data"
        self.output_dir = pathlib.Path(model_dir) / "weight"
        self.cache_dir = pathlib.Path(cache_dir)
        self.device = "cuda" if torch.cuda.is_available() else "cpu" 
        self.type_person = type_person 
        self.prompt = f'Super realistic photo of (((SOK))) {self.type_person} with {prompt}'
        

    # captioning utility
    def caption_images(self, input_image):    
        # load the processor and the captioning model
        self.blip_processor = AutoProcessor.from_pretrained(
            "Salesforce/blip-image-captioning-base", 
            cache_dir=self.cache_dir
        )
        self.blip_model = BlipForConditionalGeneration.from_pretrained(
            "Salesforce/blip-image-captioning-base",
            torch_dtype=torch.float16,
            cache_dir=self.cache_dir
        ).to(self.device) 

        inputs = self.blip_processor(images=input_image, return_tensors="pt").to(self.device, torch.float16)
        pixel_values = inputs.pixel_values

        generated_ids = self.blip_model.generate(pixel_values=pixel_values, max_length=50)
        generated_caption = self.blip_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return generated_caption
    
    def train(self):
        # create a list of (Pil.Image, path) pairs 
        imgs_and_paths = [(path,Image.open(path)) for path in glob.glob(f"{self.image_dir}/*.jpg")]

        caption_prefix = f"a photo of SOK {self.type_person}, " #@param

        json_path = self.image_dir / 'metadata.jsonl'
        json_path.unlink(missing_ok=True)

        with open(str(json_path), 'w') as outfile:
            for img in imgs_and_paths:
                caption = caption_prefix + self.caption_images(img[1]).split("\n")[0]
                entry = {"file_name":img[0].split("/")[-1], "prompt": caption}
                json.dump(entry, outfile)
                outfile.write('\n')

        # delete the BLIP pipelines and free up some memory
        self.blip_processor = None, 
        self.blip_model = None
        gc.collect()
        torch.cuda.empty_cache()

        locale.getpreferredencoding = lambda: "UTF-8"

        command = ('accelerate config default')
        os.system(command)

        self.output_dir.mkdir(exist_ok=True)

    # !accelerate config default
        instance_prompt = f'a photo of SOK {self.type_person}'
        max_train_steps = 500

        #!/usr/bin/env bash
        command = (f'accelerate launch train_dreambooth_lora_sdxl.py '
        f'--pretrained_model_name_or_path="stabilityai/stable-diffusion-xl-base-1.0" '
        f'--pretrained_vae_model_name_or_path="madebyollin/sdxl-vae-fp16-fix" '
        f'--dataset_name="{self.image_dir}" '
        f'--output_dir="{self.output_dir}" '
        f'--caption_column="prompt" '
        f'--mixed_precision="fp16" '
        f'--instance_prompt="{instance_prompt}" '
        f'--resolution=1024 '
        f'--train_batch_size=1 '
        f'--gradient_accumulation_steps=3 '
        f'--gradient_checkpointing '
        f'--learning_rate=1e-4 '
        f'--snr_gamma=5.0 '
        f'--lr_scheduler="constant" '
        f'--lr_warmup_steps=0 '
        f'--mixed_precision="fp16" '
        f'--use_8bit_adam '
        f'--max_train_steps={max_train_steps} '
        f'--checkpointing_steps=717 '
        f'--seed="0" '
        f'--cache_dir="{self.cache_dir}" ')

        os.system(command)

    def inference(self):
        # sdxl-lora-inference-base.py
        AutoencoderKL.from_pretrained(
            "madebyollin/sdxl-vae-fp16-fix", 
            torch_dtype=torch.float16,
            cache_dir=self.cache_dir
        )

        pipe = DiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=torch.float16,
            variant="fp16",
            use_safetensors=True,
            cache_dir=self.cache_dir
        )
        pipe = pipe.to("cuda")
        pipe.load_lora_weights(
            self.output_dir, 
            weight_name="pytorch_lora_weights.safetensors"
        )

        # SDXL styles: enhance, anime, photographic, digital-art, comic-book, fantasy-art, line-art, analog-film, neon-punk, isometric, low-poly, origami, modeling-compound, cinematic, 3d-mode, pixel-art, and tile-texture
        #prompt = "real photo of SOK women with geometric style tattoo design of a tree composed entirely of intersecting triangles and polygons on shoulder"
        now = datetime.now()
        date_time = now.strftime("%Y_%m_%d_%H_%M_%S")
        
        result_dir = pathlib.Path(self.model_dir) / f'result/{date_time}'
        result_dir.mkdir(parents=True, exist_ok=True)

        result = []
        for seed in range(4):
            generator = torch.Generator("cuda").manual_seed(seed)
            image = pipe(prompt=self.prompt, generator=generator, num_inference_steps=25)
            image = image.images[0]

            path_to_save = result_dir / f'tatto{seed}.png' 
            image.save(path_to_save)
            result.append(path_to_save)
        
        return result
