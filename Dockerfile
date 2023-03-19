FROM ubuntu:20.04

# Установка необходимых пакетов для Ubuntu
RUN apt-get update -y && \
    apt-get install -y software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get install -y wget unzip nano git pkg-config libfreetype6-dev libicu-dev python3.10 python3.10-dev python3.10-distutils python3-pip ffmpeg \
                       rubberband-cli tzdata locales && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    update-alternatives --install /usr/bin/python3 python /usr/bin/python3.10 1

# Копирование файлов проекта
COPY . /robot_binance_websockets
WORKDIR /robot_binance_websockets

# Установка модулей для Python3
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

# Запуск через /bin/bash необходим для поддержки переменных окружения
CMD ["/bin/bash", "-c", "python", "test_class8_with_average.py"]