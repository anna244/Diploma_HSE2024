import datetime
import pathlib
from enum import Enum
from typing import Annotated

import aiofiles
from fastapi import Depends, FastAPI, Form, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from utils import model_inference_Lora, model_train, translit

app = FastAPI()

APP_DIR = pathlib.Path(__file__).parent.resolve()
STORAGE_DIR = APP_DIR / "../storage"

HUGGINGFACE_CACHE_DIR = STORAGE_DIR / "cache"
HUGGINGFACE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

STATIC_DIR = STORAGE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")  


class ModelName(str, Enum):
    ControlNet = "ControlNet"
    Lora = "Lora"

class Gender(str, Enum):
    Women = "women"
    Men = "men"


class InputTrain(BaseModel):
    fio : str
    gender : Gender
    name_of_model: ModelName
    promt: str

    # https://stackoverflow.com/questions/60127234/how-to-use-a-pydantic-model-with-form-data-in-fastapi
    @classmethod
    def as_form(
        cls,
        fio: str = Form(),
        gender : Gender = Form(),
        name_of_model: ModelName = Form(),
        promt: str = Form(),

    ):
        return cls(fio=fio, gender = gender, promt=promt, name_of_model=name_of_model)
    

class InputInference(BaseModel):
    fio : str
    gender : Gender
    promt: str
    

def make_image_urls(request: Request, fio: str, generated_images: list[pathlib.Path]) -> list[str]:
    image_urls = []
    user_static_path = pathlib.Path(STATIC_DIR) / fio  # 'app/storate/static/123/'
    user_static_path.mkdir(parents=True, exist_ok=True)
    for image_path in generated_images:
        # image_path = pathlib.Path(image)

        # перенести картинку из image_path в STATIC_DIR
        new_image_name = image_path.name  # 'tatoo0.png'
        new_image_path = user_static_path / new_image_name   # 'app/storate/static/123/tatoo0.png'

        # не перезаписываем существующую картинку
        prefix = 0
        while new_image_path.exists():
            prefix += 1
            new_image_name = f'{prefix}_{image_path.name}'
            new_image_path = user_static_path / new_image_name  # 'app/storate/static/123/1_tatoo0.png'

        image_path.rename(new_image_path)

        # формируем урл до картинки и записываем в ответ
        # https://www.starlette.io/routing/#reverse-url-lookups
        image_urls.append(
            str(request.url_for("static", path=f'{fio}/{new_image_name}'))
        )
    return image_urls

# /{datetime.datetime.now():%Y.%m.%d_%H.%M.%S}
def get_directories(model_name: str, fio: str) -> tuple[str, str]:
    model_dir = STORAGE_DIR / f"content_{model_name}/{fio}"
    images_dir = model_dir / "data"
    images_dir.mkdir(parents=True, exist_ok=True)

    return model_dir, images_dir


#https://stackoverflow.com/questions/63580229/how-to-save-uploadfile-in-fastapi
@app.post("/input_train/")
async def input_train(
    input_model: Annotated[InputTrain, Depends(InputTrain.as_form)],
    files: list[UploadFile], 
    request: Request
):  
    
    fio = translit(input_model.fio)
    model_dir, images_dir = get_directories(model_name=input_model.name_of_model.value, fio=fio)

    for file in files:
        async with aiofiles.open (images_dir/file.filename, "wb") as out_file:
            content = await file.read()  # async read
            await out_file.write(content)  # async write

    generated_images = model_train(
        model_dir=model_dir, 
        cache_dir=HUGGINGFACE_CACHE_DIR,
        promt=input_model.promt,
        model_name=input_model.name_of_model, 
        type_person=input_model.gender
    )

    return {
        "generated_images": make_image_urls(request=request, fio=fio, generated_images=generated_images),
    }


@app.post("/input_inference/")
async def input_inference(
    input_model:InputInference,
    request: Request
):
    
    fio = translit(input_model.fio)
    model_dir, images_dir = get_directories(model_name=input_model.name_of_model.value, fio=fio)

    generated_images = model_inference_Lora(
        model_dir=model_dir, 
        promt=input_model.promt,
        type_person=input_model.gender
    )

    return {
        "generated_images": make_image_urls(request=request, fio=fio, generated_images=generated_images),
    }