import re

import ControlNet
import Lora


def translit(text: str) -> str:
    pattern = re.compile('[\W]+')
    return pattern.sub("", text)


def model_train(model_dir: str, cache_dir: str, promt: str, model_name: str = 'Lora', type_person: str = 'women') -> list[str]:
    if model_name == 'Lora':
        instance = Lora.DreamBoth_LoRA(model_dir, cache_dir, promt, type_person)
        instance.train()
        return instance.inference()
    elif model_name == 'ControlNet':
        instance = ControlNet.ControlNet(model_dir, cache_dir, promt)
        instance.get_model()
        return instance.generate()
    

def model_inference_Lora(model_dir: str, promt: str, type_person: str = 'women') -> list[str]:
    instance = Lora.DreamBoth_LoRA(model_dir, promt, type_person)
    return instance.inference()

