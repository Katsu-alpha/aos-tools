#
#   show datapath message-queue counters をパースし、差分を表示
#

import sys
import re
import argparse
import mylogger as log
from collections import defaultdict
import fileinput
from colorama import Fore, Style

Color = True

if Color:
   GREEN = Fore.GREEN
   CYAN = Fore.CYAN
   RED = Fore.RED
   MAGENTA = Fore.MAGENTA
   BLUE = Fore.BLUE
   YELLOW = Fore.YELLOW
   RESET = Style.RESET_ALL
else:
    GREEN = ""
    CYAN = ""
    RED = ""
    MAGENTA = ""
    BLUE = ""
    YELLOW = ""
    RESET = ""


re_prompt = r'[\)\]] \*?#'

# key: [command][parameter]
ctr = defaultdict(lambda: defaultdict(lambda: 0))

#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Parse show datapath message-queue counters")
    parser.add_argument('infile', help="Input file(s)", type=str, nargs='+')
    parser.add_argument('--full', help='Full output', action='store_true')
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)


    f = fileinput.input(args.infile, encoding='utf-8')
    out = []
    cmd = ""
    lines = 0

    for l in f:
        l = l.rstrip()
        if lines > 0:
            print(l)
            lines -= 1
            continue

        r = re.search(re_prompt + r'(show .*)', l)
        if r:
            cmd = r.group(1)
            if "show clock" in cmd:
                print(l)
                cmd = ""
                lines = 2
                continue

            if "radio-stats" in cmd or "client-stats" in cmd:
                print("\n" + CYAN + l + RESET)
                continue
            else:
                cmd = ""
                continue

        if cmd == "":
            continue

        # radio-stats counters
        r = re.match(r'(.+)  +([0-9]+)$', l)
        if r:
            param = r.group(1)
            val = int(r.group(2))
            if ctr[cmd][param] == 0:
                diff = ""
            else:
                diff = f"{val - ctr[cmd][param]:+}"
            ctr[cmd][param] = val
            # if diff != 0:
            print(l + " " * (50 - len(l)) + f'{diff:>12}')
            continue

        if args.full:
            print(l)
