[![Stars](https://img.shields.io/github/stars/freewms/1CUPS.svg?label=Github%20%E2%98%85&a)](https://github.com/freewms/1CUPS/stargazers)
[![Release](https://img.shields.io/github/tag/freewms/1CUPS.svg?label=Last%20release&a)](https://github.com/freewms/1CUPS/releases)
[![Downloads](https://img.shields.io/github/downloads/freewms/1CUPS/total)](https://github.com/freewms/1CUPS/releases)

# 1CUPS
Сервис для печати из 1С посредством CUPS

## Возможности:
- Печать документов как поштучно, так и пакетом
- Отправка заданий на печать на стороне сервера (&НаСевере)
- Получение информации о принтерах из служб CUPS

## Установка:

Пути указаны для ОС Debian.

```bash
apt install libcups2-dev
pip install markdown
pip install jsonschema
pip uninstall cups
pip install pycups
git clone https://github.com/freewms/1CUPS.git
cd ./1CUPS
sudo mkdir /opt/1CUPS
sudo cp ./* /opt/1CUPS
sudo chmod +x /opt/1CUPS/1cups.py
sudo cp ./1cups.service /etc/systemd/system/
sudo chmod +x /etc/systemd/system/1cups.service
```

## Запуск:  

### В качестве скрипта:
```bash
python /opt/1CUPS/1cups.py
```

### В качестве демона:
```bash
sudo systemctl enable 1cups
sudo systemctl start 1cups
```
