#   Parse show commands and store the contents to 2-dimension lists
#       show ap database long
#       show ap bss-table
#       show ap active
#       show ap association
#       show user-table
#       show datapath session verbose
#       show datapath session dpi
#       show datapath bridge
#

import re
import glob
import fileinput
import sys
import argparse
from colorama import Fore, Style
import mylogger as log

AP_DATABASE_TABLE = "show ap database"
AP_DATABASE_LONG_TABLE = "show ap database long"
AP_BSS_TABLE = "show ap bss-table"
AP_ACTIVE_TABLE = "show ap active"
AP_ASSOCIATION_TABLE = "show ap association"
USER_TABLE = "show user-table"
DATAPATH_SESSION_TABLE = "show datapath session verbose"
DATAPATH_SESSION_DPI = "show datapath session dpi"
DATAPATH_USER = "show datapath user table"

def _get_cols_gen(tbl, *cols):
    idx = [tbl[0].index(col) for col in cols]
    if len(cols) == 1:
        for row in tbl[1:]:
            yield(row[idx[0]])
    else:
        for row in tbl[1:]:
            yield(list(row[i] for i in idx))

class AOSParser:
    """
    show コマンドパーサ
    """

    def file_line(self):
        if self.fromfile:
            return(f"{fileinput.filename()}:{fileinput.filelineno()}: ")
        else:
            return(f"{self.lno}: ")

    def print_log_finfo(self, msg):
        return (Fore.CYAN + self.file_line() + Style.RESET_ALL + msg)

    def end_of_cmd(self):
        '''
        1つのコマンドをパース完了した場合に呼ばれる。
        cur_table を辞書の配列 tables に追加するか、merge=True の場合はマージする
        :return:
        '''
        log.debug(str(self.num) + " entries found.")
        if self.num == 0:
            return
        self.num = 0
        if not self.isMerge:
            self.tables[self.cur_cmd].append(self.cur_table)    # 表の配列に追加
            return

        if len(self.tables[self.cur_cmd]) == 0:
            self.tables[self.cur_cmd].append(self.cur_table)
            return

        log.debug(f"Merging table of '{self.cur_cmd}'...")
        tbl = self.tables[self.cur_cmd][0]     # マージ先2次元配列
        if len(tbl[0]) != len(self.cur_table[0]):
            log.err(f"Can't merge the output for '{self.cur_cmd}'. Num of columns does not match: {len(self.cur_table[0])} vs {len(tbl[0])}.")
            return

        tbl.extend(self.cur_table[1:])
        log.debug(f"Merge success. Total entries: {len(tbl)-1}")
        return

    def __init__(self, files, cmds=(AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE), activeonly=True, merge=False, encoding='utf-8'):
        """
        tech-support または show コマンドログファイルをパースし、以下の table の内容を
        2 次元配列に格納
            show ap database long
            show ap active
        :param files: ファイル名 or ファイル名のリスト or コマンド出力を含む文字列
        :param cmds: パース対象コマンド
        :param activeonly: show ap database では、ステータスが Up のもののみ格納
        :param merge: コマンドが複数回出現する場合、結合する
        """

        self.isMerge = merge
        self.tables = {}        # 各コマンドのパース結果を格納するdict. キー=コマンド名, val=パース結果の配列
        if type(cmds) == str:
            cmds = [cmds]
        for cmd in cmds:
            self.tables[cmd] = []

        in_cmd  = False
        in_cont = False

        self.fromfile = True
        if type(files) == str:
            if '\n' in files:   # files = ファイル名ではなく、パースする入力データとみなす
                data = files.splitlines()
                self.fromfile = False
            elif '*' in files:
                files = glob.glob(files)

        if self.fromfile:
            data = fileinput.input(files, encoding=encoding)

        self.lno = 0
        for line in data:
            line = line.rstrip()
            self.lno += 1

            if not in_cmd and "show " not in line:
                continue            # optimize parse speed a bit

            if not in_cont and in_cmd and "show " in line:
                in_cmd = False
                self.end_of_cmd()
                # fall through

            if not in_cmd:
                for cmd in cmds:
                    pat = cmd + "$"
                    if re.search(pat, line):
                        log.debug(self.file_line() + "Parsing " + cmd)
                        in_cmd = True
                        self.cur_cmd = cmd
                        self.cur_table = []
                        self.num = 0
                        continue

                continue

            if in_cont:     # inside a table content
                #
                #   end of table check
                #
                if self.cur_cmd in (DATAPATH_SESSION_TABLE, DATAPATH_SESSION_DPI, DATAPATH_USER):
                    if line == '':
                        continue        # skip blank line in datapath session table
                    if re.match("[0-9A-Fa-f][0-9A-Fa-f]:", line):
                        continue        # skip entries start with MAC address
                    if not line[0].isdigit():
                        in_cmd = False
                        in_cont = False
                        self.end_of_cmd()
                        continue
                elif self.cur_cmd == AP_ASSOCIATION_TABLE:
                    if line.startswith("Num Clients:"):
                        in_cmd = False
                        in_cont = False
                        self.end_of_cmd()
                        continue
                elif ('ap-list' in self.cur_cmd) or ('client-list' in self.cur_cmd):
                    if line.startswith("Start:"):
                        in_cmd = False
                        in_cont = False
                        self.end_of_cmd()
                        continue
                elif line.startswith('end of '):
                    in_cmd = False
                    in_cont = False
                    self.end_of_cmd()
                    continue

                if line == '':          # end of a contents section
                    in_cont = False
                    continue

                #
                #   split columns and add them to a list
                #
                row = [line[idx[i]:idx[i + 1]].rstrip() for i in range(len(idx) - 1)]
                row.append(line[idx[-1]:].rstrip())

                #
                #   apply some filter
                #
                if self.cur_cmd in (AP_DATABASE_TABLE, AP_DATABASE_LONG_TABLE):
                    if activeonly and not row[idx_status].startswith("Up"):
                        continue  # skip if Status is not 'Up'
                elif self.cur_cmd == DATAPATH_SESSION_DPI:
                    app = row[idx_app]
                    if app.startswith(" "):
                        row[idx_app] = "unknown"
                    else:
                        row[idx_app] = app.split(" ")[0]

                self.cur_table.append(row)
                self.num += 1
                continue



            #
            #   inside supported show command output
            #

            if self.cur_cmd == 'show datapath bridge' and line.startswith('--- '):
                continue    # skip the first table

            if re.match("-+ +-", line):  # beginning of a content section
                in_cont = True
                idx = []
                for r in re.finditer('-+', line):
                    idx.append(r.span(0)[0])  # index of each separator string '----'

                if len(self.cur_table) == 0:
                    # the very first content section for a table... parse header
                    hdr = prev_line  # save the first header line
                    row = [hdr[idx[i]:idx[i + 1]].strip() for i in range(len(idx) - 1)]
                    row.append(hdr[idx[-1]:].strip())

                    if self.cur_cmd in (AP_DATABASE_TABLE, AP_DATABASE_LONG_TABLE):
                        idx_status = row.index("Status")
                    elif self.cur_cmd == DATAPATH_SESSION_DPI:
                        idx_app = row.index("AppID")
                    self.cur_table.append(row)

            else:
                prev_line = line

        # EOF
        if in_cmd:
            self.end_of_cmd()

    def get_num_tables(self, cmd):
        if cmd not in self.tables:
            return 0
        return len(self.tables[cmd])

    def get_table(self, cmd, *cols):
        '''
        コマンドの結果テーブルを1つ取得する
        :param cmd: コマンド
        :param cols: 取得したい列名
        :return: コマンド結果テーブル
        '''
        if cmd not in self.tables or len(self.tables[cmd])==0:
            return None
        if len(cols) != 0:
            tbl = []
            for row in _get_cols_gen(self.tables[cmd][0], *cols):
                tbl.append(row)
            return tbl
        return self.tables[cmd][0]

    def get_tables(self, cmd, *cols):
        '''
        コマンドの結果テーブルを複数取得する
        :param cmd: コマンド
        :param cols: 取得したい列名
        :return: コマンド結果テーブルのリスト
        '''
        if cmd not in self.tables or len(self.tables[cmd])==0:
            return None
        if len(cols) != 0:
            return [_get_cols_gen(tbl, *cols) for tbl in self.tables[cmd]]
        return self.tables[cmd]

    def cols2str(self, table, *col_names):
        if len(col_names) == 0 or col_names[0] == '*':
            return self.table2str(table)

        max_col_widths = [0] * len(table[0])
        for row in table:
            max_col_widths = list(map(max, max_col_widths, map(len, row)))

        idx = [table[0].index(col) for col in col_names]
        fmt = ""
        for i in idx[:-1]:
            fmt += "{:" + str(max_col_widths[i]) + "}  "
        fmt += "{}"

        s = []
        for row in table:
            r2 = [row[i] for i in idx]
            s.append(fmt.format(*r2))

        return "\n".join(s) + "\n"

    def write_table(self, table, fn):
        if len(table) < 2:
            log.info(f"No data written to {fn}.")
            return True

        with open(fn, mode="w") as f:
            f.write(self.table2str(table))

        log.info(f"{len(table)-1} records written to {fn}.")
        return True

    def write_table_csv(self, table_num, fn):
        table = self.tables[table_num]
        if len(table) < 2:
            log.info(f"No data written to {fn}.")
            return True

        with open(fn, mode="w") as f:
            f.write(self.table2csv(table_num))

        log.info(f"{len(table)-1} records written to {fn}.")
        return True

    def table2str(self, table):
        if len(table) < 2:
            return ""

        max_col_widths = [0] * len(table[0])
        for row in table:
            max_col_widths = list(map(max, max_col_widths, map(len, row)))

        fmt = ""
        for i in range(len(max_col_widths)-1):
            fmt += "{:" + str(max_col_widths[i]) + "}  "
        fmt += "{}"

        s = [fmt.format(*row) for row in table]
        return "\n".join(s) + "\n"

    def table2csv(self, table):
        if len(table) < 2:
            return ""

        s = [",".join(row) for row in table]
        return "\n".join(s) + "\n"


#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="parse show command outputs and format it to txt/csv files")
    parser.add_argument('files', help="tech-support logs/show ap bss-table output", type=str, nargs='*')
    parser.add_argument('--csv', help='output csv format', action='store_true')
    parser.add_argument('--debug', help='debug log', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)

    cmds = [AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE, AP_ASSOCIATION_TABLE, USER_TABLE]
    aos = AOSParser(args.files, cmds=cmds)

    #   write files
    for cmd in cmds:
        tbl = aos.get_table(cmd)
        if tbl:
            if args.csv:
                aos.write_csv(tbl, cmd + ".csv")
            else:
                aos.write_table(tbl, cmd+".txt")

    sys.exit(0)

