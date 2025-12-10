#
#   show ap debug radio-stats/client-stats をパースし、差分を表示
#
#   History:
#       2025/11/16  Supported multi-column output (show ap debug radius-statistics)
#

import sys
import re
import argparse
import subprocess

from win32gui import ResetDC

import mylogger as log
from collections import defaultdict
import fileinput
from colorama import Fore, Style

Color = True

if Color:
    GREEN = Fore.GREEN
    CYAN = Fore.CYAN
    RED = Fore.RED
    BRIGHTRED = Style.BRIGHT + Fore.RED
    BRIGHTWHITE = Style.BRIGHT + Fore.WHITE
    MAGENTA = Fore.MAGENTA
    BLUE = Fore.BLUE
    YELLOW = Fore.YELLOW
    GRAY = Fore.LIGHTBLACK_EX
    RESET = Style.RESET_ALL
else:
    GREEN = ""
    CYAN = ""
    RED = ""
    BRIGHTRED = ""
    BRIGHTWHITE = ""
    MAGENTA = ""
    BLUE = ""
    YELLOW = ""
    GRAY = ""
    RESET = ""


re_prompt = r'[\)\]] \*?#|Command: |COMMAND='

# Stats counter
# key: [command][parameter]
ctr = defaultdict(lambda: defaultdict(lambda: 0))

# Multi-column stats counter
# key: [command][parameter][idx]
mcol_ctr = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0)))


def replace_str(s, pos, newstr):
    """Replace part of string s at pos with newstr"""
    if pos > len(s):
        return s + " " * (pos - len(s)) + newstr

    return s[:pos] + newstr + s[pos+len(newstr):]



#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Parse show datapath message-queue counters")
    parser.add_argument('infile', help="Input file(s)", type=str, nargs='+')
    parser.add_argument('--full', '-f', help='Full output', action='store_true')
    parser.add_argument('--num', '-n', help='Display line number', action='store_true')
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)


    f = fileinput.input(args.infile, encoding='utf-8')
    out = []
    cmd = ""
    lno = ""
    skip_lines = 0

    try:
        with subprocess.Popen(['less', '-RM'], stdin=subprocess.PIPE, encoding='utf-8') as process:
            sys.stdout.flush()
            sys.stdout = process.stdin
            for l in f:
                l = l.rstrip()
                if skip_lines > 0:
                    print(l)
                    skip_lines -= 1
                    continue

                if l.startswith('Output Time:'):
                    print(l)
                    continue


                r = re.search(re_prompt, l)
                if r:
                    # after match
                    cmd = l[r.end():].strip()
                    if "show clock" in cmd:
                        print(l)
                        cmd = ""
                        skip_lines = 2
                        continue

                    if "radio-stats" in cmd or "client-stats" in cmd or "radius-statistics" in cmd or "pmk-sync-statistics" in cmd:
                        print("\n" + CYAN + l + RESET)
                        continue
                    else:
                        cmd = ""        # non-supported command, do NOT parse
                        continue

                if cmd == "":
                    continue

                if args.num:
                    lno = f"{GRAY}{fileinput.lineno():>5}{RESET} "

                # multi-column counters (show ap debug radius-statistics)
                if cmd == "show ap debug radius-statistics":
                    r = re.match(r'([\w()/ -]+?)( +\d+){2,}$', l)
                    if r:
                        #print(f"DBUG: match {r.group(0)}")
                        param = r.group(1)
                        plen = len(param)
                        for idx, m in enumerate(re.finditer(r'([0-9]+)', l[plen:])):
                            pos = m.end() + plen
                            val = int(m.group(0))
                            if mcol_ctr[cmd][param][idx] == 0:
                                diff = ""
                            else:
                                diff = f"{val - mcol_ctr[cmd][param][idx]:+}"
                            mcol_ctr[cmd][param][idx] = val
                            if len(diff) > 0:
                                l = replace_str(l, pos+1, diff)
                        print(lno + l)
                        continue

                else:
                    # radio-stats counters
                    r = re.match(r'(.+)  +([0-9]+)$', l)
                    if r:
                        param = r.group(1)
                        val = int(r.group(2))
                        if ctr[cmd][param] == 0:
                            diff = 0
                            sdiff = ""
                        else:
                            diff = val - ctr[cmd][param]
                            sdiff = f"{diff:+}"
                        ctr[cmd][param] = val
                        e1 = e2 = ''
                        if diff > 0 and re.search(r'error|fail|drop|reject|timeout', param, re.IGNORECASE):
                            e1 = BRIGHTRED
                            e2 = RESET
                        print(lno + e1 + l + " " * (50 - len(l)) + f'{sdiff:>12}' + e2)
                        continue
                    else:
                        print(lno + l)
                        continue



                if args.full:
                    print(lno + l)


    except (BrokenPipeError, OSError):
        pass

    sys.exit(0)
