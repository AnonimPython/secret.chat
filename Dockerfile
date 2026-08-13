#/ ============================================================================
#/  Dockerfile — SecretChat в контейнере с GUI на Xvfb + noVNC
#/  Dockerfile — SecretChat in a container with GUI on Xvfb + noVNC
#/ ============================================================================
#/  собрать:  docker build -t secretchat .
#/  build:    docker build -t secretchat .
#/  проще через Makefile:  make up

#? лёгкий Debian, Qt-библиотеки ставим системой   |  slim Debian, Qt libs from apt
FROM python:3.12-slim

#/ системные пакеты: Qt6/xcb, шрифты, X-сервер, VNC, noVNC
#/ system packages: Qt6/xcb, fonts, X server, VNC, noVNC
RUN apt-get update && apt-get install -y --no-install-recommends \
      libglib2.0-0 libgl1 libegl1 \
      libxkbcommon0 libxkbcommon-x11-0 \
      libxcb1 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
      libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 \
      libxcb-xfixes0 libxcb-xkb1 libxcb-shm0 libxcb-util1 \
      libfontconfig1 libdbus-1-3 libsm6 libice6 libxrender1 libxi6 libxtst6 \
      libfreetype6 libgssapi-krb5-2 libssl3 procps \
      fonts-dejavu-core \
      xvfb x11vnc novnc websockify xauth \
    && rm -rf /var/lib/apt/lists/*

#/ рабочая папка  |  the working folder
WORKDIR /app

#/ сначала зависимости — кэшируем слой             |  deps first — cache the layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#/ весь проект                                    |  the whole project
COPY . .

#/ P2P, VNC, noVNC                                 |  P2P, VNC, noVNC
EXPOSE 42000 5900 6080

#/ entrypoint сам поднимает Xvfb, x11vnc, noVNC и запускает GUI
#/ the entrypoint starts Xvfb, x11vnc, noVNC itself and runs the GUI
ENTRYPOINT ["python", "docker/entrypoint.py"]
