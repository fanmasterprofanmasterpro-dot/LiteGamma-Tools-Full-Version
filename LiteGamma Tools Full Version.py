import os

import asyncio

import signal

import traceback

import json

import datetime

import re

import tempfile

import requests

import sys

import hashlib

import shutil

import time

from pathlib import Path

from telethon import TelegramClient

from telethon.tl.types import Channel, Chat, User

from telethon.tl.functions.channels import JoinChannelRequest

from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest

from telethon.tl.functions.chatlists import CheckChatlistInviteRequest, JoinChatlistInviteRequest

from telethon.errors import (

    FloodWaitError, ChannelPrivateError, ChatAdminRequiredError,

    UserPrivacyRestrictedError, AuthKeyUnregisteredError, PhoneCodeInvalidError,

    SessionPasswordNeededError, PhoneNumberInvalidError, PasswordHashInvalidError,

    RPCError, InviteHashExpiredError, InviteHashInvalidError, UserAlreadyParticipantError,

    UsernameNotOccupiedError, InviteRequestSentError

)

from colorama import init, Fore, Style



# =============== UPDATE CONFIGURATION ===============

GITHUB_USER = "fanmasterprofanmasterpro-dot"

GITHUB_REPO = "LiteGamma-Tools-Full-Version"

GITHUB_BRANCH = "main"

GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}"

GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}"



# =============== ВЕРСИЯ ПРОГРАММЫ ===============

CURRENT_VERSION = "1.2.2"  

UPDATE_CHECK_INTERVAL = 3600

LAST_UPDATE_CHECK_FILE = "last_update_check.json"

AUTO_UPDATE = True

NOTIFY_ON_UPDATE = True



init(autoreset=True)

# Цветовые схемы

CLR_MAIN = Fore.CYAN + Style.BRIGHT

CLR_ACCENT = Fore.MAGENTA + Style.BRIGHT

CLR_SUCCESS = Fore.GREEN + Style.BRIGHT

CLR_WARN = Fore.YELLOW + Style.BRIGHT

CLR_ERR = Fore.RED + Style.BRIGHT

CLR_INFO = Fore.BLUE + Style.BRIGHT

BR = Style.BRIGHT

RESET = Style.RESET_ALL





class UpdateManager:

    def __init__(self):

        self.version_file = "version.json"

        self.backup_folder = "backups"

        self.update_available = False

        self.new_version = None

        self.changelog = []



    async def check_for_updates(self, force=False):

        """Проверяет наличие обновлений на GitHub"""

        try:

            if not force and not self.should_check_update():

                return False



            print(f"{Fore.CYAN}🔍 Проверка обновлений...{Style.RESET_ALL}")

            await add_to_log_buffer("🔍 Проверка обновлений...")



         

            version_url = f"{GITHUB_RAW_BASE}/version.json"

            print(f"{Fore.CYAN}URL для проверки: {version_url}{Style.RESET_ALL}")

            

            response = requests.get(version_url, timeout=10)



            if response.status_code != 200:

                print(f"{Fore.YELLOW}⚠️ Не удалось проверить обновления. Код ответа: {response.status_code}{Style.RESET_ALL}")

                print(f"{Fore.YELLOW}URL: {version_url}{Style.RESET_ALL}")

                return False



            remote_data = response.json()

            remote_version = remote_data.get("version", "0.0.0")

            

            print(f"{Fore.CYAN}Версия на GitHub: {remote_version}{Style.RESET_ALL}")

            print(f"{Fore.CYAN}Текущая версия: {CURRENT_VERSION}{Style.RESET_ALL}")



           

            if self.is_newer_version(remote_version, CURRENT_VERSION):

                self.update_available = True

                self.new_version = remote_version

                self.changelog = remote_data.get("changelog", [])



                print(f"{Fore.GREEN}📦 Доступна новая версия: {remote_version}{Style.RESET_ALL}")

                print(f"{Fore.CYAN}Текущая версия: {CURRENT_VERSION}{Style.RESET_ALL}")



                if self.changelog:

                    print(f"\n{Fore.MAGENTA}Что нового:{Style.RESET_ALL}")

                    for change in self.changelog:

                        print(f"  {change}")



                self.save_last_check()



                if AUTO_UPDATE:

                    return await self.perform_update(remote_data)



                return True

            else:

                print(f"{Fore.GREEN}✅ У вас актуальная версия ({CURRENT_VERSION}){Style.RESET_ALL}")

                self.save_last_check()

                return False



        except requests.exceptions.ConnectionError:

            print(f"{Fore.RED}❌ Ошибка подключения к GitHub. Проверьте интернет.{Style.RESET_ALL}")

            return False

        except json.JSONDecodeError:

            print(f"{Fore.RED}❌ Ошибка чтения version.json. Проверьте файл на GitHub.{Style.RESET_ALL}")

            return False

        except Exception as e:

            print(f"{Fore.RED}❌ Ошибка при проверке обновлений: {e}{Style.RESET_ALL}")

            traceback.print_exc()

            return False

    def is_newer_version(self, version1, version2):
        """Проверяет, является ли version1 новее version2"""
        try:
            # Простое строковое сравнение
            return version1 > version2
        except:
            return False



    def should_check_update(self):

        

        try:

            if os.path.exists(LAST_UPDATE_CHECK_FILE):

                with open(LAST_UPDATE_CHECK_FILE, 'r') as f:

                    data = json.load(f)

                    last_check = data.get('last_check', 0)

                    return time.time() - last_check > UPDATE_CHECK_INTERVAL

            return True

        except:

            return True



    def save_last_check(self):

       

        try:

            with open(LAST_UPDATE_CHECK_FILE, 'w') as f:

                json.dump({'last_check': time.time()}, f)

        except:

            pass



    async def perform_update(self, remote_data):

        

        global CURRENT_VERSION



        try:

            print(f"\n{Fore.YELLOW}⚙️ Начинаю обновление до версии {self.new_version}...{Style.RESET_ALL}")



            

            os.makedirs(self.backup_folder, exist_ok=True)



            

            backup_name = f"backup_v{CURRENT_VERSION}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.py"

            backup_path = os.path.join(self.backup_folder, backup_name)



            current_file = __file__

            with open(current_file, 'r', encoding='utf-8') as f:

                current_content = f.read()



            with open(backup_path, 'w', encoding='utf-8') as f:

                f.write(current_content)



            print(f"{Fore.GREEN}✅ Бэкап создан: {backup_path}{Style.RESET_ALL}")



       

            filename = os.path.basename(__file__)

        

            encoded_filename = filename.replace(' ', '%20')

            

           

            script_url = remote_data.get('download_url', f"{GITHUB_RAW_BASE}/{encoded_filename}")

            

            print(f"{Fore.CYAN}Скачиваю с URL: {script_url}{Style.RESET_ALL}")



            response = requests.get(script_url, timeout=30)

            if response.status_code == 200:

                new_content = response.text

                

                

                if len(new_content) < 100:

                    print(f"{Fore.RED}❌ Скачанный файл слишком мал. Возможно, неверный URL.{Style.RESET_ALL}")

                    return False



                # Обновляем версию в файле

                new_content = self.update_version_in_file(new_content, self.new_version)



                with open(current_file, 'w', encoding='utf-8') as f:

                    f.write(new_content)



               

                CURRENT_VERSION = self.new_version



                print(f"{Fore.GREEN}✅ Скрипт успешно обновлен до версии {self.new_version}!{Style.RESET_ALL}")



                

                self.save_config_without_version()



                if NOTIFY_ON_UPDATE and notification_enabled:

                    await send_notification(

                        f"🔄 **Программа обновлена!**\n\n"

                        f"📦 Новая версия: {self.new_version}\n"

                        f"📅 Дата: {remote_data.get('release_date', 'Неизвестно')}\n"

                        f"📝 Изменения:\n" + "\n".join([f"  {c}" for c in self.changelog]),

                        "update"

                    )



                print(f"\n{Fore.YELLOW}⚠️ Для применения обновлений необходим перезапуск{Style.RESET_ALL}")

                if input(f"{Fore.MAGENTA}Перезапустить сейчас? (y/n): {Style.RESET_ALL}").lower() == 'y':

                    self.restart_program()



                return True

            else:

                print(f"{Fore.RED}❌ Не удалось скачать обновление. Код ответа: {response.status_code}{Style.RESET_ALL}")

                print(f"{Fore.RED}URL: {script_url}{Style.RESET_ALL}")

                return False



        except Exception as e:

            print(f"{Fore.RED}❌ Ошибка при обновлении: {e}{Style.RESET_ALL}")

            traceback.print_exc()

            return False



    def save_config_without_version(self):

        

        config = {

            "api_id": current_api_id,

            "api_hash": current_api_hash,

            "session_folder": session_folder,

            "message": message_to_send,

            "delay_messages": delay_between_messages,

            "delay_accounts": delay_between_accounts,

            "max_messages_per_account": max_messages_per_account,

            "repeat_broadcast": repeat_broadcast,

            "repeat_interval": repeat_interval,

            "delete_after_send": delete_after_send,

            "recipient_type": recipient_type,

            "use_media": use_media,

            "media_path": media_path,

            "fast_mode": fast_mode,

            "fast_delay": fast_delay,

            "notification_enabled": notification_enabled,

            "notification_bot_token": notification_bot_token,

            "notification_chat_id": notification_chat_id,

            "notify_invalid_session": notify_invalid_session,

            "notify_cycle_results": notify_cycle_results,

            "notify_full_logs": notify_full_logs

           

        }

        try:

            with open(config_file, 'w', encoding='utf-8') as f:

                json.dump(config, f, ensure_ascii=False, indent=2)

            print(f"{Fore.GREEN}✔ Конфигурация сохранена.{Style.RESET_ALL}")

        except Exception as e:

            print(f"{Fore.RED}✘ Ошибка сохранения: {e}{Style.RESET_ALL}")



    def update_version_in_file(self, content, new_version):
    import re
    patterns = [
        (r'CURRENT_VERSION\s*=\s*["\']([^"\']+)["\']', f'CURRENT_VERSION = "{new_version}"'),
        (r'CURRENT_VERSION\s*=\s*([0-9.]+)', f'CURRENT_VERSION = "{new_version}"')
    ]



        updated_content = content

        for pattern, replacement in patterns:

            updated_content = re.sub(pattern, replacement, updated_content)



        

        if updated_content == content:

            

            version_line = f'\nCURRENT_VERSION = "{new_version}"\n'

           

            import_end = updated_content.find('\n\n')

            if import_end != -1:

                updated_content = updated_content[:import_end] + version_line + updated_content[import_end:]



        return updated_content



    def verify_version_in_file(self):

       

        try:

            with open(__file__, 'r', encoding='utf-8') as f:

                content = f.read()



           

            import re

            version_match = re.search(r'CURRENT_VERSION\s*=\s*["\']?([0-9.]+)["\']?', content)

            if version_match:

                file_version = version_match.group(1)

                return file_version

        except:

            pass

        return None



    def restart_program(self):

    

        print(f"{Fore.CYAN}🔄 Перезапуск...{Style.RESET_ALL}")

        python = sys.executable

        os.execl(python, python, *sys.argv)



    async def show_update_menu(self):

        

        while True:

            os.system('cls' if os.name == 'nt' else 'clear')

            print_header("🔄 СИСТЕМА ОБНОВЛЕНИЙ")



            print(f"{CLR_INFO}Текущая версия: {CLR_SUCCESS}{CURRENT_VERSION}")



            if self.update_available:

                print(f"{CLR_WARN}Доступна новая версия: {self.new_version}{Style.RESET_ALL}")

                print(f"\n{CLR_MAIN}📝 Что нового:")

                for change in self.changelog:

                    print(f"  {change}")

            else:

                print(f"{CLR_SUCCESS}✅ Обновлений не найдено{Style.RESET_ALL}")



            print(f"\n{CLR_INFO}1. 🔍 Проверить обновления")

            print(f"{CLR_INFO}2. ⬇️ Скачать и установить обновление")

            print(f"{CLR_INFO}3. 📋 История обновлений")

            print(f"{CLR_INFO}4. ⚙️ Настройки обновлений")

            print(f"{CLR_INFO}5. 🔙 Восстановить из бэкапа")

            print(f"{CLR_INFO}6. 🔍 Диагностика версии")

            print(f"{CLR_ERR}0. 🔙 Назад")



            choice = input(f"\n{CLR_MAIN}Выберите действие ➔ {RESET}").strip()



            if choice == '1':

                await self.check_for_updates(force=True)

                input("\nНажмите Enter...")

            elif choice == '2' and self.update_available:

                

                update_data = {

                    'version': self.new_version,

                    'changelog': self.changelog,

                    'download_url': f"{GITHUB_RAW_BASE}/LiteGamma%20Tools%20Full%20Version.py"

                }

                await self.perform_update(update_data)

                input("\nНажмите Enter...")

            elif choice == '3':

                self.show_update_history()

                input("\nНажмите Enter...")

            elif choice == '4':

                self.show_update_settings()

            elif choice == '5':

                self.restore_from_backup()

                input("\nНажмите Enter...")

            elif choice == '6':

                await self.diagnose_version()

                input("\nНажмите Enter...")

            elif choice == '0':

                break



    async def diagnose_version(self):

        

        print(f"\n{Fore.CYAN}🔍 ДИАГНОСТИКА ВЕРСИИ:{Style.RESET_ALL}")

        print(f"  Глобальная CURRENT_VERSION: {CURRENT_VERSION}")

        print(f"  GitHub пользователь: {GITHUB_USER}")

        print(f"  GitHub репозиторий: {GITHUB_REPO}")

        print(f"  GitHub ветка: {GITHUB_BRANCH}")

        

        # Проверяем файл version.json на GitHub

        version_url = f"{GITHUB_RAW_BASE}/version.json"

        print(f"\n{Fore.CYAN}Проверка version.json:{Style.RESET_ALL}")

        print(f"  URL: {version_url}")

        

        try:

            response = requests.get(version_url, timeout=10)

            print(f"  Статус ответа: {response.status_code}")

            

            if response.status_code == 200:

                remote_data = response.json()

                print(f"  Версия на GitHub: {remote_data.get('version', 'не найдено')}")

                print(f"  Что нового: {remote_data.get('changelog', [])}")

                print(f"  download_url: {remote_data.get('download_url', 'не указан')}")

            else:

                print(f"  {Fore.RED}Ошибка: не удалось получить version.json{Style.RESET_ALL}")

        except Exception as e:

            print(f"  {Fore.RED}Ошибка: {e}{Style.RESET_ALL}")

        

      

        filename = os.path.basename(__file__)

        encoded_filename = filename.replace(' ', '%20')

        script_url = f"{GITHUB_RAW_BASE}/{encoded_filename}"

        print(f"\n{Fore.CYAN}Проверка файла скрипта:{Style.RESET_ALL}")

        print(f"  URL: {script_url}")

        

        try:

            response = requests.head(script_url, timeout=10)

            print(f"  Статус ответа: {response.status_code}")

            if response.status_code == 200:

                print(f"  {Fore.GREEN}Файл доступен для скачивания{Style.RESET_ALL}")

            else:

                print(f"  {Fore.RED}Файл не найден на GitHub{Style.RESET_ALL}")

        except Exception as e:

            print(f"  {Fore.RED}Ошибка: {e}{Style.RESET_ALL}")



    def show_update_history(self):

        """Показывает историю обновлений"""

        print(f"\n{Fore.CYAN}📋 История обновлений:{Style.RESET_ALL}")

        backups = sorted(Path(self.backup_folder).glob("backup_*.py"), reverse=True)



        if not backups:

            print("  Нет сохраненных бэкапов")

            return



        for i, backup in enumerate(backups[:10], 1):

            version_match = re.search(r'v([\d.]+)', backup.name)

            version = version_match.group(1) if version_match else "неизвестно"

            size = backup.stat().st_size / 1024

            modified = datetime.datetime.fromtimestamp(backup.stat().st_mtime)

            print(f"  {i}. {backup.name}")

            print(f"     Версия: {version}, Размер: {size:.1f}KB, Дата: {modified.strftime('%Y-%m-%d %H:%M')}")



    def restore_from_backup(self):

       

        backups = sorted(Path(self.backup_folder).glob("backup_*.py"), reverse=True)



        if not backups:

            print(f"{Fore.RED}❌ Нет доступных бэкапов{Style.RESET_ALL}")

            return



        print(f"\n{Fore.CYAN}Доступные бэкапы:{Style.RESET_ALL}")

        for i, backup in enumerate(backups[:10], 1):

            print(f"  {i}. {backup.name}")



        try:

            choice = int(input(f"\n{Fore.MAGENTA}Выберите номер бэкапа: {Style.RESET_ALL}")) - 1

            if 0 <= choice < len(backups):

                backup_file = backups[choice]



                current_backup = Path(

                    self.backup_folder) / f"pre_restore_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.py"

                shutil.copy2(__file__, current_backup)



                shutil.copy2(backup_file, __file__)

                print(f"{Fore.GREEN}✅ Восстановлено из бэкапа!{Style.RESET_ALL}")



                if input(f"{Fore.MAGENTA}Перезапустить сейчас? (y/n): {Style.RESET_ALL}").lower() == 'y':

                    self.restart_program()

        except ValueError:

            print(f"{Fore.RED}❌ Неверный выбор{Style.RESET_ALL}")



    def show_update_settings(self):

       

        global AUTO_UPDATE, NOTIFY_ON_UPDATE, UPDATE_CHECK_INTERVAL



        while True:

            os.system('cls' if os.name == 'nt' else 'clear')

            print_header("⚙️ НАСТРОЙКИ ОБНОВЛЕНИЙ")



            print(

                f"{CLR_INFO}1. Автоматическое обновление: {CLR_SUCCESS if AUTO_UPDATE else CLR_ERR}{'ВКЛ' if AUTO_UPDATE else 'ВЫКЛ'}")

            print(

                f"{CLR_INFO}2. Уведомления об обновлениях: {CLR_SUCCESS if NOTIFY_ON_UPDATE else CLR_ERR}{'ВКЛ' if NOTIFY_ON_UPDATE else 'ВЫКЛ'}")

            print(f"{CLR_INFO}3. Интервал проверки: {CLR_WARN}{UPDATE_CHECK_INTERVAL // 60} минут")

            print(f"{CLR_INFO}4. GitHub репозиторий: {CLR_WARN}{GITHUB_USER}/{GITHUB_REPO}")

            print(f"{CLR_ERR}0. 🔙 Назад")



            choice = input(f"\n{CLR_MAIN}Выберите пункт ➔ {RESET}").strip()



            if choice == '1':

                AUTO_UPDATE = not AUTO_UPDATE

            elif choice == '2':

                NOTIFY_ON_UPDATE = not NOTIFY_ON_UPDATE

            elif choice == '3':

                try:

                    new_interval = input(f"Интервал в минутах (текущий: {UPDATE_CHECK_INTERVAL // 60}): ")

                    UPDATE_CHECK_INTERVAL = int(new_interval) * 60

                except:

                    pass

            elif choice == '0':

                break







update_manager = UpdateManager()





def print_header(text):

    print(f"\n{CLR_ACCENT}╔" + "═" * (len(text) + 4) + "╗")

    print(f"{CLR_ACCENT}║  {CLR_MAIN}{text}  {CLR_ACCENT}║")

    print(f"{CLR_ACCENT}╚" + "═" * (len(text) + 4) + "╝\n")





def print_stata(text):

    print(f"\n{CLR_ACCENT}╔" + "═" * (len(text) + 4) + "╗")

    print(f"{CLR_ACCENT}║  {CLR_MAIN}{text}    {CLR_ACCENT}║")

    print(f"{CLR_ACCENT}╚" + "═" * (len(text) + 4) + "╝\n")







DEFAULT_API_ID = 0

DEFAULT_API_HASH = "ЗАМЕНИТЕ НА ВАШ API HASH, ТАКЖЕ НАСТРОЙТЕ API ID "

DEFAULT_SESSION_FOLDER = "session"

DEFAULT_MESSAGE = """Привет! Это тестовое сообщение от бота рассылки!

Спасибо за покупку в нашем магазине @BananaStorebot_bot 😉"""

DEFAULT_DELAY_BETWEEN_MESSAGES = 3

DEFAULT_DELAY_BETWEEN_ACCOUNTS = 10

DEFAULT_MAX_MESSAGES_PER_ACCOUNT = 50

DEFAULT_REPEAT_BROADCAST = False

DEFAULT_REPEAT_INTERVAL = 30

DEFAULT_DELETE_AFTER_SEND = False

DEFAULT_RECIPIENT_TYPE = "all"

DEFAULT_USE_MEDIA = False

DEFAULT_MEDIA_PATH = ""

DEFAULT_FAST_MODE = False

DEFAULT_FAST_DELAY = 0.3



DEFAULT_NOTIFICATION_ENABLED = False

DEFAULT_NOTIFICATION_BOT_TOKEN = ""

DEFAULT_NOTIFICATION_CHAT_ID = ""

DEFAULT_NOTIFY_INVALID_SESSION = True

DEFAULT_NOTIFY_CYCLE_RESULTS = True

DEFAULT_NOTIFY_FULL_LOGS = False



# Глобальные переменные

current_api_id = DEFAULT_API_ID

current_api_hash = DEFAULT_API_HASH

session_folder = DEFAULT_SESSION_FOLDER

message_to_send = DEFAULT_MESSAGE

delay_between_messages = DEFAULT_DELAY_BETWEEN_MESSAGES

delay_between_accounts = DEFAULT_DELAY_BETWEEN_ACCOUNTS

max_messages_per_account = DEFAULT_MAX_MESSAGES_PER_ACCOUNT

repeat_broadcast = DEFAULT_REPEAT_BROADCAST

repeat_interval = DEFAULT_REPEAT_INTERVAL

delete_after_send = DEFAULT_DELETE_AFTER_SEND

recipient_type = DEFAULT_RECIPIENT_TYPE

use_media = DEFAULT_USE_MEDIA

media_path = DEFAULT_MEDIA_PATH

fast_mode = DEFAULT_FAST_MODE

fast_delay = DEFAULT_FAST_DELAY



# Глобальные переменные для уведомлений

notification_enabled = DEFAULT_NOTIFICATION_ENABLED

notification_bot_token = DEFAULT_NOTIFICATION_BOT_TOKEN

notification_chat_id = DEFAULT_NOTIFICATION_CHAT_ID

notify_invalid_session = DEFAULT_NOTIFY_INVALID_SESSION

notify_cycle_results = DEFAULT_NOTIFY_CYCLE_RESULTS

notify_full_logs = DEFAULT_NOTIFY_FULL_LOGS



stop_event = asyncio.Event()

invalid_session_log_file = "invalidsession_list.txt"



config_file = "config.json"

group_list_file = "group.json"

enter_links_file = "enter.json"



notification_client = None



log_buffer = []

log_buffer_lock = asyncio.Lock()





async def init_notification_client():

    """Инициализирует клиент для отправки уведомлений."""

    global notification_client

    if notification_enabled and notification_bot_token and notification_chat_id:

        try:

            if notification_client:

                await notification_client.disconnect()



            notification_client = TelegramClient(

                'notification_bot_session',

                api_id=current_api_id,

                api_hash=current_api_hash

            )



            await notification_client.start(bot_token=notification_bot_token)



            me = await notification_client.get_me()

            print(f"{Fore.GREEN}✔ Бот для уведомлений инициализирован: @{me.username}{Style.RESET_ALL}")



            await notification_client.send_message(

                int(notification_chat_id),

                "🔔 Уведомления успешно настроены!"

            )

            return True

        except Exception as e:

            print(f"{Fore.RED}✘ Ошибка инициализации бота уведомлений: {e}{Style.RESET_ALL}")

            notification_client = None

            return False

    return False





async def close_notification_client():

    """Закрывает клиент уведомлений."""

    global notification_client

    if notification_client:

        await notification_client.disconnect()

        notification_client = None

        print(f"{Fore.CYAN}📱 Клиент уведомлений закрыт{Style.RESET_ALL}")





async def add_to_log_buffer(message):

    """Добавляет сообщение в буфер логов."""

    global log_buffer

    async with log_buffer_lock:

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        log_buffer.append(f"[{timestamp}] {message}")

        if len(log_buffer) > 2000:

            log_buffer = log_buffer[-2000:]





async def save_logs_to_file():

    """Сохраняет буфер логов во временный файл."""

    if not log_buffer:

        return None



    async with log_buffer_lock:

        try:

            fd, temp_path = tempfile.mkstemp(suffix='.txt', prefix='telegram_log_', text=True)

            with os.fdopen(fd, 'w', encoding='utf-8') as f:

                f.write(f"Лог рассылки от {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

                f.write("=" * 50 + "\n\n")

                for line in log_buffer:

                    f.write(line + "\n")

            return temp_path

        except Exception as e:

            print(f"{Fore.RED}✘ Ошибка сохранения логов в файл: {e}{Style.RESET_ALL}")

            return None





async def send_notification(message, notification_type="info"):

    """Отправляет уведомление в Telegram, если включено."""

    if not notification_enabled or not notification_client or not notification_chat_id:

        return



    if notification_type == "invalid_session" and not notify_invalid_session:

        return

    if notification_type == "cycle_result" and not notify_cycle_results:

        return

    if notification_type == "full_log" and not notify_full_logs:

        return



    try:

        if notification_type == "full_log" and log_buffer:

            log_file_path = await save_logs_to_file()

            if log_file_path and os.path.exists(log_file_path):

                await notification_client.send_file(

                    int(notification_chat_id),

                    log_file_path,

                    caption=f"📋 **Полный лог рассылки**\nВремя: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nВсего записей: {len(log_buffer)}"

                )

                try:

                    os.unlink(log_file_path)

                except:

                    pass

            else:

                full_log = "\n".join(log_buffer[-50:])

                if len(full_log) > 3500:

                    full_log = full_log[-3500:]

                await notification_client.send_message(

                    int(notification_chat_id),

                    f"📋 **Полный лог (последние 50 строк)**\n\n{full_log}"

                )

        else:

            await notification_client.send_message(int(notification_chat_id), message)



        print(f"{Fore.GREEN}📱 Уведомление отправлено ({notification_type}){Style.RESET_ALL}")

    except Exception as e:

        print(f"{Fore.RED}✘ Ошибка отправки уведомления: {e}{Style.RESET_ALL}")





def save_config():

    """Сохраняет конфигурацию без версии"""

    config = {

        "api_id": current_api_id,

        "api_hash": current_api_hash,

        "session_folder": session_folder,

        "message": message_to_send,

        "delay_messages": delay_between_messages,

        "delay_accounts": delay_between_accounts,

        "max_messages_per_account": max_messages_per_account,

        "repeat_broadcast": repeat_broadcast,

        "repeat_interval": repeat_interval,

        "delete_after_send": delete_after_send,

        "recipient_type": recipient_type,

        "use_media": use_media,

        "media_path": media_path,

        "fast_mode": fast_mode,

        "fast_delay": fast_delay,

        "notification_enabled": notification_enabled,

        "notification_bot_token": notification_bot_token,

        "notification_chat_id": notification_chat_id,

        "notify_invalid_session": notify_invalid_session,

        "notify_cycle_results": notify_cycle_results,

        "notify_full_logs": notify_full_logs

        # Версию НЕ сохраняем!

    }

    try:

        with open(config_file, 'w', encoding='utf-8') as f:

            json.dump(config, f, ensure_ascii=False, indent=2)

        print(f"{Fore.GREEN}✔ Конфигурация сохранена.{Style.RESET_ALL}")

    except Exception as e:

        print(f"{Fore.RED}✘ Ошибка сохранения: {e}{Style.RESET_ALL}")





def load_config():

    """Загружает конфигурацию без версии"""

    global current_api_id, current_api_hash, session_folder, message_to_send, delay_between_messages, delay_between_accounts, max_messages_per_account, repeat_broadcast, repeat_interval, delete_after_send, recipient_type, use_media, media_path, fast_mode, fast_delay, notification_enabled, notification_bot_token, notification_chat_id, notify_invalid_session, notify_cycle_results, notify_full_logs

    try:

        if os.path.exists(config_file):

            with open(config_file, 'r', encoding='utf-8') as f:

                config = json.load(f)

                current_api_id = config.get("api_id", DEFAULT_API_ID)

                current_api_hash = config.get("api_hash", DEFAULT_API_HASH)

                session_folder = config.get("session_folder", DEFAULT_SESSION_FOLDER)

                message_to_send = config.get("message", DEFAULT_MESSAGE)

                delay_between_messages = config.get("delay_messages", DEFAULT_DELAY_BETWEEN_MESSAGES)

                delay_between_accounts = config.get("delay_accounts", DEFAULT_DELAY_BETWEEN_ACCOUNTS)

                max_messages_per_account = config.get("max_messages_per_account", DEFAULT_MAX_MESSAGES_PER_ACCOUNT)

                repeat_broadcast = config.get("repeat_broadcast", DEFAULT_REPEAT_BROADCAST)

                repeat_interval = config.get("repeat_interval", DEFAULT_REPEAT_INTERVAL)

                delete_after_send = config.get("delete_after_send", DEFAULT_DELETE_AFTER_SEND)

                recipient_type = config.get("recipient_type", DEFAULT_RECIPIENT_TYPE)

                use_media = config.get("use_media", DEFAULT_USE_MEDIA)

                media_path = config.get("media_path", DEFAULT_MEDIA_PATH)

                fast_mode = config.get("fast_mode", DEFAULT_FAST_MODE)

                fast_delay = config.get("fast_delay", DEFAULT_FAST_DELAY)

                notification_enabled = config.get("notification_enabled", DEFAULT_NOTIFICATION_ENABLED)

                notification_bot_token = config.get("notification_bot_token", DEFAULT_NOTIFICATION_BOT_TOKEN)

                notification_chat_id = config.get("notification_chat_id", DEFAULT_NOTIFICATION_CHAT_ID)

                notify_invalid_session = config.get("notify_invalid_session", DEFAULT_NOTIFY_INVALID_SESSION)

                notify_cycle_results = config.get("notify_cycle_results", DEFAULT_NOTIFY_CYCLE_RESULTS)

                notify_full_logs = config.get("notify_full_logs", DEFAULT_NOTIFY_FULL_LOGS)

                # Версию НЕ загружаем!

            print(f"{Fore.GREEN}✔ Конфигурация загружена.{Style.RESET_ALL}")

    except Exception as e:

        print(f"{Fore.YELLOW}⚠️ Ошибка загрузки конфигурации: {e}{Style.RESET_ALL}")





def log_invalid_session(session_file):

    """Записывает невалидную сессию в лог-файл и отправляет уведомление."""

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = f"{session_file} не рабочая ({timestamp})"

    try:

        with open(invalid_session_log_file, 'a', encoding='utf-8') as f:

            f.write(log_entry + "\n")

        print(f"{Fore.CYAN}✉ Сессия '{session_file}' добавлена в '{invalid_session_log_file}'{Style.RESET_ALL}")



        asyncio.create_task(

            send_notification(f"⚠️ Невалидная сессия: {session_file}\nВремя: {timestamp}", "invalid_session"))

    except Exception as e:

        print(f"{Fore.RED}✘ Ошибка записи в лог '{invalid_session_log_file}': {e}{Style.RESET_ALL}")





def extract_links_from_text(text):

    """Извлекает все ссылки из текста."""

    url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'

    return re.findall(url_pattern, text)





def load_target_groups(filename=group_list_file):

    """Загружает список целей из JSON файла (может содержать ID групп, ссылки на группы или ссылки на папки)."""

    target_groups = []

    if not os.path.exists(filename):

        print(f"{Fore.RED}✘ Файл '{filename}' не найден.{Style.RESET_ALL}")

        return None



    try:

        with open(filename, 'r', encoding='utf-8') as f:

            data = json.load(f)

            if isinstance(data, list):

                target_groups = data

            else:

                print(f"{Fore.RED}✘ Файл '{filename}' должен содержать JSON-массив.{Style.RESET_ALL}")

                return None

    except json.JSONDecodeError:

        print(f"{Fore.RED}✘ Ошибка декодирования JSON в файле '{filename}'.{Style.RESET_ALL}")

        return None

    except Exception as e:

        print(f"{Fore.RED}✘ Ошибка при чтении файла '{filename}': {e}{Style.RESET_ALL}")

        return None



    if not target_groups:

        print(f"{Fore.YELLOW}⚠️ Файл '{filename}' пуст.{Style.RESET_ALL}")

        return []



    print(f"{Fore.GREEN}✔ Успешно загружено {len(target_groups)} целей из '{filename}'.{Style.RESET_ALL}")

    return target_groups





def load_enter_links(filename=enter_links_file):

    """Загружает ссылки для входа из JSON файла."""

    enter_links = []

    if not os.path.exists(filename):

        print(f"{Fore.RED}✘ Файл '{filename}' не найден.{Style.RESET_ALL}")

        return None



    try:

        with open(filename, 'r', encoding='utf-8') as f:

            data = json.load(f)

            if isinstance(data, list):

                enter_links = data

            else:

                print(f"{Fore.RED}✘ Файл '{filename}' должен содержать JSON-массив.{Style.RESET_ALL}")

                return None

    except json.JSONDecodeError:

        print(f"{Fore.RED}✘ Ошибка декодирования JSON в файле '{filename}'.{Style.RESET_ALL}")

        return None

    except Exception as e:

        print(f"{Fore.RED}✘ Ошибка при чтении файла '{filename}': {e}{Style.RESET_ALL}")

        return None



    if not enter_links:

        print(f"{Fore.YELLOW}⚠️ Файл '{filename}' пуст.{Style.RESET_ALL}")

        return []



    print(f"{Fore.GREEN}✔ Успешно загружено {len(enter_links)} ссылок для входа из '{filename}'.{Style.RESET_ALL}")

    return enter_links





async def process_folder_link(client, link, session_name=""):

    """Обрабатывает ссылку на папку с группами"""

    try:

        if 'addlist/' in link:

            slug = link.split('addlist/')[-1].split('?')[0]

        else:

            slug = link



        log_msg = f"🔍 [{session_name}] Проверка папки..."

        print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)



        try:

            check_result = await client(CheckChatlistInviteRequest(slug))



            all_chats = []

            if hasattr(check_result, 'chats') and check_result.chats:

                all_chats = list(check_result.chats)

                log_msg = f"✅ [{session_name}] Папка найдена, получено {len(all_chats)} чатов"

                print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")

                await add_to_log_buffer(log_msg)



                for idx, chat in enumerate(all_chats, 1):

                    chat_title = getattr(chat, 'title', f"чат ID {chat.id}")

                    can_write = True

                    if hasattr(chat, 'left') and chat.left:

                        can_write = False

                    if hasattr(chat, 'broadcast') and chat.broadcast:

                        can_write = False

                    status = "✅" if can_write else "⚠️ (только чтение)"

                    chat_log = f"  {idx}. {chat_title[:50]} {status}"

                    print(chat_log)

                    await add_to_log_buffer(chat_log)



                return all_chats, True

            else:

                log_msg = f"⚠️ [{session_name}] Папка доступна, но чаты не получены. Возможно, нужно вступить..."

                print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")

                await add_to_log_buffer(log_msg)



                if hasattr(check_result, 'peers') and check_result.peers:

                    try:

                        join_result = await client(JoinChatlistInviteRequest(

                            slug=slug,

                            peers=check_result.peers

                        ))



                        log_msg = f"✅ [{session_name}] Успешно вступил в папку"

                        print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")

                        await add_to_log_buffer(log_msg)



                        await asyncio.sleep(2)



                        updated_check = await client(CheckChatlistInviteRequest(slug))

                        if hasattr(updated_check, 'chats') and updated_check.chats:

                            all_chats = list(updated_check.chats)

                            log_msg = f"✅ [{session_name}] Получено {len(all_chats)} чатов после вступления"

                            print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")

                            await add_to_log_buffer(log_msg)

                            return all_chats, True

                    except UserAlreadyParticipantError:

                        log_msg = f"ℹ️ [{session_name}] Уже в папке, но чаты не получены"

                        print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")

                        await add_to_log_buffer(log_msg)

                    except Exception as e:

                        log_msg = f"❌ [{session_name}] Ошибка при вступлении в папку: {e}"

                        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

                        await add_to_log_buffer(log_msg)



                return [], False



        except InviteHashExpiredError:

            log_msg = f"❌ [{session_name}] Ссылка на папку истекла"

            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

            await add_to_log_buffer(log_msg)

            return None, False



        except FloodWaitError as e:

            wait_time = e.seconds

            log_msg = f"⏳ [{session_name}] FloodWait: {wait_time}с"

            print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")

            await add_to_log_buffer(log_msg)



            for remaining in range(wait_time, 0, -1):

                if stop_event.is_set():

                    return None, False

                if remaining % 10 == 0 or remaining <= 5:

                    print(f"{Fore.YELLOW}⏳ [{session_name}] Осталось: {remaining} сек...{Style.RESET_ALL}")

                await asyncio.sleep(1)



            return await process_folder_link(client, link, session_name)



        except Exception as e:

            log_msg = f"❌ [{session_name}] Ошибка при проверке папки: {e}"

            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

            await add_to_log_buffer(log_msg)

            return None, False



    except Exception as e:

        log_msg = f"❌ [{session_name}] Ошибка обработки папки: {e}"

        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)

        return None, False





async def get_chat_from_link(client, link, session_name=""):

    """Получает объект чата по ссылке."""

    try:

        link = link.strip()



        if 'addlist' in link:

            log_msg = f"📁 [{session_name}] Обнаружена ссылка на папку с группами"

            print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")

            await add_to_log_buffer(log_msg)



            chats, success = await process_folder_link(client, link, session_name)



            if success and chats:

                return chats, "folder"

            elif success and not chats:

                log_msg = f"⚠️ [{session_name}] Папка обработана, но чаты не получены"

                print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")

                await add_to_log_buffer(log_msg)

                return [], "folder_empty"

            else:

                log_msg = f"❌ [{session_name}] Не удалось обработать папку"

                print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

                await add_to_log_buffer(log_msg)

                return None, "error"



        else:

            try:

                if 'joinchat' in link or '+' in link:

                    if 'joinchat/' in link:

                        hash_part = link.split('joinchat/')[-1].split('?')[0]

                    elif '+' in link:

                        hash_part = link.split('+')[-1].split('?')[0]

                    else:

                        hash_part = link



                    try:

                        entity = await client.get_entity(hash_part)

                        chat_title = getattr(entity, 'title', str(entity.id))

                        log_msg = f"✅ [{session_name}] Получен чат: {chat_title[:50]}"

                        print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")

                        await add_to_log_buffer(log_msg)

                        return entity, "chat"

                    except ValueError as e:

                        if "Cannot find any entity" in str(e):

                            log_msg = f"❌ [{session_name}] Не удалось найти чат по ссылке"

                            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

                            await add_to_log_buffer(log_msg)

                            return None, "error"

                        else:

                            raise



                else:

                    entity = await client.get_entity(link)

                    chat_title = getattr(entity, 'title', str(entity.id))

                    log_msg = f"✅ [{session_name}] Получен чат: {chat_title[:50]}"

                    print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")

                    await add_to_log_buffer(log_msg)

                    return entity, "chat"



            except FloodWaitError as e:

                wait_time = e.seconds

                log_msg = f"⏳ [{session_name}] FloodWait: {wait_time}с"

                print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")

                await add_to_log_buffer(log_msg)

                await asyncio.sleep(wait_time)

                return await get_chat_from_link(client, link, session_name)



            except (ChannelPrivateError, ChatAdminRequiredError):

                log_msg = f"❌ [{session_name}] Нет доступа к чату"

                print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

                await add_to_log_buffer(log_msg)

                return None, "error"



            except Exception as e:

                log_msg = f"❌ [{session_name}] Ошибка при получении чата: {e}"

                print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

                await add_to_log_buffer(log_msg)

                return None, "error"



    except Exception as e:

        log_msg = f"❌ [{session_name}] Общая ошибка: {e}"

        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)

        return None, "error"





async def get_user_chats(client, chat_type="all"):

    """Получает чаты пользователя с фильтрацией по типу."""

    chats = []

    skipped_channels = 0



    try:

        async for dialog in client.iter_dialogs():

            entity = dialog.entity



            if chat_type == "users" and isinstance(entity, User):

                chats.append(entity)

                continue



            if chat_type == "groups":

                if isinstance(entity, Chat):

                    chats.append(entity)

                    continue

                if isinstance(entity, Channel):

                    if entity.broadcast:

                        skipped_channels += 1

                        continue

                    if entity.megagroup and not entity.left:

                        chats.append(entity)

                    continue

                continue



            if chat_type == "all":

                if isinstance(entity, Chat):

                    chats.append(entity)

                    continue



                if isinstance(entity, Channel):

                    if entity.broadcast:

                        skipped_channels += 1

                        continue

                    if entity.megagroup and not entity.left:

                        chats.append(entity)

                    continue



                if isinstance(entity, User):

                    chats.append(entity)

                    continue



        type_names = {"all": "чатов/групп/личных чатов", "users": "личных чатов", "groups": "групп"}

        log_msg = f"✔ Найдено {len(chats)} {type_names[chat_type]}"

        print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)



        if skipped_channels > 0:

            log_msg = f"ℹ Пропущено каналов: {skipped_channels}"

            print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")

            await add_to_log_buffer(log_msg)



        return chats



    except Exception as e:

        log_msg = f"✘ Ошибка получения чатов: {e}"

        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)

        return []





async def send_message_safely(client, chat, message, delete_after=False, media_path=None):

    """Отправляет сообщение с опциональным медиафайлом и опционально удаляет его у себя."""

    sent_message = None

    try:

        if media_path and os.path.exists(media_path):

            sent_message = await client.send_file(chat, media_path, caption=message)

        else:

            sent_message = await client.send_message(chat, message)



        if delete_after and sent_message:

            await client.delete_messages(chat, [sent_message.id], revoke=False)

            log_msg = "🗑 Сообщение удалено у отправителя"

            print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")

            await add_to_log_buffer(log_msg)



        return True, sent_message

    except FloodWaitError as e:

        log_msg = f"⏳ FloodWait {e.seconds} сек..."

        print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)

        await asyncio.sleep(e.seconds)

        return await send_message_safely(client, chat, message, delete_after, media_path)

    except (ChatAdminRequiredError, ChannelPrivateError, UserPrivacyRestrictedError):

        return False, None

    except Exception as e:

        log_msg = f"✘ Другая ошибка: {e}"

        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)

        return False, None





async def join_chat_safely(client, link, session_name=""):

    """Безопасное вступление в чат/группу по ссылке."""

    try:

        link = link.strip()



        try:

            if 'joinchat' in link or '+' in link:

                if 'joinchat/' in link:

                    hash_part = link.split('joinchat/')[-1].split('?')[0]

                elif '+' in link:

                    hash_part = link.split('+')[-1].split('?')[0]

                else:

                    hash_part = link



                result = await client(JoinChannelRequest(hash_part))

            else:

                entity = await client.get_entity(link)

                result = await client(JoinChannelRequest(entity))



            if hasattr(result, 'chats') and result.chats:

                chat_title = result.chats[0].title

            else:

                chat_title = link[:30]



            log_msg = f"✔ [{session_name}] Успешно вступил в: {chat_title}"

            print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")

            await add_to_log_buffer(log_msg)

            return True, chat_title



        except UserAlreadyParticipantError:

            log_msg = f"⚠️ [{session_name}] Уже состоит в чате/группе"

            print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")

            await add_to_log_buffer(log_msg)

            return True, "Уже участник"



    except FloodWaitError as e:

        wait_time = e.seconds

        log_msg = f"⏳ [{session_name}] Telegram требует паузу! Ожидание {wait_time} секунд..."

        print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)



        if wait_time > 60:

            minutes = wait_time // 60

            seconds = wait_time % 60

            log_msg = f"⏳ Это примерно {minutes} минут {seconds} секунд"

            print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")

            await add_to_log_buffer(log_msg)



        for remaining in range(wait_time, 0, -1):

            if stop_event.is_set():

                print(f"\n{Fore.YELLOW}🛑 Остановлено пользователем во время ожидания{Style.RESET_ALL}")

                return False, "Остановлено"



            if remaining % 10 == 0 or remaining < 10:

                if remaining > 60:

                    mins = remaining // 60

                    secs = remaining % 60

                    print(f"{Fore.YELLOW}⏳ Осталось: {mins} мин {secs} сек...{Style.RESET_ALL}")

                else:

                    print(f"{Fore.YELLOW}⏳ Осталось: {remaining} сек...{Style.RESET_ALL}")



            await asyncio.sleep(1)



        log_msg = f"⏳ Пауза закончена, продолжаем..."

        print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)

        return await join_chat_safely(client, link, session_name)



    except InviteHashExpiredError:

        log_msg = f"✘ [{session_name}] Ссылка-приглашение истекла: {link[:50]}..."

        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)

        return False, "Ссылка истекла"



    except InviteHashInvalidError:

        log_msg = f"✘ [{session_name}] Недействительная ссылка-приглашение: {link[:50]}..."

        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)

        return False, "Недействительная ссылка"



    except ChannelPrivateError:

        log_msg = f"✘ [{session_name}] Канал/группа приватный/закрытый: {link[:50]}..."

        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)

        return False, "Приватный канал"



    except ValueError as e:

        if "Cannot find any entity" in str(e):

            log_msg = f"✘ [{session_name}] Не удалось найти чат/группу по ссылке: {link[:50]}..."

            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

            await add_to_log_buffer(log_msg)

        else:

            log_msg = f"✘ [{session_name}] Ошибка: {e}"

            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

            await add_to_log_buffer(log_msg)

        return False, str(e)[:50]



    except Exception as e:

        error_msg = str(e)[:50]

        log_msg = f"✘ [{session_name}] Ошибка при вступлении в {link[:50]}...: {error_msg}"

        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)

        return False, error_msg





async def process_account_join(session_file, api_id, api_hash, join_links, delay_between_joins=5):

    """Обрабатывает вступление для одного аккаунта."""

    client_session_name = os.path.join(session_folder, session_file.replace('.session', ''))

    client = TelegramClient(

        client_session_name, api_id, api_hash,

        connection_retries=5, timeout=20, request_retries=3, flood_sleep_threshold=60

    )



    joined_count = 0

    failed_count = 0

    already_joined_count = 0

    flood_pause_count = 0

    account_info = "неавторизована"



    try:

        await client.connect()



        if not await client.is_user_authorized():

            log_msg = f"✘ [{session_file}] НЕ АВТОРИЗОВАНА - ПРОПУЩЕНА"

            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

            await add_to_log_buffer(log_msg)

            log_invalid_session(session_file)

            return 0, 0, 0, 0, False



        try:

            me = await client.get_me()

            account_info = f"@{me.username or me.id}"

        except Exception as get_me_error:

            log_msg = f"✘ [{session_file}] Ошибка при получении информации о пользователе: {get_me_error}"

            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

            await add_to_log_buffer(log_msg)

            log_invalid_session(session_file)

            return 0, 0, 0, 0, False



        log_msg = f"\n⚙ Обработка сессии: {session_file} ({account_info})"

        print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)



        log_msg = f"ℹ Всего ссылок для входа: {len(join_links)}"

        print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)



        for i, link in enumerate(join_links, 1):

            if stop_event.is_set():

                print("\n" + Fore.YELLOW + "🛑 Остановлено пользователем" + Style.RESET_ALL)

                break



            log_msg = f"[{account_info}] [{i}/{len(join_links)}] Вступление по ссылке: {link[:50]}..."

            print(log_msg)

            await add_to_log_buffer(log_msg)



            success, result = await join_chat_safely(client, link, account_info)



            if success:

                if result == "Уже участник":

                    already_joined_count += 1

                else:

                    joined_count += 1

            else:

                failed_count += 1



            if "FloodWait" in result or "пауза" in str(result).lower():

                flood_pause_count += 1



            if i < len(join_links):

                await asyncio.sleep(delay_between_joins)



    except Exception as e:

        log_msg = f"✘ [{session_file}] {str(e)[:60]}"

        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)

        traceback.print_exc()

    finally:

        try:

            if client.is_connected():

                await client.disconnect()

        except:

            pass



    log_msg = f"\n--- ИТОГ {session_file} ({account_info}) ---"

    print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")

    await add_to_log_buffer(log_msg)



    log_msg = f"✔ Вступил: {joined_count}"

    print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")

    await add_to_log_buffer(log_msg)



    log_msg = f"⚠️ Уже состоял: {already_joined_count}"

    print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")

    await add_to_log_buffer(log_msg)



    log_msg = f"✘ Ошибок: {failed_count}"

    print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

    await add_to_log_buffer(log_msg)



    if flood_pause_count > 0:

        log_msg = f"⏳ Пауз из-за флуда: {flood_pause_count}"

        print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)



    log_msg = "-------------------------------------"

    print(log_msg)

    await add_to_log_buffer(log_msg)



    return joined_count, failed_count, already_joined_count, flood_pause_count, True





async def run_join_broadcast(api_id, api_hash, session_files, join_links):

    """Запускает вступление в группы для нескольких аккаунтов."""

    print("\n" + Fore.MAGENTA + "--- Запуск вступления в группы ---" + Style.RESET_ALL)

    print(f"Сессий: {len(session_files)}")

    print(f"Ссылок для входа: {len(join_links)}")

    print(f"Задержка между вступлениями: 5 сек")

    print("---")



    tasks = []

    processed_session_files = []



    for i, session_file in enumerate(session_files):

        if stop_event.is_set():

            break

        task = asyncio.create_task(

            process_account_join(

                session_file, api_id, api_hash,

                join_links, delay_between_joins=5

            )

        )

        tasks.append(task)

        processed_session_files.append(session_file)

        if i < len(session_files) - 1:

            await asyncio.sleep(delay_between_accounts)



    if tasks:

        results = await asyncio.gather(*tasks)



        total_joined = 0

        total_failed = 0

        total_already = 0

        total_flood_pauses = 0

        working_sessions = 0



        for i, result in enumerate(results):

            if result is None:

                continue

            try:

                joined, failed, already, flood_pauses, authorized = result

                total_joined += joined

                total_failed += failed

                total_already += already

                total_flood_pauses += flood_pauses

                if authorized:

                    working_sessions += 1

            except Exception as res_err:

                print(

                    f"\n" + Fore.RED + f"✘ Ошибка обработки результата для {processed_session_files[i]}: {res_err}" + Style.RESET_ALL)



        print("\n" + "=" * 50)

        print(f"{Fore.MAGENTA}     ✔ ОБЩАЯ СТАТИСТИКА ВСТУПЛЕНИЙ")

        print("=" * 50)

        print(f"{Fore.GREEN}✔ Всего вступили: {total_joined}")

        print(f"{Fore.YELLOW}⚠️ Уже состояли: {total_already}")

        print(f"{Fore.RED}✘ Всего ошибок: {total_failed}")

        if total_flood_pauses > 0:

            print(f"{Fore.YELLOW}⏳ Всего пауз из-за флуда: {total_flood_pauses}")

        print(f"{Fore.GREEN}✔ Работало сессий: {working_sessions}/{len(processed_session_files)}")

        print("=" * 50)



    print(Fore.MAGENTA + "--- Вступление в группы завершено ---" + Style.RESET_ALL)





async def process_account(session_file, api_id, api_hash, message, max_messages, delete_after, use_media_flag,

                          media_file_path, recipient_filter, fast_mode_flag, fast_delay_val, target_chats_ids=None):

    """Обрабатывает рассылку для одного аккаунта."""

    client_session_name = os.path.join(session_folder, session_file.replace('.session', ''))

    client = TelegramClient(

        client_session_name, api_id, api_hash,

        connection_retries=5, timeout=20, request_retries=3, flood_sleep_threshold=60

    )



    sent_count = 0

    skipped_count = 0

    deleted_count = 0

    total_chats_processed = 0

    authorized = False

    account_info = "неавторизована"



    try:

        await client.connect()



        if not await client.is_user_authorized():

            log_msg = f"✘ [{session_file}] НЕ АВТОРИЗОВАНА - ПРОПУЩЕНА"

            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

            await add_to_log_buffer(log_msg)

            log_invalid_session(session_file)

            return 0, 0, 0, 0, False



        try:

            me = await client.get_me()

            authorized = True

            account_info = f"@{me.username or me.id}"

        except Exception as get_me_error:

            log_msg = f"✘ [{session_file}] Ошибка при получении информации о пользователе: {get_me_error}"

            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

            await add_to_log_buffer(log_msg)

            log_invalid_session(session_file)

            return 0, 0, 0, 0, False



        log_msg = f"\n⚙ Обработка сессии: {session_file} ({account_info})"

        print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)



        if fast_mode_flag:

            log_msg = f"⚡ БЫСТРЫЙ РЕЖИМ: задержка {fast_delay_val}с"

            print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")

            await add_to_log_buffer(log_msg)



        chats_to_process = []



        if target_chats_ids:

            log_msg = f"ℹ Рассылка по целям из файла ({len(target_chats_ids)} шт.)"

            print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")

            await add_to_log_buffer(log_msg)



            for target in target_chats_ids:

                if stop_event.is_set():

                    break



                if isinstance(target, str):

                    result, result_type = await get_chat_from_link(client, target, account_info)



                    if result_type == "folder" and isinstance(result, list):

                        log_msg = f"✔ [{account_info}] Получено {len(result)} чатов из папки"

                        print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")

                        await add_to_log_buffer(log_msg)



                        for chat in result:

                            if chat not in chats_to_process:

                                chats_to_process.append(chat)

                    elif result_type == "folder_empty":

                        log_msg = f"⚠️ [{account_info}] Папка обработана, но чаты не получены"

                        print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")

                        await add_to_log_buffer(log_msg)

                    elif result_type == "chat" and result:

                        if result not in chats_to_process:

                            chats_to_process.append(result)

                else:

                    try:

                        entity = await client.get_entity(target)

                        if entity not in chats_to_process:

                            chats_to_process.append(entity)

                    except ValueError:

                        log_msg = f"✘ Не удалось получить информацию о группе по ID: {target}"

                        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

                        await add_to_log_buffer(log_msg)

                    except Exception as e:

                        log_msg = f"✘ Ошибка при получении группы {target}: {e}"

                        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

                        await add_to_log_buffer(log_msg)



            if not chats_to_process:

                log_msg = f"⚠️ [{account_info}] Не найдены доступные чаты для рассылки по списку!"

                print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")

                await add_to_log_buffer(log_msg)

                return 0, 0, 0, 0, True

        else:

            chats_to_process = await get_user_chats(client, recipient_filter)

            if not chats_to_process:

                filter_names = {"all": "чатов", "users": "личных чатов", "groups": "групп"}

                log_msg = f"⚠️ [{account_info}] Нет доступных {filter_names[recipient_filter]}!"

                print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")

                await add_to_log_buffer(log_msg)

                return 0, 0, 0, 0, True



        total_chats_processed = len(chats_to_process)

        log_msg = f"ℹ [{account_info}] Всего чатов для обработки: {total_chats_processed}"

        print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)



        for i, chat in enumerate(chats_to_process, 1):

            if stop_event.is_set():

                print("\n" + Fore.YELLOW + "🛑 Остановлено пользователем" + Style.RESET_ALL)

                break



            chat_title = getattr(chat, 'title', f"чат ID {chat.id}")

            if isinstance(chat, User):

                chat_title = f"{chat.first_name or ''} {chat.last_name or ''}".strip() or f"пользователь {chat.id}"



            log_msg = f"[{account_info}] [{i}/{len(chats_to_process)}] '{chat_title[:30].strip()}...'"

            print(log_msg)

            await add_to_log_buffer(log_msg)



            current_time = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]



            media_to_use = media_file_path if use_media_flag and media_file_path and os.path.exists(

                media_file_path) else None

            success, sent_message = await send_message_safely(client, chat, message, delete_after, media_to_use)



            if success:

                sent_count += 1

                log_msg = f"✔ ({current_time}) Отправлено!"

                print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")

                await add_to_log_buffer(log_msg)

                if delete_after:

                    deleted_count += 1

            else:

                skipped_count += 1

                log_msg = f"✘ ({current_time}) Пропущено (нет доступа)"

                print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

                await add_to_log_buffer(log_msg)



            if sent_count >= max_messages:

                log_msg = f"✔ Достигнут лимит: {max_messages} сообщений"

                print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")

                await add_to_log_buffer(log_msg)

                break



            if i < len(chats_to_process):

                if fast_mode_flag:

                    await asyncio.sleep(fast_delay_val)

                else:

                    await asyncio.sleep(delay_between_messages)



    except asyncio.TimeoutError:

        log_msg = f"⏳ [{session_file}] Тайм-аут подключения"

        print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)

        log_invalid_session(session_file)

    except (AuthKeyUnregisteredError, PhoneNumberInvalidError):

        log_msg = f"✘ [{session_file}] Сессия недействительна"

        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)

        log_invalid_session(session_file)

    except (PhoneCodeInvalidError, SessionPasswordNeededError, PasswordHashInvalidError):

        log_msg = f"✘ [{session_file}] Нужен логин/пароль"

        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)

        log_invalid_session(session_file)

    except RPCError as e:

        log_msg = f"✘ [{session_file}] RPC Error: {e}"

        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)

        log_invalid_session(session_file)

    except Exception as e:

        log_msg = f"✘ [{session_file}] {str(e)[:60]}"

        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)

        traceback.print_exc()

        log_invalid_session(session_file)

    finally:

        try:

            if client.is_connected():

                await client.disconnect()

        except:

            pass



    log_msg = f"\n--- ИТОГ {session_file} ({account_info}) ---"

    print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")

    await add_to_log_buffer(log_msg)



    log_msg = f"✔ Отправлено: {sent_count}"

    print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")

    await add_to_log_buffer(log_msg)



    log_msg = f"✘ Пропущено: {skipped_count}"

    print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")

    await add_to_log_buffer(log_msg)



    if delete_after:

        log_msg = f"🗑 Удалено у себя: {deleted_count}"

        print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")

        await add_to_log_buffer(log_msg)



    log_msg = f"ℹ Всего обработано: {total_chats_processed}"

    print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")

    await add_to_log_buffer(log_msg)



    log_msg = "-------------------------------------"

    print(log_msg)

    await add_to_log_buffer(log_msg)



    return sent_count, skipped_count, deleted_count, total_chats_processed, authorized





async def run_broadcast(api_id, api_hash, session_files, message, max_messages_per_account, repeat_broadcast_flag,

                        repeat_interval_val, delete_after, use_media_flag, media_file_path, recipient_filter,

                        fast_mode_flag, fast_delay_val, target_chats_ids=None, cycle_number=1):

    """Запускает рассылку для нескольких аккаунтов."""

    filter_names = {"all": "Все диалоги", "users": "Только личные чаты", "groups": "Только группы"}

    print("\n" + Fore.MAGENTA + "--- Запуск рассылки ---" + Style.RESET_ALL)

    print(f"Сообщение: '{message[:60]}...'")

    if use_media_flag and media_file_path and os.path.exists(media_file_path):

        print(f"{Fore.CYAN}🖼 Медиафайл: {os.path.basename(media_file_path)}")

    print(f"Сессий: {len(session_files)}")

    if target_chats_ids:

        total_targets = len(target_chats_ids)

        folder_count = sum(1 for t in target_chats_ids if isinstance(t, str) and 'addlist' in t)

        if folder_count > 0:

            print(

                f"{Fore.CYAN}● Цели: {total_targets} элементов (включая {folder_count} папок с группами){Style.RESET_ALL}")

        else:

            print(f"{Fore.CYAN}● Цели: {total_targets} групп/ссылок из файла{Style.RESET_ALL}")

    else:

        print(f"{Fore.CYAN}● Цели: {filter_names[recipient_filter]}")

    print(f"Макс. сообщений/аккаунт: {max_messages_per_account}")



    if fast_mode_flag:

        print(f"{Fore.YELLOW}⚡ РЕЖИМ СКОРОСТИ: БЫСТРЫЙ (задержка {fast_delay_val}с)")

    else:

        print(f"⏳ Задержка между сообщениями: {delay_between_messages}с")



    print(f"⏳ Задержка между аккаунтами: {delay_between_accounts}с")

    print(f"🔂 Повтор: {'ВКЛЮЧЕН' if repeat_broadcast_flag else 'ВЫКЛЮЧЕН'}")

    if repeat_broadcast_flag:

        print(f"⏱️ Интервал повтора: {repeat_interval_val}с")

    print(f"🗑 Удаление у себя: {'ВКЛЮЧЕНО' if delete_after else 'ВЫКЛЮЧЕНО'}")

    print("---")



    while True:

        if stop_event.is_set():

            break



        tasks = []

        processed_session_files = []



        for i, session_file in enumerate(session_files):

            if stop_event.is_set():

                break

            task = asyncio.create_task(

                process_account(

                    session_file, api_id, api_hash,

                    message, max_messages_per_account, delete_after, use_media_flag, media_file_path, recipient_filter,

                    fast_mode_flag, fast_delay_val,

                    target_chats_ids=target_chats_ids

                )

            )

            tasks.append(task)

            processed_session_files.append(session_file)

            if i < len(session_files) - 1:

                await asyncio.sleep(delay_between_accounts)



        if tasks:

            results = await asyncio.gather(*tasks)



            total_sent = 0

            total_skipped = 0

            total_deleted = 0

            total_chats = 0

            working_sessions = 0

            invalid_count = 0



            for i, result in enumerate(results):

                if result is None:

                    continue

                try:

                    sent, skipped, deleted, chats, authorized = result

                    total_sent += sent

                    total_skipped += skipped

                    total_deleted += deleted

                    total_chats += chats

                    if authorized:

                        working_sessions += 1

                    else:

                        invalid_count += 1

                except Exception as res_err:

                    print(

                        f"\n" + Fore.RED + f"✘ Ошибка обработки результата для {processed_session_files[i]}: {res_err}" + Style.RESET_ALL)



            print("\n" + "=" * 50)

            print(f"{Fore.MAGENTA}     ✔ ОБЩАЯ СТАТИСТИКА (ЦИКЛ {cycle_number})")

            print("=" * 50)

            print(f"{Fore.GREEN}✔ Всего отправлено: {total_sent}")

            print(f"{Fore.RED}✘ Всего пропущено: {total_skipped}")

            if delete_after:

                print(f"{Fore.CYAN}🗑 Всего удалено у себя: {total_deleted}")

            print(f"{Fore.CYAN}ℹ Всего чатов охвачено: {total_chats}")

            print(f"{Fore.GREEN}✔ Работало сессий: {working_sessions}/{len(processed_session_files)}")

            if invalid_count > 0:

                print(f"{Fore.RED}✘ Недействительных сессий: {invalid_count}")

            print("=" * 50)



            if notify_cycle_results:

                notification_message = f"📊 **Результаты цикла #{cycle_number}**\n\n"

                notification_message += f"✅ Отправлено: {total_sent}\n"

                notification_message += f"❌ Пропущено: {total_skipped}\n"

                if delete_after:

                    notification_message += f"🗑 Удалено у себя: {total_deleted}\n"

                notification_message += f"📝 Всего чатов: {total_chats}\n"

                notification_message += f"👥 Работало сессий: {working_sessions}/{len(processed_session_files)}\n"

                if invalid_count > 0:

                    notification_message += f"⚠️ Недействительных сессий: {invalid_count}\n"



                await send_notification(notification_message, "cycle_result")



            if notify_full_logs:

                await send_notification("", "full_log")

                async with log_buffer_lock:

                    log_buffer.clear()



        if repeat_broadcast_flag and not stop_event.is_set():

            print(f"\n{Fore.CYAN}ℹ Повтор рассылки через {repeat_interval_val} секунд...{Style.RESET_ALL}")

            for remaining in range(repeat_interval_val, 0, -1):

                if stop_event.is_set():

                    break

                if remaining % 10 == 0 or remaining <= 5:

                    print(f"{Fore.CYAN}⏳ До повтора: {remaining} сек...{Style.RESET_ALL}")

                await asyncio.sleep(1)

            cycle_number += 1

        else:

            break



    print(Fore.MAGENTA + "--- Рассылка завершена ---" + Style.RESET_ALL)





async def display_settings_menu():

    """Меню настроек."""

    global current_api_id, current_api_hash, session_folder, message_to_send, delay_between_messages, delay_between_accounts, max_messages_per_account, repeat_broadcast, repeat_interval, delete_after_send, recipient_type, use_media, media_path, fast_mode, fast_delay, notification_enabled, notification_bot_token, notification_chat_id, notify_invalid_session, notify_cycle_results, notify_full_logs



    while True:

        os.system('cls' if os.name == 'nt' else 'clear')

        print_header("⚙️ НАСТРОЙКИ ПАРАМЕТРОВ")



        print(f"{CLR_INFO}1. 🔑 API Настройки")

        print(f"{CLR_INFO}2. 📁 Настройки сессий")

        print(f"{CLR_INFO}3. ✉️ Настройки сообщений")

        print(f"{CLR_INFO}4. 🚀 Настройки рассылки")

        print(f"{CLR_INFO}5. 🔔 Настройки уведомлений")

        print(f"{CLR_ACCENT}6. ♻️ Сброс настроек")

        print(f"{CLR_ERR}0. 🔙 Назад в меню")



        print(f"\n{CLR_WARN}Текущие значения:{Style.RESET_ALL}")

        print(f"  API ID: {current_api_id}")

        print(f"  Папка сессий: {session_folder}")

        print(f"  Сообщение: {message_to_send[:30]}...")

        if notification_enabled:

            print(f"  🔔 Уведомления: ВКЛ")



        choice = input(f"\n{CLR_MAIN}Выберите раздел ➔ {RESET}").strip()



        if choice == '1':

            while True:

                os.system('cls' if os.name == 'nt' else 'clear')

                print_header("🔑 API НАСТРОЙКИ")

                print(f"{CLR_INFO}1. 🆔 API ID: {CLR_WARN}{current_api_id}")

                print(f"{CLR_INFO}2. 🔑 API Hash: {CLR_WARN}{current_api_hash[:10]}***")

                print(f"{CLR_ERR}0. 🔙 Назад")



                sub_choice = input(f"\n{CLR_MAIN}Выберите пункт ➔ {RESET}").strip()



                if sub_choice == '1':

                    new_api_id_str = input(f"API ID (текущий: {current_api_id}): ").strip()

                    if new_api_id_str.isdigit():

                        current_api_id = int(new_api_id_str)

                        print(f"{Fore.GREEN}✔ API ID обновлен.{Style.RESET_ALL}")

                    else:

                        print(f"{Fore.RED}✘ API ID должен быть числом.{Style.RESET_ALL}")

                elif sub_choice == '2':

                    new_api_hash = input("API Hash: ").strip()

                    if new_api_hash:

                        current_api_hash = new_api_hash

                        print(f"{Fore.GREEN}✔ API Hash обновлен.{Style.RESET_ALL}")

                elif sub_choice == '0':

                    break

                await asyncio.sleep(1)



        elif choice == '2':

            while True:

                os.system('cls' if os.name == 'nt' else 'clear')

                print_header("📁 НАСТРОЙКИ СЕССИЙ")

                print(f"{CLR_INFO}1. 📂 Папка сессий: {CLR_WARN}{session_folder}")

                print(

                    f"{CLR_INFO}2. 👥 Тип получателей: {CLR_WARN}{['Все диалоги', 'Только личные чаты', 'Только группы'][['all', 'users', 'groups'].index(recipient_type)]}")

                print(f"{CLR_ERR}0. 🔙 Назад")



                sub_choice = input(f"\n{CLR_MAIN}Выберите пункт ➔ {RESET}").strip()



                if sub_choice == '1':

                    new_folder = input(f"Папка сессий (текущая: '{session_folder}'): ").strip()

                    if new_folder:

                        session_folder = new_folder

                        os.makedirs(session_folder, exist_ok=True)

                        print(f"{Fore.GREEN}✔ Папка сессий обновлена.{Style.RESET_ALL}")

                elif sub_choice == '2':

                    print(f"\n{Fore.CYAN}Выберите тип получателей:")

                    print("1. Все диалоги")

                    print("2. Только личные чаты")

                    print("3. Только группы")

                    type_choice = input("Ваш выбор (1-3): ").strip()

                    if type_choice == '1':

                        recipient_type = "all"

                        print(f"{Fore.GREEN}✔ Тип получателей: Все диалоги{Style.RESET_ALL}")

                    elif type_choice == '2':

                        recipient_type = "users"

                        print(f"{Fore.GREEN}✔ Тип получателей: Только личные чаты{Style.RESET_ALL}")

                    elif type_choice == '3':

                        recipient_type = "groups"

                        print(f"{Fore.GREEN}✔ Тип получателей: Только группы{Style.RESET_ALL}")

                    else:

                        print(f"{Fore.RED}✘ Неверный выбор{Style.RESET_ALL}")

                elif sub_choice == '0':

                    break

                await asyncio.sleep(1)



        elif choice == '3':

            while True:

                os.system('cls' if os.name == 'nt' else 'clear')

                print_header("✉️ НАСТРОЙКИ СООБЩЕНИЙ")

                print(f"{CLR_INFO}1. ✉️ Текст сообщения: {CLR_WARN}{message_to_send[:40]}...")

                print(

                    f"{CLR_INFO}2. 🖼 Использовать медиа: {CLR_SUCCESS if use_media else CLR_ERR}{'ВКЛ' if use_media else 'ВЫКЛ'}")

                if use_media:

                    print(f"{CLR_INFO}3. 📁 Путь к медиафайлу: {CLR_WARN}{media_path or 'Не указан'}")

                print(

                    f"{CLR_INFO}4. 🗑 Удаление у себя: {CLR_SUCCESS if delete_after_send else CLR_ERR}{'ВКЛ' if delete_after_send else 'ВЫКЛ'}")

                print(f"{CLR_ERR}0. 🔙 Назад")



                sub_choice = input(f"\n{CLR_MAIN}Выберите пункт ➔ {RESET}").strip()



                if sub_choice == '1':

                    print(f"{Fore.YELLOW}✉ Текущее сообщение:")

                    print(f"---\n{message_to_send}\n---")

                    print("Введите новое сообщение (на новой строке, нажмите Enter дважды для сохранения):")

                    lines = []

                    while True:

                        try:

                            line = input()

                            if not line.strip() and lines:

                                break

                            elif not line.strip() and not lines:

                                print(f"{Fore.RED}✘ Сообщение не было изменено.{Style.RESET_ALL}")

                                break

                            lines.append(line)

                        except EOFError:

                            break

                    new_message = '\n'.join(lines)

                    if new_message.strip():

                        message_to_send = new_message

                        print(f"{Fore.GREEN}✔ Сообщение обновлено.{Style.RESET_ALL}")

                elif sub_choice == '2':

                    use_media = not use_media

                    print(

                        f"{Fore.GREEN}✔ Использование медиа {'включено' if use_media else 'выключено'}.{Style.RESET_ALL}")

                    if use_media and not media_path:

                        print(f"{Fore.YELLOW}⚠️ Укажите путь к медиафайлу в пункте 3.{Style.RESET_ALL}")

                elif sub_choice == '3' and use_media:

                    new_media_path = input(f"Путь к медиафайлу (текущий: {media_path}): ").strip()

                    if new_media_path:

                        if os.path.exists(new_media_path):

                            media_path = new_media_path

                            print(f"{Fore.GREEN}✔ Путь к медиафайлу обновлен.{Style.RESET_ALL}")

                        else:

                            print(f"{Fore.RED}✘ Файл не найден!{Style.RESET_ALL}")

                elif sub_choice == '4':

                    delete_after_send = not delete_after_send

                    print(

                        f"{Fore.GREEN}✔ Удаление у себя {'включено' if delete_after_send else 'выключено'}.{Style.RESET_ALL}")

                elif sub_choice == '0':

                    break

                await asyncio.sleep(1)



        elif choice == '4':

            while True:

                os.system('cls' if os.name == 'nt' else 'clear')

                print_header("🚀 НАСТРОЙКИ РАССЫЛКИ")

                print(f"{CLR_INFO}1. ⏲️ Задержка между смс (обычный режим): {CLR_WARN}{delay_between_messages}с")

                print(f"{CLR_INFO}2. ⏲️ Задержка между аккаунтами: {CLR_WARN}{delay_between_accounts}с")

                print(f"{CLR_INFO}3. 📊 Лимит сообщений на аккаунт: {CLR_WARN}{max_messages_per_account}")

                print(

                    f"{CLR_INFO}4. 🔄 Цикличная рассылка: {CLR_SUCCESS if repeat_broadcast else CLR_ERR}{'ВКЛ' if repeat_broadcast else 'ВЫКЛ'}")

                if repeat_broadcast:

                    print(f"{CLR_INFO}5. ⏱️ Интервал повтора: {CLR_WARN}{repeat_interval}с")

                print(

                    f"{CLR_INFO}6. ⚡ Быстрый режим (задержка < 1с): {CLR_SUCCESS if fast_mode else CLR_ERR}{'ВКЛ' if fast_mode else 'ВЫКЛ'}")

                if fast_mode:

                    print(f"{CLR_INFO}7. ⏱️ Задержка в быстром режиме: {CLR_WARN}{fast_delay}с")

                print(f"{CLR_ERR}0. 🔙 Назад")



                sub_choice = input(f"\n{CLR_MAIN}Выберите пункт ➔ {RESET}").strip()



                if sub_choice == '1':

                    new_delay_str = input(f"Задержка сообщений (сек, текущая: {delay_between_messages}): ").strip()

                    try:

                        delay_between_messages = max(0, int(new_delay_str))

                        print(f"{Fore.GREEN}✔ Задержка обновлена.{Style.RESET_ALL}")

                    except ValueError:

                        print(f"{Fore.RED}✘ Введите число.{Style.RESET_ALL}")

                elif sub_choice == '2':

                    new_delay_str = input(f"Задержка аккаунтов (сек, текущая: {delay_between_accounts}): ").strip()

                    try:

                        delay_between_accounts = max(0, int(new_delay_str))

                        print(f"{Fore.GREEN}✔ Задержка обновлена.{Style.RESET_ALL}")

                    except ValueError:

                        print(f"{Fore.RED}✘ Введите число.{Style.RESET_ALL}")

                elif sub_choice == '3':

                    new_max_str = input(f"Макс. сообщений/аккаунт (текущий: {max_messages_per_account}): ").strip()

                    try:

                        max_messages_per_account = max(1, int(new_max_str))

                        print(f"{Fore.GREEN}✔ Лимит обновлен.{Style.RESET_ALL}")

                    except ValueError:

                        print(f"{Fore.RED}✘ Введите число больше 0.{Style.RESET_ALL}")

                elif sub_choice == '4':

                    repeat_broadcast = not repeat_broadcast

                    print(

                        f"{Fore.GREEN}✔ Повтор рассылки {'включен' if repeat_broadcast else 'выключен'}.{Style.RESET_ALL}")

                elif sub_choice == '5' and repeat_broadcast:

                    new_interval_str = input(f"Интервал повтора (сек, текущий: {repeat_interval}): ").strip()

                    try:

                        repeat_interval = max(1, int(new_interval_str))

                        print(f"{Fore.GREEN}✔ Интервал повтора обновлен.{Style.RESET_ALL}")

                    except ValueError:

                        print(f"{Fore.RED}✘ Введите число больше 0.{Style.RESET_ALL}")

                elif sub_choice == '6':

                    fast_mode = not fast_mode

                    print(f"{Fore.GREEN}✔ Быстрый режим {'включен' if fast_mode else 'выключен'}.{Style.RESET_ALL}")

                elif sub_choice == '7' and fast_mode:

                    new_delay_str = input(f"Задержка в быстром режиме (0.1-0.9, текущая: {fast_delay}): ").strip()

                    try:

                        new_delay = float(new_delay_str)

                        if 0.1 <= new_delay <= 0.9:

                            fast_delay = new_delay

                            print(f"{Fore.GREEN}✔ Задержка в быстром режиме обновлена.{Style.RESET_ALL}")

                        else:

                            print(f"{Fore.RED}✘ Введите число от 0.1 до 0.9.{Style.RESET_ALL}")

                    except ValueError:

                        print(f"{Fore.RED}✘ Введите число (например, 0.3).{Style.RESET_ALL}")

                elif sub_choice == '0':

                    break

                await asyncio.sleep(1)



        elif choice == '5':

            while True:

                os.system('cls' if os.name == 'nt' else 'clear')

                print_header("🔔 НАСТРОЙКИ УВЕДОМЛЕНИЙ")

                print(

                    f"{CLR_INFO}1. 🔔 Уведомления: {CLR_SUCCESS if notification_enabled else CLR_ERR}{'ВКЛ' if notification_enabled else 'ВЫКЛ'}")

                if notification_enabled:

                    print(

                        f"{CLR_INFO}2. 🤖 Токен бота: {CLR_WARN}{notification_bot_token[:15] if notification_bot_token else 'Не указан'}...")

                    print(f"{CLR_INFO}3. 👤 Chat ID: {CLR_WARN}{notification_chat_id or 'Не указан'}")

                    print(

                        f"{CLR_INFO}4. ⚠️ Невалидные сессии: {CLR_SUCCESS if notify_invalid_session else CLR_ERR}{'ВКЛ' if notify_invalid_session else 'ВЫКЛ'}")

                    print(

                        f"{CLR_INFO}5. 📊 Результаты циклов: {CLR_SUCCESS if notify_cycle_results else CLR_ERR}{'ВКЛ' if notify_cycle_results else 'ВЫКЛ'}")

                    print(

                        f"{CLR_INFO}6. 📋 Полные логи: {CLR_SUCCESS if notify_full_logs else CLR_ERR}{'ВКЛ' if notify_full_logs else 'ВЫКЛ'}")

                print(f"{CLR_ERR}0. 🔙 Назад")



                sub_choice = input(f"\n{CLR_MAIN}Выберите пункт ➔ {RESET}").strip()



                if sub_choice == '1':

                    notification_enabled = not notification_enabled

                    print(

                        f"{Fore.GREEN}✔ Уведомления {'включены' if notification_enabled else 'выключены'}.{Style.RESET_ALL}")

                    if notification_enabled:

                        await init_notification_client()

                    else:

                        await close_notification_client()

                elif sub_choice == '2' and notification_enabled:

                    new_token = input("Токен бота (получить у @BotFather): ").strip()

                    if new_token:

                        notification_bot_token = new_token

                        print(f"{Fore.GREEN}✔ Токен бота обновлен.{Style.RESET_ALL}")

                        await init_notification_client()

                elif sub_choice == '3' and notification_enabled:

                    new_chat_id = input("Chat ID (можно узнать у @userinfobot): ").strip()

                    if new_chat_id:

                        notification_chat_id = new_chat_id

                        print(f"{Fore.GREEN}✔ Chat ID обновлен.{Style.RESET_ALL}")

                elif sub_choice == '4' and notification_enabled:

                    notify_invalid_session = not notify_invalid_session

                    print(

                        f"{Fore.GREEN}✔ Уведомления о невалидных сессиях {'включены' if notify_invalid_session else 'выключены'}.{Style.RESET_ALL}")

                elif sub_choice == '5' and notification_enabled:

                    notify_cycle_results = not notify_cycle_results

                    print(

                        f"{Fore.GREEN}✔ Уведомления о результатах циклов {'включены' if notify_cycle_results else 'выключены'}.{Style.RESET_ALL}")

                elif sub_choice == '6' and notification_enabled:

                    notify_full_logs = not notify_full_logs

                    print(

                        f"{Fore.GREEN}✔ Отправка полных логов {'включена' if notify_full_logs else 'выключена'}.{Style.RESET_ALL}")

                elif sub_choice == '0':

                    break

                await asyncio.sleep(1)



        elif choice == '6':

            if input(f"{Fore.YELLOW}⚠️ Сбросить ВСЕ настройки к умолчанию? (y/n): ").lower() == 'y':

                globals().update({

                    'current_api_id': DEFAULT_API_ID,

                    'current_api_hash': DEFAULT_API_HASH,

                    'session_folder': DEFAULT_SESSION_FOLDER,

                    'message_to_send': DEFAULT_MESSAGE,

                    'delay_between_messages': DEFAULT_DELAY_BETWEEN_MESSAGES,

                    'delay_between_accounts': DEFAULT_DELAY_BETWEEN_ACCOUNTS,

                    'max_messages_per_account': DEFAULT_MAX_MESSAGES_PER_ACCOUNT,

                    'repeat_broadcast': DEFAULT_REPEAT_BROADCAST,

                    'repeat_interval': DEFAULT_REPEAT_INTERVAL,

                    'delete_after_send': DEFAULT_DELETE_AFTER_SEND,

                    'recipient_type': DEFAULT_RECIPIENT_TYPE,

                    'use_media': DEFAULT_USE_MEDIA,

                    'media_path': DEFAULT_MEDIA_PATH,

                    'fast_mode': DEFAULT_FAST_MODE,

                    'fast_delay': DEFAULT_FAST_DELAY,

                    'notification_enabled': DEFAULT_NOTIFICATION_ENABLED,

                    'notification_bot_token': DEFAULT_NOTIFICATION_BOT_TOKEN,

                    'notification_chat_id': DEFAULT_NOTIFICATION_CHAT_ID,

                    'notify_invalid_session': DEFAULT_NOTIFY_INVALID_SESSION,

                    'notify_cycle_results': DEFAULT_NOTIFY_CYCLE_RESULTS,

                    'notify_full_logs': DEFAULT_NOTIFY_FULL_LOGS

                })

                print(f"{Fore.GREEN}✔ Все настройки сброшены!{Style.RESET_ALL}")

                await close_notification_client()



        elif choice == '0':

            save_config()

            break

        else:

            print(f"{Fore.RED}✘ Некорректный выбор.{Style.RESET_ALL}")

        await asyncio.sleep(1)





async def add_session_by_number():

    """Добавляет новую сессию Telegram по номеру телефона."""

    print("\n" + Fore.MAGENTA + "--- Добавление сессии по номеру ---" + Style.RESET_ALL)

    phone_number = input("1. Введите номер телефона (с кодом страны, например, +79991234567): ").strip()



    if not phone_number:

        print(f"{Fore.RED}✘ Номер телефона не введен. Попробуйте снова.{Style.RESET_ALL}")

        return



    session_name = input("2. Введите название для сессии (например, my_session): ").strip()

    if not session_name:

        print(f"{Fore.RED}✘ Название сессии не введено. Попробуйте снова.{Style.RESET_ALL}")

        return



    session_filename = f"{session_name}.session"

    session_path_base = os.path.join(session_folder, session_name)



    if os.path.exists(session_path_base + ".session"):

        if input(

                f"{Fore.YELLOW}⚠️ Файл сессии '{session_filename}' уже существует. Перезаписать? (y/n): ").lower() != 'y':

            print(f"{Fore.RED}✘ Добавление сессии отменено.{Style.RESET_ALL}")

            return

        else:

            print(f"{Fore.CYAN}✔ Перезаписываем существующий файл сессии...{Style.RESET_ALL}")



    auth_client = TelegramClient(

        session_path_base, api_id=current_api_id, api_hash=current_api_hash,

        connection_retries=3, timeout=15

    )



    try:

        await auth_client.connect()

        if await auth_client.is_user_authorized():

            print(f"{Fore.YELLOW}⚠️ Сессия '{session_name}' уже активна. Пропускаем авторизацию.{Style.RESET_ALL}")

            return



        await auth_client.send_code_request(phone_number)

        print(f"{Fore.GREEN}✔ Код запроса отправлен на номер {phone_number}.{Style.RESET_ALL}")



        tg_code = input("3. Введите код подтверждения из Telegram: ").strip()

        if not tg_code:

            print(f"{Fore.RED}✘ Код подтверждения не введен. Попробуйте снова.{Style.RESET_ALL}")

            return



        print(f"{Fore.CYAN}✔ Попытка входа с кодом...{Style.RESET_ALL}")

        await auth_client.sign_in(phone_number, tg_code)



        try:

            await auth_client.get_me()

            print(

                f"{Fore.GREEN}✔ Сессия '{session_name}' успешно добавлена и сохранена в файле: {session_path_base}.session{Style.RESET_ALL}")

        except SessionPasswordNeededError:

            password = input("Введите ваш пароль двухфакторной аутентификации: ").strip()

            await auth_client.sign_in(password=password)

            await auth_client.get_me()

            print(

                f"{Fore.GREEN}✔ Сессия '{session_name}' успешно добавлена и сохранена в файле: {session_path_base}.session{Style.RESET_ALL}")



    except PhoneCodeInvalidError:

        print(f"{Fore.RED}✘ Неверный код подтверждения из Telegram.{Style.RESET_ALL}")

    except PhoneNumberInvalidError:

        print(f"{Fore.RED}✘ Неверный формат номера телефона.{Style.RESET_ALL}")

    except PasswordHashInvalidError:

        print(f"{Fore.RED}✘ Неверный пароль двухфакторной аутентификации.{Style.RESET_ALL}")

    except FloodWaitError as e:

        print(f"{Fore.RED}✘ Слишком много запросов. Повторите через {e.seconds} секунд.{Style.RESET_ALL}")

    except Exception as e:

        print(f"{Fore.RED}✘ Произошла непредвиденная ошибка: {e}{Style.RESET_ALL}")

        traceback.print_exc()

    finally:

        if auth_client.is_connected():

            await auth_client.disconnect()





async def main_menu():

    """Главное меню программы."""

    global CURRENT_VERSION



    load_config()

    os.makedirs(session_folder, exist_ok=True)



    # Проверка обновлений при запуске

    if AUTO_UPDATE:

        asyncio.create_task(update_manager.check_for_updates())



    if notification_enabled:

        await init_notification_client()



    if os.path.exists(invalid_session_log_file):

        try:

            os.remove(invalid_session_log_file)

            print(f"{Fore.GREEN}✔ Файл '{invalid_session_log_file}' был очищен.{Style.RESET_ALL}")

        except Exception as e:

            print(f"{Fore.RED}✘ Не удалось очистить файл '{invalid_session_log_file}': {e}{Style.RESET_ALL}")



    while True:

        os.system('cls' if os.name == 'nt' else 'clear')

        print(f"{CLR_ACCENT}╔═══════════════════════════════════════════════════╗")

        print(f"{CLR_ACCENT}║{CLR_MAIN}     🚀  LITEGAMMA TOOLS  |  FULL VERSION          {CLR_ACCENT}║")

        print(f"{CLR_ACCENT}║{CLR_INFO}       С уважением : @BananaStorebot_bot           {CLR_ACCENT}║")

        print(f"{CLR_ACCENT}╚═══════════════════════════════════════════════════╝")



        print(f"\n{CLR_SUCCESS}  [1] ➔  🚀 ЗАПУСТИТЬ РАССЫЛКУ")

        print(f"{CLR_SUCCESS}  [2] ➔  🔗 ВСТУПИТЬ В ГРУППЫ (из enter.json)")

        print(f"{CLR_MAIN}  [3] ➔  ⚙️  НАСТРОЙКИ СИСТЕМЫ")

        print(f"{CLR_INFO}  [4] ➔  📂  МОИ СЕССИИ (ИНФО)")

        print(f"{CLR_ACCENT}  [5] ➔  ➕  ДОБАВИТЬ АККАУНТ")

        print(f"{CLR_ACCENT}  [6] ➔  🔄  ОБНОВЛЕНИЯ")

        print(f"{CLR_ERR}  [7] ➔  🚪  ВЫЙТИ")



        print(f"\n{CLR_ACCENT}─────────────────────────────────────────────────────")



        if fast_mode:

            print(f"{Fore.YELLOW}⚡ ТЕКУЩИЙ РЕЖИМ: БЫСТРЫЙ (задержка {fast_delay}с){Style.RESET_ALL}")

        if repeat_broadcast:

            print(f"{Fore.CYAN}🔄 ПОВТОР ВКЛЮЧЕН (интервал {repeat_interval}с){Style.RESET_ALL}")

        if notification_enabled:

            print(f"{Fore.GREEN}🔔 УВЕДОМЛЕНИЯ ВКЛЮЧЕНЫ{Style.RESET_ALL}")

        print(f"{Fore.CYAN}📦 Текущая версия: {CURRENT_VERSION}{Style.RESET_ALL}")



        choice = input(f"{CLR_MAIN}Введите номер команды ➔ {RESET}").strip()



        if choice == '1':

            if current_api_id == DEFAULT_API_ID or not current_api_hash or current_api_hash == "ЗАМЕНИТЕ НА ВАШ API HASH, ТАКЖЕ НАСТРОЙТЕ API ID ":

                print(

                    "\n" + Fore.YELLOW + "[!] ВНИМАНИЕ: Настройте API ID и API Hash в меню '3. Настройки'" + Style.RESET_ALL)

                input("Нажмите Enter...")

                continue



            session_files = [f for f in os.listdir(session_folder) if f.endswith('.session')]

            if not session_files:

                print(f"\n{Fore.RED}✘ Не найдены .session файлы в '{session_folder}'")

                print("1. Авторизуйтесь через TelegramClient (создаст файл)")

                print("2. Поместите .session файлы в папку")

                input("Нажмите Enter...")

                continue



            print(f"\n{Fore.GREEN}✔ Найдено {len(session_files)} сессий:")

            for i, f in enumerate(session_files):

                print(f"{i + 1}. {f}")



            print(f"\n{Fore.CYAN}● Режим работы:")

            print("1. 1️⃣ Одна сессия")

            print("2. 🔢 Несколько сессий")

            print("3. ♾️ Все сессии")

            print("4. 📂 Группы из файла (group.json) - поддержка ссылок на группы и папки")

            print("0. Назад")



            sub_choice = input("Выберите: ").strip()

            selected_sessions = []

            target_groups_file_data = None



            if sub_choice == '1':

                selected_sessions = session_files[:1]

            elif sub_choice == '2':

                indices_str = input("Сессии через запятую (1,3,5): ").strip()

                try:

                    nums = [int(x.strip()) - 1 for x in indices_str.split(',') if x.strip()]

                    selected_sessions = [session_files[i] for i in nums if 0 <= i < len(session_files)]

                    if not selected_sessions:

                        print(

                            f"{Fore.YELLOW}⚠️ Не выбрано ни одной сессии. Будет использована первая.{Style.RESET_ALL}")

                        selected_sessions = session_files[:1]

                except ValueError:

                    print(f"{Fore.RED}✘ Некорректный ввод. Будет использована первая сессия.{Style.RESET_ALL}")

                    selected_sessions = session_files[:1]

            elif sub_choice == '3':

                selected_sessions = session_files

            elif sub_choice == '4':

                target_groups_file_data = load_target_groups()

                if target_groups_file_data is None:

                    print(f"{Fore.RED}✘ Не удалось загрузить группы из файла. Возврат в меню.{Style.RESET_ALL}")

                    continue



                folder_links = [t for t in target_groups_file_data if isinstance(t, str) and 'addlist' in t]

                if folder_links:

                    print(

                        f"{Fore.CYAN}ℹ Обнаружены ссылки на папки с группами: {len(folder_links)} шт.{Style.RESET_ALL}")



                print("\nВыберите сессии, из которых будет производиться рассылка по указанным группам:")

                print("1. 1️⃣ Одна сессия")

                print("2. 🔢 Несколько сессий")

                print("3. ♾️ Все сессии")

                print("0. Назад")

                session_choice_for_groups = input("Выберите: ").strip()



                if session_choice_for_groups == '1':

                    selected_sessions = session_files[:1]

                elif session_choice_for_groups == '2':

                    indices_str = input("Сессии через запятую (1,3,5): ").strip()

                    try:

                        nums = [int(x.strip()) - 1 for x in indices_str.split(',') if x.strip()]

                        selected_sessions = [session_files[i] for i in nums if 0 <= i < len(session_files)]

                        if not selected_sessions:

                            print(

                                f"{Fore.YELLOW}⚠️ Не выбрано ни одной сессии. Будет использована первая.{Style.RESET_ALL}")

                            selected_sessions = session_files[:1]

                    except ValueError:

                        print(f"{Fore.RED}✘ Некорректный ввод. Будет использована первая сессия.{Style.RESET_ALL}")

                        selected_sessions = session_files[:1]

                elif session_choice_for_groups == '3':

                    selected_sessions = session_files

                else:

                    continue

            else:

                continue



            if not selected_sessions:

                print(f"{Fore.RED}✘ Ошибка выбора сессии. Возврат в меню.{Style.RESET_ALL}")

                await asyncio.sleep(2)

                continue



            recipient_names = {"all": "Все диалоги", "users": "Только личные чаты", "groups": "Только группы"}

            print(f"\n{Fore.CYAN}ℹ Параметры:")

            if target_groups_file_data is not None:

                folder_count = sum(1 for t in target_groups_file_data if isinstance(t, str) and 'addlist' in t)

                if folder_count > 0:

                    print(

                        f"{Fore.CYAN}● Цели: {len(target_groups_file_data)} элементов (включая {folder_count} папок с группами){Style.RESET_ALL}")

                else:

                    print(f"{Fore.CYAN}● Цели: {len(target_groups_file_data)} групп/ссылок из файла{Style.RESET_ALL}")

            else:

                print(f"{Fore.CYAN}● Цели: {recipient_names[recipient_type]}")

            if use_media and media_path and os.path.exists(media_path):

                print(f"{Fore.CYAN}🖼 Медиафайл: {os.path.basename(media_path)}")

            print(f"🔢 Макс./аккаунт: {max_messages_per_account}")



            if fast_mode:

                print(f"{Fore.YELLOW}⚡ Режим: БЫСТРЫЙ (задержка {fast_delay}с)")

            else:

                print(f"⏳ Между чатами: {delay_between_messages}с")



            print(f"⏳ Между аккаунтами: {delay_between_accounts}с")

            print(f"🔂 Повтор: {'ВКЛЮЧЕН' if repeat_broadcast else 'ВЫКЛЮЧЕН'}")

            if repeat_broadcast:

                print(f"⏱️ Интервал повтора: {repeat_interval}с")

            print(f"🗑 Удаление у себя: {'ВКЛЮЧЕНО' if delete_after_send else 'ВЫКЛЮЧЕНО'}")

            if notification_enabled:

                print(f"{Fore.GREEN}🔔 Уведомления: ВКЛЮЧЕНЫ{Style.RESET_ALL}")



            if input("\n🚀 Запустить рассылку параллельно? (y/n): ").lower() == 'y':

                print("\n" + Fore.MAGENTA + "🚀 Запуск рассылки..." + Style.RESET_ALL)

                await run_broadcast(current_api_id, current_api_hash, selected_sessions, message_to_send,

                                    max_messages_per_account, repeat_broadcast, repeat_interval, delete_after_send,

                                    use_media, media_path, recipient_type,

                                    fast_mode, fast_delay,

                                    target_chats_ids=target_groups_file_data)

                input("Нажмите Enter для продолжения...")



        elif choice == '2':

            if current_api_id == DEFAULT_API_ID or not current_api_hash or current_api_hash == "ЗАМЕНИТЕ НА ВАШ API HASH, ТАКЖЕ НАСТРОЙТЕ API ID ":

                print(

                    "\n" + Fore.YELLOW + "[!] ВНИМАНИЕ: Настройте API ID и API Hash в меню '3. Настройки'" + Style.RESET_ALL)

                input("Нажмите Enter...")

                continue



            session_files = [f for f in os.listdir(session_folder) if f.endswith('.session')]

            if not session_files:

                print(f"\n{Fore.RED}✘ Не найдены .session файлы в '{session_folder}'")

                print("1. Авторизуйтесь через TelegramClient (создаст файл)")

                print("2. Поместите .session файлы в папку")

                input("Нажмите Enter...")

                continue



            enter_links = load_enter_links()

            if enter_links is None:

                input("Нажмите Enter для продолжения...")

                continue

            if not enter_links:

                print(f"{Fore.YELLOW}⚠️ Файл '{enter_links_file}' пуст. Добавьте ссылки для входа.{Style.RESET_ALL}")

                input("Нажмите Enter для продолжения...")

                continue



            print(f"\n{Fore.GREEN}✔ Найдено {len(session_files)} сессий:")

            for i, f in enumerate(session_files):

                print(f"{i + 1}. {f}")



            print(f"\n{Fore.CYAN}● Выберите сессии для вступления в группы:")

            print("1. 1️⃣ Одна сессия")

            print("2. 🔢 Несколько сессий")

            print("3. ♾️ Все сессии")

            print("0. Назад")



            sub_choice = input("Выберите: ").strip()

            selected_sessions = []



            if sub_choice == '1':

                selected_sessions = session_files[:1]

            elif sub_choice == '2':

                indices_str = input("Сессии через запятую (1,3,5): ").strip()

                try:

                    nums = [int(x.strip()) - 1 for x in indices_str.split(',') if x.strip()]

                    selected_sessions = [session_files[i] for i in nums if 0 <= i < len(session_files)]

                    if not selected_sessions:

                        print(

                            f"{Fore.YELLOW}⚠️ Не выбрано ни одной сессии. Будет использована первая.{Style.RESET_ALL}")

                        selected_sessions = session_files[:1]

                except ValueError:

                    print(f"{Fore.RED}✘ Некорректный ввод. Будет использована первая сессия.{Style.RESET_ALL}")

                    selected_sessions = session_files[:1]

            elif sub_choice == '3':

                selected_sessions = session_files

            else:

                continue



            if not selected_sessions:

                print(f"{Fore.RED}✘ Ошибка выбора сессии. Возврат в меню.{Style.RESET_ALL}")

                await asyncio.sleep(2)

                continue



            print(f"\n{Fore.CYAN}ℹ Параметры вступления:")

            print(f"📋 Сессий: {len(selected_sessions)}")

            print(f"🔗 Ссылок для входа: {len(enter_links)}")

            print(f"⏳ Задержка между вступлениями: 5 сек")

            print(f"⏳ Задержка между аккаунтами: {delay_between_accounts}с")



            if input("\n🚀 Запустить вступление в группы? (y/n): ").lower() == 'y':

                print("\n" + Fore.MAGENTA + "🚀 Запуск вступления в группы..." + Style.RESET_ALL)

                await run_join_broadcast(current_api_id, current_api_hash, selected_sessions, enter_links)

                input("Нажмите Enter для продолжения...")



        elif choice == '3':

            await display_settings_menu()

        elif choice == '4':

            session_files = [f for f in os.listdir(session_folder) if f.endswith('.session')]

            print(f"\n{Fore.BLUE}📁 Сессий в '{session_folder}': {len(session_files)}")

            if not session_files:

                print("   (Не найдено)")

            for i, f in enumerate(session_files):

                try:

                    size = os.path.getsize(os.path.join(session_folder, f)) / 1024

                    print(f"{i + 1}. {f:<25} ({size:5.1f} КБ)")

                except OSError:

                    print(f"{i + 1}. {f:<25} (ошибка чтения размера)")

            input("\nEnter...")

        elif choice == '5':

            await add_session_by_number()

            input("Нажмите Enter для продолжения...")

        elif choice == '6':

            await update_manager.show_update_menu()

            input("Нажмите Enter для продолжения...")

        elif choice == '7':

            save_config()

            await close_notification_client()

            print(f"{Fore.CYAN}🚪 До свидания!{Style.RESET_ALL}")

            break

        else:

            print(f"{Fore.RED}✘ Выберите 1-7{Style.RESET_ALL}")

            await asyncio.sleep(1)





def signal_handler(sig, frame):

    print("\n" + Fore.YELLOW + "🛑 Остановлено..." + Style.RESET_ALL)

    stop_event.set()





signal.signal(signal.SIGINT, signal_handler)



if __name__ == '__main__':

    try:

        asyncio.run(main_menu())

    except KeyboardInterrupt:

        print("\n" + Fore.CYAN + "🚪 Выход (KeyboardInterrupt)" + Style.RESET_ALL)

    except Exception as e:

        print(f"\n{Fore.RED}✘ Ошибка: {e}{Style.RESET_ALL}")

        traceback.print_exc()









