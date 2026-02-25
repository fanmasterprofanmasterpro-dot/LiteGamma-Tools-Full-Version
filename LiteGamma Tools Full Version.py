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
import random
import webbrowser
import threading
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat, User, MessageEntityMention, MessageEntityMentionName, MessageEntityTextUrl, \
    MessageEntityUrl
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
from telethon.tl.functions.chatlists import CheckChatlistInviteRequest, JoinChatlistInviteRequest
from telethon.errors import FloodWaitError, ChannelPrivateError, ChatAdminRequiredError, UserPrivacyRestrictedError, \
    AuthKeyUnregisteredError, PhoneCodeInvalidError, SessionPasswordNeededError, PhoneNumberInvalidError, \
    PasswordHashInvalidError, RPCError, InviteHashExpiredError, InviteHashInvalidError, UserAlreadyParticipantError, \
    UsernameNotOccupiedError, InviteRequestSentError, InviteHashEmptyError, PhoneCodeExpiredError
from colorama import init, Fore, Style
from datetime import datetime, timedelta
import socks

GITHUB_USER = "fanmasterprofanmasterpro-dot" 
GITHUB_REPO = "LiteGamma-Tools-Full-Version"
GITHUB_BRANCH = "main"
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}"
CURRENT_VERSION = "1.8.2"
UPDATE_CHECK_INTERVAL = 3600
LAST_UPDATE_CHECK_FILE = "last_update_check.json"
AUTO_UPDATE = True
NOTIFY_ON_UPDATE = True

init(autoreset=True)

CLR_MAIN = Fore.CYAN + Style.BRIGHT
CLR_ACCENT = Fore.MAGENTA + Style.BRIGHT
CLR_SUCCESS = Fore.GREEN + Style.BRIGHT
CLR_WARN = Fore.YELLOW + Style.BRIGHT
CLR_ERR = Fore.RED + Style.BRIGHT
CLR_INFO = Fore.BLUE + Style.BRIGHT
CLR_PROXY = Fore.LIGHTMAGENTA_EX + Style.BRIGHT
BR = Style.BRIGHT
RESET = Style.RESET_ALL

AUTO_SUBSCRIBE_ENABLED = False
AUTO_SUBSCRIBE_ON_MENTION = True
AUTO_SUBSCRIBE_DELAY = 3
AUTO_SUBSCRIBE_MAX_FLOOD_WAIT = 300
AUTO_SUBSCRIBE_RETRY_AFTER_FLOOD = True
AUTO_SUBSCRIBE_CHECK_INTERVAL = 5
AUTO_SUBSCRIBE_WAIT_FOR_MENTION = 10
AUTO_SUBSCRIBE_PAUSE_BETWEEN_CHANNELS = 3
AUTO_SUBSCRIBE_FORCED_CHANNELS = []
AUTO_SUBSCRIBE_FIRST_CYCLE_ONLY = True

CHANNEL_PATTERNS = [r'@(\w+)', r'https://t\.me/(\w+)', r't\.me/(\w+)', r'telegram\.me/(\w+)', r'joinchat/([\w\-]+)',
                    r'\+([\w\-]+)']
flood_wait_occurred = False 
total_flood_time = 0
failed_subscriptions_file = "failed_subscriptions.txt"


class LogManager:
    def __init__(self):
        self.logs = []
        self.logs_by_category = {
            'success': [],
            'error': [],
            'warning': [],
            'info': [],
            'proxy': [],
            'flood': [],
            'system': []
        }
        self.lock = asyncio.Lock()
        self.html_file = None
        self.server = None
        self.server_thread = None
        self.port = self.find_free_port()

    def find_free_port(self):
        for port in range(8080, 9000):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return port
            except:
                continue
        return 8080

    def cleanup_old_logs(self):
        """Удаляет старые HTML файлы логов"""
        try:
            for file in Path('.').glob('logs_*.html'):
                try:
                    if self.html_file and file.name != os.path.basename(self.html_file):
                        os.remove(file)
                        print(f"{Fore.CYAN}🧹 Удален старый лог-файл: {file}{Style.RESET_ALL}")
                except:
                    pass
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Ошибка при очистке старых логов: {e}{Style.RESET_ALL}")

    def generate_html_file(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
        self.html_file = f"logs_{timestamp}_{random_suffix}.html"

        # Сначала удаляем старые файлы, кроме текущего
        self.cleanup_old_logs()

        html_template = """<!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>LiteGamma Tools - Логи мониторинга</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }

                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }

                .container {
                    max-width: 1400px;
                    margin: 0 auto;
                }

                .header {
                    background: rgba(255, 255, 255, 0.95);
                    border-radius: 15px;
                    padding: 25px;
                    margin-bottom: 25px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    backdrop-filter: blur(10px);
                }

                .header h1 {
                    color: #333;
                    font-size: 28px;
                    margin-bottom: 10px;
                }

                .header h1 span {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }

                .stats-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-top: 20px;
                }

                .stat-card {
                    background: white;
                    border-radius: 12px;
                    padding: 20px;
                    text-align: center;
                    box-shadow: 0 5px 20px rgba(0,0,0,0.1);
                    transition: transform 0.3s;
                }

                .stat-card:hover {
                    transform: translateY(-5px);
                }

                .stat-card .value {
                    font-size: 36px;
                    font-weight: bold;
                    margin-bottom: 5px;
                }

                .stat-card .label {
                    color: #666;
                    font-size: 14px;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }

                .stat-card.success .value { color: #10b981; }
                .stat-card.error .value { color: #ef4444; }
                .stat-card.warning .value { color: #f59e0b; }
                .stat-card.info .value { color: #3b82f6; }
                .stat-card.proxy .value { color: #8b5cf6; }

                .controls {
                    display: flex;
                    gap: 10px;
                    margin-bottom: 20px;
                }

                .refresh-btn {
                    padding: 12px 25px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
                }

                .refresh-btn:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 8px 20px rgba(102, 126, 234, 0.6);
                }

                .refresh-btn:active {
                    transform: translateY(0);
                }

                .refresh-btn svg {
                    width: 20px;
                    height: 20px;
                    transition: transform 0.5s;
                }

                .refresh-btn:hover svg {
                    transform: rotate(180deg);
                }

                .filters {
                    background: white;
                    border-radius: 12px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 5px 20px rgba(0,0,0,0.1);
                    flex: 1;
                }

                .filter-buttons {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 10px;
                    margin-bottom: 15px;
                }

                .filter-btn {
                    padding: 10px 20px;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s;
                    background: #f3f4f6;
                    color: #4b5563;
                }

                .filter-btn:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                }

                .filter-btn.active {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }

                .filter-btn.success.active { background: #10b981; }
                .filter-btn.error.active { background: #ef4444; }
                .filter-btn.warning.active { background: #f59e0b; }
                .filter-btn.info.active { background: #3b82f6; }
                .filter-btn.proxy.active { background: #8b5cf6; }
                .filter-btn.flood.active { background: #ec4899; }

                .search-box {
                    width: 100%;
                    padding: 12px 20px;
                    border: 2px solid #e5e7eb;
                    border-radius: 8px;
                    font-size: 14px;
                    transition: border-color 0.3s;
                }

                .search-box:focus {
                    outline: none;
                    border-color: #667eea;
                }

                .logs-container {
                    background: white;
                    border-radius: 12px;
                    padding: 20px;
                    box-shadow: 0 5px 20px rgba(0,0,0,0.1);
                }

                .logs-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                    padding-bottom: 15px;
                    border-bottom: 2px solid #f3f4f6;
                }

                .logs-title {
                    font-size: 18px;
                    font-weight: 600;
                    color: #333;
                }

                .log-actions {
                    display: flex;
                    gap: 10px;
                }

                .clear-btn, .top-btn {
                    padding: 8px 16px;
                    background: #f3f4f6;
                    border: none;
                    border-radius: 6px;
                    color: #4b5563;
                    cursor: pointer;
                    transition: all 0.3s;
                    display: flex;
                    align-items: center;
                    gap: 5px;
                }

                .clear-btn:hover, .top-btn:hover {
                    background: #e5e7eb;
                }

                .top-btn.active {
                    background: #667eea;
                    color: white;
                }

                .logs-list {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }

                .log-entry {
                    padding: 12px 15px;
                    border-radius: 8px;
                    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                    font-size: 13px;
                    line-height: 1.5;
                    animation: slideIn 0.3s;
                    position: relative;
                    overflow: hidden;
                }

                .log-entry::before {
                    content: '';
                    position: absolute;
                    left: 0;
                    top: 0;
                    bottom: 0;
                    width: 4px;
                }

                .log-entry.success {
                    background: #d1fae5;
                    border-left: 4px solid #10b981;
                }
                .log-entry.success::before { background: #10b981; }

                .log-entry.error {
                    background: #fee2e2;
                    border-left: 4px solid #ef4444;
                }
                .log-entry.error::before { background: #ef4444; }

                .log-entry.warning {
                    background: #ffedd5;
                    border-left: 4px solid #f59e0b;
                }
                .log-entry.warning::before { background: #f59e0b; }

                .log-entry.info {
                    background: #dbeafe;
                    border-left: 4px solid #3b82f6;
                }
                .log-entry.info::before { background: #3b82f6; }

                .log-entry.proxy {
                    background: #ede9fe;
                    border-left: 4px solid #8b5cf6;
                }
                .log-entry.proxy::before { background: #8b5cf6; }

                .log-entry.flood {
                    background: #fce7f3;
                    border-left: 4px solid #ec4899;
                }
                .log-entry.flood::before { background: #ec4899; }

                .log-entry.system {
                    background: #f3f4f6;
                    border-left: 4px solid #6b7280;
                }
                .log-entry.system::before { background: #6b7280; }

                .log-time {
                    color: #6b7280;
                    font-size: 12px;
                    margin-right: 15px;
                    display: inline-block;
                }

                .log-category {
                    display: inline-block;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                    text-transform: uppercase;
                    margin-right: 10px;
                }

                .log-category.success { background: #10b981; color: white; }
                .log-category.error { background: #ef4444; color: white; }
                .log-category.warning { background: #f59e0b; color: white; }
                .log-category.info { background: #3b82f6; color: white; }
                .log-category.proxy { background: #8b5cf6; color: white; }
                .log-category.flood { background: #ec4899; color: white; }
                .log-category.system { background: #6b7280; color: white; }

                .log-message {
                    color: #1f2937;
                }

                .stats-summary {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 15px;
                    margin-bottom: 20px;
                }

                .stat-item {
                    background: #f9fafb;
                    border-radius: 8px;
                    padding: 15px;
                    text-align: center;
                }

                .stat-label {
                    color: #6b7280;
                    font-size: 12px;
                    margin-bottom: 5px;
                }

                .stat-number {
                    font-size: 24px;
                    font-weight: bold;
                }

                @keyframes slideIn {
                    from {
                        opacity: 0;
                        transform: translateY(-20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }

                .proxy-info {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 15px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                }

                .proxy-stats {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 10px;
                    margin-top: 10px;
                }

                .proxy-stat {
                    background: rgba(255,255,255,0.2);
                    padding: 10px;
                    border-radius: 8px;
                    text-align: center;
                }

                .footer {
                    text-align: center;
                    margin-top: 20px;
                    padding: 20px;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                    backdrop-filter: blur(5px);
                }

                .footer-content {
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }

                .footer-links {
                    display: flex;
                    justify-content: center;
                    gap: 20px;
                    flex-wrap: wrap;
                }

                .footer-link {
                    color: white;
                    text-decoration: none;
                    padding: 8px 16px;
                    background: rgba(255, 255, 255, 0.2);
                    border-radius: 20px;
                    transition: all 0.3s;
                    font-size: 14px;
                }

                .footer-link:hover {
                    background: rgba(255, 255, 255, 0.3);
                    transform: translateY(-2px);
                }

                .footer-link i {
                    margin-right: 5px;
                }

                .footer-copyright {
                    color: rgba(255, 255, 255, 0.8);
                    font-size: 12px;
                }

                .footer-copyright a {
                    color: white;
                    text-decoration: none;
                    font-weight: 600;
                }

                .footer-copyright a:hover {
                    text-decoration: underline;
                }

                .version-badge {
                    display: inline-block;
                    padding: 4px 12px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: 600;
                    margin-left: 10px;
                }

                .loading {
                    display: inline-block;
                    width: 20px;
                    height: 20px;
                    border: 3px solid rgba(255,255,255,.3);
                    border-radius: 50%;
                    border-top-color: white;
                    animation: spin 1s ease-in-out infinite;
                }

                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 <span>LiteGamma Tools</span> <span class="version-badge">v""" + CURRENT_VERSION + """</span></h1>
                    <p>Мониторинг логов в реальном времени</p>
                    <div class="stats-grid" id="statsGrid"></div>
                </div>

                <div class="controls">
                    <button class="refresh-btn" onclick="refreshLogs()">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M1 4v6h6"></path>
                            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
                        </svg>
                        Обновить логи
                    </button>

                    <div class="filters">
                        <div class="filter-buttons">
                            <button class="filter-btn active" onclick="filterLogs('all')">📋 Все</button>
                            <button class="filter-btn success" onclick="filterLogs('success')">✅ Успешно</button>
                            <button class="filter-btn error" onclick="filterLogs('error')">❌ Ошибки</button>
                            <button class="filter-btn warning" onclick="filterLogs('warning')">⚠️ Предупреждения</button>
                            <button class="filter-btn info" onclick="filterLogs('info')">ℹ️ Информация</button>
                            <button class="filter-btn proxy" onclick="filterLogs('proxy')">🌐 Прокси</button>
                            <button class="filter-btn flood" onclick="filterLogs('flood')">🚫 Флуд</button>
                        </div>
                        <input type="text" class="search-box" id="searchInput" placeholder="🔍 Поиск по логам..." onkeyup="filterLogs()">
                    </div>
                </div>

                <div class="proxy-info" id="proxyInfo"></div>

                <div class="logs-container">
                    <div class="logs-header">
                        <span class="logs-title" id="logsTitle">📋 Все логи</span>
                        <div class="log-actions">
                            <button class="top-btn" id="topBtn" onclick="toggleTop()" title="Новые логи сверху">
                                ⬆️ Сверху
                            </button>
                            <button class="clear-btn" onclick="clearLogs()">🗑 Очистить</button>
                        </div>
                    </div>
                    <div class="logs-list" id="logs"></div>
                </div>

                <div class="footer">
<div class="footer-links">
    <a href="https://t.me/BananaStorebot_bot" target="_blank" class="footer-link">
        🤖 Магазин @BananaStorebot_bot
    </a>
    <a href="https://t.me/LiteGamma" target="_blank" class="footer-link">
        👨‍💻 Связь с разработчиком @LiteGamma
    </a>
    <a href="https://t.me/LiteGammaTools" target="_blank" class="footer-link">
        📢 Канал обновлений @LiteGammaTools
    </a>
</div>
<div class="footer-copyright">
    С уважением, <a href="https://t.me/BananaStorebot_bot" target="_blank">@BananaStorebot_bot</a> | 
    <a href="https://t.me/LiteGamma" target="_blank">@LiteGamma</a> |
    <a href="https://t.me/LiteGammaTools" target="_blank">@LiteGammaTools</a>
</div>
<div class="update-info" style="margin-top: 10px; font-size: 12px; color: rgba(255,255,255,0.6);">
    Информацию об обновлениях можно узнать здесь: 
    <a href="https://t.me/LiteGammaTools" target="_blank" style="color: #ffd700; text-decoration: none;">
        https://t.me/LiteGammaTools
    </a>
</div>
                    </div>
                </div>
            </div>

            <script>
                let allLogs = [];
                let currentFilter = 'all';
                let searchTerm = '';
                let newOnTop = true;

                function updateStats() {
                    const stats = {
                        success: allLogs.filter(l => l.category === 'success').length,
                        error: allLogs.filter(l => l.category === 'error').length,
                        warning: allLogs.filter(l => l.category === 'warning').length,
                        info: allLogs.filter(l => l.category === 'info').length,
                        proxy: allLogs.filter(l => l.category === 'proxy').length,
                        flood: allLogs.filter(l => l.category === 'flood').length
                    };

                    document.getElementById('statsGrid').innerHTML = `
                        <div class="stat-card success">
                            <div class="value">${stats.success}</div>
                            <div class="label">✅ Успешно</div>
                        </div>
                        <div class="stat-card error">
                            <div class="value">${stats.error}</div>
                            <div class="label">❌ Ошибки</div>
                        </div>
                        <div class="stat-card warning">
                            <div class="value">${stats.warning}</div>
                            <div class="label">⚠️ Предупреждения</div>
                        </div>
                        <div class="stat-card info">
                            <div class="value">${stats.info}</div>
                            <div class="label">ℹ️ Информация</div>
                        </div>
                        <div class="stat-card proxy">
                            <div class="value">${stats.proxy}</div>
                            <div class="label">🌐 Прокси</div>
                        </div>
                        <div class="stat-card flood">
                            <div class="value">${stats.flood}</div>
                            <div class="label">🚫 Флуд</div>
                        </div>
                    `;
                }

                function toggleTop() {
                    newOnTop = !newOnTop;
                    const btn = document.getElementById('topBtn');
                    if (newOnTop) {
                        btn.innerHTML = '⬆️ Сверху';
                        btn.classList.add('active');
                    } else {
                        btn.innerHTML = '⬇️ Снизу';
                        btn.classList.remove('active');
                    }
                    displayLogs();
                }

                function filterLogs(category) {
                    if (category) {
                        currentFilter = category;
                        document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
                        event.target.classList.add('active');

                        const titles = {
                            'all': '📋 Все логи',
                            'success': '✅ Успешные операции',
                            'error': '❌ Ошибки',
                            'warning': '⚠️ Предупреждения',
                            'info': 'ℹ️ Информация',
                            'proxy': '🌐 Прокси',
                            'flood': '🚫 Флуд'
                        };
                        document.getElementById('logsTitle').textContent = titles[category] || '📋 Все логи';
                    }

                    searchTerm = document.getElementById('searchInput').value.toLowerCase();
                    displayLogs();
                }

                function displayLogs() {
                    let filtered = allLogs;

                    if (currentFilter !== 'all') {
                        filtered = filtered.filter(log => log.category === currentFilter);
                    }

                    if (searchTerm) {
                        filtered = filtered.filter(log => 
                            log.message.toLowerCase().includes(searchTerm) ||
                            log.time.toLowerCase().includes(searchTerm)
                        );
                    }

                    // Сортируем логи: новые сверху или снизу
                    const sortedLogs = newOnTop ? [...filtered].reverse() : filtered;

                    const logsHtml = sortedLogs.map(log => `
                        <div class="log-entry ${log.category}">
                            <span class="log-time">${log.time}</span>
                            <span class="log-category ${log.category}">${log.category}</span>
                            <span class="log-message">${log.message}</span>
                        </div>
                    `).join('');

                    document.getElementById('logs').innerHTML = logsHtml || '<div style="text-align: center; padding: 30px; color: #999;">Нет логов для отображения</div>';
                }

                function updateProxyInfo(info) {
                    document.getElementById('proxyInfo').innerHTML = info;
                }

                function clearLogs() {
                    fetch('/clear_logs', { method: 'POST' })
                        .then(() => {
                            allLogs = [];
                            displayLogs();
                            updateStats();
                        });
                }

                function refreshLogs() {
                    const btn = document.querySelector('.refresh-btn');
                    btn.innerHTML = '<span class="loading"></span> Загрузка...';
                    btn.disabled = true;

                    fetch('/logs')
                        .then(response => response.json())
                        .then(data => {
                            allLogs = data.logs;
                            displayLogs();
                            updateStats();
                            if (data.proxy_info) {
                                updateProxyInfo(data.proxy_info);
                            }
                        })
                        .finally(() => {
                            btn.innerHTML = `
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M1 4v6h6"></path>
                                    <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
                                </svg>
                                Обновить логи
                            `;
                            btn.disabled = false;
                        });
                }

                // Первая загрузка
                refreshLogs();
            </script>
        </body>
        </html>"""

        with open(self.html_file, 'w', encoding='utf-8') as f:
            f.write(html_template)

        print(f"{Fore.GREEN}📊 Веб-интерфейс создан: {self.html_file}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🌐 Откройте в браузере: http://localhost:{self.port}{Style.RESET_ALL}")

    def start_server(self):
        class LogHandler(BaseHTTPRequestHandler):
            log_manager = self

            def do_GET(self):
                try:
                    if self.path == '/':
                        self.send_response(302)
                        self.send_header('Location', f'http://localhost:{self.log_manager.port}/logs.html')
                        self.end_headers()
                    elif self.path == '/logs.html':
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html; charset=utf-8')
                        self.end_headers()
                        if self.log_manager.html_file and os.path.exists(self.log_manager.html_file):
                            with open(self.log_manager.html_file, 'rb') as f:
                                self.wfile.write(f.read())
                        else:
                            self.wfile.write(b"<h1>Log file not found</h1>")
                    elif self.path == '/logs':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()

                        logs_data = []

                        async def get_logs():
                            async with self.log_manager.lock:
                                for log in self.log_manager.logs[-500:]:
                                    logs_data.append({
                                        'time': log['time'],
                                        'category': log['category'],
                                        'message': log['message']
                                    })

                        asyncio.run(get_logs())

                        proxy_info = ""
                        if use_proxy and proxy_manager.has_proxies():
                            proxy_info = f"""
                            <div class="proxy-stats">
                                <div class="proxy-stat">📊 Всего прокси: {proxy_manager.get_proxy_count()}</div>
                                <div class="proxy-stat">✅ Активных прокси : {proxy_manager.get_proxy_count() - len(proxy_manager.bad_proxies)}</div>
                                <div class="proxy-stat">❌ Плохих прокси: {len(proxy_manager.bad_proxies)}</div>
                            </div>
                            """

                        response = {
                            'logs': logs_data,
                            'proxy_info': proxy_info
                        }
                        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
                    else:
                        self.send_response(404)
                        self.end_headers()
                except Exception as e:
                    print(f"{Fore.RED}✘ Ошибка в HTTP сервере: {e}{Style.RESET_ALL}")
                    try:
                        self.send_response(500)
                        self.end_headers()
                    except:
                        pass

            def do_POST(self):
                try:
                    if self.path == '/clear_logs':
                        async def clear():
                            async with self.log_manager.lock:
                                self.log_manager.logs.clear()
                                for cat in self.log_manager.logs_by_category:
                                    self.log_manager.logs_by_category[cat].clear()

                        asyncio.run(clear())
                        self.send_response(200)
                        self.end_headers()
                    else:
                        self.send_response(404)
                        self.end_headers()
                except Exception as e:
                    print(f"{Fore.RED}✘ Ошибка в HTTP сервере: {e}{Style.RESET_ALL}")
                    try:
                        self.send_response(500)
                        self.end_headers()
                    except:
                        pass

            def log_message(self, format, *args):
                pass

        self.server = HTTPServer(('localhost', self.port), LogHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

        webbrowser.open(f'http://localhost:{self.port}/logs.html')

    def stop_server(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    async def add_log(self, message, category='info'):
        async with self.lock:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = {
                'time': timestamp,
                'category': category,
                'message': message
            }
            self.logs.append(log_entry)
            self.logs_by_category[category].append(log_entry)

            if len(self.logs) > 2000:
                self.logs = self.logs[-2000:]
                for cat in self.logs_by_category:
                    if len(self.logs_by_category[cat]) > 500:
                        self.logs_by_category[cat] = self.logs_by_category[cat][-500:]

class AccountProtector:
    def __init__(self):
        self.account_actions = {}
        self.daily_limits = {}
        self.account_age = {}
        self.last_action_time = {}
        self.action_history = {}
        self.warnings = {}

    def register_account(self, session_name, account_age_days=0):
        if session_name not in self.account_actions:
            self.account_actions[session_name] = {
                'messages_sent': 0,
                'channels_joined': 0,
                'groups_joined': 0,
                'last_message_time': None,
                'daily_message_count': 0,
                'daily_join_count': 0,
                'last_reset_date': datetime.now().date()
            }
            self.account_age[session_name] = account_age_days
            self.last_action_time[session_name] = time.time()
            self.action_history[session_name] = []
            self.warnings[session_name] = []

    def check_daily_reset(self, session_name):
        if session_name in self.account_actions:
            today = datetime.now().date()
            if self.account_actions[session_name]['last_reset_date'] != today:
                self.account_actions[session_name]['daily_message_count'] = 0
                self.account_actions[session_name]['daily_join_count'] = 0
                self.account_actions[session_name]['last_reset_date'] = today

    def can_send_message(self, session_name):
        if session_name not in self.account_actions:
            return True, 0
        self.check_daily_reset(session_name)
        age_days = self.account_age.get(session_name, 0)
        if age_days < 1:
            limit = 20
        elif age_days < 3:
            limit = 50
        elif age_days < 7:
            limit = 100
        elif age_days < 30:
            limit = 200
        else:
            limit = 500
        current = self.account_actions[session_name]['daily_message_count']
        if current >= limit:
            return False, limit
        return True, limit - current

    def can_join_channel(self, session_name):
        if session_name not in self.account_actions:
            return True, 0
        self.check_daily_reset(session_name)
        age_days = self.account_age.get(session_name, 0)
        if age_days < 1:
            limit = 10
        elif age_days < 3:
            limit = 25
        elif age_days < 7:
            limit = 50
        elif age_days < 30:
            limit = 100
        else:
            limit = 200
        current = self.account_actions[session_name]['daily_join_count']
        if current >= limit:
            return False, limit
        return True, limit - current

    def record_message_sent(self, session_name):
        if session_name in self.account_actions:
            self.account_actions[session_name]['messages_sent'] += 1
            self.account_actions[session_name]['daily_message_count'] += 1
            self.account_actions[session_name]['last_message_time'] = datetime.now()
            self.last_action_time[session_name] = time.time()
            self.action_history[session_name].append(('message', time.time()))
            if len(self.action_history[session_name]) > 100:
                self.action_history[session_name] = self.action_history[session_name][-100:]

    def record_join(self, session_name, is_channel=True):
        if session_name in self.account_actions:
            if is_channel:
                self.account_actions[session_name]['channels_joined'] += 1
            else:
                self.account_actions[session_name]['groups_joined'] += 1
            self.account_actions[session_name]['daily_join_count'] += 1
            self.last_action_time[session_name] = time.time()
            self.action_history[session_name].append(('join', time.time()))
            if len(self.action_history[session_name]) > 100:
                self.action_history[session_name] = self.action_history[session_name][-100:]

    def get_safe_delay(self, session_name, base_delay):
        if session_name not in self.last_action_time:
            return base_delay
        time_since_last = time.time() - self.last_action_time[session_name]
        if time_since_last < 5:
            return max(base_delay, 10 - time_since_last)
        recent_actions = sum(1 for _, t in self.action_history.get(session_name, []) if time.time() - t < 60)
        if recent_actions > 10:
            return base_delay * 2
        elif recent_actions > 20:
            return base_delay * 3
        elif recent_actions > 30:
            return base_delay * 5
        return base_delay

    def should_pause(self, session_name):
        if session_name not in self.action_history:
            return False, 0
        recent_actions = self.action_history.get(session_name, [])
        if len(recent_actions) < 5:
            return False, 0
        times = [t for _, t in recent_actions[-10:]]
        if len(times) < 2:
            return False, 0
        intervals = [times[i + 1] - times[i] for i in range(len(times) - 1)]
        avg_interval = sum(intervals) / len(intervals)
        if avg_interval < 2:
            pause_time = 60
            return True, pause_time
        elif avg_interval < 3:
            pause_time = 30
            return True, pause_time
        elif avg_interval < 5:
            pause_time = 15
            return True, pause_time
        return False, 0

    def add_warning(self, session_name, warning_type):
        if session_name not in self.warnings:
            self.warnings[session_name] = []
        self.warnings[session_name].append((warning_type, time.time()))
        if len(self.warnings[session_name]) > 3:
            warnings_recent = [w for w, t in self.warnings[session_name] if time.time() - t < 3600]
            if len(warnings_recent) > 5:
                return 300
        return 0

    def get_account_stats(self, session_name):
        if session_name not in self.account_actions:
            return {}
        return self.account_actions[session_name]


class ProxyManager:
    def __init__(self, proxy_file="proxies.txt"):
        self.proxy_file = proxy_file
        self.proxies = []
        self.proxy_stats = {}
        self.current_proxy_index = 0
        self.current_proxy = None
        self.bad_proxies = set()
        self.proxy_assignments = {}
        self.proxy_usage_count = {}
        self.load_proxies()

    def load_proxies(self):
        try:
            if os.path.exists(self.proxy_file):
                with open(self.proxy_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines, 1):
                        proxy = line.strip()
                        if proxy and not proxy.startswith('#'):
                            self.proxies.append(proxy)
                            self.proxy_stats[proxy] = {
                                'success': 0,
                                'fail': 0,
                                'last_used': 0,
                                'consecutive_fails': 0,
                                'line_number': i,
                                'host': self.extract_host(proxy)
                            }
                            self.proxy_usage_count[proxy] = 0
                print(f"{Fore.GREEN}✔ Загружено {len(self.proxies)} прокси из {self.proxy_file}{Style.RESET_ALL}")
                if self.proxies:
                    print(f"{Fore.CYAN}📊 Прокси будут распределяться равномерно между аккаунтами{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠️ Файл {self.proxy_file} не найден. Прокси не используются.{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}✘ Ошибка загрузки прокси: {e}{Style.RESET_ALL}")

    def extract_host(self, proxy_str):
        try:
            if '@' in proxy_str:
                return proxy_str.split('@')[1].split(':')[0]
            elif '://' in proxy_str:
                parts = proxy_str.split('://')[1]
                if '@' in parts:
                    return parts.split('@')[1].split(':')[0]
                else:
                    return parts.split(':')[0]
            else:
                return proxy_str.split(':')[0]
        except:
            return "unknown"

    def get_proxy_info(self, proxy_str):
        if proxy_str in self.proxy_stats:
            stats = self.proxy_stats[proxy_str]
            return f"#{stats['line_number']} {stats['host']}"
        return "unknown"

    def get_proxy_for_session(self, session_name):
        if not self.proxies:
            return None
        if session_name in self.proxy_assignments:
            proxy_str = self.proxy_assignments[session_name]
            if proxy_str not in self.bad_proxies:
                return self.parse_proxy_string(proxy_str)
            else:
                del self.proxy_assignments[session_name]
        available_proxies = [p for p in self.proxies if p not in self.bad_proxies]
        if not available_proxies:
            print(f"{Fore.YELLOW}⚠️ Все прокси помечены как плохие. Сбрасываем статистику...{Style.RESET_ALL}")
            self.bad_proxies.clear()
            available_proxies = self.proxies
        available_proxies.sort(key=lambda p: self.proxy_usage_count.get(p, 0))
        selected_proxy = available_proxies[0]
        self.proxy_assignments[session_name] = selected_proxy
        self.proxy_usage_count[selected_proxy] = self.proxy_usage_count.get(selected_proxy, 0) + 1
        self.current_proxy = self.parse_proxy_string(selected_proxy)
        return self.current_proxy

    def mark_proxy_success(self, session_name):
        if session_name in self.proxy_assignments:
            proxy_str = self.proxy_assignments[session_name]
            if proxy_str in self.proxy_stats:
                self.proxy_stats[proxy_str]['success'] += 1
                self.proxy_stats[proxy_str]['consecutive_fails'] = 0

    def mark_proxy_failure(self, session_name):
        if session_name in self.proxy_assignments:
            proxy_str = self.proxy_assignments[session_name]
            if proxy_str in self.proxy_stats:
                self.proxy_stats[proxy_str]['fail'] += 1
                self.proxy_stats[proxy_str]['consecutive_fails'] += 1
                if self.proxy_stats[proxy_str]['consecutive_fails'] >= 3:
                    print(
                        f"{Fore.YELLOW}⚠️ Прокси #{self.proxy_stats[proxy_str]['line_number']} {self.proxy_stats[proxy_str]['host']} не работает 3 раза подряд, временно исключаем{Style.RESET_ALL}")
                    self.bad_proxies.add(proxy_str)
                    self.proxy_usage_count[proxy_str] = max(0, self.proxy_usage_count.get(proxy_str, 1) - 1)
            del self.proxy_assignments[session_name]

    def rotate_proxy_for_session(self, session_name):
        if session_name in self.proxy_assignments:
            old_proxy = self.proxy_assignments[session_name]
            self.proxy_usage_count[old_proxy] = max(0, self.proxy_usage_count.get(old_proxy, 1) - 1)
            del self.proxy_assignments[session_name]
        return self.get_proxy_for_session(session_name)

    def get_any_valid_proxy(self):
        if not self.proxies:
            return None
        available = [p for p in self.proxies if p not in self.bad_proxies]
        if not available:
            self.bad_proxies.clear()
            available = self.proxies
        proxy_str = random.choice(available)
        self.proxy_stats[proxy_str]['last_used'] = time.time()
        return self.parse_proxy_string(proxy_str)

    def get_best_proxy(self):
        if not self.proxies:
            return None
        available = [p for p in self.proxies if p not in self.bad_proxies]
        if not available:
            self.bad_proxies.clear()
            available = self.proxies

        def get_score(proxy):
            stats = self.proxy_stats.get(proxy, {'success': 0, 'fail': 0})
            total = stats['success'] + stats['fail']
            if total == 0:
                return 0
            return stats['success'] / total - stats['fail'] * 0.1

        available.sort(key=get_score, reverse=True)
        proxy_str = available[0]
        self.proxy_stats[proxy_str]['last_used'] = time.time()
        return self.parse_proxy_string(proxy_str)

    def get_next_proxy(self):
        if not self.proxies:
            return None
        attempts = 0
        while attempts < len(self.proxies) * 2:
            proxy_str = self.proxies[self.current_proxy_index]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
            if proxy_str not in self.bad_proxies:
                self.proxy_stats[proxy_str]['last_used'] = time.time()
                self.current_proxy = self.parse_proxy_string(proxy_str)
                return self.current_proxy
            attempts += 1
        self.bad_proxies.clear()
        proxy_str = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        self.current_proxy = self.parse_proxy_string(proxy_str)
        return self.current_proxy

    def get_current_proxy(self):
        return self.current_proxy

    def get_random_proxy(self):
        if not self.proxies:
            return None
        available = [p for p in self.proxies if p not in self.bad_proxies]
        if not available:
            self.bad_proxies.clear()
            available = self.proxies
        proxy_str = random.choice(available)
        self.proxy_stats[proxy_str]['last_used'] = time.time()
        return self.parse_proxy_string(proxy_str)

    def parse_proxy_string(self, proxy_str):
        try:
            proxy_str = proxy_str.strip()
            if '://' in proxy_str:
                parts = proxy_str.split('://')
                proxy_type = parts[0].lower()
                rest = parts[1]
            else:
                proxy_type = 'socks5'
                rest = proxy_str
            if '@' in rest:
                auth, addr = rest.split('@')
                if ':' in auth:
                    username, password = auth.split(':', 1)
                else:
                    username, password = auth, ''
                if ':' in addr:
                    host, port = addr.split(':')
                else:
                    host, port = addr, '1080'
            else:
                username, password = None, None
                if ':' in rest:
                    host, port = rest.split(':')
                else:
                    host, port = rest, '1080'
            port = int(port)
            proxy_type_map = {'socks5': socks.SOCKS5, 'socks4': socks.SOCKS4, 'http': socks.HTTP, 'https': socks.HTTP}
            proxy_type_num = proxy_type_map.get(proxy_type, socks.SOCKS5)
            if username and password:
                return (proxy_type_num, host, port, True, username, password)
            else:
                return (proxy_type_num, host, port)
        except Exception as e:
            print(f"{Fore.RED}✘ Ошибка парсинга прокси {proxy_str}: {e}{Style.RESET_ALL}")
            return None

    def get_proxy_count(self):
        return len(self.proxies)

    def has_proxies(self):
        return len(self.proxies) > 0

    def rotate_proxy(self):
        if self.proxies:
            old_proxy = self.proxies[self.current_proxy_index]
            self.proxy_stats[old_proxy]['fail'] += 1
            self.proxy_stats[old_proxy]['consecutive_fails'] += 1
            if self.proxy_stats[old_proxy]['consecutive_fails'] >= 3:
                self.bad_proxies.add(old_proxy)
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
            proxy_str = self.proxies[self.current_proxy_index]
            self.current_proxy = self.parse_proxy_string(proxy_str)
            return True
        return False

    def report_success(self, session_name=None):
        if session_name and session_name in self.proxy_assignments:
            proxy_str = self.proxy_assignments[session_name]
            if proxy_str in self.proxy_stats:
                self.proxy_stats[proxy_str]['success'] += 1
                self.proxy_stats[proxy_str]['consecutive_fails'] = 0
        elif self.current_proxy:
            proxy_str = self.get_proxy_string_from_tuple(self.current_proxy)
            if proxy_str in self.proxy_stats:
                self.proxy_stats[proxy_str]['success'] += 1
                self.proxy_stats[proxy_str]['consecutive_fails'] = 0

    def get_proxy_string_from_tuple(self, proxy_tuple):
        if not proxy_tuple:
            return None
        for proxy_str, stats in self.proxy_stats.items():
            parsed = self.parse_proxy_string(proxy_str)
            if parsed and len(parsed) >= 3:
                if parsed[0] == proxy_tuple[0] and parsed[1] == proxy_tuple[1] and parsed[2] == proxy_tuple[2]:
                    return proxy_str
        return None

    def get_stats(self):
        stats = []
        for proxy, data in self.proxy_stats.items():
            total = data['success'] + data['fail']
            success_rate = (data['success'] / total * 100) if total > 0 else 0
            status = "✅" if proxy not in self.bad_proxies else "❌"
            usage = self.proxy_usage_count.get(proxy, 0)
            stats.append({
                'line': data['line_number'],
                'host': data['host'],
                'proxy': proxy[:50] + '...' if len(proxy) > 50 else proxy,
                'success': data['success'],
                'fail': data['fail'],
                'rate': f"{success_rate:.1f}%",
                'status': status,
                'usage': usage
            })
        return stats

    def clear_bad_proxies(self):
        self.bad_proxies.clear()
        print(f"{Fore.GREEN}✔ Список плохих прокси очищен{Style.RESET_ALL}")


class UpdateManager:
    def __init__(self):
        self.version_file = "version.json"
        self.backup_folder = "backups"
        self.update_available = False
        self.new_version = None
        self.changelog = []

    async def check_for_updates(self, force=False):
        try:
            if not force and not self.should_check_update():
                return False
            print(f"{Fore.CYAN}🔍 Проверка обновлений...{Style.RESET_ALL}")
            await add_to_log_buffer("🔍 Проверка обновлений...", "info")
            version_url = f"{GITHUB_RAW_BASE}/version.json"
            response = requests.get(version_url, timeout=10)
            if response.status_code != 200:
                print(f"{Fore.YELLOW}⚠️ Не удалось проверить обновления{Style.RESET_ALL}")
                await add_to_log_buffer("⚠️ Не удалось проверить обновления", "warning")
                return False
            remote_data = response.json()
            remote_version = remote_data.get("version", "0.0.0")
            if self.compare_versions(remote_version, CURRENT_VERSION) > 0:
                self.update_available = True
                self.new_version = remote_version
                self.changelog = remote_data.get("changelog", [])
                print(f"{Fore.GREEN}📦 Доступна новая версия: {remote_version}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}Текущая версия: {CURRENT_VERSION}{Style.RESET_ALL}")
                await add_to_log_buffer(f"📦 Доступна новая версия: {remote_version}", "info")
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
                await add_to_log_buffer(f"✅ У вас актуальная версия ({CURRENT_VERSION})", "success")
                self.save_last_check()
                return False
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Ошибка при проверке обновлений: {e}{Style.RESET_ALL}")
            await add_to_log_buffer(f"⚠️ Ошибка при проверке обновлений: {e}", "warning")
            return False

    def compare_versions(self, version1, version2):
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
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
            await add_to_log_buffer(f"⚙️ Начинаю обновление до версии {self.new_version}...", "info")

            # Создаем папку для бэкапов
            os.makedirs(self.backup_folder, exist_ok=True)

            # Создаем бэкап текущего файла
            backup_name = f"backup_v{CURRENT_VERSION}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            backup_path = os.path.join(self.backup_folder, backup_name)
            current_file = __file__

            # Читаем текущий файл
            with open(current_file, 'r', encoding='utf-8') as f:
                current_content = f.read()

            # Сохраняем бэкап
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(current_content)

            print(f"{Fore.GREEN}✅ Бэкап создан: {backup_path}{Style.RESET_ALL}")
            await add_to_log_buffer(f"✅ Бэкап создан: {backup_path}", "success")

            # Скачиваем новый файл с GitHub
            script_url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/LiteGamma%20Tools%20Full%20Version.py"
            expected_sha256 = remote_data.get('checksums', {}).get('sha256')

            # ВАЖНО: Скачиваем с правильными заголовками
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/vnd.github.v3.raw'
            }
            response = requests.get(script_url, timeout=30, headers=headers)

            if response.status_code == 200:
                # Получаем содержимое
                new_content = response.text

                # Проверяем хеш если есть
                if expected_sha256:
                    actual_sha256 = hashlib.sha256(new_content.encode('utf-8')).hexdigest()
                    if actual_sha256 != expected_sha256:
                        print(f"{Fore.RED}❌ Ошибка: хеш файла не совпадает!{Style.RESET_ALL}")
                        await add_to_log_buffer("❌ Ошибка: хеш файла не совпадает!", "error")
                        return False

                # ВАЖНО: Нормализуем окончания строк для Windows
                # Заменяем LF на CRLF для Windows
                if os.name == 'nt':  # Если это Windows
                    new_content = new_content.replace('\n', '\r\n')

                # Обновляем версию в файле (аккуратно)
                new_content = self.update_version_in_file_safe(new_content, self.new_version)

                # Сохраняем новый файл
                with open(current_file, 'w', encoding='utf-8', newline='') as f:
                    f.write(new_content)

                CURRENT_VERSION = self.new_version
                print(f"{Fore.GREEN}✅ Скрипт успешно обновлен до версии {self.new_version}!{Style.RESET_ALL}")
                await add_to_log_buffer(f"✅ Скрипт успешно обновлен до версии {self.new_version}!", "success")

                save_config()

                if NOTIFY_ON_UPDATE and notification_enabled:
                    await send_notification(
                        f"🔄 **Программа обновлена!**\n\n📦 Новая версия: {self.new_version}\n📅 Дата: {remote_data.get('release_date', 'Неизвестно')}\n📝 Изменения:\n" +
                        "\n".join([f"  {c}" for c in self.changelog]), "update"
                    )

                print(f"\n{Fore.YELLOW}⚠️ Для применения обновлений необходим перезапуск{Style.RESET_ALL}")
                await add_to_log_buffer("⚠️ Для применения обновлений необходим перезапуск", "warning")

                if input(f"{Fore.MAGENTA}Перезапустить сейчас? (y/n): {Style.RESET_ALL}").lower() == 'y':
                    self.restart_program()

                return True
            else:
                print(f"{Fore.RED}❌ Не удалось скачать обновление (статус: {response.status_code}){Style.RESET_ALL}")
                await add_to_log_buffer("❌ Не удалось скачать обновление", "error")
                return False

        except Exception as e:
            print(f"{Fore.RED}❌ Ошибка при обновлении: {e}{Style.RESET_ALL}")
            await add_to_log_buffer(f"❌ Ошибка при обновлении: {e}", "error")
            traceback.print_exc()
            return False

    def update_version_in_file_safe(self, content, new_version):
        """Безопасно обновляет версию в файле без ломания форматирования"""
        import re

        # Ищем разные варианты объявления версии
        patterns = [
            (r'(CURRENT_VERSION\s*=\s*["\'])([^"\']+)(["\'])', f'\\g<1>{new_version}\\g<3>'),
            (r'(CURRENT_VERSION\s*=\s*)([0-9.]+)', f'\\g<1>"{new_version}"'),
            (r'(__version__\s*=\s*["\'])([^"\']+)(["\'])', f'\\g<1>{new_version}\\g<3>'),
            (r'(VERSION\s*=\s*["\'])([^"\']+)(["\'])', f'\\g<1>{new_version}\\g<3>')
        ]

        updated_content = content
        for pattern, replacement in patterns:
            updated_content = re.sub(pattern, replacement, updated_content, flags=re.MULTILINE)

        # Проверяем, что замена произошла
        if updated_content == content:
            # Если не нашли, добавляем после импортов
            lines = updated_content.splitlines(True)
            import_end = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_end = i + 1

            version_line = f'CURRENT_VERSION = "{new_version}"\n'
            lines.insert(import_end, version_line)
            updated_content = ''.join(lines)

        return updated_content

    def verify_formatting(self, file_path):
        """Проверяет, что файл имеет правильные окончания строк"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()

            # Проверяем наличие смешанных окончаний
            if b'\r\n' in content and b'\n' not in content.replace(b'\r\n', b''):
                print(f"{Fore.GREEN}✅ Файл имеет правильные окончания строк (Windows){Style.RESET_ALL}")
            elif b'\n' in content and b'\r\n' not in content:
                print(f"{Fore.GREEN}✅ Файл имеет правильные окончания строк (Unix){Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠️ Файл имеет смешанные окончания строк{Style.RESET_ALL}")
                return False
            return True
        except Exception as e:
            print(f"{Fore.RED}✘ Ошибка проверки форматирования: {e}{Style.RESET_ALL}")
            return False

    def normalize_line_endings(content):
        """Нормализует окончания строк в зависимости от ОС"""
        if os.name == 'nt':  # Windows
            return content.replace('\n', '\r\n')
        else:  # Linux/Mac
            return content.replace('\r\n', '\n')
    def update_version_in_file(self, content, new_version):
        import re
        patterns = [(r'CURRENT_VERSION\s*=\s*["\']([^"\']+)["\']', f'CURRENT_VERSION = "{new_version}"'),
                    (r'CURRENT_VERSION\s*=\s*([0-9.]+)', f'CURRENT_VERSION = "{new_version}"'),
                    (r'__version__\s*=\s*["\']([^"\']+)["\']', f'__version__ = "{new_version}"'),
                    (r'VERSION\s*=\s*["\']([^"\']+)["\']', f'VERSION = "{new_version}"')]
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
                print(f"{Fore.CYAN}📄 Версия в файле: {file_version}{Style.RESET_ALL}")
                return file_version
        except Exception as e:
            print(f"{Fore.RED}✘ Ошибка проверки версии: {e}{Style.RESET_ALL}")
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
        print(f"{Fore.CYAN}🔍 Диагностика версии:{Style.RESET_ALL}")
        print(f"  Глобальная CURRENT_VERSION: {CURRENT_VERSION}")
        file_version = self.verify_version_in_file()
        print(f"  Версия в файле: {file_version}")
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    config_version = config.get('current_version', 'не найдено')
                    print(f"  Версия в config.json: {config_version}")
        except:
            print(f"  Версия в config.json: ошибка чтения")
        try:
            response = requests.get(f"{GITHUB_RAW_BASE}/version.json", timeout=5)
            if response.status_code == 200:
                remote = response.json()
                print(f"  Версия на GitHub: {remote.get('version', 'не найдено')}")
                print(f"  Что нового: {remote.get('changelog', [])}")
        except:
            print(f"  Версия на GitHub: ошибка проверки")

    def show_update_history(self):
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
                current_backup = Path(self.backup_folder) / f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
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


def cleanup_old_logs():
    """Удаляет старые HTML файлы логов"""
    try:
        for file in Path('.').glob('logs_*.html'):
            try:
                os.remove(file)
                print(f"{Fore.CYAN}🧹 Удален старый лог-файл: {file}{Style.RESET_ALL}")
            except:
                pass
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️ Ошибка при очистке старых логов: {e}{Style.RESET_ALL}")


update_manager = UpdateManager()
account_protector = AccountProtector()
proxy_manager = ProxyManager()
log_manager = LogManager()


def print_header(text):
    print(f"\n{CLR_ACCENT}╔" + "═" * (len(text) + 2) + "╗")
    print(f"{CLR_ACCENT}║ {CLR_MAIN}{text}{CLR_ACCENT} ║")
    print(f"{CLR_ACCENT}╚" + "═" * (len(text) + 2) + "╝\n")


def print_stata(text):
    print(f"\n{CLR_ACCENT}╔" + "═" * (len(text) + 2) + "╗")
    print(f"{CLR_ACCENT}║ {CLR_MAIN}{text}{CLR_ACCENT} ║")
    print(f"{CLR_ACCENT}╚" + "═" * (len(text) + 2) + "╝\n")


DEFAULT_API_ID = 0
DEFAULT_API_HASH = "ЗАМЕНИТЕ НА ВАШ API HASH"
DEFAULT_SESSION_FOLDER = "session"
DEFAULT_MESSAGE = """Привет! Это тестовое сообщение от бота рассылки!\n\nСпасибо за покупку в нашем магазине @BananaStorebot_bot 😉"""
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
DEFAULT_USE_PROXY = False
DEFAULT_PROXY_FILE = "proxy.txt"
DEFAULT_PROXY_ROTATE_ON_FAIL = True
DEFAULT_PROXY_MAX_RETRIES = 3
DEFAULT_SAFE_MODE = True
DEFAULT_MAX_DAILY_MESSAGES = 100
DEFAULT_MAX_DAILY_JOINS = 50
DEFAULT_ANTI_BAN_ENABLED = True
DEFAULT_HUMAN_LIKE_DELAYS = True
DEFAULT_RANDOM_PAUSE_ENABLED = True

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
notification_enabled = DEFAULT_NOTIFICATION_ENABLED
notification_bot_token = DEFAULT_NOTIFICATION_BOT_TOKEN
notification_chat_id = DEFAULT_NOTIFICATION_CHAT_ID
notify_invalid_session = DEFAULT_NOTIFY_INVALID_SESSION
notify_cycle_results = DEFAULT_NOTIFY_CYCLE_RESULTS
notify_full_logs = DEFAULT_NOTIFY_FULL_LOGS
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
use_proxy = DEFAULT_USE_PROXY
proxy_file = DEFAULT_PROXY_FILE
proxy_rotate_on_fail = DEFAULT_PROXY_ROTATE_ON_FAIL
proxy_max_retries = DEFAULT_PROXY_MAX_RETRIES
safe_mode = DEFAULT_SAFE_MODE
max_daily_messages = DEFAULT_MAX_DAILY_MESSAGES
max_daily_joins = DEFAULT_MAX_DAILY_JOINS
anti_ban_enabled = DEFAULT_ANTI_BAN_ENABLED
human_like_delays = DEFAULT_HUMAN_LIKE_DELAYS
random_pause_enabled = DEFAULT_RANDOM_PAUSE_ENABLED

stop_event = asyncio.Event()
invalid_session_log_file = "invalidsession_list.txt"
config_file = "config.json"
group_list_file = "group.json"
enter_links_file = "enter.json"
notification_client = None
log_buffer = []
log_buffer_lock = asyncio.Lock()


def clear_failed_subscriptions_file():
    try:
        if os.path.exists(failed_subscriptions_file):
            os.remove(failed_subscriptions_file)
            print(f"{Fore.GREEN}✔ Файл '{failed_subscriptions_file}' очищен.{Style.RESET_ALL}")
            asyncio.create_task(log_manager.add_log(f"✔ Файл '{failed_subscriptions_file}' очищен", "success"))
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️ Не удалось очистить файл '{failed_subscriptions_file}': {e}{Style.RESET_ALL}")
        asyncio.create_task(
            log_manager.add_log(f"⚠️ Не удалось очистить файл '{failed_subscriptions_file}': {e}", "warning"))


def log_failed_subscription(session_name, channel_link, reason):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        if os.path.exists(failed_subscriptions_file):
            with open(failed_subscriptions_file, 'r', encoding='utf-8') as f:
                existing = f.read()
                if channel_link in existing and session_name in existing:
                    return
        with open(failed_subscriptions_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {session_name} | {channel_link} | {reason}\n")
        print(f"{Fore.RED}✘ Ошибка записи в файл неудачных подписок: {e}{Style.RESET_ALL}")
        asyncio.create_task(log_manager.add_log(f"❌ {session_name} | {channel_link} | {reason}", "error"))
    except Exception as e:
        print(f"{Fore.RED}✘ Ошибка записи в файл неудачных подписок: {e}{Style.RESET_ALL}")
        asyncio.create_task(log_manager.add_log(f"✘ Ошибка записи в файл неудачных подписок: {e}", "error"))


async def init_notification_client():
    global notification_client
    if notification_enabled and notification_bot_token and notification_chat_id:
        try:
            if notification_client:
                await notification_client.disconnect()
            proxy = proxy_manager.get_best_proxy() if use_proxy and proxy_manager.has_proxies() else None
            notification_client = TelegramClient('notification_bot_session', api_id=current_api_id,
                                                 api_hash=current_api_hash, proxy=proxy)
            await notification_client.start(bot_token=notification_bot_token)
            me = await notification_client.get_me()
            print(f"{Fore.GREEN}✔ Бот для уведомлений инициализирован: @{me.username}{Style.RESET_ALL}")
            await log_manager.add_log(f"✔ Бот для уведомлений инициализирован: @{me.username}", "success")
            await notification_client.send_message(int(notification_chat_id), "🔔 Уведомления успешно настроены!")
            return True
        except Exception as e:
            print(f"{Fore.RED}✘ Ошибка инициализации бота уведомлений: {e}{Style.RESET_ALL}")
            await log_manager.add_log(f"✘ Ошибка инициализации бота уведомлений: {e}", "error")
            notification_client = None
            return False
    return False


async def close_notification_client():
    global notification_client
    if notification_client:
        await notification_client.disconnect()
        notification_client = None
        print(f"{Fore.CYAN}📱 Клиент уведомлений закрыт{Style.RESET_ALL}")
        await log_manager.add_log("📱 Клиент уведомлений закрыт", "info")


async def add_to_log_buffer(message, category="info"):
    global log_buffer
    async with log_buffer_lock:
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_buffer.append(f"[{timestamp}] {message}")
        if len(log_buffer) > 2000:
            log_buffer = log_buffer[-2000:]
    await log_manager.add_log(message, category)


async def save_logs_to_file():
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
            await log_manager.add_log(f"✘ Ошибка сохранения логов в файл: {e}", "error")
            return None


async def send_notification(message, notification_type="info"):
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
                await notification_client.send_file(int(notification_chat_id), log_file_path,
                                                    caption=f"📋 **Полный лог рассылки**\nВремя: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nВсего записей: {len(log_buffer)}")
                try:
                    os.unlink(log_file_path)
                except:
                    pass
            else:
                full_log = "\n".join(log_buffer[-50:])
                if len(full_log) > 3500:
                    full_log = full_log[-3500:]
                await notification_client.send_message(int(notification_chat_id),
                                                       f"📋 **Полный лог (последние 50 строк)**\n\n{full_log}")
        else:
            await notification_client.send_message(int(notification_chat_id), message)
        print(f"{Fore.GREEN}📱 Уведомление отправлено ({notification_type}){Style.RESET_ALL}")
        await log_manager.add_log(f"📱 Уведомление отправлено ({notification_type})", "success")
    except Exception as e:
        print(f"{Fore.RED}✘ Ошибка отправки уведомления: {e}{Style.RESET_ALL}")
        await log_manager.add_log(f"✘ Ошибка отправки уведомления: {e}", "error")


def save_config():
    config = {"api_id": current_api_id, "api_hash": current_api_hash, "session_folder": session_folder,
              "message": message_to_send, "delay_messages": delay_between_messages,
              "delay_accounts": delay_between_accounts, "max_messages_per_account": max_messages_per_account,
              "repeat_broadcast": repeat_broadcast, "repeat_interval": repeat_interval,
              "delete_after_send": delete_after_send, "recipient_type": recipient_type, "use_media": use_media,
              "media_path": media_path, "fast_mode": fast_mode, "fast_delay": fast_delay,
              "notification_enabled": notification_enabled, "notification_bot_token": notification_bot_token,
              "notification_chat_id": notification_chat_id, "notify_invalid_session": notify_invalid_session,
              "notify_cycle_results": notify_cycle_results, "notify_full_logs": notify_full_logs,
              "auto_subscribe_enabled": auto_subscribe_enabled, "auto_subscribe_on_mention": auto_subscribe_on_mention,
              "auto_subscribe_delay": auto_subscribe_delay,
              "auto_subscribe_max_flood_wait": auto_subscribe_max_flood_wait,
              "auto_subscribe_retry_after_flood": auto_subscribe_retry_after_flood,
              "auto_subscribe_check_interval": auto_subscribe_check_interval,
              "auto_subscribe_wait_for_mention": auto_subscribe_wait_for_mention,
              "auto_subscribe_pause_between_channels": auto_subscribe_pause_between_channels,
              "auto_subscribe_forced_channels": auto_subscribe_forced_channels,
              "auto_subscribe_first_cycle_only": auto_subscribe_first_cycle_only, "use_proxy": use_proxy,
              "proxy_file": proxy_file, "proxy_rotate_on_fail": proxy_rotate_on_fail,
              "proxy_max_retries": proxy_max_retries, "safe_mode": safe_mode, "max_daily_messages": max_daily_messages,
              "max_daily_joins": max_daily_joins, "anti_ban_enabled": anti_ban_enabled,
              "human_like_delays": human_like_delays, "random_pause_enabled": random_pause_enabled,
              "current_version": CURRENT_VERSION}
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"{Fore.GREEN}✔ Конфигурация сохранена.{Style.RESET_ALL}")
        asyncio.create_task(log_manager.add_log("✔ Конфигурация сохранена", "success"))
    except Exception as e:
        print(f"{Fore.RED}✘ Ошибка сохранения: {e}{Style.RESET_ALL}")
        asyncio.create_task(log_manager.add_log(f"✘ Ошибка сохранения: {e}", "error"))


def load_config():
    global current_api_id, current_api_hash, session_folder, message_to_send, delay_between_messages, delay_between_accounts, max_messages_per_account, repeat_broadcast, repeat_interval, delete_after_send, recipient_type, use_media, media_path, fast_mode, fast_delay, notification_enabled, notification_bot_token, notification_chat_id, notify_invalid_session, notify_cycle_results, notify_full_logs, CURRENT_VERSION
    global auto_subscribe_enabled, auto_subscribe_on_mention, auto_subscribe_delay, auto_subscribe_max_flood_wait, auto_subscribe_retry_after_flood, auto_subscribe_check_interval, auto_subscribe_wait_for_mention, auto_subscribe_pause_between_channels, auto_subscribe_forced_channels, auto_subscribe_first_cycle_only
    global use_proxy, proxy_file, proxy_rotate_on_fail, proxy_max_retries, safe_mode, max_daily_messages, max_daily_joins, anti_ban_enabled, human_like_delays, random_pause_enabled
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
                use_proxy = config.get("use_proxy", DEFAULT_USE_PROXY)
                proxy_file = config.get("proxy_file", DEFAULT_PROXY_FILE)
                proxy_rotate_on_fail = config.get("proxy_rotate_on_fail", DEFAULT_PROXY_ROTATE_ON_FAIL)
                proxy_max_retries = config.get("proxy_max_retries", DEFAULT_PROXY_MAX_RETRIES)
                safe_mode = config.get("safe_mode", DEFAULT_SAFE_MODE)
                max_daily_messages = config.get("max_daily_messages", DEFAULT_MAX_DAILY_MESSAGES)
                max_daily_joins = config.get("max_daily_joins", DEFAULT_MAX_DAILY_JOINS)
                anti_ban_enabled = config.get("anti_ban_enabled", DEFAULT_ANTI_BAN_ENABLED)
                human_like_delays = config.get("human_like_delays", DEFAULT_HUMAN_LIKE_DELAYS)
                random_pause_enabled = config.get("random_pause_enabled", DEFAULT_RANDOM_PAUSE_ENABLED)
                CURRENT_VERSION = config.get("current_version", CURRENT_VERSION)
            print(f"{Fore.GREEN}✔ Конфигурация загружена.{Style.RESET_ALL}")
            asyncio.create_task(log_manager.add_log("✔ Конфигурация загружена", "success"))
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️ Ошибка загрузки конфигурации: {e}{Style.RESET_ALL}")
        asyncio.create_task(log_manager.add_log(f"⚠️ Ошибка загрузки конфигурации: {e}", "warning"))


def log_invalid_session(session_file):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{session_file} не рабочая ({timestamp})"
    try:
        with open(invalid_session_log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + "\n")
        print(f"{Fore.CYAN}✉ Сессия '{session_file}' добавлена в '{invalid_session_log_file}'{Style.RESET_ALL}")
        asyncio.create_task(
            log_manager.add_log(f"✉ Сессия '{session_file}' добавлена в '{invalid_session_log_file}'", "warning"))
        asyncio.create_task(
            send_notification(f"⚠️ Невалидная сессия: {session_file}\nВремя: {timestamp}", "invalid_session"))
    except Exception as e:
        print(f"{Fore.RED}✘ Ошибка записи в лог '{invalid_session_log_file}': {e}{Style.RESET_ALL}")
        asyncio.create_task(log_manager.add_log(f"✘ Ошибка записи в лог '{invalid_session_log_file}': {e}", "error"))


def extract_links_from_text(text):
    url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
    return re.findall(url_pattern, text)


def load_target_groups(filename=group_list_file):
    target_groups = []
    if not os.path.exists(filename):
        print(f"{Fore.RED}✘ Файл '{filename}' не найден.{Style.RESET_ALL}")
        asyncio.create_task(log_manager.add_log(f"✘ Файл '{filename}' не найден", "error"))
        return None
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                target_groups = data
            else:
                print(f"{Fore.RED}✘ Файл '{filename}' должен содержать JSON-массив.{Style.RESET_ALL}")
                asyncio.create_task(log_manager.add_log(f"✘ Файл '{filename}' должен содержать JSON-массив", "error"))
                return None
    except json.JSONDecodeError:
        print(f"{Fore.RED}✘ Ошибка декодирования JSON в файле '{filename}'.{Style.RESET_ALL}")
        asyncio.create_task(log_manager.add_log(f"✘ Ошибка декодирования JSON в файле '{filename}'", "error"))
        return None
    except Exception as e:
        print(f"{Fore.RED}✘ Ошибка при чтении файла '{filename}': {e}{Style.RESET_ALL}")
        asyncio.create_task(log_manager.add_log(f"✘ Ошибка при чтении файла '{filename}': {e}", "error"))
        return None
    if not target_groups:
        print(f"{Fore.YELLOW}⚠️ Файл '{filename}' пуст.{Style.RESET_ALL}")
        asyncio.create_task(log_manager.add_log(f"⚠️ Файл '{filename}' пуст", "warning"))
        return []
    print(f"{Fore.GREEN}✔ Успешно загружено {len(target_groups)} целей из '{filename}'.{Style.RESET_ALL}")
    asyncio.create_task(
        log_manager.add_log(f"✔ Успешно загружено {len(target_groups)} целей из '{filename}'", "success"))
    return target_groups


def load_enter_links(filename=enter_links_file):
    enter_links = []
    if not os.path.exists(filename):
        print(f"{Fore.RED}✘ Файл '{filename}' не найден.{Style.RESET_ALL}")
        asyncio.create_task(log_manager.add_log(f"✘ Файл '{filename}' не найден", "error"))
        return None
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                enter_links = data
            else:
                print(f"{Fore.RED}✘ Файл '{filename}' должен содержать JSON-массив.{Style.RESET_ALL}")
                asyncio.create_task(log_manager.add_log(f"✘ Файл '{filename}' должен содержать JSON-массив", "error"))
                return None
    except json.JSONDecodeError:
        print(f"{Fore.RED}✘ Ошибка декодирования JSON в файле '{filename}'.{Style.RESET_ALL}")
        asyncio.create_task(log_manager.add_log(f"✘ Ошибка декодирования JSON в файле '{filename}'", "error"))
        return None
    except Exception as e:
        print(f"{Fore.RED}✘ Ошибка при чтении файла '{filename}': {e}{Style.RESET_ALL}")
        asyncio.create_task(log_manager.add_log(f"✘ Ошибка при чтении файла '{filename}': {e}", "error"))
        return None
    if not enter_links:
        print(f"{Fore.YELLOW}⚠️ Файл '{filename}' пуст.{Style.RESET_ALL}")
        asyncio.create_task(log_manager.add_log(f"⚠️ Файл '{filename}' пуст", "warning"))
        return []
    print(f"{Fore.GREEN}✔ Успешно загружено {len(enter_links)} ссылок для входа из '{filename}'.{Style.RESET_ALL}")
    asyncio.create_task(
        log_manager.add_log(f"✔ Успешно загружено {len(enter_links)} ссылок для входа из '{filename}'", "success"))
    return enter_links


def format_time(seconds):
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
    if '/joinchat/' in invite_link:
        return invite_link.split('/joinchat/')[-1]
    elif '/+' in invite_link:
        return invite_link.split('/+')[-1]
    elif 't.me/+' in invite_link:
        return invite_link.split('t.me/+')[-1]
    return None


async def human_like_pause(base_delay, session_name=""):
    if human_like_delays:
        variation = random.uniform(0.7, 1.5)
        delay = base_delay * variation
        if random_pause_enabled and random.random() < 0.3:
            extra_pause = random.randint(2, 8)
            log_msg = f"⏱️ [{session_name}] Человекоподобная пауза +{extra_pause}с..."
            print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "info")
            delay += extra_pause
        return delay
    return base_delay


async def handle_flood_wait(e, operation_name="операция", session_name=""):
    global flood_wait_occurred, total_flood_time
    wait_seconds = e.seconds
    flood_wait_occurred = True
    total_flood_time += wait_seconds
    current_time = datetime.now()
    end_time = current_time + timedelta(seconds=wait_seconds)
    log_msg = f"\n{'=' * 60}"
    print(log_msg)
    await add_to_log_buffer(log_msg, "flood")
    log_msg = f"🚫 [{session_name}] ОБНАРУЖЕН ФЛУД-КОНТРОЛЬ!"
    print(log_msg)
    await add_to_log_buffer(log_msg, "flood")
    log_msg = f"{'=' * 60}"
    print(log_msg)
    await add_to_log_buffer(log_msg, "flood")
    log_msg = f"📌 Операция: {operation_name}"
    print(log_msg)
    await add_to_log_buffer(log_msg, "flood")
    log_msg = f"⏱️ Время ожидания: {format_time(wait_seconds)}"
    print(log_msg)
    await add_to_log_buffer(log_msg, "flood")
    log_msg = f"🕐 Начало: {current_time.strftime('%H:%M:%S')}"
    print(log_msg)
    await add_to_log_buffer(log_msg, "flood")
    log_msg = f"🕐 Окончание: {end_time.strftime('%H:%M:%S')}"
    print(log_msg)
    await add_to_log_buffer(log_msg, "flood")
    if wait_seconds > auto_subscribe_max_flood_wait:
        log_msg = f"⚠️ Внимание! Время ожидания превышает лимит в {format_time(auto_subscribe_max_flood_wait)}"
        print(log_msg)
        await add_to_log_buffer(log_msg, "warning")
        log_msg = f"❌ Пропускаем эту операцию"
        print(log_msg)
        await add_to_log_buffer(log_msg, "error")
        return False
    log_msg = f"\n⏳ Ожидание... (проверка каждые {auto_subscribe_check_interval} сек)"
    print(log_msg)
    await add_to_log_buffer(log_msg, "flood")
    elapsed = 0
    while elapsed < wait_seconds:
        if stop_event.is_set():
            log_msg = f"\n{Fore.YELLOW}🛑 Остановлено пользователем во время ожидания{Style.RESET_ALL}"
            print(log_msg)
            await add_to_log_buffer(log_msg, "warning")
            return False
        await asyncio.sleep(min(auto_subscribe_check_interval, wait_seconds - elapsed))
        elapsed += auto_subscribe_check_interval
        remaining = wait_seconds - elapsed
        if remaining > 0:
            progress = (elapsed / wait_seconds) * 100
            log_msg = f"   Прогресс: {progress:.1f}% | Осталось: {format_time(remaining)}"
            print(log_msg)
            await add_to_log_buffer(log_msg, "flood")
    log_msg = f"✅ Ожидание завершено! Продолжаем..."
    print(log_msg)
    await add_to_log_buffer(log_msg, "success")
    log_msg = f"{'=' * 60}\n"
    print(log_msg)
    await add_to_log_buffer(log_msg, "flood")
    return True


async def extract_channels_from_entities(message):
    channels = []
    if not message.entities:
        return channels
    for entity in message.entities:
        if isinstance(entity, MessageEntityTextUrl) and entity.url:
            if any(pattern in entity.url for pattern in ['t.me', 'telegram.me']):
                channels.append(entity.url)
                log_msg = f"🔗 Найдена ссылка в entity: {entity.url}"
                print(log_msg)
                await add_to_log_buffer(log_msg, "info")
        elif isinstance(entity, MessageEntityUrl):
            url = message.text[entity.offset:entity.offset + entity.length]
            if any(pattern in url for pattern in ['t.me', 'telegram.me']):
                channels.append(url)
                log_msg = f"🔗 Найден URL в entity: {url}"
                print(log_msg)
                await add_to_log_buffer(log_msg, "info")
        elif isinstance(entity, MessageEntityMention):
            mention = message.text[entity.offset:entity.offset + entity.length]
            if mention.startswith('@'):
                channels.append(mention)
                log_msg = f"🔗 Найдено упоминание: {mention}"
                print(log_msg)
                await add_to_log_buffer(log_msg, "info")
    return channels


async def extract_channels_from_buttons(client, message):
    channels = []
    try:
        if message.reply_markup and hasattr(message.reply_markup, 'rows'):
            for row in message.reply_markup.rows:
                for button in row.buttons:
                    if hasattr(button, 'url') and button.url:
                        if any(pattern in button.url for pattern in ['t.me', 'telegram.me']):
                            channels.append(button.url)
                            log_msg = f"🔘 Найдена кнопка-ссылка: {button.url}"
                            print(log_msg)
                            await add_to_log_buffer(log_msg, "info")
    except Exception as e:
        log_msg = f"⚠️ Ошибка при анализе кнопок: {e}"
        print(log_msg)
        await add_to_log_buffer(log_msg, "warning")
    return channels


async def find_channels_in_message(client, message):
    channels = []
    log_msg = "\n🔍 Анализируем сообщение..."
    print(log_msg)
    await add_to_log_buffer(log_msg, "info")
    entity_channels = await extract_channels_from_entities(message)
    channels.extend(entity_channels)
    button_channels = await extract_channels_from_buttons(client, message)
    channels.extend(button_channels)
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
    if auto_subscribe_forced_channels:
        channels.extend(auto_subscribe_forced_channels)
    unique_channels = []
    seen = set()
    for channel in channels:
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
    try:
        invite_hash = extract_invite_hash(invite_link)
        if not invite_hash:
            log_msg = f"❌ [{session_name}] Не удалось извлечь хеш из ссылки: {invite_link}"
            print(log_msg)
            await add_to_log_buffer(log_msg, "error")
            return False, "invalid_invite_link"
        log_msg = f"🔑 [{session_name}] Извлечен хеш приглашения: {invite_hash}"
        print(log_msg)
        await add_to_log_buffer(log_msg, "info")
        try:
            await client(ImportChatInviteRequest(invite_hash))
            log_msg = f"✅ [{session_name}] Успешно присоединились по ссылке-приглашению!"
            print(log_msg)
            await add_to_log_buffer(log_msg, "success")
            return True, "joined_by_invite"
        except FloodWaitError as e:
            log_msg = f"🚫 [{session_name}] Флуд-контроль при присоединении по приглашению!"
            print(log_msg)
            await add_to_log_buffer(log_msg, "flood")
            if await handle_flood_wait(e, f"присоединение к {invite_link}", session_name):
                return await join_invite_link(client, invite_link, session_name)
            return False, "flood_wait"
        except InviteHashExpiredError:
            log_msg = f"❌ [{session_name}] Срок действия приглашения истек"
            print(log_msg)
            await add_to_log_buffer(log_msg, "error")
            log_failed_subscription(session_name, invite_link, "Срок действия приглашения истек")
            return False, "invite_expired"
        except InviteHashInvalidError:
            log_msg = f"❌ [{session_name}] Недействительное приглашение"
            print(log_msg)
            await add_to_log_buffer(log_msg, "error")
            log_failed_subscription(session_name, invite_link, "Недействительное приглашение")
            return False, "invite_invalid"
        except InviteHashEmptyError:
            log_msg = f"❌ [{session_name}] Пустой хеш приглашения"
            print(log_msg)
            await add_to_log_buffer(log_msg, "error")
            log_failed_subscription(session_name, invite_link, "Пустой хеш приглашения")
            return False, "invite_empty"
        except Exception as e:
            log_msg = f"❌ [{session_name}] Ошибка при присоединении по приглашению: {e}"
            print(log_msg)
            await add_to_log_buffer(log_msg, "error")
            log_failed_subscription(session_name, invite_link, str(e)[:100])
            return False, f"invite_error: {str(e)[:50]}"
    except Exception as e:
        log_msg = f"❌ [{session_name}] Ошибка при обработке ссылки-приглашения: {e}"
        print(log_msg)
        await add_to_log_buffer(log_msg, "error")
        log_failed_subscription(session_name, invite_link, str(e)[:100])
        return False, "invite_processing_error"


async def subscribe_to_channel(client, channel_ref, session_name="", retry_count=0):
    max_retries = 3
    try:
        log_msg = f"\n📥 [{session_name}] Обработка: {channel_ref}"
        print(log_msg)
        await add_to_log_buffer(log_msg, "info")
        if any(x in channel_ref for x in ['joinchat', 't.me/+', '/+']):
            log_msg = f"🔗 [{session_name}] Это ссылка-приглашение, пробуем присоединиться..."
            print(log_msg)
            await add_to_log_buffer(log_msg, "info")
            return await join_invite_link(client, channel_ref, session_name)
        if channel_ref.startswith('@'):
            username = channel_ref[1:]
            channel_ref = f"https://t.me/{username}"
        try:
            channel_entity = await client.get_entity(channel_ref)
            channel_title = getattr(channel_entity, 'title', username)
            log_msg = f"✅ [{session_name}] Получена сущность канала: {channel_title}"
            print(log_msg)
            await add_to_log_buffer(log_msg, "success")
        except FloodWaitError as e:
            log_msg = f"🚫 [{session_name}] Флуд-контроль при получении информации о канале!"
            print(log_msg)
            await add_to_log_buffer(log_msg, "flood")
            if await handle_flood_wait(e, f"получение информации о {channel_ref}", session_name):
                return await subscribe_to_channel(client, channel_ref, session_name, retry_count + 1)
            return False, "flood_timeout"
        except ValueError as e:
            if "No user has" in str(e):
                log_msg = f"❌ [{session_name}] Канал не найден: {channel_ref}"
                print(log_msg)
                await add_to_log_buffer(log_msg, "error")
                log_failed_subscription(session_name, channel_ref, "Канал не найден")
                return False, "channel_not_found"
            log_msg = f"⚠️ [{session_name}] Ошибка при получении канала: {e}"
            print(log_msg)
            await add_to_log_buffer(log_msg, "warning")
            log_failed_subscription(session_name, channel_ref, str(e)[:100])
            return False, "channel_error"
        except Exception as e:
            log_msg = f"⚠️ [{session_name}] Не удалось получить канал: {e}"
            print(log_msg)
            await add_to_log_buffer(log_msg, "warning")
            log_failed_subscription(session_name, channel_ref, str(e)[:100])
            return False, "entity_error"
        try:
            await client.get_permissions(channel_entity, 'me')
            log_msg = f"ℹ️ [{session_name}] Уже подписаны на этот канал"
            print(log_msg)
            await add_to_log_buffer(log_msg, "info")
            return True, "already_subscribed"
        except FloodWaitError as e:
            log_msg = f"🚫 [{session_name}] Флуд-контроль при проверке подписки!"
            print(log_msg)
            await add_to_log_buffer(log_msg, "flood")
            if await handle_flood_wait(e, f"проверка подписки на {channel_ref}", session_name):
                return await subscribe_to_channel(client, channel_ref, session_name, retry_count + 1)
            return False, "flood_timeout"
        except Exception:
            pass
        try:
            await client(JoinChannelRequest(channel_entity))
            log_msg = f"✅ [{session_name}] Успешно подписались на канал!"
            print(log_msg)
            await add_to_log_buffer(log_msg, "success")
            await asyncio.sleep(2)
            try:
                await client.get_permissions(channel_entity, 'me')
                log_msg = f"✅ [{session_name}] Подписка подтверждена!"
                print(log_msg)
                await add_to_log_buffer(log_msg, "success")
            except:
                log_msg = f"⚠️ [{session_name}] Не удалось подтвердить подписку"
                print(log_msg)
                await add_to_log_buffer(log_msg, "warning")
            await asyncio.sleep(auto_subscribe_pause_between_channels)
            return True, "subscribed"
        except FloodWaitError as e:
            log_msg = f"\n{'🚫' * 10} [{session_name}] ФЛУД-КОНТРОЛЬ {'🚫' * 10}"
            print(log_msg)
            await add_to_log_buffer(log_msg, "flood")
            log_msg = f"📊 Статистика по флуду:"
            print(log_msg)
            await add_to_log_buffer(log_msg, "flood")
            log_msg = f"   • Канал: {channel_ref}"
            print(log_msg)
            await add_to_log_buffer(log_msg, "flood")
            log_msg = f"   • Попытка: {retry_count + 1}/{max_retries}"
            print(log_msg)
            await add_to_log_buffer(log_msg, "flood")
            log_msg = f"   • Время ожидания: {format_time(e.seconds)}"
            print(log_msg)
            await add_to_log_buffer(log_msg, "flood")
            if await handle_flood_wait(e, f"подписка на {channel_ref}", session_name):
                if retry_count < max_retries:
                    log_msg = f"🔄 [{session_name}] Повторная попытка {retry_count + 2}/{max_retries}..."
                    print(log_msg)
                    await add_to_log_buffer(log_msg, "info")
                    return await subscribe_to_channel(client, channel_ref, session_name, retry_count + 1)
                else:
                    log_msg = f"❌ [{session_name}] Достигнуто максимальное количество попыток ({max_retries})"
                    print(log_msg)
                    await add_to_log_buffer(log_msg, "error")
                    log_failed_subscription(session_name, channel_ref, "Максимальное количество попыток")
                    return False, "max_retries_reached"
            return False, "flood_timeout"
        except Exception as e:
            log_msg = f"❌ [{session_name}] Ошибка при подписке: {e}"
            print(log_msg)
            await add_to_log_buffer(log_msg, "error")
            log_failed_subscription(session_name, channel_ref, str(e)[:100])
            return False, "subscribe_error"
    except Exception as e:
        log_msg = f"❌ [{session_name}] Ошибка при обработке канала: {e}"
        print(log_msg)
        await add_to_log_buffer(log_msg, "error")
        log_failed_subscription(session_name, channel_ref, str(e)[:100])
        return False, "unknown_error"


async def subscribe_to_channels(client, message, session_name=""):
    global flood_wait_occurred, total_flood_time
    flood_wait_occurred = False
    total_flood_time = 0
    start_time = time.time()
    log_msg = "\n🔍 Ищем каналы для подписки..."
    print(log_msg)
    await add_to_log_buffer(log_msg, "info")
    channels_to_join = await find_channels_in_message(client, message)
    if not channels_to_join:
        log_msg = "❌ Не найдены ссылки на каналы"
        print(log_msg)
        await add_to_log_buffer(log_msg, "warning")
        return False
    log_msg = f"\n🔍 Найдены каналы для подписки:"
    print(log_msg)
    await add_to_log_buffer(log_msg, "info")
    for i, channel in enumerate(channels_to_join, 1):
        log_msg = f"  {i}. {channel}"
        print(log_msg)
        await add_to_log_buffer(log_msg, "info")
    results = {"success": 0, "already_subscribed": 0, "failed": 0, "flood_wait": 0, "joined_by_invite": 0,
               "details": []}
    for i, channel_ref in enumerate(channels_to_join, 1):
        log_msg = f"\n{'─' * 40}"
        print(log_msg)
        await add_to_log_buffer(log_msg, "info")
        log_msg = f"📌 Канал {i}/{len(channels_to_join)}"
        print(log_msg)
        await add_to_log_buffer(log_msg, "info")
        log_msg = f"{'─' * 40}"
        print(log_msg)
        await add_to_log_buffer(log_msg, "info")
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
        if i < len(channels_to_join) and not flood_wait_occurred:
            log_msg = f"⏳ [{session_name}] Пауза {auto_subscribe_pause_between_channels} секунд перед следующим каналом..."
            print(log_msg)
            await add_to_log_buffer(log_msg, "info")
            await asyncio.sleep(auto_subscribe_pause_between_channels)
    total_time = time.time() - start_time
    log_msg = f"\n{'=' * 60}"
    print(log_msg)
    await add_to_log_buffer(log_msg, "info")
    log_msg = f"📊 ИТОГОВАЯ СТАТИСТИКА ПОДПИСОК [{session_name}]"
    print(log_msg)
    await add_to_log_buffer(log_msg, "info")
    log_msg = f"{'=' * 60}"
    print(log_msg)
    await add_to_log_buffer(log_msg, "info")
    log_msg = f"✅ Успешно подписались: {results['success']}"
    print(log_msg)
    await add_to_log_buffer(log_msg, "success")
    if results['joined_by_invite'] > 0:
        log_msg = f"   └ По ссылкам-приглашениям: {results['joined_by_invite']}"
        print(log_msg)
        await add_to_log_buffer(log_msg, "success")
    log_msg = f"ℹ️ Уже были подписаны: {results['already_subscribed']}"
    print(log_msg)
    await add_to_log_buffer(log_msg, "info")
    log_msg = f"❌ Не удалось подписаться: {results['failed']}"
    print(log_msg)
    await add_to_log_buffer(log_msg, "error")
    if results['flood_wait'] > 0:
        log_msg = f"🚫 Из-за флуд-контроля: {results['flood_wait']}"
        print(log_msg)
        await add_to_log_buffer(log_msg, "flood")
    if total_flood_time > 0:
        log_msg = f"⏱️ Общее время ожидания флуда: {format_time(int(total_flood_time))}"
        print(log_msg)
        await add_to_log_buffer(log_msg, "flood")
    log_msg = f"⏱️ Общее время операции: {format_time(int(total_time))}"
    print(log_msg)
    await add_to_log_buffer(log_msg, "info")
    if flood_wait_occurred:
        log_msg = f"\n⚠️ ВНИМАНИЕ: Во время подписки был обнаружен флуд-контроль!"
        print(log_msg)
        await add_to_log_buffer(log_msg, "warning")
        log_msg = f"   Рекомендуется сделать паузу перед следующим действием."
        print(log_msg)
        await add_to_log_buffer(log_msg, "warning")
        log_msg = f"   Рекомендуемая пауза: {format_time(min(total_flood_time * 2, 300))}"
        print(log_msg)
        await add_to_log_buffer(log_msg, "warning")
    log_msg = f"{'=' * 60}\n"
    print(log_msg)
    await add_to_log_buffer(log_msg, "info")
    log_msg = "📋 Детали по каждой ссылке:"
    print(log_msg)
    await add_to_log_buffer(log_msg, "info")
    for detail in results["details"]:
        log_msg = f"   {detail}"
        print(log_msg)
        await add_to_log_buffer(log_msg, "info")
    if results["success"] > 0 or results["already_subscribed"] > 0:
        return True
    return False


async def monitor_and_subscribe(client, session_name="", target_group=None):
    global flood_wait_occurred, total_flood_time
    if not target_group:
        return
    try:
        me = await client.get_me()
        user_id = me.id
        username = me.username
        log_msg = f"\n🔄 [{session_name}] Запущен мониторинг группы {getattr(target_group, 'title', target_group)}"
        print(log_msg)
        await add_to_log_buffer(log_msg, "info")
        log_msg = f"👤 [{session_name}] Аккаунт: {me.first_name} (@{username if username else 'нет юзернейма'})"
        print(log_msg)
        await add_to_log_buffer(log_msg, "info")
        mentioned = False
        subscription_complete = False

        @client.on(events.NewMessage(chats=target_group))
        async def mention_handler(event):
            nonlocal mentioned, subscription_complete
            if mentioned or stop_event.is_set():
                return
            if str(user_id) in event.message.text or (username and f"@{username}" in event.message.text):
                mentioned = True
                log_msg = f"\n🔔 [{session_name}] ПОЛУЧЕНО УПОМИНАНИЕ ОТ БОТА!"
                print(log_msg)
                await add_to_log_buffer(log_msg, "success")
                log_msg = f"📩 Текст сообщения:\n{event.message.text[:200]}..."
                print(log_msg)
                await add_to_log_buffer(log_msg, "info")
                log_msg = f"\n🔄 [{session_name}] Начинаем процесс подписки..."
                print(log_msg)
                await add_to_log_buffer(log_msg, "info")
                subscription_complete = await subscribe_to_channels(client, event.message, session_name)
                if subscription_complete:
                    log_msg = f"\n✅ [{session_name}] Все операции с каналами завершены!"
                    print(log_msg)
                    await add_to_log_buffer(log_msg, "success")

        log_msg = f"📤 [{session_name}] Отправляем сообщение для активации бота..."
        print(log_msg)
        await add_to_log_buffer(log_msg, "info")
        await client.send_message(target_group, "s")
        log_msg = f"✅ [{session_name}] Сообщение отправлено, ожидаем упоминания (макс. {auto_subscribe_wait_for_mention} сек)..."
        print(log_msg)
        await add_to_log_buffer(log_msg, "info")
        wait_time = 0
        max_wait_time = auto_subscribe_wait_for_mention
        while wait_time < max_wait_time and not stop_event.is_set():
            if mentioned and subscription_complete:
                log_msg = f"\n✅ [{session_name}] Все задачи выполнены!"
                print(log_msg)
                await add_to_log_buffer(log_msg, "success")
                break
            elif mentioned and not subscription_complete:
                await asyncio.sleep(1)
                wait_time += 1
                if wait_time % 5 == 0:
                    log_msg = f"⏳ [{session_name}] Завершаем подписку... {wait_time}с"
                    print(log_msg)
                    await add_to_log_buffer(log_msg, "info")
            else:
                await asyncio.sleep(1)
                wait_time += 1
                if wait_time % 5 == 0:
                    log_msg = f"⏳ [{session_name}] Ожидание упоминания... {wait_time}/{max_wait_time}с"
                    print(log_msg)
                    await add_to_log_buffer(log_msg, "info")
        client.remove_event_handler(mention_handler)
        if wait_time >= max_wait_time:
            log_msg = f"\n⏰ [{session_name}] Время ожидания упоминания истекло ({max_wait_time}с) - продолжаем без подписки"
            print(log_msg)
            await add_to_log_buffer(log_msg, "warning")
    except Exception as e:
        log_msg = f"❌ [{session_name}] Ошибка в мониторинге: {e}"
        print(log_msg)
        await add_to_log_buffer(log_msg, "error")
        traceback.print_exc()


async def process_folder_link(client, link, session_name=""):
    try:
        if 'addlist/' in link:
            slug = link.split('addlist/')[-1].split('?')[0]
        else:
            slug = link
        log_msg = f"🔍 [{session_name}] Проверка папки..."
        print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "info")
        try:
            check_result = await client(CheckChatlistInviteRequest(slug))
            all_chats = []
            if hasattr(check_result, 'chats') and check_result.chats:
                all_chats = list(check_result.chats)
                log_msg = f"✅ [{session_name}] Папка найдена, получено {len(all_chats)} чатов"
                print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")
                await add_to_log_buffer(log_msg, "success")
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
                    await add_to_log_buffer(chat_log, "info" if can_write else "warning")
                return all_chats, True
            else:
                log_msg = f"⚠️ [{session_name}] Папка доступна, но чаты не получены. Возможно, нужно вступить..."
                print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
                await add_to_log_buffer(log_msg, "warning")
                if hasattr(check_result, 'peers') and check_result.peers:
                    try:
                        join_result = await client(JoinChatlistInviteRequest(slug=slug, peers=check_result.peers))
                        log_msg = f"✅ [{session_name}] Успешно вступил в папку"
                        print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")
                        await add_to_log_buffer(log_msg, "success")
                        await asyncio.sleep(2)
                        updated_check = await client(CheckChatlistInviteRequest(slug))
                        if hasattr(updated_check, 'chats') and updated_check.chats:
                            all_chats = list(updated_check.chats)
                            log_msg = f"✅ [{session_name}] Получено {len(all_chats)} чатов после вступления"
                            print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")
                            await add_to_log_buffer(log_msg, "success")
                            return all_chats, True
                    except UserAlreadyParticipantError:
                        log_msg = f"ℹ️ [{session_name}] Уже в папке, но чаты не получены"
                        print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
                        await add_to_log_buffer(log_msg, "info")
                    except Exception as e:
                        log_msg = f"❌ [{session_name}] Ошибка при вступлении в папку: {e}"
                        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
                        await add_to_log_buffer(log_msg, "error")
                return [], False
        except InviteHashExpiredError:
            log_msg = f"❌ [{session_name}] Ссылка на папку истекла"
            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "error")
            return None, False
        except FloodWaitError as e:
            wait_time = e.seconds
            log_msg = f"⏳ [{session_name}] FloodWait: {wait_time}с"
            print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "flood")
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
            await add_to_log_buffer(log_msg, "error")
            return None, False
    except Exception as e:
        log_msg = f"❌ [{session_name}] Ошибка обработки папки: {e}"
        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "error")
        return None, False


async def get_chat_from_link(client, link, session_name=""):
    try:
        link = link.strip()
        if 'addlist' in link:
            log_msg = f"📁 [{session_name}] Обнаружена ссылка на папку с группами"
            print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "info")
            chats, success = await process_folder_link(client, link, session_name)
            if success and chats:
                return chats, "folder"
            elif success and not chats:
                log_msg = f"⚠️ [{session_name}] Папка обработана, но чаты не получены"
                print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
                await add_to_log_buffer(log_msg, "warning")
                return [], "folder_empty"
            else:
                log_msg = f"❌ [{session_name}] Не удалось обработать папку"
                print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
                await add_to_log_buffer(log_msg, "error")
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
                        await add_to_log_buffer(log_msg, "success")
                        return entity, "chat"
                    except ValueError as e:
                        if "Cannot find any entity" in str(e):
                            log_msg = f"❌ [{session_name}] Не удалось найти чат по ссылке"
                            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
                            await add_to_log_buffer(log_msg, "error")
                            return None, "error"
                        else:
                            raise
                else:
                    entity = await client.get_entity(link)
                    chat_title = getattr(entity, 'title', str(entity.id))
                    log_msg = f"✅ [{session_name}] Получен чат: {chat_title[:50]}"
                    print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")
                    await add_to_log_buffer(log_msg, "success")
                    return entity, "chat"
            except FloodWaitError as e:
                wait_time = e.seconds
                log_msg = f"⏳ [{session_name}] FloodWait: {wait_time}с"
                print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
                await add_to_log_buffer(log_msg, "flood")
                await asyncio.sleep(wait_time)
                return await get_chat_from_link(client, link, session_name)
            except (ChannelPrivateError, ChatAdminRequiredError):
                log_msg = f"❌ [{session_name}] Нет доступа к чату"
                print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
                await add_to_log_buffer(log_msg, "error")
                return None, "error"
            except Exception as e:
                log_msg = f"❌ [{session_name}] Ошибка при получении чата: {e}"
                print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
                await add_to_log_buffer(log_msg, "error")
                return None, "error"
    except Exception as e:
        log_msg = f"❌ [{session_name}] Общая ошибка: {e}"
        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "error")
        return None, "error"


async def get_user_chats(client, chat_type="all"):
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
        await add_to_log_buffer(log_msg, "success")
        if skipped_channels > 0:
            log_msg = f"ℹ Пропущено каналов: {skipped_channels}"
            print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "info")
        return chats
    except Exception as e:
        log_msg = f"✘ Ошибка получения чатов: {e}"
        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "error")
        return []


async def send_message_safely(client, chat, message, delete_after=False, media_path=None, retry_count=0,
                              session_name=""):
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
            await add_to_log_buffer(log_msg, "info")
        if use_proxy and session_name:
            proxy_manager.mark_proxy_success(session_name)
        return True, sent_message
    except FloodWaitError as e:
        log_msg = f"⏳ FloodWait {e.seconds} сек..."
        print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "flood")
        await asyncio.sleep(e.seconds)
        return await send_message_safely(client, chat, message, delete_after, media_path, retry_count, session_name)
    except (ChatAdminRequiredError, ChannelPrivateError, UserPrivacyRestrictedError):
        return False, None
    except (ConnectionError, TimeoutError, asyncio.TimeoutError, OSError) as e:
        if use_proxy and proxy_manager.has_proxies() and session_name and retry_count < proxy_max_retries * len(
                proxy_manager.proxies):
            proxy_info = ""
            if session_name in proxy_manager.proxy_assignments:
                proxy_str = proxy_manager.proxy_assignments[session_name]
                proxy_info = f" (прокси #{proxy_manager.proxy_stats[proxy_str]['line_number']} {proxy_manager.proxy_stats[proxy_str]['host']})"
            log_msg = f"🌐 Ошибка подключения{proxy_info}: {e}. Меняем прокси для {session_name} и пробуем снова ({retry_count + 1}/{proxy_max_retries * len(proxy_manager.proxies)})..."
            print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "proxy")
            proxy_manager.mark_proxy_failure(session_name)
            new_proxy = proxy_manager.rotate_proxy_for_session(session_name)
            if new_proxy:
                if session_name in proxy_manager.proxy_assignments:
                    new_proxy_str = proxy_manager.proxy_assignments[session_name]
                    new_proxy_info = f"#{proxy_manager.proxy_stats[new_proxy_str]['line_number']} {proxy_manager.proxy_stats[new_proxy_str]['host']}"
                    log_msg = f"🔄 [{session_name}] Назначен новый прокси: {new_proxy_info}"
                    print(f"{Fore.MAGENTA}{log_msg}{Style.RESET_ALL}")
                    await add_to_log_buffer(log_msg, "proxy")
                await client.disconnect()
                client.set_proxy(new_proxy)
                await asyncio.sleep(2)
                await client.connect()
                return await send_message_safely(client, chat, message, delete_after, media_path, retry_count + 1,
                                                 session_name)
        return False, None
    except Exception as e:
        log_msg = f"✘ Другая ошибка: {e}"
        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "error")
        return False, None


async def join_chat_safely(client, link, session_name="", retry_count=0):
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
            await add_to_log_buffer(log_msg, "success")
            if use_proxy and session_name:
                proxy_manager.mark_proxy_success(session_name)
            return True, chat_title
        except UserAlreadyParticipantError:
            log_msg = f"⚠️ [{session_name}] Уже состоит в чате/группе"
            print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "warning")
            return True, "Уже участник"
    except FloodWaitError as e:
        wait_time = e.seconds
        log_msg = f"⏳ [{session_name}] Telegram требует паузу! Ожидание {wait_time} секунд..."
        print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "flood")
        if wait_time > 60:
            minutes = wait_time // 60
            seconds = wait_time % 60
            log_msg = f"⏳ Это примерно {minutes} минут {seconds} секунд"
            print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "flood")
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
        await add_to_log_buffer(log_msg, "info")
        return await join_chat_safely(client, link, session_name, retry_count)
    except (ConnectionError, TimeoutError, asyncio.TimeoutError, OSError) as e:
        if use_proxy and proxy_manager.has_proxies() and session_name and retry_count < proxy_max_retries * len(
                proxy_manager.proxies):
            proxy_info = ""
            if session_name in proxy_manager.proxy_assignments:
                proxy_str = proxy_manager.proxy_assignments[session_name]
                proxy_info = f" (прокси #{proxy_manager.proxy_stats[proxy_str]['line_number']} {proxy_manager.proxy_stats[proxy_str]['host']})"
            log_msg = f"🌐 Ошибка подключения{proxy_info}: {e}. Меняем прокси для {session_name} и пробуем снова ({retry_count + 1}/{proxy_max_retries * len(proxy_manager.proxies)})..."
            print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "proxy")
            proxy_manager.mark_proxy_failure(session_name)
            new_proxy = proxy_manager.rotate_proxy_for_session(session_name)
            if new_proxy:
                if session_name in proxy_manager.proxy_assignments:
                    new_proxy_str = proxy_manager.proxy_assignments[session_name]
                    new_proxy_info = f"#{proxy_manager.proxy_stats[new_proxy_str]['line_number']} {proxy_manager.proxy_stats[new_proxy_str]['host']}"
                    log_msg = f"🔄 [{session_name}] Назначен новый прокси: {new_proxy_info}"
                    print(f"{Fore.MAGENTA}{log_msg}{Style.RESET_ALL}")
                    await add_to_log_buffer(log_msg, "proxy")
                await client.disconnect()
                client.set_proxy(new_proxy)
                await asyncio.sleep(2)
                await client.connect()
                return await join_chat_safely(client, link, session_name, retry_count + 1)
        return False, str(e)[:50]
    except InviteHashExpiredError:
        log_msg = f"✘ [{session_name}] Ссылка-приглашение истекла: {link[:50]}..."
        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "error")
        return False, "Ссылка истекла"
    except InviteHashInvalidError:
        log_msg = f"✘ [{session_name}] Недействительная ссылка-приглашение: {link[:50]}..."
        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "error")
        return False, "Недействительная ссылка"
    except ChannelPrivateError:
        log_msg = f"✘ [{session_name}] Канал/группа приватный/закрытый: {link[:50]}..."
        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "error")
        return False, "Приватный канал"
    except ValueError as e:
        if "Cannot find any entity" in str(e):
            log_msg = f"✘ [{session_name}] Не удалось найти чат/группу по ссылке: {link[:50]}..."
            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "error")
        else:
            log_msg = f"✘ [{session_name}] Ошибка: {e}"
            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "error")
        return False, str(e)[:50]
    except Exception as e:
        error_msg = str(e)[:50]
        log_msg = f"✘ [{session_name}] Ошибка при вступлении в {link[:50]}...: {error_msg}"
        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "error")
        return False, error_msg


async def create_telegram_client(session_name, api_id, api_hash, account_age_days=0):
    session_path = os.path.join(session_folder, session_name.replace('.session', ''))
    proxy = proxy_manager.get_proxy_for_session(session_name) if use_proxy and proxy_manager.has_proxies() else None
    device_models = ["PC", "Desktop", "Windows", "MacBook", "iPhone", "Android", "Linux", "Chrome", "Firefox"]
    system_versions = ["Windows 10", "Windows 11", "macOS 13", "Android 13", "iOS 16", "Ubuntu 22.04", "Debian 11"]
    app_versions = [CURRENT_VERSION, "1.6.0", "1.5.2", "1.4.0", "1.3.0"]
    client = TelegramClient(session_path, api_id, api_hash, connection_retries=5, timeout=30, request_retries=3,
                            flood_sleep_threshold=60, proxy=proxy, device_model=random.choice(device_models),
                            system_version=random.choice(system_versions), app_version=random.choice(app_versions))
    account_protector.register_account(session_name, account_age_days)
    if proxy and session_name in proxy_manager.proxy_assignments:
        proxy_str = proxy_manager.proxy_assignments[session_name]
        proxy_info = f"#{proxy_manager.proxy_stats[proxy_str]['line_number']} {proxy_manager.proxy_stats[proxy_str]['host']}"
        log_msg = f"🌐 Сессии {session_name} назначен прокси: {proxy_info}"
        print(f"{Fore.MAGENTA}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "proxy")
    return client


async def process_account_join(session_file, api_id, api_hash, join_links, delay_between_joins=5):
    client = await create_telegram_client(session_file, api_id, api_hash)
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
            await add_to_log_buffer(log_msg, "error")
            log_invalid_session(session_file)
            return 0, 0, 0, 0, False
        try:
            me = await client.get_me()
            account_info = f"@{me.username or me.id}"
        except Exception as get_me_error:
            log_msg = f"✘ [{session_file}] Ошибка при получении информации о пользователе: {get_me_error}"
            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "error")
            log_invalid_session(session_file)
            return 0, 0, 0, 0, False
        proxy_info = ""
        if session_file in proxy_manager.proxy_assignments:
            proxy_str = proxy_manager.proxy_assignments[session_file]
            proxy_info = f" [прокси #{proxy_manager.proxy_stats[proxy_str]['line_number']} {proxy_manager.proxy_stats[proxy_str]['host']}]"
        log_msg = f"\n⚙ Обработка сессии: {session_file} ({account_info}){proxy_info}"
        print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "info")
        log_msg = f"ℹ Всего ссылок для входа: {len(join_links)}"
        print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "info")
        for i, link in enumerate(join_links, 1):
            if stop_event.is_set():
                print("\n" + Fore.YELLOW + "🛑 Остановлено пользователем" + Style.RESET_ALL)
                await add_to_log_buffer("🛑 Остановлено пользователем", "warning")
                break
            log_msg = f"[{account_info}] [{i}/{len(join_links)}] Вступление по ссылке: {link[:50]}..."
            print(log_msg)
            await add_to_log_buffer(log_msg, "info")
            if anti_ban_enabled:
                can_join, remaining = account_protector.can_join_channel(session_file)
                if not can_join:
                    log_msg = f"⚠️ [{session_file}] Достигнут дневной лимит вступлений ({max_daily_joins}). Пропускаем..."
                    print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
                    await add_to_log_buffer(log_msg, "warning")
                    failed_count += 1
                    continue
            success, result = await join_chat_safely(client, link, account_info)
            if success:
                if result == "Уже участник":
                    already_joined_count += 1
                else:
                    joined_count += 1
                    if anti_ban_enabled:
                        account_protector.record_join(session_file, is_channel=True)
            else:
                failed_count += 1
            if "FloodWait" in result or "пауза" in str(result).lower():
                flood_pause_count += 1
            if i < len(join_links):
                delay = delay_between_joins
                if anti_ban_enabled:
                    delay = account_protector.get_safe_delay(session_file, delay)
                    should_pause, pause_time = account_protector.should_pause(session_file)
                    if should_pause:
                        log_msg = f"⏸️ [{session_file}] Защитная пауза {pause_time}с для предотвращения бана..."
                        print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
                        await add_to_log_buffer(log_msg, "warning")
                        await asyncio.sleep(pause_time)
                delay = await human_like_pause(delay, session_file)
                await asyncio.sleep(delay)
    except Exception as e:
        log_msg = f"✘ [{session_file}] {str(e)[:60]}"
        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "error")
        traceback.print_exc()
    finally:
        try:
            if client.is_connected():
                await client.disconnect()
        except:
            pass
    proxy_info = ""
    if session_file in proxy_manager.proxy_assignments:
        proxy_str = proxy_manager.proxy_assignments[session_file]
        proxy_info = f" [прокси #{proxy_manager.proxy_stats[proxy_str]['line_number']} {proxy_manager.proxy_stats[proxy_str]['host']}]"
    log_msg = f"\n--- ИТОГ {session_file} ({account_info}){proxy_info} ---"
    print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")
    await add_to_log_buffer(log_msg, "info")
    log_msg = f"✔ Вступил: {joined_count}"
    print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")
    await add_to_log_buffer(log_msg, "success")
    log_msg = f"⚠️ Уже состоял: {already_joined_count}"
    print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
    await add_to_log_buffer(log_msg, "warning")
    log_msg = f"✘ Ошибок: {failed_count}"
    print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
    await add_to_log_buffer(log_msg, "error")
    if flood_pause_count > 0:
        log_msg = f"⏳ Пауз из-за флуда: {flood_pause_count}"
        print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "flood")
    log_msg = "-------------------------------------"
    print(log_msg)
    await add_to_log_buffer(log_msg, "info")
    return joined_count, failed_count, already_joined_count, flood_pause_count, True


async def run_join_broadcast(api_id, api_hash, session_files, join_links):
    print("\n" + Fore.MAGENTA + "--- Запуск вступления в группы ---" + Style.RESET_ALL)
    await add_to_log_buffer("--- Запуск вступления в группы ---", "info")
    print(f"Сессий: {len(session_files)}")
    await add_to_log_buffer(f"Сессий: {len(session_files)}", "info")
    print(f"Ссылок для входа: {len(join_links)}")
    await add_to_log_buffer(f"Ссылок для входа: {len(join_links)}", "info")
    print(f"Задержка между вступлениями: 5 сек")
    await add_to_log_buffer("Задержка между вступлениями: 5 сек", "info")
    if anti_ban_enabled:
        print(f"{Fore.GREEN}🛡️ Анти-бан защита: ВКЛЮЧЕНА{Style.RESET_ALL}")
        await add_to_log_buffer("🛡️ Анти-бан защита: ВКЛЮЧЕНА", "success")
    if safe_mode:
        print(f"{Fore.GREEN}🔒 Безопасный режим: ВКЛЮЧЕН{Style.RESET_ALL}")
        await add_to_log_buffer("🔒 Безопасный режим: ВКЛЮЧЕН", "success")
    if use_proxy and proxy_manager.has_proxies():
        print(f"{Fore.CYAN}🌐 Используется {proxy_manager.get_proxy_count()} прокси{Style.RESET_ALL}")
        await add_to_log_buffer(f"🌐 Используется {proxy_manager.get_proxy_count()} прокси", "proxy")
    print("---")
    await add_to_log_buffer("---", "info")
    tasks = []
    processed_session_files = []
    for i, session_file in enumerate(session_files):
        if stop_event.is_set():
            break
        task = asyncio.create_task(
            process_account_join(session_file, api_id, api_hash, join_links, delay_between_joins=5))
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
                await add_to_log_buffer(f"✘ Ошибка обработки результата для {processed_session_files[i]}: {res_err}",
                                        "error")
        print("\n" + "=" * 50)
        await add_to_log_buffer("=" * 50, "info")
        print(f"{Fore.MAGENTA}     ✔ ОБЩАЯ СТАТИСТИКА ВСТУПЛЕНИЙ")
        await add_to_log_buffer("✔ ОБЩАЯ СТАТИСТИКА ВСТУПЛЕНИЙ", "success")
        print("=" * 50)
        await add_to_log_buffer("=" * 50, "info")
        print(f"{Fore.GREEN}✔ Всего вступили: {total_joined}")
        await add_to_log_buffer(f"✔ Всего вступили: {total_joined}", "success")
        print(f"{Fore.YELLOW}⚠️ Уже состояли: {total_already}")
        await add_to_log_buffer(f"⚠️ Уже состояли: {total_already}", "warning")
        print(f"{Fore.RED}✘ Всего ошибок: {total_failed}")
        await add_to_log_buffer(f"✘ Всего ошибок: {total_failed}", "error")
        if total_flood_pauses > 0:
            print(f"{Fore.YELLOW}⏳ Всего пауз из-за флуда: {total_flood_pauses}")
            await add_to_log_buffer(f"⏳ Всего пауз из-за флуда: {total_flood_pauses}", "flood")
        print(f"{Fore.GREEN}✔ Работало сессий: {working_sessions}/{len(processed_session_files)}")
        await add_to_log_buffer(f"✔ Работало сессий: {working_sessions}/{len(processed_session_files)}", "success")
        print("=" * 50)
        await add_to_log_buffer("=" * 50, "info")
    print(Fore.MAGENTA + "--- Вступление в группы завершено ---" + Style.RESET_ALL)
    await add_to_log_buffer("--- Вступление в группы завершено ---", "info")


async def process_account(session_file, api_id, api_hash, message, max_messages, delete_after, use_media_flag,
                          media_file_path, recipient_filter, fast_mode_flag, fast_delay_val, target_chats_ids=None,
                          cycle_number=1):
    client = await create_telegram_client(session_file, api_id, api_hash)
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
            await add_to_log_buffer(log_msg, "error")
            log_invalid_session(session_file)
            return 0, 0, 0, 0, False
        try:
            me = await client.get_me()
            authorized = True
            account_info = f"@{me.username or me.id}"
        except Exception as get_me_error:
            log_msg = f"✘ [{session_file}] Ошибка при получении информации о пользователе: {get_me_error}"
            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "error")
            log_invalid_session(session_file)
            return 0, 0, 0, 0, False
        proxy_info = ""
        if session_file in proxy_manager.proxy_assignments:
            proxy_str = proxy_manager.proxy_assignments[session_file]
            proxy_info = f" [прокси #{proxy_manager.proxy_stats[proxy_str]['line_number']} {proxy_manager.proxy_stats[proxy_str]['host']}]"
        log_msg = f"\n⚙ Обработка сессии: {session_file} ({account_info}){proxy_info}"
        print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "info")
        if fast_mode_flag and safe_mode:
            log_msg = f"⚠️ Быстрый режим отключен в безопасном режиме"
            print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "warning")
            fast_mode_flag = False
        if fast_mode_flag:
            log_msg = f"⚡ БЫСТРЫЙ РЕЖИМ: задержка {fast_delay_val}с"
            print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "info")
        if auto_subscribe_enabled and auto_subscribe_first_cycle_only and cycle_number == 1:
            log_msg = f"🤖 [{account_info}] Запускаем проверку автоподписки (цикл 1)..."
            print(f"{Fore.MAGENTA}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "info")
            groups_to_monitor = []
            if target_chats_ids:
                for target in target_chats_ids:
                    if isinstance(target, str) and ('t.me' in target or '@' in target):
                        try:
                            entity = await client.get_entity(target)
                            if isinstance(entity, (Channel, Chat)) and not isinstance(entity, User):
                                groups_to_monitor.append(entity)
                        except:
                            pass
            else:
                all_chats = await get_user_chats(client, "groups")
                groups_to_monitor.extend(all_chats)
            if groups_to_monitor:
                log_msg = f"🔍 [{account_info}] Проверяем {len(groups_to_monitor)} групп на необходимость подписки..."
                print(log_msg)
                await add_to_log_buffer(log_msg, "info")
                for group in groups_to_monitor[:5]:
                    if stop_event.is_set():
                        break
                    try:
                        await monitor_and_subscribe(client, account_info, group)
                    except Exception as e:
                        log_msg = f"⚠️ [{account_info}] Ошибка при проверке группы: {e}"
                        print(log_msg)
                        await add_to_log_buffer(log_msg, "warning")
                log_msg = f"✅ [{account_info}] Проверка автоподписки завершена"
                print(log_msg)
                await add_to_log_buffer(log_msg, "success")
            else:
                log_msg = f"ℹ️ [{account_info}] Нет групп для проверки автоподписки"
                print(log_msg)
                await add_to_log_buffer(log_msg, "info")
        chats_to_process = []
        if target_chats_ids:
            log_msg = f"ℹ Рассылка по целям из файла ({len(target_chats_ids)} шт.)"
            print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "info")
            for target in target_chats_ids:
                if stop_event.is_set():
                    break
                if isinstance(target, str):
                    result, result_type = await get_chat_from_link(client, target, account_info)
                    if result_type == "folder" and isinstance(result, list):
                        log_msg = f"✔ [{account_info}] Получено {len(result)} чатов из папки"
                        print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")
                        await add_to_log_buffer(log_msg, "success")
                        for chat in result:
                            if chat not in chats_to_process:
                                chats_to_process.append(chat)
                    elif result_type == "folder_empty":
                        log_msg = f"⚠️ [{account_info}] Папка обработана, но чаты не получены"
                        print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
                        await add_to_log_buffer(log_msg, "warning")
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
                        await add_to_log_buffer(log_msg, "error")
                    except Exception as e:
                        log_msg = f"✘ Ошибка при получении группы {target}: {e}"
                        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
                        await add_to_log_buffer(log_msg, "error")
            if not chats_to_process:
                log_msg = f"⚠️ [{account_info}] Не найдены доступные чаты для рассылки по списку!"
                print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
                await add_to_log_buffer(log_msg, "warning")
                return 0, 0, 0, 0, True
        else:
            chats_to_process = await get_user_chats(client, recipient_filter)
            if not chats_to_process:
                filter_names = {"all": "чатов", "users": "личных чатов", "groups": "групп"}
                log_msg = f"⚠️ [{account_info}] Нет доступных {filter_names[recipient_filter]}!"
                print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
                await add_to_log_buffer(log_msg, "warning")
                return 0, 0, 0, 0, True
        total_chats_processed = len(chats_to_process)
        log_msg = f"ℹ [{account_info}] Всего чатов для обработки: {total_chats_processed}"
        print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "info")
        for i, chat in enumerate(chats_to_process, 1):
            if stop_event.is_set():
                print("\n" + Fore.YELLOW + "🛑 Остановлено пользователем" + Style.RESET_ALL)
                await add_to_log_buffer("🛑 Остановлено пользователем", "warning")
                break
            if anti_ban_enabled:
                can_send, remaining = account_protector.can_send_message(session_file)
                if not can_send:
                    log_msg = f"⚠️ [{session_file}] Достигнут дневной лимит сообщений ({max_daily_messages}). Останавливаем..."
                    print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
                    await add_to_log_buffer(log_msg, "warning")
                    break
            chat_title = getattr(chat, 'title', f"чат ID {chat.id}")
            if isinstance(chat, User):
                chat_title = f"{chat.first_name or ''} {chat.last_name or ''}".strip() or f"пользователь {chat.id}"
            log_msg = f"[{account_info}] [{i}/{len(chats_to_process)}] '{chat_title[:30].strip()}...'"
            print(log_msg)
            await add_to_log_buffer(log_msg, "info")
            current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            media_to_use = media_file_path if use_media_flag and media_file_path and os.path.exists(
                media_file_path) else None
            success, sent_message = await send_message_safely(client, chat, message, delete_after, media_to_use,
                                                              session_name=session_file)
            if success:
                sent_count += 1
                log_msg = f"✔ ({current_time}) Отправлено!"
                print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")
                await add_to_log_buffer(log_msg, "success")
                if delete_after:
                    deleted_count += 1
                if anti_ban_enabled:
                    account_protector.record_message_sent(session_file)
            else:
                skipped_count += 1
                log_msg = f"✘ ({current_time}) Пропущено (нет доступа)"
                print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
                await add_to_log_buffer(log_msg, "error")
            if sent_count >= max_messages:
                log_msg = f"✔ Достигнут лимит: {max_messages} сообщений"
                print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")
                await add_to_log_buffer(log_msg, "success")
                break
            if i < len(chats_to_process):
                if fast_mode_flag:
                    delay = fast_delay_val
                else:
                    delay = delay_between_messages
                if anti_ban_enabled:
                    delay = account_protector.get_safe_delay(session_file, delay)
                    should_pause, pause_time = account_protector.should_pause(session_file)
                    if should_pause:
                        log_msg = f"⏸️ [{session_file}] Защитная пауза {pause_time}с для предотвращения бана..."
                        print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
                        await add_to_log_buffer(log_msg, "warning")
                        await asyncio.sleep(pause_time)
                delay = await human_like_pause(delay, session_file)
                await asyncio.sleep(delay)
    except asyncio.TimeoutError:
        log_msg = f"⏳ [{session_file}] Тайм-аут подключения"
        print(f"{Fore.YELLOW}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "warning")
        log_invalid_session(session_file)
    except (AuthKeyUnregisteredError, PhoneNumberInvalidError):
        log_msg = f"✘ [{session_file}] Сессия недействительна"
        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "error")
        log_invalid_session(session_file)
    except (PhoneCodeInvalidError, SessionPasswordNeededError, PasswordHashInvalidError):
        log_msg = f"✘ [{session_file}] Нужен логин/пароль"
        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "error")
        log_invalid_session(session_file)
    except RPCError as e:
        log_msg = f"✘ [{session_file}] RPC Error: {e}"
        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "error")
        log_invalid_session(session_file)
    except Exception as e:
        log_msg = f"✘ [{session_file}] {str(e)[:60]}"
        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "error")
        traceback.print_exc()
        log_invalid_session(session_file)
    finally:
        try:
            if client.is_connected():
                await client.disconnect()
        except:
            pass
    proxy_info = ""
    if session_file in proxy_manager.proxy_assignments:
        proxy_str = proxy_manager.proxy_assignments[session_file]
        proxy_info = f" [прокси #{proxy_manager.proxy_stats[proxy_str]['line_number']} {proxy_manager.proxy_stats[proxy_str]['host']}]"
    log_msg = f"\n--- ИТОГ {session_file} ({account_info}){proxy_info} ---"
    print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")
    await add_to_log_buffer(log_msg, "info")
    log_msg = f"✔ Отправлено: {sent_count}"
    print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")
    await add_to_log_buffer(log_msg, "success")
    log_msg = f"✘ Пропущено: {skipped_count}"
    print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
    await add_to_log_buffer(log_msg, "error")
    if delete_after:
        log_msg = f"🗑 Удалено у себя: {deleted_count}"
        print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "info")
    log_msg = f"ℹ Всего обработано: {total_chats_processed}"
    print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")
    await add_to_log_buffer(log_msg, "info")
    log_msg = "-------------------------------------"
    print(log_msg)
    await add_to_log_buffer(log_msg, "info")
    return sent_count, skipped_count, deleted_count, total_chats_processed, authorized


async def run_broadcast(api_id, api_hash, session_files, message, max_messages_per_account, repeat_broadcast_flag,
                        repeat_interval_val, delete_after, use_media_flag, media_file_path, recipient_filter,
                        fast_mode_flag, fast_delay_val, target_chats_ids=None, cycle_number=1):
    filter_names = {"all": "Все диалоги", "users": "Только личные чаты", "groups": "Только группы"}
    print("\n" + Fore.MAGENTA + "--- Запуск рассылки ---" + Style.RESET_ALL)
    await add_to_log_buffer("--- Запуск рассылки ---", "info")
    print(f"Сообщение: '{message[:60]}...'")
    await add_to_log_buffer(f"Сообщение: '{message[:60]}...'", "info")
    if use_media_flag and media_file_path and os.path.exists(media_file_path):
        print(f"{Fore.CYAN}🖼 Медиафайл: {os.path.basename(media_file_path)}")
        await add_to_log_buffer(f"🖼 Медиафайл: {os.path.basename(media_file_path)}", "info")
    print(f"Сессий: {len(session_files)}")
    await add_to_log_buffer(f"Сессий: {len(session_files)}", "info")
    if target_chats_ids:
        total_targets = len(target_chats_ids)
        folder_count = sum(1 for t in target_chats_ids if isinstance(t, str) and 'addlist' in t)
        if folder_count > 0:
            print(
                f"{Fore.CYAN}● Цели: {total_targets} элементов (включая {folder_count} папок с группами){Style.RESET_ALL}")
            await add_to_log_buffer(f"● Цели: {total_targets} элементов (включая {folder_count} папок с группами)",
                                    "info")
        else:
            print(f"{Fore.CYAN}● Цели: {total_targets} групп/ссылок из файла{Style.RESET_ALL}")
            await add_to_log_buffer(f"● Цели: {total_targets} групп/ссылок из файла", "info")
    else:
        print(f"{Fore.CYAN}● Цели: {filter_names[recipient_filter]}")
        await add_to_log_buffer(f"● Цели: {filter_names[recipient_filter]}", "info")
    print(f"Макс. сообщений/аккаунт: {max_messages_per_account}")
    await add_to_log_buffer(f"Макс. сообщений/аккаунт: {max_messages_per_account}", "info")
    if fast_mode_flag and not safe_mode:
        print(f"{Fore.YELLOW}⚡ РЕЖИМ СКОРОСТИ: БЫСТРЫЙ (задержка {fast_delay_val}с)")
        await add_to_log_buffer(f"⚡ РЕЖИМ СКОРОСТИ: БЫСТРЫЙ (задержка {fast_delay_val}с)", "info")
    elif fast_mode_flag and safe_mode:
        print(f"{Fore.YELLOW}⚡ Быстрый режим отключен в безопасном режиме{Style.RESET_ALL}")
        await add_to_log_buffer("⚡ Быстрый режим отключен в безопасном режиме", "warning")
    else:
        print(f"⏳ Задержка между сообщениями: {delay_between_messages}с")
        await add_to_log_buffer(f"⏳ Задержка между сообщениями: {delay_between_messages}с", "info")
    print(f"⏳ Задержка между аккаунтами: {delay_between_accounts}с")
    await add_to_log_buffer(f"⏳ Задержка между аккаунтами: {delay_between_accounts}с", "info")
    print(f"🔂 Повтор: {'ВКЛЮЧЕН' if repeat_broadcast_flag else 'ВЫКЛЮЧЕН'}")
    await add_to_log_buffer(f"🔂 Повтор: {'ВКЛЮЧЕН' if repeat_broadcast_flag else 'ВЫКЛЮЧЕН'}", "info")
    if repeat_broadcast_flag:
        print(f"⏱️ Интервал повтора: {repeat_interval_val}с")
        await add_to_log_buffer(f"⏱️ Интервал повтора: {repeat_interval_val}с", "info")
    print(f"🗑 Удаление у себя: {'ВКЛЮЧЕНО' if delete_after else 'ВЫКЛЮЧЕНО'}")
    await add_to_log_buffer(f"🗑 Удаление у себя: {'ВКЛЮЧЕНО' if delete_after else 'ВЫКЛЮЧЕНО'}", "info")
    if auto_subscribe_enabled:
        if auto_subscribe_first_cycle_only:
            print(
                f"{Fore.MAGENTA}🤖 АВТОПОДПИСКА: Только 1-й цикл (ожидание {auto_subscribe_wait_for_mention}с){Style.RESET_ALL}")
            await add_to_log_buffer(f"🤖 АВТОПОДПИСКА: Только 1-й цикл (ожидание {auto_subscribe_wait_for_mention}с)",
                                    "info")
        else:
            print(
                f"{Fore.MAGENTA}🤖 АВТОПОДПИСКА: Каждый цикл (ожидание {auto_subscribe_wait_for_mention}с){Style.RESET_ALL}")
            await add_to_log_buffer(f"🤖 АВТОПОДПИСКА: Каждый цикл (ожидание {auto_subscribe_wait_for_mention}с)",
                                    "info")
    if use_proxy and proxy_manager.has_proxies():
        print(f"{Fore.CYAN}🌐 Прокси: ВКЛЮЧЕНЫ ({proxy_manager.get_proxy_count()} шт.){Style.RESET_ALL}")
        await add_to_log_buffer(f"🌐 Прокси: ВКЛЮЧЕНЫ ({proxy_manager.get_proxy_count()} шт.)", "proxy")
    if anti_ban_enabled:
        print(f"{Fore.GREEN}🛡️ Анти-бан защита: ВКЛЮЧЕНА{Style.RESET_ALL}")
        await add_to_log_buffer("🛡️ Анти-бан защита: ВКЛЮЧЕНА", "success")
    if safe_mode:
        print(f"{Fore.GREEN}🔒 Безопасный режим: ВКЛЮЧЕН{Style.RESET_ALL}")
        await add_to_log_buffer("🔒 Безопасный режим: ВКЛЮЧЕН", "success")
    if human_like_delays:
        print(f"{Fore.GREEN}👤 Человекоподобные задержки: ВКЛЮЧЕНЫ{Style.RESET_ALL}")
        await add_to_log_buffer("👤 Человекоподобные задержки: ВКЛЮЧЕНЫ", "info")
    print("---")
    await add_to_log_buffer("---", "info")
    while True:
        if stop_event.is_set():
            break
        tasks = []
        processed_session_files = []
        for i, session_file in enumerate(session_files):
            if stop_event.is_set():
                break
            task = asyncio.create_task(
                process_account(session_file, api_id, api_hash, message, max_messages_per_account, delete_after,
                                use_media_flag, media_file_path, recipient_filter, fast_mode_flag, fast_delay_val,
                                target_chats_ids=target_chats_ids, cycle_number=cycle_number))
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
                    await add_to_log_buffer(
                        f"✘ Ошибка обработки результата для {processed_session_files[i]}: {res_err}", "error")
            print("\n" + "=" * 50)
            await add_to_log_buffer("=" * 50, "info")
            print(f"{Fore.MAGENTA}     ✔ ОБЩАЯ СТАТИСТИКА (ЦИКЛ {cycle_number})")
            await add_to_log_buffer(f"✔ ОБЩАЯ СТАТИСТИКА (ЦИКЛ {cycle_number})", "success")
            print("=" * 50)
            await add_to_log_buffer("=" * 50, "info")
            print(f"{Fore.GREEN}✔ Всего отправлено: {total_sent}")
            await add_to_log_buffer(f"✔ Всего отправлено: {total_sent}", "success")
            print(f"{Fore.RED}✘ Всего пропущено: {total_skipped}")
            await add_to_log_buffer(f"✘ Всего пропущено: {total_skipped}", "error")
            if delete_after:
                print(f"{Fore.CYAN}🗑 Всего удалено у себя: {total_deleted}")
                await add_to_log_buffer(f"🗑 Всего удалено у себя: {total_deleted}", "info")
            print(f"{Fore.CYAN}ℹ Всего чатов охвачено: {total_chats}")
            await add_to_log_buffer(f"ℹ Всего чатов охвачено: {total_chats}", "info")
            print(f"{Fore.GREEN}✔ Работало сессий: {working_sessions}/{len(processed_session_files)}")
            await add_to_log_buffer(f"✔ Работало сессий: {working_sessions}/{len(processed_session_files)}", "success")
            if invalid_count > 0:
                print(f"{Fore.RED}✘ Недействительных сессий: {invalid_count}")
                await add_to_log_buffer(f"✘ Недействительных сессий: {invalid_count}", "error")
            if os.path.exists(failed_subscriptions_file) and os.path.getsize(failed_subscriptions_file) > 0:
                print(f"{Fore.YELLOW}📋 Неудачные подписки сохранены в: {failed_subscriptions_file}{Style.RESET_ALL}")
                await add_to_log_buffer(f"📋 Неудачные подписки сохранены в: {failed_subscriptions_file}", "warning")
            print("=" * 50)
            await add_to_log_buffer("=" * 50, "info")
            if notify_cycle_results:
                proxy_summary = ""
                if use_proxy and proxy_manager.has_proxies():
                    proxy_summary = f"\n🌐 Использовано прокси: {len(proxy_manager.proxy_assignments)}"
                notification_message = f"📊 **Результаты цикла #{cycle_number}**\n\n✅ Отправлено: {total_sent}\n❌ Пропущено: {total_skipped}\n"
                if delete_after:
                    notification_message += f"🗑 Удалено у себя: {total_deleted}\n"
                notification_message += f"📝 Всего чатов: {total_chats}\n👥 Работало сессий: {working_sessions}/{len(processed_session_files)}\n"
                if invalid_count > 0:
                    notification_message += f"⚠️ Недействительных сессий: {invalid_count}\n"
                if proxy_summary:
                    notification_message += proxy_summary
                await send_notification(notification_message, "cycle_result")
            if notify_full_logs:
                await send_notification("", "full_log")
                async with log_buffer_lock:
                    log_buffer.clear()
        if repeat_broadcast_flag and not stop_event.is_set():
            print(f"\n{Fore.CYAN}ℹ Повтор рассылки через {repeat_interval_val} секунд...{Style.RESET_ALL}")
            await add_to_log_buffer(f"ℹ Повтор рассылки через {repeat_interval_val} секунд...", "info")
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
    await add_to_log_buffer("--- Рассылка завершена ---", "info")


async def run_auto_subscribe(api_id, api_hash, session_files, target_group_link):
    print("\n" + Fore.MAGENTA + "--- Запуск автоподписки на каналы ---" + Style.RESET_ALL)
    await add_to_log_buffer("--- Запуск автоподписки на каналы ---", "info")
    print(f"Сессий: {len(session_files)}")
    await add_to_log_buffer(f"Сессий: {len(session_files)}", "info")
    print(f"Целевая группа: {target_group_link}")
    await add_to_log_buffer(f"Целевая группа: {target_group_link}", "info")
    print(f"Режим: {'По упоминанию' if auto_subscribe_on_mention else 'По расписанию'}")
    await add_to_log_buffer(f"Режим: {'По упоминанию' if auto_subscribe_on_mention else 'По расписанию'}", "info")
    print(f"Макс. время ожидания упоминания: {auto_subscribe_wait_for_mention}с")
    await add_to_log_buffer(f"Макс. время ожидания упоминания: {auto_subscribe_wait_for_mention}с", "info")
    print(f"Задержка между подписками: {auto_subscribe_pause_between_channels}с")
    await add_to_log_buffer(f"Задержка между подписками: {auto_subscribe_pause_between_channels}с", "info")
    if anti_ban_enabled:
        print(f"{Fore.GREEN}🛡️ Анти-бан защита: ВКЛЮЧЕНА{Style.RESET_ALL}")
        await add_to_log_buffer("🛡️ Анти-бан защита: ВКЛЮЧЕНА", "success")
    print("---")
    await add_to_log_buffer("---", "info")
    tasks = []
    processed_session_files = []
    for i, session_file in enumerate(session_files):
        if stop_event.is_set():
            break
        task = asyncio.create_task(process_account_auto_subscribe(session_file, api_id, api_hash, target_group_link))
        tasks.append(task)
        processed_session_files.append(session_file)
        if i < len(session_files) - 1:
            log_msg = f"\n⏳ Задержка {delay_between_accounts}с перед следующей сессией..."
            print(log_msg)
            await add_to_log_buffer(log_msg, "info")
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
        await add_to_log_buffer("=" * 50, "info")
        print(f"{Fore.MAGENTA}     ✔ ОБЩАЯ СТАТИСТИКА АВТОПОДПИСКИ")
        await add_to_log_buffer("✔ ОБЩАЯ СТАТИСТИКА АВТОПОДПИСКИ", "success")
        print("=" * 50)
        await add_to_log_buffer("=" * 50, "info")
        print(f"{Fore.GREEN}✔ Успешно завершено: {successful}")
        await add_to_log_buffer(f"✔ Успешно завершено: {successful}", "success")
        print(f"{Fore.RED}✘ Ошибок: {failed}")
        await add_to_log_buffer(f"✘ Ошибок: {failed}", "error")
        print("=" * 50)
        await add_to_log_buffer("=" * 50, "info")
        if notify_cycle_results:
            notification_message = f"📊 **Результаты автоподписки**\n\n✅ Успешно: {successful}\n❌ Ошибок: {failed}\n"
            await send_notification(notification_message, "cycle_result")
    print(Fore.MAGENTA + "--- Автоподписка завершена ---" + Style.RESET_ALL)
    await add_to_log_buffer("--- Автоподписка завершена ---", "info")


async def process_account_auto_subscribe(session_file, api_id, api_hash, target_group_link):
    client = await create_telegram_client(session_file, api_id, api_hash)
    account_info = "неавторизована"
    success = False
    try:
        await client.connect()
        if not await client.is_user_authorized():
            log_msg = f"✘ [{session_file}] НЕ АВТОРИЗОВАНА - ПРОПУЩЕНА"
            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "error")
            log_invalid_session(session_file)
            return False
        try:
            me = await client.get_me()
            account_info = f"@{me.username or me.id}"
        except Exception as get_me_error:
            log_msg = f"✘ [{session_file}] Ошибка при получении информации о пользователе: {get_me_error}"
            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "error")
            log_invalid_session(session_file)
            return False
        proxy_info = ""
        if session_file in proxy_manager.proxy_assignments:
            proxy_str = proxy_manager.proxy_assignments[session_file]
            proxy_info = f" [прокси #{proxy_manager.proxy_stats[proxy_str]['line_number']} {proxy_manager.proxy_stats[proxy_str]['host']}]"
        log_msg = f"\n⚙ Обработка сессии: {session_file} ({account_info}){proxy_info}"
        print(f"{Fore.CYAN}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "info")
        try:
            target_group = await client.get_entity(target_group_link)
            log_msg = f"✅ [{account_info}] Найдена группа: {target_group.title}"
            print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "success")
        except Exception as e:
            log_msg = f"❌ [{account_info}] Не удалось найти группу: {e}"
            print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
            await add_to_log_buffer(log_msg, "error")
            return False
        await monitor_and_subscribe(client, account_info, target_group)
        log_msg = f"\n✅ [{account_info}] Процесс автоподписки завершен"
        print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "success")
        success = True
    except Exception as e:
        log_msg = f"✘ [{account_info}] Ошибка: {str(e)[:60]}"
        print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
        await add_to_log_buffer(log_msg, "error")
        traceback.print_exc()
    finally:
        try:
            if client.is_connected():
                await client.disconnect()
        except:
            pass
    return success


async def display_proxy_menu():
    global use_proxy, proxy_file, proxy_rotate_on_fail, proxy_max_retries, proxy_manager
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_header("🌐 НАСТРОЙКИ ПРОКСИ")
        proxy_count = proxy_manager.get_proxy_count()
        bad_count = len(proxy_manager.bad_proxies)
        print(
            f"{CLR_INFO}1. Использовать прокси: {CLR_SUCCESS if use_proxy else CLR_ERR}{'ВКЛ' if use_proxy else 'ВЫКЛ'}")
        print(f"{CLR_INFO}2. Файл с прокси: {CLR_WARN}{proxy_file}")
        print(f"{CLR_INFO}3. Загружено прокси: {CLR_WARN}{proxy_count} (🚫 {bad_count} плохих)")
        print(
            f"{CLR_INFO}4. Менять прокси при ошибке: {CLR_SUCCESS if proxy_rotate_on_fail else CLR_ERR}{'ВКЛ' if proxy_rotate_on_fail else 'ВЫКЛ'}")
        print(f"{CLR_INFO}5. Макс. количество попыток: {CLR_WARN}{proxy_max_retries}")
        print(f"{CLR_INFO}6. Перезагрузить прокси из файла")
        print(f"{CLR_INFO}7. Форматы прокси (примеры)")
        print(f"{CLR_INFO}8. 📊 Статистика прокси")
        print(f"{CLR_INFO}9. 🔄 Очистить список плохих прокси")
        print(f"{CLR_INFO}10. ℹ️ Информация о распределении")
        print(f"{CLR_ERR}0. 🔙 Назад")
        print(f"\n{CLR_WARN}Поддерживаемые форматы:{Style.RESET_ALL}")
        print("  • socks5://user:pass@ip:port")
        print("  • socks5://ip:port")
        print("  • ip:port (по умолчанию socks5)")
        print("  • user:pass@ip:port")
        print(f"\n{Fore.CYAN}Текущее распределение:{Style.RESET_ALL}")
        if proxy_manager.proxy_assignments:
            for session, proxy in list(proxy_manager.proxy_assignments.items())[:5]:
                if proxy in proxy_manager.proxy_stats:
                    proxy_info = f"#{proxy_manager.proxy_stats[proxy]['line_number']} {proxy_manager.proxy_stats[proxy]['host']}"
                    print(f"  📱 {session[:15]}... → {proxy_info}")
            if len(proxy_manager.proxy_assignments) > 5:
                print(f"  ... и еще {len(proxy_manager.proxy_assignments) - 5} сессий")
        else:
            print("  Нет активных назначений")
        choice = input(f"\n{CLR_MAIN}Выберите пункт ➔ {RESET}").strip()
        if choice == '1':
            use_proxy = not use_proxy
            print(f"{Fore.GREEN}✔ Использование прокси {'включено' if use_proxy else 'выключено'}.{Style.RESET_ALL}")
        elif choice == '2':
            new_file = input(f"Имя файла с прокси (текущий: {proxy_file}): ").strip()
            if new_file:
                proxy_file = new_file
                new_manager = ProxyManager(proxy_file)
                proxy_manager = new_manager
                print(
                    f"{Fore.GREEN}✔ Файл с прокси обновлен. Загружено {proxy_manager.get_proxy_count()} прокси.{Style.RESET_ALL}")
        elif choice == '3':
            print(f"{Fore.CYAN}Загружено прокси: {proxy_count}{Style.RESET_ALL}")
            if proxy_count > 0:
                print(f"{Fore.YELLOW}Первые 10 прокси:{Style.RESET_ALL}")
                for i, p in enumerate(proxy_manager.proxies[:10], 1):
                    status = "✅" if p not in proxy_manager.bad_proxies else "❌"
                    usage = proxy_manager.proxy_usage_count.get(p, 0)
                    if p in proxy_manager.proxy_stats:
                        line_num = proxy_manager.proxy_stats[p]['line_number']
                        host = proxy_manager.proxy_stats[p]['host']
                        print(f"  {i}. {status} #{line_num} {host} (использован: {usage} раз)")
            input("Нажмите Enter...")
        elif choice == '4':
            proxy_rotate_on_fail = not proxy_rotate_on_fail
            print(
                f"{Fore.GREEN}✔ Автоматическая смена прокси при ошибке {'включена' if proxy_rotate_on_fail else 'выключена'}.{Style.RESET_ALL}")
        elif choice == '5':
            try:
                new_value = int(input(f"Макс. количество попыток (текущее: {proxy_max_retries}): "))
                if new_value > 0:
                    proxy_max_retries = new_value
                    print(f"{Fore.GREEN}✔ Количество попыток обновлено.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}✘ Введите число больше 0.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}✘ Введите число.{Style.RESET_ALL}")
        elif choice == '6':
            new_manager = ProxyManager(proxy_file)
            proxy_manager = new_manager
            print(
                f"{Fore.GREEN}✔ Прокси перезагружены. Загружено {proxy_manager.get_proxy_count()} прокси.{Style.RESET_ALL}")
        elif choice == '7':
            print(f"\n{Fore.CYAN}Примеры форматов прокси:{Style.RESET_ALL}")
            print("1. socks5://username:password@192.168.1.1:1080")
            print("2. socks5://192.168.1.1:1080")
            print("3. http://username:password@192.168.1.1:8080")
            print("4. 192.168.1.1:1080 (будет использован как socks5)")
            print("5. username:password@192.168.1.1:1080")
            print("\nКаждая строка в файле - один прокси.")
            input("Нажмите Enter...")
        elif choice == '8':
            stats = proxy_manager.get_stats()
            print(f"\n{Fore.CYAN}📊 Статистика прокси:{Style.RESET_ALL}")
            print(f"{'#':<4} {'Статус':<6} {'Успех':<6} {'Провал':<6} {'Исп.':<6} {'Рейтинг':<8} Прокси")
            print("-" * 80)
            for s in sorted(stats, key=lambda x: x['line'])[:20]:
                print(
                    f"{s['line']:<4} {s['status']:<6} {s['success']:<6} {s['fail']:<6} {s['usage']:<6} {s['rate']:<8} {s['host']}")
            input("Нажмите Enter...")
        elif choice == '9':
            proxy_manager.clear_bad_proxies()
        elif choice == '10':
            print(f"\n{Fore.CYAN}ℹ️ Информация о распределении прокси:{Style.RESET_ALL}")
            print("• Каждой сессии назначается свой прокси при создании")
            print("• Прокси распределяются равномерно (наименее использованные получают новые сессии)")
            print("• Если прокси не работает 3 раза подряд - он временно исключается")
            print("• При ошибке подключения прокси автоматически меняется на другой")
            print(f"• Сейчас активно сессий с прокси: {len(proxy_manager.proxy_assignments)}")
            print(f"• Всего прокси: {proxy_count}, плохих: {bad_count}")
            input("Нажмите Enter...")
        elif choice == '0':
            save_config()
            break
        await asyncio.sleep(1)


async def display_protection_menu():
    global safe_mode, max_daily_messages, max_daily_joins, anti_ban_enabled, human_like_delays, random_pause_enabled
    global proxy_manager
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_header("🛡️ НАСТРОЙКИ ЗАЩИТЫ")
        print(
            f"{CLR_INFO}1. 🛡️ Анти-бан защита: {CLR_SUCCESS if anti_ban_enabled else CLR_ERR}{'ВКЛ' if anti_ban_enabled else 'ВЫКЛ'}")
        print(
            f"{CLR_INFO}2. 🔒 Безопасный режим: {CLR_SUCCESS if safe_mode else CLR_ERR}{'ВКЛ' if safe_mode else 'ВЫКЛ'}")
        print(
            f"{CLR_INFO}3. 👤 Человекоподобные задержки: {CLR_SUCCESS if human_like_delays else CLR_ERR}{'ВКЛ' if human_like_delays else 'ВЫКЛ'}")
        print(
            f"{CLR_INFO}4. 🎲 Случайные паузы: {CLR_SUCCESS if random_pause_enabled else CLR_ERR}{'ВКЛ' if random_pause_enabled else 'ВЫКЛ'}")
        print(f"{CLR_INFO}5. 📊 Макс. сообщений в день: {CLR_WARN}{max_daily_messages}")
        print(f"{CLR_INFO}6. 📊 Макс. вступлений в день: {CLR_WARN}{max_daily_joins}")
        print(f"{CLR_INFO}7. ℹ️ Информация о защите")
        print(f"{CLR_ERR}0. 🔙 Назад")
        print(f"\n{CLR_WARN}Рекомендации:{Style.RESET_ALL}")
        print("  • Новые аккаунты (< 7 дней): 20-50 сообщений/день")
        print("  • Средние аккаунты (7-30 дней): 50-100 сообщений/день")
        print("  • Старые аккаунты (> 30 дней): 100-500 сообщений/день")
        choice = input(f"\n{CLR_MAIN}Выберите пункт ➔ {RESET}").strip()
        if choice == '1':
            anti_ban_enabled = not anti_ban_enabled
            print(f"{Fore.GREEN}✔ Анти-бан защита {'включена' if anti_ban_enabled else 'выключена'}.{Style.RESET_ALL}")
        elif choice == '2':
            safe_mode = not safe_mode
            print(f"{Fore.GREEN}✔ Безопасный режим {'включен' if safe_mode else 'выключен'}.{Style.RESET_ALL}")
        elif choice == '3':
            human_like_delays = not human_like_delays
            print(
                f"{Fore.GREEN}✔ Человекоподобные задержки {'включены' if human_like_delays else 'выключены'}.{Style.RESET_ALL}")
        elif choice == '4':
            random_pause_enabled = not random_pause_enabled
            print(
                f"{Fore.GREEN}✔ Случайные паузы {'включены' if random_pause_enabled else 'выключены'}.{Style.RESET_ALL}")
        elif choice == '5':
            try:
                new_value = int(input(f"Макс. сообщений в день (текущее: {max_daily_messages}): "))
                if new_value > 0:
                    max_daily_messages = new_value
                    print(f"{Fore.GREEN}✔ Лимит сообщений обновлен.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}✘ Введите число больше 0.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}✘ Введите число.{Style.RESET_ALL}")
        elif choice == '6':
            try:
                new_value = int(input(f"Макс. вступлений в день (текущее: {max_daily_joins}): "))
                if new_value > 0:
                    max_daily_joins = new_value
                    print(f"{Fore.GREEN}✔ Лимит вступлений обновлен.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}✘ Введите число больше 0.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}✘ Введите число.{Style.RESET_ALL}")
        elif choice == '7':
            print(f"\n{Fore.CYAN}🛡️ Информация о защите:{Style.RESET_ALL}")
            print("1. Анти-бан защита - автоматическое ограничение активности")
            print("2. Безопасный режим - отключает быстрый режим и агрессивные настройки")
            print("3. Человекоподобные задержки - имитация поведения реального пользователя")
            print("4. Случайные паузы - дополнительные случайные паузы между действиями")
            print("5. Дневные лимиты - предотвращают превышение лимитов Telegram")
            input("Нажмите Enter...")
        elif choice == '0':
            save_config()
            break
        await asyncio.sleep(1)


async def display_auto_subscribe_menu():
    global auto_subscribe_enabled, auto_subscribe_on_mention, auto_subscribe_delay, auto_subscribe_max_flood_wait
    global auto_subscribe_retry_after_flood, auto_subscribe_check_interval, auto_subscribe_wait_for_mention
    global auto_subscribe_pause_between_channels, auto_subscribe_forced_channels, auto_subscribe_first_cycle_only
    global proxy_manager
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
    global current_api_id, current_api_hash, session_folder, message_to_send, delay_between_messages, delay_between_accounts, max_messages_per_account, repeat_broadcast, repeat_interval, delete_after_send, recipient_type, use_media, media_path, fast_mode, fast_delay, notification_enabled, notification_bot_token, notification_chat_id, notify_invalid_session, notify_cycle_results, notify_full_logs
    global proxy_manager
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_header("⚙️ НАСТРОЙКИ ПАРАМЕТРОВ")
        print(f"{CLR_INFO}1. 🔑 API Настройки")
        print(f"{CLR_INFO}2. 📁 Настройки сессий")
        print(f"{CLR_INFO}3. ✉️ Настройки сообщений")
        print(f"{CLR_INFO}4. 🚀 Настройки рассылки")
        print(f"{CLR_INFO}5. 🔔 Настройки уведомлений")
        print(f"{CLR_INFO}6. 🤖 Настройки автоподписки")
        print(f"{CLR_INFO}7. 🌐 Настройки прокси")
        print(f"{CLR_INFO}8. 🛡️ Настройки защиты")
        print(f"{CLR_ACCENT}9. ♻️ Сброс настроек")
        print(f"{CLR_ERR}0. 🔙 Назад в меню")
        print(f"\n{CLR_WARN}Текущие значения:{Style.RESET_ALL}")
        print(f"  API ID: {current_api_id}")
        print(f"  Папка сессий: {session_folder}")
        print(f"  Сообщение: {message_to_send[:30]}...")
        if notification_enabled:
            print(f"  🔔 Уведомления: ВКЛ")
        if auto_subscribe_enabled:
            print(f"  🤖 Автоподписка: ВКЛ")
        if use_proxy and proxy_manager.has_proxies():
            print(f"  🌐 Прокси: ВКЛ ({proxy_manager.get_proxy_count()} шт.)")
        if anti_ban_enabled:
            print(f"  🛡️ Анти-бан: ВКЛ")
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
            await display_auto_subscribe_menu()
        elif choice == '7':
            await display_proxy_menu()
        elif choice == '8':
            await display_protection_menu()
        elif choice == '9':
            if input(f"{Fore.YELLOW}⚠️ Сбросить ВСЕ настройки к умолчанию? (y/n): ").lower() == 'y':
                globals().update({'current_api_id': DEFAULT_API_ID, 'current_api_hash': DEFAULT_API_HASH,
                                  'session_folder': DEFAULT_SESSION_FOLDER, 'message_to_send': DEFAULT_MESSAGE,
                                  'delay_between_messages': DEFAULT_DELAY_BETWEEN_MESSAGES,
                                  'delay_between_accounts': DEFAULT_DELAY_BETWEEN_ACCOUNTS,
                                  'max_messages_per_account': DEFAULT_MAX_MESSAGES_PER_ACCOUNT,
                                  'repeat_broadcast': DEFAULT_REPEAT_BROADCAST,
                                  'repeat_interval': DEFAULT_REPEAT_INTERVAL,
                                  'delete_after_send': DEFAULT_DELETE_AFTER_SEND,
                                  'recipient_type': DEFAULT_RECIPIENT_TYPE, 'use_media': DEFAULT_USE_MEDIA,
                                  'media_path': DEFAULT_MEDIA_PATH, 'fast_mode': DEFAULT_FAST_MODE,
                                  'fast_delay': DEFAULT_FAST_DELAY,
                                  'notification_enabled': DEFAULT_NOTIFICATION_ENABLED,
                                  'notification_bot_token': DEFAULT_NOTIFICATION_BOT_TOKEN,
                                  'notification_chat_id': DEFAULT_NOTIFICATION_CHAT_ID,
                                  'notify_invalid_session': DEFAULT_NOTIFY_INVALID_SESSION,
                                  'notify_cycle_results': DEFAULT_NOTIFY_CYCLE_RESULTS,
                                  'notify_full_logs': DEFAULT_NOTIFY_FULL_LOGS,
                                  'auto_subscribe_enabled': DEFAULT_AUTO_SUBSCRIBE_ENABLED,
                                  'auto_subscribe_on_mention': DEFAULT_AUTO_SUBSCRIBE_ON_MENTION,
                                  'auto_subscribe_delay': DEFAULT_AUTO_SUBSCRIBE_DELAY,
                                  'auto_subscribe_max_flood_wait': DEFAULT_AUTO_SUBSCRIBE_MAX_FLOOD_WAIT,
                                  'auto_subscribe_retry_after_flood': DEFAULT_AUTO_SUBSCRIBE_RETRY_AFTER_FLOOD,
                                  'auto_subscribe_check_interval': DEFAULT_AUTO_SUBSCRIBE_CHECK_INTERVAL,
                                  'auto_subscribe_wait_for_mention': DEFAULT_AUTO_SUBSCRIBE_WAIT_FOR_MENTION,
                                  'auto_subscribe_pause_between_channels': DEFAULT_AUTO_SUBSCRIBE_PAUSE_BETWEEN_CHANNELS,
                                  'auto_subscribe_forced_channels': DEFAULT_AUTO_SUBSCRIBE_FORCED_CHANNELS,
                                  'auto_subscribe_first_cycle_only': DEFAULT_AUTO_SUBSCRIBE_FIRST_CYCLE_ONLY,
                                  'use_proxy': DEFAULT_USE_PROXY, 'proxy_file': DEFAULT_PROXY_FILE,
                                  'proxy_rotate_on_fail': DEFAULT_PROXY_ROTATE_ON_FAIL,
                                  'proxy_max_retries': DEFAULT_PROXY_MAX_RETRIES, 'safe_mode': DEFAULT_SAFE_MODE,
                                  'max_daily_messages': DEFAULT_MAX_DAILY_MESSAGES,
                                  'max_daily_joins': DEFAULT_MAX_DAILY_JOINS,
                                  'anti_ban_enabled': DEFAULT_ANTI_BAN_ENABLED,
                                  'human_like_delays': DEFAULT_HUMAN_LIKE_DELAYS,
                                  'random_pause_enabled': DEFAULT_RANDOM_PAUSE_ENABLED})
                print(f"{Fore.GREEN}✔ Все настройки сброшены!{Style.RESET_ALL}")
                proxy_manager = ProxyManager(proxy_file)
                await close_notification_client()
        elif choice == '0':
            save_config()
            break
        else:
            print(f"{Fore.RED}✘ Некорректный выбор.{Style.RESET_ALL}")
        await asyncio.sleep(1)


async def add_session_by_number():
    print("\n" + Fore.MAGENTA + "--- Добавление сессии по номеру ---" + Style.RESET_ALL)
    await add_to_log_buffer("--- Добавление сессии по номеру ---", "info")
    if current_api_id == DEFAULT_API_ID or not current_api_hash or current_api_hash == "ЗАМЕНИТЕ НА ВАШ API HASH":
        print(f"\n{Fore.YELLOW}[!] ВНИМАНИЕ: Сначала настройте API ID и API Hash в меню настроек!{Style.RESET_ALL}")
        await add_to_log_buffer("[!] ВНИМАНИЕ: Сначала настройте API ID и API Hash в меню настроек!", "warning")
        print(f"{Fore.CYAN}1. Перейдите в меню '3. Настройки'")
        print("2. Выберите '1. 🔑 API Настройки'")
        print(f"3. Укажите ваши API ID и API Hash{Style.RESET_ALL}")
        input("\nНажмите Enter для продолжения...")
        return
    phone_number = input("1. Введите номер телефона (с кодом страны, например, +79991234567): ").strip()
    if not phone_number:
        print(f"{Fore.RED}✘ Номер телефона не введен.{Style.RESET_ALL}")
        await add_to_log_buffer("✘ Номер телефона не введен", "error")
        return
    if not phone_number.startswith('+'):
        print(f"{Fore.YELLOW}⚠️ Рекомендуется указывать номер в формате +код_страныномер{Style.RESET_ALL}")
        await add_to_log_buffer("⚠️ Рекомендуется указывать номер в формате +код_страныномер", "warning")
        if input("Продолжить? (y/n): ").lower() != 'y':
            return
    session_name = input("2. Введите название для сессии (например, my_session): ").strip()
    if not session_name:
        print(f"{Fore.RED}✘ Название сессии не введено.{Style.RESET_ALL}")
        await add_to_log_buffer("✘ Название сессии не введено", "error")
        return
    session_name = re.sub(r'[^\w\-_]', '', session_name)
    if not session_name:
        session_name = f"session_{int(time.time())}"
        print(f"{Fore.YELLOW}⚠️ Используется автоматическое имя: {session_name}{Style.RESET_ALL}")
        await add_to_log_buffer(f"⚠️ Используется автоматическое имя: {session_name}", "warning")
    session_filename = f"{session_name}.session"
    session_path_base = os.path.join(session_folder, session_name)
    if os.path.exists(session_path_base + ".session"):
        if input(
                f"{Fore.YELLOW}⚠️ Файл сессии '{session_filename}' уже существует. Перезаписать? (y/n): ").lower() != 'y':
            print(f"{Fore.RED}✘ Добавление сессии отменено.{Style.RESET_ALL}")
            await add_to_log_buffer("✘ Добавление сессии отменено", "error")
            return
        else:
            backup_name = f"{session_path_base}_backup_{int(time.time())}.session"
            try:
                shutil.copy2(session_path_base + ".session", backup_name)
                print(f"{Fore.CYAN}✔ Создан бэкап старой сессии: {backup_name}{Style.RESET_ALL}")
                await add_to_log_buffer(f"✔ Создан бэкап старой сессии: {backup_name}", "success")
            except:
                pass
    proxy = proxy_manager.get_best_proxy() if use_proxy and proxy_manager.has_proxies() else None
    device_models = ["PC", "Desktop", "Windows", "MacBook", "iPhone", "Android", "Linux", "Chrome", "Firefox"]
    system_versions = ["Windows 10", "Windows 11", "macOS 13", "Android 13", "iOS 16", "Ubuntu 22.04", "Debian 11"]
    app_versions = [CURRENT_VERSION, "1.6.0", "1.5.2", "1.4.0", "1.3.0"]
    auth_client = TelegramClient(session_path_base, api_id=current_api_id, api_hash=current_api_hash,
                                 connection_retries=5, timeout=30, device_model=random.choice(device_models),
                                 system_version=random.choice(system_versions), app_version=random.choice(app_versions),
                                 proxy=proxy, flood_sleep_threshold=60)
    try:
        print(f"{Fore.CYAN}🔄 Подключение к Telegram...{Style.RESET_ALL}")
        await add_to_log_buffer("🔄 Подключение к Telegram...", "info")
        await auth_client.connect()
        if await auth_client.is_user_authorized():
            print(f"{Fore.GREEN}✔ Сессия '{session_name}' уже активна.{Style.RESET_ALL}")
            await add_to_log_buffer(f"✔ Сессия '{session_name}' уже активна", "success")
            return
        print(f"{Fore.CYAN}📱 Запрос кода подтверждения на номер {phone_number}...{Style.RESET_ALL}")
        await add_to_log_buffer(f"📱 Запрос кода подтверждения на номер {phone_number}...", "info")
        await asyncio.sleep(random.uniform(1, 3))
        try:
            sent_code = await auth_client.send_code_request(phone_number)
            print(f"{Fore.GREEN}✔ Код запроса отправлен!{Style.RESET_ALL}")
            await add_to_log_buffer("✔ Код запроса отправлен!", "success")
            print(f"{Fore.CYAN}⏱️ Код действителен в течение: {sent_code.timeout} секунд{Style.RESET_ALL}")
            await add_to_log_buffer(f"⏱️ Код действителен в течение: {sent_code.timeout} секунд", "info")
            print(f"{Fore.YELLOW}📱 Проверьте Telegram в приложении или по SMS{Style.RESET_ALL}")
            await add_to_log_buffer("📱 Проверьте Telegram в приложении или по SMS", "info")
        except FloodWaitError as e:
            wait_time = e.seconds
            print(f"{Fore.RED}✘ Слишком много попыток! Подождите {wait_time} секунд.{Style.RESET_ALL}")
            await add_to_log_buffer(f"✘ Слишком много попыток! Подождите {wait_time} секунд", "flood")
            print(f"{Fore.YELLOW}⏳ Это примерно {wait_time // 60} минут {wait_time % 60} секунд{Style.RESET_ALL}")
            await add_to_log_buffer(f"⏳ Это примерно {wait_time // 60} минут {wait_time % 60} секунд", "flood")
            if wait_time > 300:
                print(f"{Fore.RED}❌ Слишком долгое ожидание. Рекомендуется сменить IP или прокси.{Style.RESET_ALL}")
                await add_to_log_buffer("❌ Слишком долгое ожидание. Рекомендуется сменить IP или прокси", "error")
                return
            for remaining in range(wait_time, 0, -10):
                if remaining % 60 == 0 or remaining < 60:
                    mins = remaining // 60
                    secs = remaining % 60
                    print(f"{Fore.YELLOW}⏳ Осталось: {mins} мин {secs} сек...{Style.RESET_ALL}")
                await asyncio.sleep(min(10, remaining))
            print(f"{Fore.GREEN}✔ Можно пробовать снова!{Style.RESET_ALL}")
            await add_to_log_buffer("✔ Можно пробовать снова!", "success")
            return
        except Exception as e:
            if "FLOOD_PREMIUM_WAIT" in str(e):
                print(f"{Fore.RED}✘ Превышен лимит запросов для обычного аккаунта.{Style.RESET_ALL}")
                await add_to_log_buffer("✘ Превышен лимит запросов для обычного аккаунта", "error")
                print(
                    f"{Fore.YELLOW}💡 Используйте аккаунт с Telegram Premium или подождите несколько часов.{Style.RESET_ALL}")
                await add_to_log_buffer("💡 Используйте аккаунт с Telegram Premium или подождите несколько часов",
                                        "info")
                return
            raise
        print(f"\n{Fore.CYAN}3. Введите код подтверждения из Telegram{Style.RESET_ALL}")
        await add_to_log_buffer("3. Введите код подтверждения из Telegram", "info")
        print(f"{Fore.YELLOW}📝 Код обычно приходит в виде 5 цифр (например: 12345){Style.RESET_ALL}")
        await add_to_log_buffer("📝 Код обычно приходит в виде 5 цифр (например: 12345)", "info")
        tg_code = input("Код: ").strip()
        if not tg_code:
            print(f"{Fore.RED}✘ Код не введен.{Style.RESET_ALL}")
            await add_to_log_buffer("✘ Код не введен", "error")
            return
        tg_code = re.sub(r'\D', '', tg_code)
        if len(tg_code) != 5:
            print(f"{Fore.YELLOW}⚠️ Код обычно состоит из 5 цифр. Продолжить? (y/n): ", end="")
            await add_to_log_buffer("⚠️ Код обычно состоит из 5 цифр", "warning")
            if input().lower() != 'y':
                return
        print(f"{Fore.CYAN}🔄 Выполняю вход с кодом...{Style.RESET_ALL}")
        await add_to_log_buffer("🔄 Выполняю вход с кодом...", "info")
        await asyncio.sleep(random.uniform(1, 2))
        try:
            await auth_client.sign_in(phone_number, tg_code)
        except SessionPasswordNeededError:
            print(f"\n{Fore.YELLOW}🔐 Требуется двухфакторная аутентификация{Style.RESET_ALL}")
            await add_to_log_buffer("🔐 Требуется двухфакторная аутентификация", "info")
            print(
                f"{Fore.CYAN}💡 Если не помните пароль, используйте функцию сброса в официальном приложении{Style.RESET_ALL}")
            await add_to_log_buffer("💡 Если не помните пароль, используйте функцию сброса в официальном приложении",
                                    "info")
            password = input("Введите ваш пароль 2FA: ").strip()
            if not password:
                print(f"{Fore.RED}✘ Пароль не введен.{Style.RESET_ALL}")
                await add_to_log_buffer("✘ Пароль не введен", "error")
                return
            await asyncio.sleep(random.uniform(1, 2))
            try:
                await auth_client.sign_in(password=password)
            except PasswordHashInvalidError:
                print(f"{Fore.RED}✘ Неверный пароль 2FA{Style.RESET_ALL}")
                await add_to_log_buffer("✘ Неверный пароль 2FA", "error")
                return
        except PhoneCodeInvalidError:
            print(f"{Fore.RED}✘ Неверный код подтверждения{Style.RESET_ALL}")
            await add_to_log_buffer("✘ Неверный код подтверждения", "error")
            print(f"{Fore.YELLOW}💡 Проверьте код и попробуйте снова{Style.RESET_ALL}")
            await add_to_log_buffer("💡 Проверьте код и попробуйте снова", "info")
            return
        except PhoneCodeExpiredError:
            print(f"{Fore.RED}✘ Срок действия кода истек{Style.RESET_ALL}")
            await add_to_log_buffer("✘ Срок действия кода истек", "error")
            print(f"{Fore.YELLOW}💡 Запросите новый код{Style.RESET_ALL}")
            await add_to_log_buffer("💡 Запросите новый код", "info")
            return
        await asyncio.sleep(random.uniform(2, 4))
        try:
            me = await auth_client.get_me()
            print(f"\n{Fore.GREEN}✅ СЕССИЯ УСПЕШНО ДОБАВЛЕНА!{Style.RESET_ALL}")
            await add_to_log_buffer("✅ СЕССИЯ УСПЕШНО ДОБАВЛЕНА!", "success")
            print(f"{Fore.CYAN}📱 Информация об аккаунте:{Style.RESET_ALL}")
            await add_to_log_buffer("📱 Информация об аккаунте:", "info")
            print(f"   ID: {me.id}")
            await add_to_log_buffer(f"   ID: {me.id}", "info")
            print(f"   Имя: {me.first_name} {me.last_name or ''}")
            await add_to_log_buffer(f"   Имя: {me.first_name} {me.last_name or ''}", "info")
            print(f"   Юзернейм: @{me.username or 'отсутствует'}")
            await add_to_log_buffer(f"   Юзернейм: @{me.username or 'отсутствует'}", "info")
            print(f"   Номер: {me.phone}")
            await add_to_log_buffer(f"   Номер: {me.phone}", "info")
            print(f"\n{Fore.GREEN}✔ Файл сессии сохранен: {session_path_base}.session{Style.RESET_ALL}")
            await add_to_log_buffer(f"✔ Файл сессии сохранен: {session_path_base}.session", "success")
            account_protector.register_account(session_name, 0)
            await auth_client.disconnect()
            await asyncio.sleep(2)
            print(f"\n{Fore.YELLOW}⚠️ ВАЖНО: Чтобы избежать заморозки:{Style.RESET_ALL}")
            await add_to_log_buffer("⚠️ ВАЖНО: Чтобы избежать заморозки:", "warning")
            print("  • Не используйте аккаунт сразу для массовых действий")
            await add_to_log_buffer("  • Не используйте аккаунт сразу для массовых действий", "info")
            print("  • Подождите 10-15 минут перед первым использованием")
            await add_to_log_buffer("  • Подождите 10-15 минут перед первым использованием", "info")
            print("  • Зайдите в официальное приложение и подтвердите устройство")
            await add_to_log_buffer("  • Зайдите в официальное приложение и подтвердите устройство", "info")
            print("  • Добавьте 2FA для дополнительной защиты")
            await add_to_log_buffer("  • Добавьте 2FA для дополнительной защиты", "info")
            save_config()
        except Exception as e:
            print(f"{Fore.RED}✘ Ошибка при получении информации: {e}{Style.RESET_ALL}")
            await add_to_log_buffer(f"✘ Ошибка при получении информации: {e}", "error")
    except PhoneNumberInvalidError:
        print(f"{Fore.RED}✘ Неверный формат номера телефона{Style.RESET_ALL}")
        await add_to_log_buffer("✘ Неверный формат номера телефона", "error")
        print(f"{Fore.YELLOW}💡 Используйте формат: +код_страныномер (например, +79991234567){Style.RESET_ALL}")
        await add_to_log_buffer("💡 Используйте формат: +код_страныномер (например, +79991234567)", "info")
    except Exception as e:
        error_str = str(e)
        if "FLOOD" in error_str.upper():
            print(f"{Fore.RED}✘ Флуд-контроль от Telegram!{Style.RESET_ALL}")
            await add_to_log_buffer("✘ Флуд-контроль от Telegram!", "flood")
            print(f"{Fore.YELLOW}💡 Подождите несколько часов или используйте другой IP/прокси{Style.RESET_ALL}")
            await add_to_log_buffer("💡 Подождите несколько часов или используйте другой IP/прокси", "info")
        elif "PHONE_NUMBER_INVALID" in error_str.upper():
            print(f"{Fore.RED}✘ Неверный формат номера{Style.RESET_ALL}")
            await add_to_log_buffer("✘ Неверный формат номера", "error")
        elif "PHONE_CODE_INVALID" in error_str.upper():
            print(f"{Fore.RED}✘ Неверный код{Style.RESET_ALL}")
            await add_to_log_buffer("✘ Неверный код", "error")
        else:
            print(f"{Fore.RED}✘ Непредвиденная ошибка: {e}{Style.RESET_ALL}")
            await add_to_log_buffer(f"✘ Непредвиденная ошибка: {e}", "error")
            print(f"{Fore.YELLOW}📋 Детали ошибки:{Style.RESET_ALL}")
            traceback.print_exc()
    finally:
        if auth_client.is_connected():
            await auth_client.disconnect()
            print(f"{Fore.CYAN}🔌 Соединение закрыто{Style.RESET_ALL}")
            await add_to_log_buffer("🔌 Соединение закрыто", "info")


async def display_update_info():
    """Отображает информацию о том как обновить софт"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print_header("📢 ИНФОРМАЦИЯ ОБ ОБНОВЛЕНИЯХ")

    print(f"{CLR_INFO}📌 Актуальная информация об обновлениях:{Style.RESET_ALL}")
    print(f"{CLR_ACCENT}🔗 https://t.me/LiteGammaTools{Style.RESET_ALL}\n")

    print(f"{CLR_MAIN}⚙️ КАК ОБНОВИТЬ СОФТ ДО ПОСЛЕДНЕЙ ВЕРСИИ:{Style.RESET_ALL}\n")

    print(f"{CLR_SUCCESS}1️⃣ ЗАКРОЙТЕ ПРОГРАММУ{Style.RESET_ALL}")
    print(f"   • Убедитесь, что софт полностью закрыт\n")

    print(f"{CLR_SUCCESS}2️⃣ ОТКРОЙТЕ КОРНЕВУЮ ПАПКУ{Style.RESET_ALL}")
    print(f"   • Найдите папку, где установлен софт\n")

    print(f"{CLR_SUCCESS}3️⃣ ОТРЕДАКТИРУЙТЕ КОНФИГ{Style.RESET_ALL}")
    print(f"   • Откройте файл {CLR_WARN}config.json{Style.RESET_ALL} любым текстовым редактором")
    print(f"   • Найдите строку: {CLR_WARN}\"current_version\": \"{CURRENT_VERSION}\"{Style.RESET_ALL}")
    print(f"   • {CLR_ERR}УДАЛИТЕ{Style.RESET_ALL} эту строку полностью или измените версию на более старую")
    print(f"   • Пример после удаления: {CLR_WARN}\"current_version\": \"1.0.0\"{Style.RESET_ALL}")
    print(f"   • {CLR_SUCCESS}СОХРАНИТЕ{Style.RESET_ALL} файл\n")

    print(f"{CLR_SUCCESS}4️⃣ УДАЛИТЕ ФАЙЛ ПРОВЕРКИ{Style.RESET_ALL}")
    print(f"   • Удалите файл {CLR_WARN}last_update_check.json{Style.RESET_ALL} (если есть)\n")

    print(f"{CLR_SUCCESS}5️⃣ ЗАПУСТИТЕ СОФТ{Style.RESET_ALL}")
    print(f"   • Запустите программу заново\n")

    print(f"{CLR_SUCCESS}6️⃣ ЗАЙДИТЕ В МЕНЮ ОБНОВЛЕНИЙ{Style.RESET_ALL}")
    print(f"   • В главном меню выберите пункт {CLR_WARN}[6] ➔ 🔄 ОБНОВЛЕНИЯ{Style.RESET_ALL}")
    print(f"   • Нажмите {CLR_WARN}[1] ➔ 🔍 Проверить обновления{Style.RESET_ALL}")
    print(f"   • Если обновление найдено, нажмите {CLR_WARN}[2] ➔ ⬇️ Скачать и установить{Style.RESET_ALL}")
    print(f"   • После установки программа предложит перезапуститься\n")

    print(f"{CLR_WARN}⚠️ ВАЖНО:{Style.RESET_ALL}")
    print(f"   • Все настройки и сессии сохранятся")
    print(f"   • Создаётся автоматический бэкап текущей версии в папке {CLR_WARN}backups{Style.RESET_ALL}")
    print(f"   • При проблемах можно восстановиться из бэкапа\n")

    print(f"{CLR_ACCENT}📢 Подпишитесь на канал обновлений:{Style.RESET_ALL}")
    print(f"{CLR_MAIN}👉 https://t.me/LiteGammaTools{Style.RESET_ALL}\n")

    input(f"{CLR_INFO}Нажмите Enter для возврата в меню...{Style.RESET_ALL}")

async def main_menu():
    global CURRENT_VERSION
    global auto_subscribe_enabled, auto_subscribe_on_mention, auto_subscribe_delay
    global auto_subscribe_max_flood_wait, auto_subscribe_retry_after_flood
    global auto_subscribe_check_interval, auto_subscribe_wait_for_mention
    global auto_subscribe_pause_between_channels, auto_subscribe_forced_channels, auto_subscribe_first_cycle_only
    global flood_wait_occurred, total_flood_time
    load_config()
    os.makedirs(session_folder, exist_ok=True)
    clear_failed_subscriptions_file()
    file_version = update_manager.verify_version_in_file()
    if file_version and file_version != CURRENT_VERSION:
        print(f"{Fore.YELLOW}⚠️ Обновляю версию в памяти: {CURRENT_VERSION} -> {file_version}{Style.RESET_ALL}")
        await add_to_log_buffer(f"⚠️ Обновляю версию в памяти: {CURRENT_VERSION} -> {file_version}", "warning")
        CURRENT_VERSION = file_version
        save_config()
    if AUTO_UPDATE:
        asyncio.create_task(update_manager.check_for_updates())
    if notification_enabled:
        await init_notification_client()
    if os.path.exists(invalid_session_log_file):
        try:
            os.remove(invalid_session_log_file)
            print(f"{Fore.GREEN}✔ Файл '{invalid_session_log_file}' был очищен.{Style.RESET_ALL}")
            await add_to_log_buffer(f"✔ Файл '{invalid_session_log_file}' был очищен", "success")
        except Exception as e:
            print(f"{Fore.RED}✘ Не удалось очистить файл '{invalid_session_log_file}': {e}{Style.RESET_ALL}")
            await add_to_log_buffer(f"✘ Не удалось очистить файл '{invalid_session_log_file}': {e}", "error")

    # Генерируем HTML файл и запускаем сервер
    log_manager.generate_html_file()
    log_manager.start_server()

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{CLR_ACCENT}╔════════════════════════════════════════════╗")
        print(f"{CLR_ACCENT}║{CLR_MAIN}     🚀 LITEGAMMA TOOLS❤️  |  FULL VERSION  {CLR_ACCENT}║")
        print(f"{CLR_ACCENT}║{CLR_INFO}       С уважением : @BananaStorebot_bot    {CLR_ACCENT}║")
        print(f"{CLR_ACCENT}╚════════════════════════════════════════════╝")
        print(f"\n{CLR_SUCCESS}  [1] ➔  🚀 ЗАПУСТИТЬ РАССЫЛКУ")
        print(f"{CLR_SUCCESS}  [2] ➔  🔗 ВСТУПИТЬ В ГРУППЫ (из enter.json)")
        print(f"{CLR_MAIN}  [3] ➔  ⚙️  НАСТРОЙКИ СИСТЕМЫ")
        print(f"{CLR_INFO}  [4] ➔  📂  МОИ СЕССИИ (ИНФО)")
        print(f"{CLR_ACCENT}  [5] ➔  ➕  ДОБАВИТЬ АККАУНТ")
        print(f"{CLR_ACCENT}  [6] ➔  🔄  ОБНОВЛЕНИЯ")
        print(f"{CLR_INFO}  [7] ➔  📢 ИНФОРМАЦИЯ ОБ ОБНОВЛЕНИЯХ")
        print(f"{CLR_ERR}  [8] ➔  🚪  ВЫЙТИ")
        print(f"\n{CLR_ACCENT}────────────────────────────────────────────")
        if fast_mode:
            print(f"{Fore.YELLOW}⚡ ТЕКУЩИЙ РЕЖИМ: БЫСТРЫЙ (задержка {fast_delay}с){Style.RESET_ALL}")
        if repeat_broadcast:
            print(f"{Fore.CYAN}🔄 ПОВТОР ВКЛЮЧЕН (интервал {repeat_interval}с){Style.RESET_ALL}")
        if notification_enabled:
            print(f"{Fore.GREEN}🔔 УВЕДОМЛЕНИЯ ВКЛЮЧЕНЫ{Style.RESET_ALL}")
        if auto_subscribe_enabled:
            mode = "ТОЛЬКО 1-Й ЦИКЛ" if auto_subscribe_first_cycle_only else "КАЖДЫЙ ЦИКЛ"
            print(f"{Fore.MAGENTA}🤖 АВТОПОДПИСКА ВКЛЮЧЕНА ({mode}){Style.RESET_ALL}")
        if use_proxy and proxy_manager.has_proxies():
            print(f"{Fore.CYAN}🌐 ПРОКСИ ВКЛЮЧЕНЫ ({proxy_manager.get_proxy_count()} шт.){Style.RESET_ALL}")
        if anti_ban_enabled:
            print(f"{Fore.GREEN}🛡️ АНТИ-БАН ВКЛЮЧЕН{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📦 Версия: {CURRENT_VERSION}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📊 Веб-интерфейс: http://localhost:{log_manager.port}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📢 Канал обновлений: @LiteGammaTools{Style.RESET_ALL}")
        choice = input(f"{CLR_MAIN}Введите номер команды ➔ {RESET}").strip()
        if choice == '1':
            if current_api_id == DEFAULT_API_ID or not current_api_hash or current_api_hash == "ЗАМЕНИТЕ НА ВАШ API HASH":
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
            if use_proxy and proxy_manager.has_proxies():
                print(f"{Fore.CYAN}🌐 Прокси: ВКЛЮЧЕНЫ{Style.RESET_ALL}")
            if anti_ban_enabled:
                print(f"{Fore.GREEN}🛡️ Анти-бан защита: ВКЛЮЧЕНА{Style.RESET_ALL}")
            if input("\n🚀 Запустить рассылку параллельно? (y/n): ").lower() == 'y':
                print("\n" + Fore.MAGENTA + "🚀 Запуск рассылки..." + Style.RESET_ALL)
                await run_broadcast(current_api_id, current_api_hash, selected_sessions, message_to_send,
                                    max_messages_per_account, repeat_broadcast, repeat_interval, delete_after_send,
                                    use_media, media_path, recipient_type, fast_mode, fast_delay,
                                    target_chats_ids=target_groups_file_data, cycle_number=1)
                input("Нажмите Enter для продолжения...")
        elif choice == '2':
            if current_api_id == DEFAULT_API_ID or not current_api_hash or current_api_hash == "ЗАМЕНИТЕ НА ВАШ API HASH":
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
            if use_proxy and proxy_manager.has_proxies():
                print(f"{Fore.CYAN}🌐 Прокси: ВКЛЮЧЕНЫ{Style.RESET_ALL}")
            if anti_ban_enabled:
                print(f"{Fore.GREEN}🛡️ Анти-бан защита: ВКЛЮЧЕНА{Style.RESET_ALL}")
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
            await display_update_info()
        elif choice == '8':
            save_config()
            await close_notification_client()
            log_manager.stop_server()
            print(f"{Fore.CYAN}🚪 До свидания!{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}✘ Выберите 1-8{Style.RESET_ALL}")
            await asyncio.sleep(1)


def signal_handler(sig, frame):
    print("\n" + Fore.YELLOW + "🛑 Остановлено..." + Style.RESET_ALL)
    stop_event.set()
    log_manager.stop_server()


signal.signal(signal.SIGINT, signal_handler)

if __name__ == '__main__':
    try:
        asyncio.run(main_menu())
    except KeyboardInterrupt:
        print("\n" + Fore.CYAN + "🚪 Выход (KeyboardInterrupt)" + Style.RESET_ALL)
        log_manager.stop_server()
    except Exception as e:
        print(f"\n{Fore.RED}✘ Ошибка: {e}{Style.RESET_ALL}")
        traceback.print_exc()
        log_manager.stop_server()





