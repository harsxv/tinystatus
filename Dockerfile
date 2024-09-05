FROM python:3
WORKDIR /usr/src/app

COPY checks.yaml ./
COPY history.html.theme ./
COPY incidents.md ./
COPY index.html.theme ./
COPY requirements.txt ./
COPY tinystatus.py ./

RUN pip install --no-cache-dir -r requirements.txt
CMD [ "python", "/usr/src/app/tinystatus.py" ]
