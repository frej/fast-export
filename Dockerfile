#############################################
#############################################
## Dockerfile to run Mercurial Fast-Export ##
#############################################
#############################################

##################
# Get base image #
##################
FROM ubuntu:20.04

################################
# Set ARG values used in Build #
################################
# Version of mercurial to install
ARG MERCURIAL_VERSION='5.7.1'
# Make the install non interactive
ARG DEBIAN_FRONTEND=noninteractive
# Set TimeZone to stop it from asking during build
ENV TZ=UTC

#########################################
# Label the instance and set maintainer #
#########################################
LABEL maintainer="GitHub DevOps <github_devops@github.com>" \
    org.opencontainers.image.authors="GitHub DevOps <github_devops@github.com>" \
    org.opencontainers.image.vendor="GitHub" \
    org.opencontainers.image.description="Mercurial Fast-Export container"

#################################
# Install all base dependancies #
#################################
# hadolint ignore=DL3008
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
  bash \
  build-essential \
  curl \
  git \
  git-lfs \
  python3 \
  python3-dev \
  python3-pip \
  software-properties-common \
  vim \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

################
# Pip Installs #
################
RUN pip3 install --no-cache-dir \
  mercurial==${MERCURIAL_VERSION}

##################################
# Create exporter user and group #
##################################
RUN adduser exporter \
  && usermod -aG exporter exporter

#############################
# Copy export file contents #
#############################
COPY . /fast-export/

######################################
# Set exporter user as owner of repo #
######################################
RUN chown -R exporter:exporter /fast-export

########################
# Run as exporter user #
########################
USER exporter

######################
# Set the entrypoint #
######################
ENTRYPOINT ["/bin/bash"]
