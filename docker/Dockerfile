FROM ubuntu:18.04

MAINTAINER Sergei Zabolotskikh <sergei@adblockplus.org>

RUN dpkg --add-architecture i386
RUN apt-get update -qyy

RUN apt-get install -qyy \
  dumb-init \
  curl \
  libc6:i386

RUN curl -L https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh | bash

COPY pin-gitlab-runner.pref /etc/apt/preferences.d/pin-gitlab-runner.pref

RUN apt-get install -qyy \
  gitlab-runner

ENTRYPOINT ["/usr/bin/dumb-init", "--"]

CMD ["gitlab-runner", "run", "--working-directory", "/opt/ci"]
