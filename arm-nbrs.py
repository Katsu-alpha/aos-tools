#
#   arm-nbrs.py
#
#   show ap tech 内の show ap monitor / show ap arm neighbors をパースし、色分けして表示
#   show ap bss-table が含まれたファイルが指定されれば、AP名を表示
#
#       青色      weak AP (SNR < 10)
#       黄色      Co-channel AP (Aruba, 同一Ch, SNR >= 10)
#       紫        interfering AP (他Ch)
#       赤        interfering AP (Co-Ch)
#       白        Coverage AP (Co-ch AP ではなく、SNR >= 25 の Aruba AP)
#       水色      weak Coverage AP (Co-ch AP ではなく、SNR < 25 の Aruba AP)
#

import sys
import re
import argparse
import fileinput
import mylogger as log
from aos_parser import AOSParser, AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE
from colorama import Fore, Style
from collections import defaultdict

Suppress_VAPs = True
Print_APList = True
Print_ARMNbr = True
Sort = True
Only5G = True
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

apn2ch = {}
#exclude_ssids = ['ELITE-Corp', 'KLSPOT', 'Visitor-Guest']
exclude_ssids = []
bss2apn = defaultdict(lambda: "")
bssresolve = False

def parse_bss_tbl(out):
    global bss2apn, bssresolve
    cmd = "show ap bss-table"
    aos = AOSParser("".join(out), [cmd])
    tbl = aos.get_table(cmd)
    if tbl == None:
        print(f"No bss-table found.")
        return
    for r in tbl[1:]:
        bss2apn[r[0]] = r[8]

    bssresolve = True

def parse_ap_mon(out, apn):
    global apn2ch, bss2apn, bssresolve
    cmd = "show ap monitor ap-list .*"
    aos = AOSParser("".join(out), [cmd])
    tbl = aos.get_table(cmd)
    if tbl == None:
        print(f"No ap-list found for {apn}")
        return
    mych = ""
    tbl2 = []
    bss_set = set()
    for r in tbl[1:]:
        # print(r)
        bss = r[0]
        type = r[3]
        if Suppress_VAPs and type == 'valid' and bss[:16] in bss_set:
            continue
        bss_set.add(bss[:16])
        ess = r[1]
        radio = r[2]
        snr = int(r[10])

        if Only5G:
            m = re.match(r'5GHz/(\d+)', radio)
        else:
            m = re.search(r'GHz/(\d+)', radio)
        if m:
            ch = m.group(1)
        else:
            continue
        if bss.endswith('(+)'):
            mych = ch
            apn2ch[apn] = mych
        tbl2.append([bss, ess, radio, ch, type, snr])

    if not Print_APList:
        return

    # print(f'Found Monitor AP List for AP "{apn}" Ch={mych}')
    print(out[0])
    print("BSSID                 ESSID                         Radio                  Type                SNR")
    print("-----                 -----                         -----                  ----                ---")
    apnres = ""
    if Sort:
        tbl2 = sorted(tbl2, key=lambda x: x[5], reverse=True)
    for r in tbl2:
        #if r[3] != mych: continue
        if r[1] in exclude_ssids: continue
        col = False
        if r[0].endswith('(+)'):
            col = True
            print(GREEN, end="")
        elif r[5] < 10:
            print(BLUE, end="")
            col = True
        elif r[3] == mych:
            print(YELLOW, end="")
            col = True
        elif r[5] < 25:
            print(CYAN, end="")
            col = True
        if bssresolve:
            apnres = bss2apn[r[0][:17]]
        print(f"{r[0]:22}{r[1]:30}{r[2]:23}{r[4]:20}{r[5]:>3}  {apnres}")
        if col:
            print(RESET, end="")


def parse_arm_nbr(out, apn):
    global apn2ch, bss2apn, bssresolve
    cmd = "show ap arm neighbors"
    aos = AOSParser("".join(out), [cmd])
    tbl = aos.get_table(cmd)
    print(f"TBL: {tbl}")
    mych = apn2ch[apn]
    tbl2 = []
    bss_set = set()
    nintf = 0
    cov = 0
    apnres = ""
    for r in tbl[1:]:
        if r[2] != '5GHz': continue
        if r[7] == 'Indirect': continue
        bss = r[0]
        if Suppress_VAPs and bss[:16] in bss_set:
            continue
        bss_set.add(bss[:16])
        ess = r[1]
        ch = r[3]
        m = re.match(r'(\d+)', ch)
        if m:
            pch = m.group(1)
        else:
            pch = 0
        snr = int(r[4])
        eirp = r[5]
        pl = r[6]
        flg = r[7]
        tbl2.append([bss, ess, ch, snr, eirp, pl, flg, pch])

    if Print_ARMNbr:
        print(f'\nFound ARM Neighbor for AP "{apn}" Ch={mych}')
        print("BSSID               ESSID                         Ch   SNR  EIRP  PL (dB)  AP Flags")
        print("-----               -----                         --   ---  ----  -------  --------")
    if Sort:
        tbl2 = sorted(tbl2, key=lambda x:x[3], reverse=True)
    for r in tbl2:
        #if r[2] != mych: continue
        if r[1] in exclude_ssids: continue
        col = False
        if r[3] < 10:
            print(BLUE, end="")        # SNR <10
            col = True
        elif r[7] == mych and r[4]=='0':
            print(RED, end="")         # interfering AP
            col = True
        elif r[7] == mych:
            print(YELLOW, end="")      # co-channel AP
            nintf += 1
            if r[3] >= 25:
                cov += 1
            col = True
        elif r[4]=='0':
            print(MAGENTA, end="")     # interfering AP (not co-channel)
            col = True
        elif r[3] < 25:
            print(CYAN, end="")        # weak coverage
            col = True
        else:
            cov += 1
        if Print_ARMNbr:
            if bssresolve:
                apnres = bss2apn[r[0][:17]]
            print(f"{r[0]:20}{r[1]:30}{r[2]:5}{r[3]:>3} {r[4]:>5}   {r[5]:>5}   {r[6]:8}  {apnres}")
        if col:
            print(RESET, end="")
    if Print_ARMNbr:
        print("\n==================================================================================\n")
    # else:
    #     print(f"{apn},{mych},{nintf},{cov}")

#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Parse show ap tech and display neighbor APs")
    parser.add_argument('infile', help="Input file(s)", type=str, nargs='+')
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)

    #
    #   search below cmds
    #   show ap arm neighbors ap-name <apn>
    #

    f = fileinput.input(args.infile, encoding='utf-8')
    out = []
    cont = 0
    for l in f:
        if cont != 0 and (l.startswith('show ') or l.startswith('Neighbor Summary')):
            if cont == 1:
                #print(f"** found ap-list at LINE {fileinput.lineno()}")
                print(f"\n\nFile: {fileinput.filename()}")
                parse_ap_mon(out, apn)
                cont = 0
            elif cont == 2:
                parse_arm_nbr(out, apn)
                cont = 0
            elif cont == 3:
                parse_bss_tbl(out)
                cont = 0
        elif cont != 0:
            out.append(l)
            continue

        # cont == 0
        if not (l.startswith('show ') or l.startswith('COMMAND')): continue

        r = re.search(r'show ap monitor ap-list +ap-name "([\w-]+)"', l)
        if r:
            apn = r.group(1)
            cont = 1
            out = [l]
            continue

        r = re.search(r'show ap arm neighbors +ap-name "([\w-]+)"', l)
        if r:
            apn = r.group(1)
            cont = 2
            out = [l]
            continue

        r = re.search(r'show ap bss-table[\r\n ]*$', l)
        if r:
            cont = 3
            out = [l]
            continue

        # for IAP
        r = re.search(r'show ap arm neighbors', l)
        if r:
            apn = "APGTS3424A"
            apn2ch[apn] = '36+'
            cont = 2
            out = [l]
            continue


        continue


