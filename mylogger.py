#!/usr/bin/python3

import colorama
from colorama import Fore, Style

colorama.init(strip=False)

LOG_DEBUG = 0
LOG_INFO = 1
LOG_WARN = 2
LOG_ERR = 3
LogLevel = LOG_WARN     # default log level


def setloglevel(level):
    global LogLevel
    LogLevel = level

def debug(msg):
    global LogLevel
    if LogLevel <= LOG_DEBUG:
        print(Fore.GREEN + "[DBUG] " + msg + Style.RESET_ALL)

def info(msg):
    global LogLevel
    if LogLevel <= LOG_INFO:
        print(Fore.CYAN + "[INFO] " + msg + Style.RESET_ALL)

def warn(msg):
    global LogLevel
    if LogLevel <= LOG_WARN:
        print(Fore.YELLOW + "[WARN] " + msg + Style.RESET_ALL)

def err(msg):
    global LogLevel
    if LogLevel <= LOG_ERR:
        print(Fore.RED + "[ERR]  " + msg + Style.RESET_ALL)

