FROM python:3-alpine
WORKDIR /usr/src/app

COPY checks.yaml \
     history.html.theme \
     incidents.md \
     index.html.theme \
     requirements.txt \
     tinystatus.py ./

RUN pip install --no-cache-dir -r requirements.txt
CMD [ "python", "/usr/src/app/tinystatus.py" ]
