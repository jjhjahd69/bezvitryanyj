# Конфігураційний файл
# НЕОБХІДНО ПЕРЕЙМЕНУВАТИ У config.py

# Базові дані авторизації
TOKEN = ''
BOT = ""
ID = None # int Application ID 
PREFIX = ""
ALLOWED_GUILD = None # Якщо необхідно обмежити певним дискорд сервером
MODERATOR_LIST = [] # userid модераторів через кому
START_MEMBER_ROLES = None # int айді ролі, яка в1идається користувачу при вході
START_BOT_ROLES = None # int айді ролі, яка видається боту на вході

# Дані підключення до MYSQL
db_host = "127.0.0.1" # або ip сервера, якщо бот НЕ там же де база
db_port = 3306 # або інший порт
db_user = "root"
db_password = "" 
db_name = ""
