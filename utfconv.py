#
#   Shift-JIS ファイルを UTF-8 に変換
#   CRLF -> LF
#

import argparse

from chardet.universaldetector import UniversalDetector

parser = argparse.ArgumentParser(
    description=f"Convert files to UTF-8 encoding.")
parser.add_argument('infile', help="Input files(s)", type=str, nargs='+')
# parser.add_argument('outfile', help='Output Excel file', type=str, nargs='?', default='')
parser.add_argument('--debug', help='Enable debug log', action='store_true')
args = parser.parse_args()


detector = UniversalDetector()
for fn in args.infile:
    detector.reset()
    for line in open(fn, 'rb'):
        detector.feed(line)
        if detector.done: break
    detector.close()
    print(f"{fn} - ", detector.result)

    enc = detector.result['encoding']
    if enc == 'ascii' or enc == 'utf-8':
        continue

    print("Converting to UTF-8...", end="")
    with open(fn, encoding=enc) as f:
        Ses = f.read()

    Ses = Ses.replace('\r', '')
    with open(fn, 'w', encoding='utf-8') as f:
        f.write(Ses)
    print("Done.")
