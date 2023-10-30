FROM python:latest

WORKDIR /traffic_matrix_generator

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD [ "python3", "-m" , "flask", "--app", "traffic_matrix_generator_svc.py", "run", "--host", "0.0.0.0", "--port", "8000"]