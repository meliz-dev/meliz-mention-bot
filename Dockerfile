FROM ubuntu:18.04

USER root

# Change apt repository to Daumkakao mirror for faster deployment
RUN sed -i 's/kr.archive.ubuntu.com/mirror.kakao.com/g' /etc/apt/sources.list
RUN sed -i 's/archive.ubuntu.com/mirror.kakao.com/g' /etc/apt/sources.list
RUN sed -i 's/security.ubuntu.com/mirror.kakao.com/g' /etc/apt/sources.list
RUN sed -i 's/extras.ubuntu.com/mirror.kakao.com/g' /etc/apt/sources.list

RUN apt update
RUN apt install python3-pip -y

COPY . /meliz-bot

WORKDIR /meliz-bot
RUN pip3 install -r requirements.txt

EXPOSE 5000
RUN chmod +x run.sh
ENTRYPOINT ["./run.sh"]
