FROM python:latest

RUN mkdir stash 
WORKDIR stash
COPY ./fileserver.py fileserver.py
RUN ln -s fileserver.py fileserver

ENTRYPOINT ["./fileserver"]

