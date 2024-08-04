FROM python:3.12.4
WORKDIR /usr/src/app

# Install core dependencies.
RUN apt-get update && apt-get install -y libpq-dev build-essential

# Install python dependencies.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


CMD [ "python", "app.py" ]
