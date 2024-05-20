FROM continuumio/miniconda3

RUN mkdir -p /app
RUN mkdir -p /storage && chmod 777 /storage

RUN conda update conda && conda install -n base conda-libmamba-solver && conda config --set solver libmamba

# pytorch with gpu support
RUN conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia --yes

COPY requirements.txt requirements.txt 
RUN conda install -c conda-forge --yes --file requirements.txt && pip install controlnet-aux==0.0.8

# installed version has missing 
# Could not find the bitsandbytes CUDA binary at PosixPath('/opt/conda/lib/python3.12/site-packages/bitsandbytes/libbitsandbytes_cuda121.so')
RUN pip install --upgrade --no-deps --force-reinstall numpy bitsandbytes git+https://github.com/huggingface/diffusers.git

EXPOSE 80

# переходим в директорию
WORKDIR /app 

# запуск в продакшене
# COPY ./app /app
# ENTRYPOINT ["fastapi", "run", "app/main.py", "--port", "80"]

# запуск в dev
ENTRYPOINT /bin/bash