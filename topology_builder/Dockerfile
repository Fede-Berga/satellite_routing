FROM python:3.10

WORKDIR /usr/src/topology_builder

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD [ "python3", "-m", "flask", "--app", "svc", "run" ]