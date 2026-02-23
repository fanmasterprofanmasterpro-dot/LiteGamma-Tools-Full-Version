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
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat, User, MessageEntityMention, MessageEntityMentionName, MessageEntityTextUrl, \
    MessageEntityUrl
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
from telethon.tl.functions.chatlists import CheckChatlistInviteRequest, JoinChatlistInviteRequest
from telethon.errors import (
    FloodWaitError, ChannelPrivateError, ChatAdminRequiredError,
    UserPrivacyRestrictedError, AuthKeyUnregisteredError, PhoneCodeInvalidError,
    SessionPasswordNeededError, PhoneNumberInvalidError, PasswordHashInvalidError,
    RPCError, InviteHashExpiredError, InviteHashInvalidError, UserAlreadyParticipantError,
    UsernameNotOccupiedError, InviteRequestSentError, InviteHashEmptyError
)
from colorama import init, Fore, Style
from datetime import datetime, timedelta

# =============== UPDATE CONFIGURATION ===============
GITHUB_USER = "fanmasterprofanmasterpro-dot"
GITHUB_REPO = "LiteGamma-Tools-Full-Version"
GITHUB_BRANCH = "main"
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}"

CURRENT_VERSION = "1.5.2"  # Обновлена версия
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

# =============== НОВЫЕ НАСТРОЙКИ ДЛЯ АВТОПОДПИСКИ ===============
AUTO_SUBSCRIBE_ENABLED = False  # Включена ли автоподписка
AUTO_SUBSCRIBE_ON_MENTION = True  # Подписываться при упоминании
AUTO_SUBSCRIBE_DELAY = 3  # Задержка между подписками (сек)
AUTO_SUBSCRIBE_MAX_FLOOD_WAIT = 300  # Максимальное время ожидания флуда (5 мин)
AUTO_SUBSCRIBE_RETRY_AFTER_FLOOD = True  # Повторять после флуда
AUTO_SUBSCRIBE_CHECK_INTERVAL = 5  # Интервал проверки при ожидании
AUTO_SUBSCRIBE_WAIT_FOR_MENTION = 10  # Макс время ожидания упоминания (сек) - УМЕНЬШЕНО ДО 10
AUTO_SUBSCRIBE_PAUSE_BETWEEN_CHANNELS = 3  # Пауза между каналами
AUTO_SUBSCRIBE_FORCED_CHANNELS = []  # Ручной список каналов для подписки
AUTO_SUBSCRIBE_FIRST_CYCLE_ONLY = True  # Только первый цикл ждет подписки

# Паттерны для поиска каналов
CHANNEL_PATTERNS = [
    r'@(\w+)',  # @username
    r'https://t\.me/(\w+)',  # https://t.me/username
    r't\.me/(\w+)',  # t.me/username
    r'telegram\.me/(\w+)',  # telegram.me/username
    r'joinchat/([\w\-]+)',  # joinchat links
    r'\+([\w\-]+)',  # invite links
]

# Глобальные переменные для автоподписки
flood_wait_occurred = False
total_flood_time = 0
failed_subscriptions_file = "failed_subscriptions.txt"  # Файл для неудачных подписок


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
            response = requests.get(version_url, timeout=10)

            if response.status_code != 200:
                print(f"{Fore.YELLOW}⚠️ Не удалось проверить обновления{Style.RESET_ALL}")
                return False

            remote_data = response.json()
            remote_version = remote_data.get("version", "0.0.0")

            # Сравниваем версии
            if self.compare_versions(remote_version, CURRENT_VERSION) > 0:
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

        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Ошибка при проверке обновлений: {e}{Style.RESET_ALL}")
            return False

    def compare_versions(self, version1, version2):
        """Сравнивает две версии"""
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]

        # Дополняем нулями до одинаковой длины
        while len(v1_parts) < len(v2_parts):
            v1_parts.append(0)
        while len(v2_parts) < len(v1_parts):
            v2_parts.append(0)

        for i in range(len(v1_parts)):
            if v1_parts[i] > v2_parts[i]:
                return 1
            elif v1_parts[i] < v2_parts[i]:
                return -1
        return 0

    def should_check_update(self):
        """Проверяет, нужно ли проверять обновления"""
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
        """Сохраняет время последней проверки"""
        try:
            with open(LAST_UPDATE_CHECK_FILE, 'w') as f:
                json.dump({'last_check': time.time()}, f)
        except:
            pass

    async def perform_update(self, remote_data):
        """Выполняет обновление скрипта"""
        global CURRENT_VERSION

        try:
            print(f"\n{Fore.YELLOW}⚙️ Начинаю обновление до версии {self.new_version}...{Style.RESET_ALL}")

            os.makedirs(self.backup_folder, exist_ok=True)

            backup_name = f"backup_v{CURRENT_VERSION}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            backup_path = os.path.join(self.backup_folder, backup_name)

            current_file = __file__
            with open(current_file, 'r', encoding='utf-8') as f:
                current_content = f.read()

            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(current_content)

            print(f"{Fore.GREEN}✅ Бэкап создан: {backup_path}{Style.RESET_ALL}")

            script_url = remote_data.get('download_url', f"{GITHUB_RAW_BASE}/LiteGamma%20Tools%20Full%20Version.py")

            expected_sha256 = remote_data.get('checksums', {}).get('sha256')

            response = requests.get(script_url, timeout=30)
            if response.status_code == 200:
                new_content = response.text

                if expected_sha256:
                    actual_sha256 = hashlib.sha256(new_content.encode()).hexdigest()
                    if actual_sha256 != expected_sha256:
                        print(f"{Fore.RED}❌ Ошибка: хеш файла не совпадает!{Style.RESET_ALL}")
                        print(f"Ожидаемый: {expected_sha256}")
                        print(f"Полученный: {actual_sha256}")
                        return False

                # Обновляем версию в файле
                new_content = self.update_version_in_file(new_content, self.new_version)

                with open(current_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                # Обновляем глобальную переменную
                CURRENT_VERSION = self.new_version

                print(f"{Fore.GREEN}✅ Скрипт успешно обновлен до версии {self.new_version}!{Style.RESET_ALL}")

                # Сохраняем в конфиг
                save_config()

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
                print(f"{Fore.RED}❌ Не удалось скачать обновление{Style.RESET_ALL}")
                return False

        except Exception as e:
            print(f"{Fore.RED}❌ Ошибка при обновлении: {e}{Style.RESET_ALL}")
            traceback.print_exc()
            return False

    def update_version_in_file(self, content, new_version):
        """Обновляет версию в файле"""
        import re

        # Ищем разные варианты объявления версии
        patterns = [
            (r'CURRENT_VERSION\s*=\s*["\']([^"\']+)["\']', f'CURRENT_VERSION = "{new_version}"'),
            (r'CURRENT_VERSION\s*=\s*([0-9.]+)', f'CURRENT_VERSION = "{new_version}"'),
            (r'__version__\s*=\s*["\']([^"\']+)["\']', f'__version__ = "{new_version}"'),
            (r'VERSION\s*=\s*["\']([^"\']+)["\']', f'VERSION = "{new_version}"')
        ]

        updated_content = content
        for pattern, replacement in patterns:
            updated_content = re.sub(pattern, replacement, updated_content)

        # Проверяем, что замена произошла
        if updated_content == content:
            # Если не нашли, добавляем объявление версии после импортов
            version_line = f'\nCURRENT_VERSION = "{new_version}"\n'
            # Вставляем после импортов
            import_end = updated_content.find('\n\n')
            if import_end != -1:
                updated_content = updated_content[:import_end] + version_line + updated_content[import_end:]

        return updated_content

    def verify_version_in_file(self):
        """Проверяет, какая версия реально записана в файле"""
        try:
            with open(__file__, 'r', encoding='utf-8') as f:
                content = f.read()

            # Ищем версию в файле
            import re
            version_match = re.search(r'CURRENT_VERSION\s*=\s*["\']?([0-9.]+)["\']?', content)
            if version_match:
                file_version = version_match.group(1)
                print(f"{Fore.CYAN}📄 Версия в файле: {file_version}{Style.RESET_ALL}")
                return file_version
        except Exception as e:
            print(f"{Fore.RED}✘ Ошибка проверки версии: {e}{Style.RESET_ALL}")
        return None

    def restart_program(self):
        """Перезапускает программу"""
        print(f"{Fore.CYAN}🔄 Перезапуск...{Style.RESET_ALL}")
        python = sys.executable
        os.execl(python, python, *sys.argv)

    async def show_update_menu(self):
        """Показывает меню обновлений"""
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
                await self.perform_update({'version': self.new_version, 'changelog': self.changelog})
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
        """Диагностика проблемы с версией"""
        print(f"{Fore.CYAN}🔍 Диагностика версии:{Style.RESET_ALL}")
        print(f"  Глобальная CURRENT_VERSION: {CURRENT_VERSION}")

        # Проверяем в файле
        file_version = self.verify_version_in_file()
        print(f"  Версия в файле: {file_version}")

        # Проверяем в конфиге
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    config_version = config.get('current_version', 'не найдено')
                    print(f"  Версия в config.json: {config_version}")
        except:
            print(f"  Версия в config.json: ошибка чтения")

        # Проверяем в version.json на GitHub
        try:
            response = requests.get(f"{GITHUB_RAW_BASE}/version.json", timeout=5)
            if response.status_code == 200:
                remote = response.json()
                print(f"  Версия на GitHub: {remote.get('version', 'не найдено')}")
                print(f"  Что нового: {remote.get('changelog', [])}")
        except:
            print(f"  Версия на GitHub: ошибка проверки")

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
            modified = datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"  {i}. {backup.name}")
            print(f"     Версия: {version}, Размер: {size:.1f}KB, Дата: {modified.strftime('%Y-%m-%d %H:%M')}")

    def restore_from_backup(self):
        """Восстанавливает из бэкапа"""
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
                    self.backup_folder) / f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
                shutil.copy2(__file__, current_backup)

                shutil.copy2(backup_file, __file__)
                print(f"{Fore.GREEN}✅ Восстановлено из бэкапа!{Style.RESET_ALL}")

                if input(f"{Fore.MAGENTA}Перезапустить сейчас? (y/n): {Style.RESET_ALL}").lower() == 'y':
                    self.restart_program()
        except ValueError:
            print(f"{Fore.RED}❌ Неверный выбор{Style.RESET_ALL}")

    def show_update_settings(self):
        """Настройки обновлений"""
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


# Создаем глобальный менеджер обновлений
update_manager = UpdateManager()


def print_header(text):
    print(f"\n{CLR_ACCENT}╔" + "═" * (len(text) + 4) + "╗")
    print(f"{CLR_ACCENT}║  {CLR_MAIN}{text}  {CLR_ACCENT}║")
    print(f"{CLR_ACCENT}╚" + "═" * (len(text) + 4) + "╝\n")


def print_stata(text):
    print(f"\n{CLR_ACCENT}╔" + "═" * (len(text) + 4) + "╗")
    print(f"{CLR_ACCENT}║  {CLR_MAIN}{text}    {CLR_ACCENT}║")
    print(f"{CLR_ACCENT}╚" + "═" * (len(text) + 4) + "╝\n")


# =============== CONFIGURATION ===============
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

# =============== НОВЫЕ НАСТРОЙКИ АВТОПОДПИСКИ ПО УМОЛЧАНИЮ ===============
DEFAULT_AUTO_SUBSCRIBE_ENABLED = False
DEFAULT_AUTO_SUBSCRIBE_ON_MENTION = True
DEFAULT_AUTO_SUBSCRIBE_DELAY = 3
DEFAULT_AUTO_SUBSCRIBE_MAX_FLOOD_WAIT = 300
DEFAULT_AUTO_SUBSCRIBE_RETRY_AFTER_FLOOD = True
DEFAULT_AUTO_SUBSCRIBE_CHECK_INTERVAL = 5
DEFAULT_AUTO_SUBSCRIBE_WAIT_FOR_MENTION = 10
DEFAULT_AUTO_SUBSCRIBE_PAUSE_BETWEEN_CHANNELS = 3
DEFAULT_AUTO_SUBSCRIBE_FORCED_CHANNELS = []
DEFAULT_AUTO_SUBSCRIBE_FIRST_CYCLE_ONLY = True

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

# =============== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ АВТОПОДПИСКИ ===============
auto_subscribe_enabled = DEFAULT_AUTO_SUBSCRIBE_ENABLED
auto_subscribe_on_mention = DEFAULT_AUTO_SUBSCRIBE_ON_MENTION
auto_subscribe_delay = DEFAULT_AUTO_SUBSCRIBE_DELAY
auto_subscribe_max_flood_wait = DEFAULT_AUTO_SUBSCRIBE_MAX_FLOOD_WAIT
auto_subscribe_retry_after_flood = DEFAULT_AUTO_SUBSCRIBE_RETRY_AFTER_FLOOD
auto_subscribe_check_interval = DEFAULT_AUTO_SUBSCRIBE_CHECK_INTERVAL
auto_subscribe_wait_for_mention = DEFAULT_AUTO_SUBSCRIBE_WAIT_FOR_MENTION
auto_subscribe_pause_between_channels = DEFAULT_AUTO_SUBSCRIBE_PAUSE_BETWEEN_CHANNELS
auto_subscribe_forced_channels = DEFAULT_AUTO_SUBSCRIBE_FORCED_CHANNELS
auto_subscribe_first_cycle_only = DEFAULT_AUTO_SUBSCRIBE_FIRST_CYCLE_ONLY

stop_event = asyncio.Event()
invalid_session_log_file = "invalidsession_list.txt"

config_file = "config.json"
group_list_file = "group.json"
enter_links_file = "enter.json"

notification_client = None

log_buffer = []
log_buffer_lock = asyncio.Lock()


def clear_failed_subscriptions_file():
    """Очищает файл с неудачными подписками при запуске"""
    try:
        if os.path.exists(failed_subscriptions_file):
            os.remove(failed_subscriptions_file)
            print(f"{Fore.GREEN}✔ Файл '{failed_subscriptions_file}' очищен.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️ Не удалось очистить файл '{failed_subscriptions_file}': {e}{Style.RESET_ALL}")


def log_failed_subscription(session_name, channel_link, reason):
    """Записывает неудачную подписку в файл"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        # Проверяем, есть ли уже такая запись
        if os.path.exists(failed_subscriptions_file):
            with open(failed_subscriptions_file, 'r', encoding='utf-8') as f:
                existing = f.read()
                if channel_link in existing and session_name in existing:
                    return  # Уже есть такая запись

        with open(failed_subscriptions_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {session_name} | {channel_link} | {reason}\n")
    except Exception as e:
        print(f"{Fore.RED}✘ Ошибка записи в файл неудачных подписок: {e}{Style.RESET_ALL}")


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
        timestamp = datetime.now().strftime("%H:%M:%S")
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
                f.write(f"Лог рассылки от {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
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
                    caption=f"📋 **Полный лог рассылки**\nВремя: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nВсего записей: {len(log_buffer)}"
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
        "notify_full_logs": notify_full_logs,
        # Новые настройки автоподписки
        "auto_subscribe_enabled": auto_subscribe_enabled,
        "auto_subscribe_on_mention": auto_subscribe_on_mention,
        "auto_subscribe_delay": auto_subscribe_delay,
        "auto_subscribe_max_flood_wait": auto_subscribe_max_flood_wait,
        "auto_subscribe_retry_after_flood": auto_subscribe_retry_after_flood,
        "auto_subscribe_check_interval": auto_subscribe_check_interval,
        "auto_subscribe_wait_for_mention": auto_subscribe_wait_for_mention,
        "auto_subscribe_pause_between_channels": auto_subscribe_pause_between_channels,
        "auto_subscribe_forced_channels": auto_subscribe_forced_channels,
        "auto_subscribe_first_cycle_only": auto_subscribe_first_cycle_only,
        "current_version": CURRENT_VERSION
    }
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"{Fore.GREEN}✔ Конфигурация сохранена.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}✘ Ошибка сохранения: {e}{Style.RESET_ALL}")


def load_config():
    global current_api_id, current_api_hash, session_folder, message_to_send, delay_between_messages, delay_between_accounts, max_messages_per_account, repeat_broadcast, repeat_interval, delete_after_send, recipient_type, use_media, media_path, fast_mode, fast_delay, notification_enabled, notification_bot_token, notification_chat_id, notify_invalid_session, notify_cycle_results, notify_full_logs, CURRENT_VERSION
    global auto_subscribe_enabled, auto_subscribe_on_mention, auto_subscribe_delay, auto_subscribe_max_flood_wait, auto_subscribe_retry_after_flood, auto_subscribe_check_interval, auto_subscribe_wait_for_mention, auto_subscribe_pause_between_channels, auto_subscribe_forced_channels, auto_subscribe_first_cycle_only

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

                # Загрузка настроек автоподписки
                auto_subscribe_enabled = config.get("auto_subscribe_enabled", DEFAULT_AUTO_SUBSCRIBE_ENABLED)
                auto_subscribe_on_mention = config.get("auto_subscribe_on_mention", DEFAULT_AUTO_SUBSCRIBE_ON_MENTION)
                auto_subscribe_delay = config.get("auto_subscribe_delay", DEFAULT_AUTO_SUBSCRIBE_DELAY)
                auto_subscribe_max_flood_wait = config.get("auto_subscribe_max_flood_wait",
                                                           DEFAULT_AUTO_SUBSCRIBE_MAX_FLOOD_WAIT)
                auto_subscribe_retry_after_flood = config.get("auto_subscribe_retry_after_flood",
                                                              DEFAULT_AUTO_SUBSCRIBE_RETRY_AFTER_FLOOD)
                auto_subscribe_check_interval = config.get("auto_subscribe_check_interval",
                                                           DEFAULT_AUTO_SUBSCRIBE_CHECK_INTERVAL)
                auto_subscribe_wait_for_mention = config.get("auto_subscribe_wait_for_mention",
                                                             DEFAULT_AUTO_SUBSCRIBE_WAIT_FOR_MENTION)
                auto_subscribe_pause_between_channels = config.get("auto_subscribe_pause_between_channels",
                                                                   DEFAULT_AUTO_SUBSCRIBE_PAUSE_BETWEEN_CHANNELS)
                auto_subscribe_forced_channels = config.get("auto_subscribe_forced_channels",
                                                            DEFAULT_AUTO_SUBSCRIBE_FORCED_CHANNELS)
                auto_subscribe_first_cycle_only = config.get("auto_subscribe_first_cycle_only",
                                                             DEFAULT_AUTO_SUBSCRIBE_FIRST_CYCLE_ONLY)

                CURRENT_VERSION = config.get("current_version", CURRENT_VERSION)
            print(f"{Fore.GREEN}✔ Конфигурация загружена.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️ Ошибка загрузки конфигурации: {e}{Style.RESET_ALL}")


def log_invalid_session(session_file):
    """Записывает невалидную сессию в лог-файл и отправляет уведомление."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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


# =============== ФУНКЦИИ ДЛЯ АВТОПОДПИСКИ ===============
def format_time(seconds):
    """Форматирует время в читаемый вид"""
    if seconds < 60:
        return f"{seconds} сек"
    elif seconds < 3600:
        minutes = seconds // 60
        seconds_remain = seconds % 60
        return f"{minutes} мин {seconds_remain} сек"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} ч {minutes} мин"


def extract_invite_hash(invite_link):
    """Извлекает хеш из ссылки-приглашения"""
    if '/joinchat/' in invite_link:
        return invite_link.split('/joinchat/')[-1]
    elif '/+' in invite_link:
        return invite_link.split('/+')[-1]
    elif 't.me/+' in invite_link:
        return invite_link.split('t.me/+')[-1]
    return None


async def handle_flood_wait(e, operation_name="операция", session_name=""):
    """Обрабатывает флуд-контроль и возвращает время ожидания"""
    global flood_wait_occurred, total_flood_time

    wait_seconds = e.seconds
    flood_wait_occurred = True
    total_flood_time += wait_seconds

    # Текущее время и время окончания ожидания
    current_time = datetime.now()
    end_time = current_time + timedelta(seconds=wait_seconds)

    log_msg = f"\n{'=' * 60}"
    print(log_msg)
    await add_to_log_buffer(log_msg)

    log_msg = f"🚫 [{session_name}] ОБНАРУЖЕН ФЛУД-КОНТРОЛЬ!"
    print(log_msg)
    await add_to_log_buffer(log_msg)

    log_msg = f"{'=' * 60}"
    print(log_msg)
    await add_to_log_buffer(log_msg)

    log_msg = f"📌 Операция: {operation_name}"
    print(log_msg)
    await add_to_log_buffer(log_msg)

    log_msg = f"⏱️ Время ожидания: {format_time(wait_seconds)}"
    print(log_msg)
    await add_to_log_buffer(log_msg)

    log_msg = f"🕐 Начало: {current_time.strftime('%H:%M:%S')}"
    print(log_msg)
    await add_to_log_buffer(log_msg)

    log_msg = f"🕐 Окончание: {end_time.strftime('%H:%M:%S')}"
    print(log_msg)
    await add_to_log_buffer(log_msg)

    if wait_seconds > auto_subscribe_max_flood_wait:
        log_msg = f"⚠️ Внимание! Время ожидания превышает лимит в {format_time(auto_subscribe_max_flood_wait)}"
        print(log_msg)
        await add_to_log_buffer(log_msg)
        log_msg = f"❌ Пропускаем эту операцию"
        print(log_msg)
        await add_to_log_buffer(log_msg)
        return False

    log_msg = f"\n⏳ Ожидание... (проверка каждые {auto_subscribe_check_interval} сек)"
    print(log_msg)
    await add_to_log_buffer(log_msg)

    # Ожидаем с индикацией прогресса
    elapsed = 0
    while elapsed < wait_seconds:
        if stop_event.is_set():
            log_msg = f"\n{Fore.YELLOW}🛑 Остановлено пользователем во время ожидания{Style.RESET_ALL}"
            print(log_msg)
            await add_to_log_buffer(log_msg)
            return False

        await asyncio.sleep(min(auto_subscribe_check_interval, wait_seconds - elapsed))
        elapsed += auto_subscribe_check_interval
        remaining = wait_seconds - elapsed
        if remaining > 0:
            progress = (elapsed / wait_seconds) * 100
            log_msg = f"   Прогресс: {progress:.1f}% | Осталось: {format_time(remaining)}"
            print(log_msg)
            await add_to_log_buffer(log_msg)

    log_msg = f"✅ Ожидание завершено! Продолжаем..."
    print(log_msg)
    await add_to_log_buffer(log_msg)
    log_msg = f"{'=' * 60}\n"
    print(log_msg)
    await add_to_log_buffer(log_msg)
    return True


async def extract_channels_from_entities(message):
    """Извлекает каналы из entities сообщения"""
    channels = []

    if not message.entities:
        return channels

    for entity in message.entities:
        # Проверяем текстовые ссылки
        if isinstance(entity, MessageEntityTextUrl) and entity.url:
            if any(pattern in entity.url for pattern in ['t.me', 'telegram.me']):
                channels.append(entity.url)
                log_msg = f"🔗 Найдена ссылка в entity: {entity.url}"
                print(log_msg)
                await add_to_log_buffer(log_msg)

        # Проверяем обычные URL
        elif isinstance(entity, MessageEntityUrl):
            url = message.text[entity.offset:entity.offset + entity.length]
            if any(pattern in url for pattern in ['t.me', 'telegram.me']):
                channels.append(url)
                log_msg = f"🔗 Найден URL в entity: {url}"
                print(log_msg)
                await add_to_log_buffer(log_msg)

        # Проверяем Mention (это может быть @username)
        elif isinstance(entity, MessageEntityMention):
            mention = message.text[entity.offset:entity.offset + entity.length]
            if mention.startswith('@'):
                channels.append(mention)
                log_msg = f"🔗 Найдено упоминание: {mention}"
                print(log_msg)
                await add_to_log_buffer(log_msg)

    return channels


async def extract_channels_from_buttons(client, message):
    """Извлекает каналы из кнопок сообщения"""
    channels = []

    try:
        # Проверяем, есть ли кнопки в сообщении
        if message.reply_markup and hasattr(message.reply_markup, 'rows'):
            for row in message.reply_markup.rows:
                for button in row.buttons:
                    # Разные типы кнопок
                    if hasattr(button, 'url') and button.url:
                        if any(pattern in button.url for pattern in ['t.me', 'telegram.me']):
                            channels.append(button.url)
                            log_msg = f"🔘 Найдена кнопка-ссылка: {button.url}"
                            print(log_msg)
                            await add_to_log_buffer(log_msg)
    except Exception as e:
        log_msg = f"⚠️ Ошибка при анализе кнопок: {e}"
        print(log_msg)
        await add_to_log_buffer(log_msg)

    return channels


async def find_channels_in_message(client, message):
    """Комплексный поиск каналов в сообщении"""
    channels = []

    log_msg = "\n🔍 Анализируем сообщение..."
    print(log_msg)
    await add_to_log_buffer(log_msg)

    # Способ 1: Из entities
    entity_channels = await extract_channels_from_entities(message)
    channels.extend(entity_channels)

    # Способ 2: Из кнопок
    button_channels = await extract_channels_from_buttons(client, message)
    channels.extend(button_channels)

    # Способ 3: Регулярные выражения по тексту
    text = message.text or ''
    for pattern in CHANNEL_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = next((m for m in match if m), None)
            if match and len(match) > 3:
                if pattern == r'@(\w+)':
                    channels.append(f"@{match}")
                elif 'joinchat' in pattern or '+' in pattern:
                    channels.append(f"https://t.me/joinchat/{match}")
                else:
                    channels.append(f"https://t.me/{match}")

    # Способ 4: Ручной список
    if auto_subscribe_forced_channels:
        channels.extend(auto_subscribe_forced_channels)

    # Удаляем дубликаты и пустые значения
    unique_channels = []
    seen = set()

    for channel in channels:
        # Нормализуем ссылки-приглашения
        if 't.me/+' in channel or 'joinchat' in channel:
            normalized = channel
        elif channel.startswith('@'):
            normalized = channel
        elif 't.me' in channel:
            normalized = channel
        else:
            normalized = f"@{channel}" if not channel.startswith(('http', '@')) else channel

        if normalized not in seen and normalized:
            seen.add(normalized)
            unique_channels.append(normalized)

    return unique_channels


async def join_invite_link(client, invite_link, session_name=""):
    """Присоединяется по ссылке-приглашению"""
    try:
        # Извлекаем хеш из ссылки
        invite_hash = extract_invite_hash(invite_link)
        if not invite_hash:
            log_msg = f"❌ [{session_name}] Не удалось извлечь хеш из ссылки: {invite_link}"
            print(log_msg)
            await add_to_log_buffer(log_msg)
            return False, "invalid_invite_link"

        log_msg = f"🔑 [{session_name}] Извлечен хеш приглашения: {invite_hash}"
        print(log_msg)
        await add_to_log_buffer(log_msg)

        # Пробуем присоединиться через ImportChatInviteRequest
        try:
            await client(ImportChatInviteRequest(invite_hash))
            log_msg = f"✅ [{session_name}] Успешно присоединились по ссылке-приглашению!"
            print(log_msg)
            await add_to_log_buffer(log_msg)
            return True, "joined_by_invite"
        except FloodWaitError as e:
            log_msg = f"🚫 [{session_name}] Флуд-контроль при присоединении по приглашению!"
            print(log_msg)
            await add_to_log_buffer(log_msg)
            if await handle_flood_wait(e, f"присоединение к {invite_link}", session_name):
                return await join_invite_link(client, invite_link, session_name)
            return False, "flood_wait"
        except InviteHashExpiredError:
            log_msg = f"❌ [{session_name}] Срок действия приглашения истек"
            print(log_msg)
            await add_to_log_buffer(log_msg)
            log_failed_subscription(session_name, invite_link, "Срок действия приглашения истек")
            return False, "invite_expired"
        except InviteHashInvalidError:
            log_msg = f"❌ [{session_name}] Недействительное приглашение"
            print(log_msg)
            await add_to_log_buffer(log_msg)
            log_failed_subscription(session_name, invite_link, "Недействительное приглашение")
            return False, "invite_invalid"
        except InviteHashEmptyError:
            log_msg = f"❌ [{session_name}] Пустой хеш приглашения"
            print(log_msg)
            await add_to_log_buffer(log_msg)
            log_failed_subscription(session_name, invite_link, "Пустой хеш приглашения")
            return False, "invite_empty"
        except Exception as e:
            log_msg = f"❌ [{session_name}] Ошибка при присоединении по приглашению: {e}"
            print(log_msg)
            await add_to_log_buffer(log_msg)
            log_failed_subscription(session_name, invite_link, str(e)[:100])
            return False, f"invite_error: {str(e)[:50]}"

    except Exception as e:
        log_msg = f"❌ [{session_name}] Ошибка при обработке ссылки-приглашения: {e}"
        print(log_msg)
        await add_to_log_buffer(log_msg)
        log_failed_subscription(session_name, invite_link, str(e)[:100])
        return False, "invite_processing_error"


async def subscribe_to_channel(client, channel_ref, session_name="", retry_count=0):
    """Подписывается на один канал с обработкой флуд-контроля"""
    max_retries = 3  # Максимальное количество попыток при флуде

    try:
        log_msg = f"\n📥 [{session_name}] Обработка: {channel_ref}"
        print(log_msg)
        await add_to_log_buffer(log_msg)

        # Проверяем, не ссылка ли это на приглашение
        if any(x in channel_ref for x in ['joinchat', 't.me/+', '/+']):
            log_msg = f"🔗 [{session_name}] Это ссылка-приглашение, пробуем присоединиться..."
            print(log_msg)
            await add_to_log_buffer(log_msg)
            return await join_invite_link(client, channel_ref, session_name)

        # Преобразуем @username в ссылку если нужно
        if channel_ref.startswith('@'):
            username = channel_ref[1:]
            channel_ref = f"https://t.me/{username}"

        # Получаем сущность канала
        try:
            channel_entity = await client.get_entity(channel_ref)
            channel_title = getattr(channel_entity, 'title', username)
            log_msg = f"✅ [{session_name}] Получена сущность канала: {channel_title}"
            print(log_msg)
            await add_to_log_buffer(log_msg)
        except FloodWaitError as e:
            log_msg = f"🚫 [{session_name}] Флуд-контроль при получении информации о канале!"
            print(log_msg)
            await add_to_log_buffer(log_msg)
            if await handle_flood_wait(e, f"получение информации о {channel_ref}", session_name):
                return await subscribe_to_channel(client, channel_ref, session_name, retry_count + 1)
            return False, "flood_timeout"
        except ValueError as e:
            if "No user has" in str(e):
                log_msg = f"❌ [{session_name}] Канал не найден: {channel_ref}"
                print(log_msg)
                await add_to_log_buffer(log_msg)
                log_failed_subscription(session_name, channel_ref, "Канал не найден")
                return False, "channel_not_found"
            log_msg = f"⚠️ [{session_name}] Ошибка при получении канала: {e}"
            print(log_msg)
            await add_to_log_buffer(log_msg)
            log_failed_subscription(session_name, channel_ref, str(e)[:100])
            return False, "channel_error"
        except Exception as e:
            log_msg = f"⚠️ [{session_name}] Не удалось получить канал: {e}"
            print(log_msg)
            await add_to_log_buffer(log_msg)
            log_failed_subscription(session_name, channel_ref, str(e)[:100])
            return False, "entity_error"

        # Проверяем, не подписаны ли уже
        try:
            await client.get_permissions(channel_entity, 'me')
            log_msg = f"ℹ️ [{session_name}] Уже подписаны на этот канал"
            print(log_msg)
            await add_to_log_buffer(log_msg)
            return True, "already_subscribed"
        except FloodWaitError as e:
            log_msg = f"🚫 [{session_name}] Флуд-контроль при проверке подписки!"
            print(log_msg)
            await add_to_log_buffer(log_msg)
            if await handle_flood_wait(e, f"проверка подписки на {channel_ref}", session_name):
                return await subscribe_to_channel(client, channel_ref, session_name, retry_count + 1)
            return False, "flood_timeout"
        except Exception:
            # Не подписаны, пробуем вступить
            pass

        # Вступаем в канал
        try:
            await client(JoinChannelRequest(channel_entity))
            log_msg = f"✅ [{session_name}] Успешно подписались на канал!"
            print(log_msg)
            await add_to_log_buffer(log_msg)

            # Проверяем, действительно ли подписались
            await asyncio.sleep(2)
            try:
                await client.get_permissions(channel_entity, 'me')
                log_msg = f"✅ [{session_name}] Подписка подтверждена!"
                print(log_msg)
                await add_to_log_buffer(log_msg)
            except:
                log_msg = f"⚠️ [{session_name}] Не удалось подтвердить подписку"
                print(log_msg)
                await add_to_log_buffer(log_msg)

            await asyncio.sleep(auto_subscribe_pause_between_channels)
            return True, "subscribed"

        except FloodWaitError as e:
            log_msg = f"\n{'🚫' * 10} [{session_name}] ФЛУД-КОНТРОЛЬ {'🚫' * 10}"
            print(log_msg)
            await add_to_log_buffer(log_msg)
            log_msg = f"📊 Статистика по флуду:"
            print(log_msg)
            await add_to_log_buffer(log_msg)
            log_msg = f"   • Канал: {channel_ref}"
            print(log_msg)
            await add_to_log_buffer(log_msg)
            log_msg = f"   • Попытка: {retry_count + 1}/{max_retries}"
            print(log_msg)
            await add_to_log_buffer(log_msg)
            log_msg = f"   • Время ожидания: {format_time(e.seconds)}"
            print(log_msg)
            await add_to_log_buffer(log_msg)

            if await handle_flood_wait(e, f"подписка на {channel_ref}", session_name):
                if retry_count < max_retries:
                    log_msg = f"🔄 [{session_name}] Повторная попытка {retry_count + 2}/{max_retries}..."
                    print(log_msg)
                    await add_to_log_buffer(log_msg)
                    return await subscribe_to_channel(client, channel_ref, session_name, retry_count + 1)
                else:
                    log_msg = f"❌ [{session_name}] Достигнуто максимальное количество попыток ({max_retries})"
                    print(log_msg)
                    await add_to_log_buffer(log_msg)
                    log_failed_subscription(session_name, channel_ref, "Максимальное количество попыток")
                    return False, "max_retries_reached"
            return False, "flood_timeout"

        except Exception as e:
            log_msg = f"❌ [{session_name}] Ошибка при подписке: {e}"
            print(log_msg)
            await add_to_log_buffer(log_msg)
            log_failed_subscription(session_name, channel_ref, str(e)[:100])
            return False, "subscribe_error"

    except Exception as e:
        log_msg = f"❌ [{session_name}] Ошибка при обработке канала: {e}"
        print(log_msg)
        await add_to_log_buffer(log_msg)
        log_failed_subscription(session_name, channel_ref, str(e)[:100])
        return False, "unknown_error"


async def subscribe_to_channels(client, message, session_name=""):
    """Подписывается на каналы из сообщения бота с обработкой флуда"""
    global flood_wait_occurred, total_flood_time

    # Сбрасываем счетчики для новой сессии подписок
    flood_wait_occurred = False
    total_flood_time = 0
    start_time = time.time()

    log_msg = "\n🔍 Ищем каналы для подписки..."
    print(log_msg)
    await add_to_log_buffer(log_msg)

    channels_to_join = await find_channels_in_message(client, message)

    if not channels_to_join:
        log_msg = "❌ Не найдены ссылки на каналы"
        print(log_msg)
        await add_to_log_buffer(log_msg)
        return False

    log_msg = f"\n🔍 Найдены каналы для подписки:"
    print(log_msg)
    await add_to_log_buffer(log_msg)

    for i, channel in enumerate(channels_to_join, 1):
        log_msg = f"  {i}. {channel}"
        print(log_msg)
        await add_to_log_buffer(log_msg)

    # Вступаем в каждый канал
    results = {
        "success": 0,
        "already_subscribed": 0,
        "failed": 0,
        "flood_wait": 0,
        "joined_by_invite": 0,
        "details": []
    }

    for i, channel_ref in enumerate(channels_to_join, 1):
        log_msg = f"\n{'─' * 40}"
        print(log_msg)
        await add_to_log_buffer(log_msg)

        log_msg = f"📌 Канал {i}/{len(channels_to_join)}"
        print(log_msg)
        await add_to_log_buffer(log_msg)

        log_msg = f"{'─' * 40}"
        print(log_msg)
        await add_to_log_buffer(log_msg)

        success, status = await subscribe_to_channel(client, channel_ref, session_name)

        if success:
            if status == "already_subscribed":
                results["already_subscribed"] += 1
                results["details"].append(f"ℹ️ {channel_ref} - уже подписаны")
            elif status == "joined_by_invite":
                results["success"] += 1
                results["joined_by_invite"] += 1
                results["details"].append(f"✅ {channel_ref} - присоединились по приглашению")
            else:
                results["success"] += 1
                results["details"].append(f"✅ {channel_ref} - успешно подписались")
        else:
            results["failed"] += 1
            if "flood" in status:
                results["flood_wait"] += 1
            results["details"].append(f"❌ {channel_ref} - {status}")

        # Пауза между каналами, если не было флуда
        if i < len(channels_to_join) and not flood_wait_occurred:
            log_msg = f"⏳ [{session_name}] Пауза {auto_subscribe_pause_between_channels} секунд перед следующим каналом..."
            print(log_msg)
            await add_to_log_buffer(log_msg)
            await asyncio.sleep(auto_subscribe_pause_between_channels)

    # Итоговая статистика
    total_time = time.time() - start_time

    log_msg = f"\n{'=' * 60}"
    print(log_msg)
    await add_to_log_buffer(log_msg)

    log_msg = f"📊 ИТОГОВАЯ СТАТИСТИКА ПОДПИСОК [{session_name}]"
    print(log_msg)
    await add_to_log_buffer(log_msg)

    log_msg = f"{'=' * 60}"
    print(log_msg)
    await add_to_log_buffer(log_msg)

    log_msg = f"✅ Успешно подписались: {results['success']}"
    print(log_msg)
    await add_to_log_buffer(log_msg)

    if results['joined_by_invite'] > 0:
        log_msg = f"   └ По ссылкам-приглашениям: {results['joined_by_invite']}"
        print(log_msg)
        await add_to_log_buffer(log_msg)

    log_msg = f"ℹ️ Уже были подписаны: {results['already_subscribed']}"
    print(log_msg)
    await add_to_log_buffer(log_msg)

    log_msg = f"❌ Не удалось подписаться: {results['failed']}"
    print(log_msg)
    await add_to_log_buffer(log_msg)

    if results['flood_wait'] > 0:
        log_msg = f"🚫 Из-за флуд-контроля: {results['flood_wait']}"
        print(log_msg)
        await add_to_log_buffer(log_msg)

    if total_flood_time > 0:
        log_msg = f"⏱️ Общее время ожидания флуда: {format_time(int(total_flood_time))}"
        print(log_msg)
        await add_to_log_buffer(log_msg)

    log_msg = f"⏱️ Общее время операции: {format_time(int(total_time))}"
    print(log_msg)
    await add_to_log_buffer(log_msg)

    if flood_wait_occurred:
        log_msg = f"\n⚠️ ВНИМАНИЕ: Во время подписки был обнаружен флуд-контроль!"
        print(log_msg)
        await add_to_log_buffer(log_msg)
        log_msg = f"   Рекомендуется сделать паузу перед следующим действием."
        print(log_msg)
        await add_to_log_buffer(log_msg)
        log_msg = f"   Рекомендуемая пауза: {format_time(min(total_flood_time * 2, 300))}"
        print(log_msg)
        await add_to_log_buffer(log_msg)

    log_msg = f"{'=' * 60}\n"
    print(log_msg)
    await add_to_log_buffer(log_msg)

    # Показываем детали по каждой ссылке
    log_msg = "📋 Детали по каждой ссылке:"
    print(log_msg)
    await add_to_log_buffer(log_msg)

    for detail in results["details"]:
        log_msg = f"   {detail}"
        print(log_msg)
        await add_to_log_buffer(log_msg)

    if results["success"] > 0 or results["already_subscribed"] > 0:
        return True
    return False


async def monitor_and_subscribe(client, session_name="", target_group=None):
    """Мониторит группу и подписывается при упоминании"""
    global flood_wait_occurred, total_flood_time

    if not target_group:
        return

    try:
        # Получаем информацию о пользователе
        me = await client.get_me()
        user_id = me.id
        username = me.username

        log_msg = f"\n🔄 [{session_name}] Запущен мониторинг группы {getattr(target_group, 'title', target_group)}"
        print(log_msg)
        await add_to_log_buffer(log_msg)

        log_msg = f"👤 [{session_name}] Аккаунт: {me.first_name} (@{username if username else 'нет юзернейма'})"
        print(log_msg)
        await add_to_log_buffer(log_msg)

        # Флаг для отслеживания упоминания
        mentioned = False
        subscription_complete = False

        @client.on(events.NewMessage(chats=target_group))
        async def mention_handler(event):
            nonlocal mentioned, subscription_complete

            if mentioned or stop_event.is_set():
                return

            # Проверяем упоминание по user_id
            if str(user_id) in event.message.text or (username and f"@{username}" in event.message.text):
                mentioned = True
                log_msg = f"\n🔔 [{session_name}] ПОЛУЧЕНО УПОМИНАНИЕ ОТ БОТА!"
                print(log_msg)
                await add_to_log_buffer(log_msg)

                log_msg = f"📩 Текст сообщения:\n{event.message.text[:200]}..."
                print(log_msg)
                await add_to_log_buffer(log_msg)

                # Подписываемся на каналы
                log_msg = f"\n🔄 [{session_name}] Начинаем процесс подписки..."
                print(log_msg)
                await add_to_log_buffer(log_msg)

                subscription_complete = await subscribe_to_channels(client, event.message, session_name)

                if subscription_complete:
                    log_msg = f"\n✅ [{session_name}] Все операции с каналами завершены!"
                    print(log_msg)
                    await add_to_log_buffer(log_msg)

        # Отправляем сообщение для активации бота
        log_msg = f"📤 [{session_name}] Отправляем сообщение для активации бота..."
        print(log_msg)
        await add_to_log_buffer(log_msg)

        await client.send_message(target_group, "s")
        log_msg = f"✅ [{session_name}] Сообщение отправлено, ожидаем упоминания (макс. {auto_subscribe_wait_for_mention} сек)..."
        print(log_msg)
        await add_to_log_buffer(log_msg)

        # Ждём упоминания и завершения подписки
        wait_time = 0
        max_wait_time = auto_subscribe_wait_for_mention

        while wait_time < max_wait_time and not stop_event.is_set():
            if mentioned and subscription_complete:
                log_msg = f"\n✅ [{session_name}] Все задачи выполнены!"
                print(log_msg)
                await add_to_log_buffer(log_msg)
                break
            elif mentioned and not subscription_complete:
                await asyncio.sleep(1)
                wait_time += 1
                if wait_time % 5 == 0:
                    log_msg = f"⏳ [{session_name}] Завершаем подписку... {wait_time}с"
                    print(log_msg)
                    await add_to_log_buffer(log_msg)
            else:
                await asyncio.sleep(1)
                wait_time += 1
                if wait_time % 5 == 0:
                    log_msg = f"⏳ [{session_name}] Ожидание упоминания... {wait_time}/{max_wait_time}с"
                    print(log_msg)
                    await add_to_log_buffer(log_msg)

        # Удаляем обработчик
        client.remove_event_handler(mention_handler)

        if wait_time >= max_wait_time:
            log_msg = f"\n⏰ [{session_name}] Время ожидания упоминания истекло ({max_wait_time}с) - продолжаем без подписки"
            print(log_msg)
            await add_to_log_buffer(log_msg)

    except Exception as e:
        log_msg = f"❌ [{session_name}] Ошибка в мониторинге: {e}"
        print(log_msg)
        await add_to_log_buffer(log_msg)
        traceback.print_exc()


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
                          media_file_path, recipient_filter, fast_mode_flag, fast_delay_val, target_chats_ids=None,
                          cycle_number=1):
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

        # Проверяем, нужно ли запускать автоподписку (только первый цикл)
        if auto_subscribe_enabled and auto_subscribe_first_cycle_only and cycle_number == 1:
            log_msg = f"🤖 [{account_info}] Запускаем проверку автоподписки (цикл 1)..."
            print(f"{Fore.MAGENTA}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg)

            # Получаем группы для мониторинга
            groups_to_monitor = []

            if target_chats_ids:
                # Если есть цели из файла, проверяем их
                for target in target_chats_ids:
                    if isinstance(target, str) and ('t.me' in target or '@' in target):
                        try:
                            entity = await client.get_entity(target)
                            if isinstance(entity, (Channel, Chat)) and not isinstance(entity, User):
                                groups_to_monitor.append(entity)
                        except:
                            pass
            else:
                # Иначе получаем все группы пользователя
                all_chats = await get_user_chats(client, "groups")
                groups_to_monitor.extend(all_chats)

            # Для каждой группы проверяем, нужно ли подписываться
            if groups_to_monitor:
                log_msg = f"🔍 [{account_info}] Проверяем {len(groups_to_monitor)} групп на необходимость подписки..."
                print(log_msg)
                await add_to_log_buffer(log_msg)

                for group in groups_to_monitor[:5]:  # Ограничим до 5 групп для производительности
                    if stop_event.is_set():
                        break

                    try:
                        await monitor_and_subscribe(client, account_info, group)
                    except Exception as e:
                        log_msg = f"⚠️ [{account_info}] Ошибка при проверке группы: {e}"
                        print(log_msg)
                        await add_to_log_buffer(log_msg)

                log_msg = f"✅ [{account_info}] Проверка автоподписки завершена"
                print(log_msg)
                await add_to_log_buffer(log_msg)
            else:
                log_msg = f"ℹ️ [{account_info}] Нет групп для проверки автоподписки"
                print(log_msg)
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

            current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]

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

    # Информация об автоподписке
    if auto_subscribe_enabled:
        if auto_subscribe_first_cycle_only:
            print(
                f"{Fore.MAGENTA}🤖 АВТОПОДПИСКА: Только 1-й цикл (ожидание {auto_subscribe_wait_for_mention}с){Style.RESET_ALL}")
        else:
            print(
                f"{Fore.MAGENTA}🤖 АВТОПОДПИСКА: Каждый цикл (ожидание {auto_subscribe_wait_for_mention}с){Style.RESET_ALL}")
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
                    target_chats_ids=target_chats_ids,
                    cycle_number=cycle_number
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

            # Показываем информацию о файле с неудачными подписками
            if os.path.exists(failed_subscriptions_file) and os.path.getsize(failed_subscriptions_file) > 0:
                print(f"{Fore.YELLOW}📋 Неудачные подписки сохранены в: {failed_subscriptions_file}{Style.RESET_ALL}")

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


# =============== НОВАЯ ФУНКЦИЯ ДЛЯ ЗАПУСКА АВТОПОДПИСКИ ===============
async def run_auto_subscribe(api_id, api_hash, session_files, target_group_link):
    """Запускает автоподписку для нескольких аккаунтов."""
    print("\n" + Fore.MAGENTA + "--- Запуск автоподписки на каналы ---" + Style.RESET_ALL)
    print(f"Сессий: {len(session_files)}")
    print(f"Целевая группа: {target_group_link}")
    print(f"Режим: {'По упоминанию' if auto_subscribe_on_mention else 'По расписанию'}")
    print(f"Макс. время ожидания упоминания: {auto_subscribe_wait_for_mention}с")
    print(f"Задержка между подписками: {auto_subscribe_pause_between_channels}с")
    print("---")

    tasks = []
    processed_session_files = []

    for i, session_file in enumerate(session_files):
        if stop_event.is_set():
            break

        task = asyncio.create_task(
            process_account_auto_subscribe(
                session_file, api_id, api_hash, target_group_link
            )
        )
        tasks.append(task)
        processed_session_files.append(session_file)

        # Задержка между запуском сессий
        if i < len(session_files) - 1:
            log_msg = f"\n⏳ Задержка {delay_between_accounts}с перед следующей сессией..."
            print(log_msg)
            await add_to_log_buffer(log_msg)
            await asyncio.sleep(delay_between_accounts)

    if tasks:
        results = await asyncio.gather(*tasks)

        successful = 0
        failed = 0

        for i, result in enumerate(results):
            if result:
                successful += 1
            else:
                failed += 1

        print("\n" + "=" * 50)
        print(f"{Fore.MAGENTA}     ✔ ОБЩАЯ СТАТИСТИКА АВТОПОДПИСКИ")
        print("=" * 50)
        print(f"{Fore.GREEN}✔ Успешно завершено: {successful}")
        print(f"{Fore.RED}✘ Ошибок: {failed}")
        print("=" * 50)

        if notify_cycle_results:
            notification_message = f"📊 **Результаты автоподписки**\n\n"
            notification_message += f"✅ Успешно: {successful}\n"
            notification_message += f"❌ Ошибок: {failed}\n"
            await send_notification(notification_message, "cycle_result")

    print(Fore.MAGENTA + "--- Автоподписка завершена ---" + Style.RESET_ALL)


async def process_account_auto_subscribe(session_file, api_id, api_hash, target_group_link):
    """Обрабатывает автоподписку для одного аккаунта."""
    client_session_name = os.path.join(session_folder, session_file.replace('.session', ''))
    client = TelegramClient(
        client_session_name, api_id, api_hash,
        connection_retries=5, timeout=20, request_retries=3, flood_sleep_threshold=60
    )

    account_info = "неавторизована"
    success = False

    try:
        await client.connect()

        if not await client.is_user_authorized():
            log_msg = f"✘ [{session_file}] НЕ АВТОРИЗОВАНА - ПРОПУЩЕНА"
            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg)
            log_invalid_session(session_file)
            return False

        try:
            me = await client.get_me()
            account_info = f"@{me.username or me.id}"
        except Exception as get_me_error:
            log_msg = f"✘ [{session_file}] Ошибка при получении информации о пользователе: {get_me_error}"
            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg)
            log_invalid_session(session_file)
            return False

        log_msg = f"\n⚙ Обработка сессии: {session_file} ({account_info})"
        print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg)

        # Получаем целевую группу
        try:
            target_group = await client.get_entity(target_group_link)
            log_msg = f"✅ [{account_info}] Найдена группа: {target_group.title}"
            print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg)
        except Exception as e:
            log_msg = f"❌ [{account_info}] Не удалось найти группу: {e}"
            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg)
            return False

        # Запускаем мониторинг и подписку
        await monitor_and_subscribe(client, account_info, target_group)

        log_msg = f"\n✅ [{account_info}] Процесс автоподписки завершен"
        print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg)
        success = True

    except Exception as e:
        log_msg = f"✘ [{account_info}] Ошибка: {str(e)[:60]}"
        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg)
        traceback.print_exc()
    finally:
        try:
            if client.is_connected():
                await client.disconnect()
        except:
            pass

    return success


async def display_auto_subscribe_menu():
    """Меню настроек автоподписки."""
    global auto_subscribe_enabled, auto_subscribe_on_mention, auto_subscribe_delay, auto_subscribe_max_flood_wait
    global auto_subscribe_retry_after_flood, auto_subscribe_check_interval, auto_subscribe_wait_for_mention
    global auto_subscribe_pause_between_channels, auto_subscribe_forced_channels, auto_subscribe_first_cycle_only

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_header("🤖 НАСТРОЙКИ АВТОПОДПИСКИ")

        print(
            f"{CLR_INFO}1. 🔄 Автоподписка: {CLR_SUCCESS if auto_subscribe_enabled else CLR_ERR}{'ВКЛ' if auto_subscribe_enabled else 'ВЫКЛ'}")
        print(
            f"{CLR_INFO}2. 🎯 Режим упоминания: {CLR_SUCCESS if auto_subscribe_on_mention else CLR_ERR}{'ВКЛ' if auto_subscribe_on_mention else 'ВЫКЛ'}")
        print(f"{CLR_INFO}3. ⏱️ Задержка между подписками: {CLR_WARN}{auto_subscribe_pause_between_channels}с")
        print(f"{CLR_INFO}4. ⏳ Макс. время ожидания флуда: {CLR_WARN}{auto_subscribe_max_flood_wait}с")
        print(
            f"{CLR_INFO}5. 🔄 Повтор после флуда: {CLR_SUCCESS if auto_subscribe_retry_after_flood else CLR_ERR}{'ВКЛ' if auto_subscribe_retry_after_flood else 'ВЫКЛ'}")
        print(f"{CLR_INFO}6. 🔍 Интервал проверки: {CLR_WARN}{auto_subscribe_check_interval}с")
        print(f"{CLR_INFO}7. ⏰ Макс. ожидание упоминания: {CLR_WARN}{auto_subscribe_wait_for_mention}с")
        print(
            f"{CLR_INFO}8. 🔂 Только первый цикл: {CLR_SUCCESS if auto_subscribe_first_cycle_only else CLR_ERR}{'ВКЛ' if auto_subscribe_first_cycle_only else 'ВЫКЛ'}")
        print(f"{CLR_INFO}9. 📋 Ручной список каналов (JSON формат)")

        if auto_subscribe_forced_channels:
            print(f"{CLR_INFO}   Текущий список: {CLR_WARN}{len(auto_subscribe_forced_channels)} каналов")
            for i, ch in enumerate(auto_subscribe_forced_channels[:3], 1):
                print(f"      {i}. {ch}")
            if len(auto_subscribe_forced_channels) > 3:
                print(f"      ... и еще {len(auto_subscribe_forced_channels) - 3}")

        print(f"{CLR_ERR}0. 🔙 Назад")

        choice = input(f"\n{CLR_MAIN}Выберите пункт ➔ {RESET}").strip()

        if choice == '1':
            auto_subscribe_enabled = not auto_subscribe_enabled
            print(
                f"{Fore.GREEN}✔ Автоподписка {'включена' if auto_subscribe_enabled else 'выключена'}.{Style.RESET_ALL}")

        elif choice == '2':
            auto_subscribe_on_mention = not auto_subscribe_on_mention
            print(
                f"{Fore.GREEN}✔ Режим упоминания {'включен' if auto_subscribe_on_mention else 'выключен'}.{Style.RESET_ALL}")

        elif choice == '3':
            try:
                new_value = float(
                    input(f"Задержка между подписками (сек, текущая: {auto_subscribe_pause_between_channels}): "))
                if new_value >= 0.5:
                    auto_subscribe_pause_between_channels = new_value
                    print(f"{Fore.GREEN}✔ Задержка обновлена.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}✘ Задержка должна быть не менее 0.5 сек.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}✘ Введите число.{Style.RESET_ALL}")

        elif choice == '4':
            try:
                new_value = int(input(f"Макс. время ожидания флуда (сек, текущее: {auto_subscribe_max_flood_wait}): "))
                if new_value >= 10:
                    auto_subscribe_max_flood_wait = new_value
                    print(f"{Fore.GREEN}✔ Время ожидания обновлено.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}✘ Время должно быть не менее 10 сек.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}✘ Введите число.{Style.RESET_ALL}")

        elif choice == '5':
            auto_subscribe_retry_after_flood = not auto_subscribe_retry_after_flood
            print(
                f"{Fore.GREEN}✔ Повтор после флуда {'включен' if auto_subscribe_retry_after_flood else 'выключен'}.{Style.RESET_ALL}")

        elif choice == '6':
            try:
                new_value = int(input(f"Интервал проверки (сек, текущий: {auto_subscribe_check_interval}): "))
                if new_value >= 1:
                    auto_subscribe_check_interval = new_value
                    print(f"{Fore.GREEN}✔ Интервал проверки обновлен.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}✘ Интервал должен быть не менее 1 сек.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}✘ Введите число.{Style.RESET_ALL}")

        elif choice == '7':
            try:
                new_value = int(input(f"Макс. ожидание упоминания (сек, текущее: {auto_subscribe_wait_for_mention}): "))
                if new_value >= 5:
                    auto_subscribe_wait_for_mention = new_value
                    print(f"{Fore.GREEN}✔ Время ожидания обновлено.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}✘ Время должно быть не менее 5 сек.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}✘ Введите число.{Style.RESET_ALL}")

        elif choice == '8':
            auto_subscribe_first_cycle_only = not auto_subscribe_first_cycle_only
            print(
                f"{Fore.GREEN}✔ Режим 'Только первый цикл' {'включен' if auto_subscribe_first_cycle_only else 'выключен'}.{Style.RESET_ALL}")

        elif choice == '9':
            print(f"{Fore.YELLOW}Введите список каналов в формате JSON, например:")
            print(f'["@channel1", "https://t.me/channel2", "t.me/+invite_hash"]')
            current = json.dumps(auto_subscribe_forced_channels, ensure_ascii=False)
            print(f"Текущий: {current}")

            new_list = input("Новый список (или Enter для очистки): ").strip()
            if new_list:
                try:
                    parsed = json.loads(new_list)
                    if isinstance(parsed, list):
                        auto_subscribe_forced_channels = parsed
                        print(f"{Fore.GREEN}✔ Список обновлен.{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}✘ Должен быть массив JSON.{Style.RESET_ALL}")
                except json.JSONDecodeError:
                    print(f"{Fore.RED}✘ Ошибка парсинга JSON.{Style.RESET_ALL}")
            else:
                auto_subscribe_forced_channels = []
                print(f"{Fore.GREEN}✔ Список очищен.{Style.RESET_ALL}")

        elif choice == '0':
            save_config()
            break

        await asyncio.sleep(1)


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
        print(f"{CLR_INFO}6. 🤖 Настройки автоподписки")  # Новый пункт
        print(f"{CLR_ACCENT}7. ♻️ Сброс настроек")
        print(f"{CLR_ERR}0. 🔙 Назад в меню")

        print(f"\n{CLR_WARN}Текущие значения:{Style.RESET_ALL}")
        print(f"  API ID: {current_api_id}")
        print(f"  Папка сессий: {session_folder}")
        print(f"  Сообщение: {message_to_send[:30]}...")
        if notification_enabled:
            print(f"  🔔 Уведомления: ВКЛ")
        if auto_subscribe_enabled:
            print(f"  🤖 Автоподписка: ВКЛ")

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

        elif choice == '6':  # Новый пункт - автоподписка
            await display_auto_subscribe_menu()

        elif choice == '7':
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
                    'notify_full_logs': DEFAULT_NOTIFY_FULL_LOGS,
                    # Сброс настроек автоподписки
                    'auto_subscribe_enabled': DEFAULT_AUTO_SUBSCRIBE_ENABLED,
                    'auto_subscribe_on_mention': DEFAULT_AUTO_SUBSCRIBE_ON_MENTION,
                    'auto_subscribe_delay': DEFAULT_AUTO_SUBSCRIBE_DELAY,
                    'auto_subscribe_max_flood_wait': DEFAULT_AUTO_SUBSCRIBE_MAX_FLOOD_WAIT,
                    'auto_subscribe_retry_after_flood': DEFAULT_AUTO_SUBSCRIBE_RETRY_AFTER_FLOOD,
                    'auto_subscribe_check_interval': DEFAULT_AUTO_SUBSCRIBE_CHECK_INTERVAL,
                    'auto_subscribe_wait_for_mention': DEFAULT_AUTO_SUBSCRIBE_WAIT_FOR_MENTION,
                    'auto_subscribe_pause_between_channels': DEFAULT_AUTO_SUBSCRIBE_PAUSE_BETWEEN_CHANNELS,
                    'auto_subscribe_forced_channels': DEFAULT_AUTO_SUBSCRIBE_FORCED_CHANNELS,
                    'auto_subscribe_first_cycle_only': DEFAULT_AUTO_SUBSCRIBE_FIRST_CYCLE_ONLY
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
    global auto_subscribe_enabled, auto_subscribe_on_mention, auto_subscribe_delay
    global auto_subscribe_max_flood_wait, auto_subscribe_retry_after_flood
    global auto_subscribe_check_interval, auto_subscribe_wait_for_mention
    global auto_subscribe_pause_between_channels, auto_subscribe_forced_channels, auto_subscribe_first_cycle_only
    global flood_wait_occurred, total_flood_time

    load_config()
    os.makedirs(session_folder, exist_ok=True)

    # Очищаем файл с неудачными подписками при запуске
    clear_failed_subscriptions_file()

    # Проверяем реальную версию в файле
    file_version = update_manager.verify_version_in_file()
    if file_version and file_version != CURRENT_VERSION:
        print(f"{Fore.YELLOW}⚠️ Обновляю версию в памяти: {CURRENT_VERSION} -> {file_version}{Style.RESET_ALL}")
        CURRENT_VERSION = file_version
        save_config()

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
        print(f"{CLR_ACCENT}║{CLR_MAIN}     🚀 LITEGAMMA TOOLS❤️  |  FULL VERSION          {CLR_ACCENT}║")
        print(f"{CLR_ACCENT}║{CLR_INFO}       С уважением : @BananaStorebot_bot           {CLR_ACCENT}║")
        print(f"{CLR_ACCENT}╚═══════════════════════════════════════════════════╝")

        print(f"\n{CLR_SUCCESS}  [1] ➔  🚀 ЗАПУСТИТЬ РАССЫЛКУ")
        print(f"{CLR_SUCCESS}  [2] ➔  🔗 ВСТУПИТЬ В ГРУППЫ (из enter.json)")
        print(f"{CLR_MAIN}  [3] ➔  ⚙️  НАСТРОЙКИ СИСТЕМЫ")
        print(f"{CLR_INFO}  [4] ➔  📂  МОИ СЕССИИ (ИНФО)")
        print(f"{CLR_ACCENT}  [5] ➔  ➕  ДОБАВИТЬ АККАУНТ")
        print(f"{CLR_ACCENT}  [6] ➔  🔄  ОБНОВЛЕНИЯ")
        #print(f"{CLR_INFO}  [7] ➔  🤖  АВТОПОДПИСКА НА КАНАЛЫ")  # Новый пункт
        print(f"{CLR_ERR}  [7] ➔  🚪  ВЫЙТИ")

        print(f"\n{CLR_ACCENT}─────────────────────────────────────────────────────")

        if fast_mode:
            print(f"{Fore.YELLOW}⚡ ТЕКУЩИЙ РЕЖИМ: БЫСТРЫЙ (задержка {fast_delay}с){Style.RESET_ALL}")
        if repeat_broadcast:
            print(f"{Fore.CYAN}🔄 ПОВТОР ВКЛЮЧЕН (интервал {repeat_interval}с){Style.RESET_ALL}")
        if notification_enabled:
            print(f"{Fore.GREEN}🔔 УВЕДОМЛЕНИЯ ВКЛЮЧЕНЫ{Style.RESET_ALL}")
        if auto_subscribe_enabled:
            mode = "ТОЛЬКО 1-Й ЦИКЛ" if auto_subscribe_first_cycle_only else "КАЖДЫЙ ЦИКЛ"
            print(f"{Fore.MAGENTA}🤖 АВТОПОДПИСКА ВКЛЮЧЕНА ({mode}){Style.RESET_ALL}")
        print(f"{Fore.CYAN}📦 Версия: {CURRENT_VERSION}{Style.RESET_ALL}")

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
            if auto_subscribe_enabled:
                print(
                    f"{Fore.MAGENTA}🤖 Автоподписка: ВКЛЮЧЕНА (ожидание {auto_subscribe_wait_for_mention}с){Style.RESET_ALL}")

            if input("\n🚀 Запустить рассылку параллельно? (y/n): ").lower() == 'y':
                print("\n" + Fore.MAGENTA + "🚀 Запуск рассылки..." + Style.RESET_ALL)
                await run_broadcast(current_api_id, current_api_hash, selected_sessions, message_to_send,
                                    max_messages_per_account, repeat_broadcast, repeat_interval, delete_after_send,
                                    use_media, media_path, recipient_type,
                                    fast_mode, fast_delay,
                                    target_chats_ids=target_groups_file_data,
                                    cycle_number=1)
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
        elif choice == '9':  # НОВЫЙ ПУНКТ - Автоподписка
            if current_api_id == DEFAULT_API_ID or not current_api_hash or current_api_hash == "ЗАМЕНИТЕ НА ВАШ API HASH, ТАКЖЕ НАСТРОЙТЕ API ID ":
                print(
                    "\n" + Fore.YELLOW + "[!] ВНИМАНИЕ: Настройте API ID и API Hash в меню '3. Настройки'" + Style.RESET_ALL)
                input("Нажмите Enter...")
                continue

            if not auto_subscribe_enabled:
                print(f"\n{Fore.YELLOW}⚠️ Автоподписка отключена в настройках!{Style.RESET_ALL}")
                if input("Включить сейчас? (y/n): ").lower() == 'y':
                    auto_subscribe_enabled = True
                    save_config()
                else:
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

            print(f"\n{Fore.CYAN}● Выберите сессии для автоподписки:")
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

            target_group = input(
                f"\n{Fore.CYAN}Введите ссылку на группу для мониторинга (например, @group или https://t.me/group): {Style.RESET_ALL}").strip()
            if not target_group:
                print(f"{Fore.RED}✘ Ссылка на группу не введена.{Style.RESET_ALL}")
                continue

            print(f"\n{Fore.CYAN}ℹ Параметры автоподписки:")
            print(f"📋 Сессий: {len(selected_sessions)}")
            print(f"🎯 Целевая группа: {target_group}")
            print(f"⏳ Задержка между подписками: {auto_subscribe_pause_between_channels}с")
            print(f"⏰ Макс. ожидание упоминания: {auto_subscribe_wait_for_mention}с")

            if input("\n🚀 Запустить автоподписку? (y/n): ").lower() == 'y':
                print("\n" + Fore.MAGENTA + "🤖 Запуск автоподписки..." + Style.RESET_ALL)
                await run_auto_subscribe(current_api_id, current_api_hash, selected_sessions, target_group)
                input("Нажмите Enter для продолжения...")

        elif choice == '7':
            save_config()
            await close_notification_client()
            print(f"{Fore.CYAN}🚪 До свидания!{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}✘ Выберите 1-8{Style.RESET_ALL}")
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
