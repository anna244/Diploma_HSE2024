FROM continuumio/miniconda3

RUN mkdir -p /app
RUN mkdir -p /storage && chmod 777 /storage

RUN conda update conda && conda install -n base conda-libmamba-solver && conda config --set solver libmamba

# pytorch with gpu support
RUN conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia --yes

COPY requirements.txt requirements.txt 
RUN conda install -c conda-forge --yes --file requirements.txt && pip install controlnet-aux==0.0.8 pika==1.3.2

# installed version has missing 
# Could not find the bitsandbytes CUDA binary at PosixPath('/opt/conda/lib/python3.12/site-packages/bitsandbytes/libbitsandbytes_cuda121.so')
RUN pip install --upgrade --no-deps --force-reinstall numpy bitsandbytes git+https://github.com/huggingface/diffusers.git

# переходим в директорию
WORKDIR /app 

ENTRYPOINT ["python", "main.py"]