FROM python:3.9.6-slim-buster

RUN apt-get update
RUN apt-get install -y libaio1 wget unzip 
RUN mkdir -p /opt/oracle
WORKDIR /opt/oracle 
RUN wget https://download.oracle.com/otn_software/linux/instantclient/19800/instantclient-basic-linux.x64-19.8.0.0.0dbru.zip
RUN unzip instantclient-basic-linux.x64-19.8.0.0.0dbru.zip
RUN echo /opt/oracle/instantclient_19_8 > /etc/ld.so.conf.d/oracle-instantclient.conf
RUN ldconfig

WORKDIR /usr/src/app
COPY requirements.txt ./
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install pandas
RUN pip install numpy
RUN pip install tqdm
RUN pip install psycopg2-binary

EXPOSE 5000

CMD [ "python", "./main.py" ]
