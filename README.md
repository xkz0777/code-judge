# Pre-requisite

## Install docker

Please ref to [docker](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository)

Basically you can run the following commands to install docker:

1. Set up Docker's apt repository.
```bash
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
```

2. Install the Docker packages.
```bash
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

3. Verify
```bash
sudo docker run hello-world
```

# Run the project

## Build the image

```bash
sudo docker compose build
```

## Run

```bash
sudo docker compose up
```

## Stop

```bash
sudo docker compose down
```

# Debug

## Run Redis
You need to have a redis server running to test the project. You can run the following command to start a redis server.

```bash
sudo docker run -p 6379:6379 --rm --name test-redis  redis:alpine
```
And set the `REDIS_URI` env variable to `redis://localhost:6379`.

## Run the project in debug mode

```bash
REDIS_URI=redis://localhost:6379 python debug_api.py
```
