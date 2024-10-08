FROM python:3.8.3-slim-buster

LABEL "maintainer"="Scott Ng <thuongnht@gmail.com>"
LABEL "repository"="https://github.com/TKaxv-7S/ssh-scp-pipelines"
LABEL "version"="latest"

LABEL "com.github.actions.name"="ssh-scp-pipelines"
LABEL "com.github.actions.description"="Pipeline: ssh -> scp -> ssh"
LABEL "com.github.actions.icon"="terminal"
LABEL "com.github.actions.color"="gray-dark"

RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g;s|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list;

RUN apt-get update -y && \
  apt-get install -y ca-certificates openssh-client openssl sshpass

COPY requirements.txt /requirements.txt
RUN pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple -r /requirements.txt

RUN mkdir -p /opt/tools

COPY entrypoint.sh /opt/tools/entrypoint.sh
RUN chmod +x /opt/tools/entrypoint.sh

COPY app.py /opt/tools/app.py
RUN chmod +x /opt/tools/app.py

ENTRYPOINT ["/opt/tools/entrypoint.sh"]
