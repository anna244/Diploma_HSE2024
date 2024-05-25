#https://colab.research.google.com/github/huggingface/notebooks/blob/main/diffusers/controlnet.ipynb#scrollTo=wsv55Py8onJx
import glob
import pathlib
from datetime import datetime
import os

import cv2
import numpy as np
import torch
from diffusers import (ControlNetModel, StableDiffusionControlNetPipeline,
                       UniPCMultistepScheduler)
from diffusers.utils import load_image
from PIL import Image


class ControlNet():
    def __init__(self, model_dir: str, cache_dir: str, prompt: str):
        self.model_dir = pathlib.Path(model_dir)
        self.image_dir = pathlib.Path(model_dir) / "data"
        self.cache_dir = pathlib.Path(cache_dir)
        self.image_name = pathlib.Path(self.image_dir ).name
        self.prompt = f'{prompt} , best quality, extremely detailed'

    # обработка картинки
    def get_canny(self):
        # image = load_image(self.image_dir)
        images_list = glob.glob(f"{self.image_dir}/*.jpg")
        if not images_list:
            raise ValueError(f"Missing images in path: {self.image_dir}")
        images_list.sort(key=os.path.getmtime)
        # print (images_list)
        image = load_image(images_list[-1])

        image = np.array(image)

        low_threshold = 100
        high_threshold = 200

        image = cv2.Canny(image, low_threshold, high_threshold)
        image = image[:, :, None]
        image = np.concatenate([image, image, image], axis=2)
        canny_image = Image.fromarray(image)
        return canny_image

    # загрузка модели
    def get_model(self):
        self.image = self.get_canny()

        controlnet = ControlNetModel.from_pretrained(
            "lllyasviel/sd-controlnet-canny", 
            torch_dtype=torch.float16,
            cache_dir=self.cache_dir
        )

        self.pipe = StableDiffusionControlNetPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5", 
            controlnet=controlnet, 
            torch_dtype=torch.float16,
            cache_dir=self.cache_dir
        )

        self.pipe.scheduler = UniPCMultistepScheduler.from_config(self.pipe.scheduler.config)

        self.pipe.enable_model_cpu_offload()

    # генерация картинки
    def generate(self):

        now = datetime.now()
        date_time = now.strftime("%Y_%m_%d_%H_%M_%S")
        
        result_dir = pathlib.Path(self.model_dir) / f'result/{date_time}'
        result_dir.mkdir(parents=True, exist_ok=True)

        result = []

        for seed in range(4):
            generator = torch.Generator(device="cpu").manual_seed(seed)

            image = self.pipe(
                self.prompt,
                self.image,
                negative_prompt= "bad anatomy, worst quality, low quality",
                generator=generator,
                num_inference_steps=20,
            )

            image = image.images[0]

            path_to_save = result_dir / f'tatto{seed}.png' 
            image.save(path_to_save)
            result.append(path_to_save)        

        return result
