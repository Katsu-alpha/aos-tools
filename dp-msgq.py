#
#   show datapath message-queue counters をパースし、差分を表示
#

import sys
import re
import argparse
import mylogger as log
from collections import defaultdict
import fileinput


ctr = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0)))
ctr2 = defaultdict(lambda: defaultdict(lambda: 0))
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
    cont = 0
    for l in f:
        l = l.rstrip()
        r = re.match(r'Cpu--> +(\d+)', l)
        if r:
            cpu = r.group(1)
            print(l)
            continue

        # datapath message-queue counters
        r = re.match(r'([\w/]+) +[0-9a-f]{8}', l)
        if r:
            print(l)
            opcode = r.group(1)
            diff = {}
            for m in re.finditer(r' [0-9a-f]{8}', l):
                pos = m.start(0) + 1
                val = int(m.group(0), 16)
                diff[pos] = val - ctr[cpu][opcode][pos]
                ctr[cpu][opcode][pos] = val

            Ses = ''
            for pos, val in diff.items():
                Ses += ' ' * (pos - len(Ses))
                Ses += f'{val:>+8}'
            print(Ses)
            continue

        # datapath papi counters
        r = re.match(r'\| (\d\d|G |  ) \| \[\d\d\d\] \| ([\w,\. -]+?) +(\d+) \|', l)
        if r:
            cpu = r.group(1)
            desc = r.group(2)
            val = int(r.group(3))
            diff = val - ctr2[cpu][desc]
            ctr2[cpu][desc] = val
            print(f'{l} {diff:+}')
            continue


        if args.full:
            print(l)
