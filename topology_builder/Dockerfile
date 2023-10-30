# FROM ubuntu
# 
# ARG DEBIAN_FRONTEND=noninteractive
# #ARG GEOS_DIR=usr/local/bin
# 
# WORKDIR /usr/src/topology_builder
# 
# RUN apt update && apt upgrade -y
# #RUN apt install libgeos++-dev libgeos3.10.2 libgeos-c1v5 libgeos-dev libgeos-doc software-properties-common -y
# RUN apt install software-properties-common -y
# RUN add-apt-repository ppa:deadsnakes/ppa -y
# RUN apt update && apt upgrade -y
# RUN apt install python3.11 pip libgeos++-dev libgeos3.10.2 libgeos-c1v5 libgeos-dev libgeos-doc -y 

FROM python:latest

WORKDIR /topology_builder

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD [ "python3", "-m", "flask", "--app", "topology_builder/svc", "run", "--host", "0.0.0.0", "--port", "8000"]