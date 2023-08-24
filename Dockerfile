FROM ubuntu:latest

RUN apt-get update && \
    apt-get install -y python3 python3-pip cron ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get install -y python3 python3-pip
RUN apt-get install -y cron

RUN mkdir /app
RUN mkdir /app/.credentials
WORKDIR /app
ADD sync.py /app/
ADD requirements.txt /app/
RUN python3 -m pip install -r /app/requirements.txt 
ADD runner.sh /app/
RUN chmod +x /app/runner.sh

ADD cronjob /etc/cron.d/cronjob
RUN chmod 0644 /etc/cron.d/cronjob
RUN touch /var/log/cron.log
RUN printenv | sed 's/^\(.*\)$/export \1/g' > /root/project_env.sh
RUN chmod +x /app/sync.py
RUN crontab /etc/cron.d/cronjob
RUN touch /var/log/cron.log
RUN chmod +x /app/runner.sh


CMD [ "cron", "-f" ]