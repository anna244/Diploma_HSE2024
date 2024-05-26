# https://fastapi.tiangolo.com/deployment/docker/

FROM python:3.12

WORKDIR /app

COPY ./requirements.txt /requirements.txt

RUN pip install --no-cache-dir --upgrade -r /requirements.txt

# COPY ./app /code/app

CMD ["fastapi", "run", "main.py", "--port", "80"]