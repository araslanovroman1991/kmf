FROM python:3.10-slim-bullseye
RUN  python3 -m pip install --upgrade pip
RUN  python3 -m pip install psycopg2-binary
RUN apt update && apt install -y gcc cmake libpq-dev python-dev
LABEL author="Roman_Araslanov"
LABEL maintainer="araslanovroman1991@mail.ru"
LABEL version=1.0.0
RUN mkdir -p /opt/Monitoring/KMF
ADD /app /opt/Monitoring/KMF/app
ADD requirements.txt /opt/Monitoring/KMF/requirements.txt
WORKDIR /opt/Monitoring/KMF
RUN pip install -r /opt/Monitoring/KMF/requirements.txt
ENV TZ Europe/Moscow
CMD python3 /opt/Monitoring/KMF/app/KMF.py
RUN echo "This should work" 


