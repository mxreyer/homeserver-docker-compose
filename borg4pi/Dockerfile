# Base image: use a small Debian-based Python image
FROM python:3.11-slim

# Install borgbackup and its dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        borgbackup \
        openssh-client \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

# Optional: create a user so you don't run as root
# ... but to back up docker volumes, we often need to be root.
# RUN useradd -ms /bin/bash borg
# USER borg

# Default entrypoint runs the borg CLI
ENTRYPOINT ["borg"]
