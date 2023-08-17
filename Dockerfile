FROM ubuntu:latest

RUN apt-get update 
RUN apt-get install -y python3 python3-pip
RUN apt-get install -y cron

RUN mkdir /app
WORKDIR /app
ADD sync.py /app/
ADD requirements.txt /app/
RUN python3 -m pip install -r /app/requirements.txt 

ADD cronjob /etc/cron.d/cronjob
RUN chmod 0644 /etc/cron.d/cronjob
RUN touch /var/log/cron.log

ENTRYPOINT [ "cron", "-f" ]