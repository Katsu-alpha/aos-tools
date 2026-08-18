#
#   Parse show commands and store the contents to 2-dimension lists
#   - ヘッダの幅は、次の行のセパレータ '----' で判定
#   - 複数回のコマンド出力が含まれている場合、別個に配列に保存
#   - コンストラクタオプション
#       merge: 複数のコマンド出力をマージするかどうか (default: False)
#       activeonly: ステータスが Up の AP 情報のみを含めるかどうか (default: True)
#

import re
import fileinput
import mylogger as log

AP_DATABASE_TABLE = "show ap database"
AP_DATABASE_LONG_TABLE = "show ap database long"
AP_BSS_TABLE = "show ap bss-table"
AP_ACTIVE_TABLE = "show ap active"
AP_ASSOCIATION_TABLE = "show ap association"
USER_TABLE = "show user-table"
DATAPATH_SESSION_TABLE = "show datapath session verbose"
DATAPATH_SESSION_DPI = "show datapath session dpi"
DATAPATH_SESSION_INT = "show datapath session internal"
DATAPATH_USER = "show datapath user table"
DATAPATH_BRIDGE = "show datapath bridge table"
DATAPATH_TUNNEL = "show datapath tunnel verbose"


class Fore:
    BLACK = '\x1b[30m'
    BLUE = '\x1b[34m'
    CYAN = '\x1b[36m'
    GREEN = '\x1b[32m'
    MAGENTA = '\x1b[35m'
    RED = '\x1b[31m'
    RESET = '\x1b[39m'
    WHITE = '\x1b[37m'
    YELLOW = '\x1b[33m'

class Style:
    BRIGHT = '\x1b[1m'
    DIM = '\x1b[2m'
    NORMAL = '\x1b[22m'
    RESET_ALL = '\x1b[0m'

#
#   helper functions
#
def _split_cols_by_utf8_bytes(text, idx):
    """
    Split fixed-width columns by UTF-8 byte offsets.
    idx contains each column's start position in bytes.
    """
    b = text.encode('utf-8')
    row = []
    for i, start in enumerate(idx):
        end = idx[i + 1] if i + 1 < len(idx) else None
        col = b[start:end].decode('utf-8', errors='ignore').rstrip()
        row.append(col)
    return row

def _get_cols_gen(tbl, *cols):
    try:
        idx = [tbl[0].index(col) for col in cols]
    except ValueError as e:
        log.err(f"Column not found: {e}")
        return

    if len(cols) == 1:  # 1列のみ指定された場合は文字列を返す
        for row in tbl[1:]:
            yield row[idx[0]]
    else:
        for row in tbl[1:]:
            yield [row[i] for i in idx] # 複数列が指定された場合はリストを返す


def table2str(table):
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


def table2csv(table):
    if len(table) < 2:
        return ""

    s = [",".join(row) for row in table]
    return "\n".join(s) + "\n"


def write_table(table, fn):
    if len(table) < 2:
        log.info(f"No data written to {fn}.")
        return True

    with open(fn, mode="w") as f:
        f.write(table2str(table))

    log.info(f"{len(table)-1} records written to {fn}.")
    return True


def write_table_csv(table, fn):
    if len(table) < 2:
        log.info(f"No data written to {fn}.")
        return True

    with open(fn, mode="w") as f:
        f.write(table2csv(table))

    log.info(f"{len(table)-1} records written to {fn}.")
    return True


def cols2str(table, *col_names):
    if len(col_names) == 0 or col_names[0] == '*':
        return table2str(table)

    max_col_widths = [0] * len(table[0])
    for row in table:
        max_col_widths = list(map(max, max_col_widths, map(len, row)))

    try:
        idx = [table[0].index(col) for col in col_names]
    except ValueError as e:
        log.err(f"Column not found: {e}")
        return ""

    fmt = ""
    for i in idx[:-1]:
        fmt += "{:" + str(max_col_widths[i]) + "}  "
    fmt += "{}"

    s = []
    for row in table:
        r2 = [row[i] for i in idx]
        s.append(fmt.format(*r2))

    return "\n".join(s) + "\n"


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

        self.in_cmd = False
        self.in_cont = False
        if len(self.cur_table) <= 1:
            #log.info(f"No entries found for '{self.cur_cmd}'.")
            return
        log.debug(f"{len(self.cur_table)-1} entries found in '{self.cur_cmd}'.")

        if not self.isMerge:
            self.tables[self.cur_cmd].append(self.cur_table)    # 表の配列に追加
            return

        if len(self.tables[self.cur_cmd]) == 0:
            self.tables[self.cur_cmd].append(self.cur_table)
            return

        log.debug(f"Merging table '{self.cur_cmd}'...")
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
        pat = {}
        for cmd in cmds:
            self.tables[cmd] = []
            pat[cmd] = re.compile(cmd + r"$")

        self.in_cmd  = False
        self.in_cont = False

        self.fromfile = True
        if type(files) == str:
            if '\n' in files:   # files = ファイル名ではなく、パースする入力データとみなす
                data = files.splitlines()
                self.fromfile = False
            elif '*' in files:
                import glob
                files = glob.glob(files)
        else:   # files is a list
            if '\n' in files[0]:    # 改行コードが含まれている場合、ファイル名ではなく、行のリストとみなす
                data = files
                self.fromfile = False

        if self.fromfile:
            data = fileinput.input(files, encoding=encoding)

        self.lno = 0
        try:
            for line in data:
                line = line.rstrip()
                self.lno += 1

                if not self.in_cmd and "show " not in line:
                    continue            # optimize parse speed a bit

                if not self.in_cont and self.in_cmd and "show " in line:
                    self.end_of_cmd()
                    # fall through

                # found matching show command
                if not self.in_cmd:
                    for cmd, p in pat.items():
                        if p.search(line):
                            log.debug(self.file_line() + "Parsing " + cmd)
                            self.in_cmd = True
                            self.cur_cmd = cmd
                            self.cur_table = []
                            continue

                    continue

                if self.in_cont:     # inside a table content
                    #
                    #   end of table check
                    #
                    if self.cur_cmd in (DATAPATH_SESSION_TABLE, DATAPATH_SESSION_DPI, DATAPATH_SESSION_INT, DATAPATH_USER, DATAPATH_TUNNEL):
                        if line == '':
                            continue        # skip blank line in datapath session table
                        if re.match("[0-9A-Fa-f][0-9A-Fa-f]:", line):
                            continue        # skip entries start with MAC address
                        if not line[0].isdigit():
                            self.end_of_cmd()
                            continue
                    elif self.cur_cmd == DATAPATH_BRIDGE:
                        if line == '':
                            continue        # skip blank line in datapath bridge table
                        if not re.match("[0-9A-Fa-f][0-9A-Fa-f]:", line):
                            self.end_of_cmd()
                            continue
                    elif AP_ASSOCIATION_TABLE in self.cur_cmd:
                        if line.startswith("Num Clients:"):
                            self.end_of_cmd()
                            continue
                    elif ('ap-list' in self.cur_cmd) or ('client-list' in self.cur_cmd):
                        if line.startswith("Start:") or line.startswith("dt:Discovered"):
                            self.end_of_cmd()
                            continue
                    elif self.cur_cmd == 'show clients debug':
                        if len(line) < 50:
                            self.end_of_cmd()
                            continue
                    elif line.startswith('end of '):
                        self.end_of_cmd()
                        continue
                    elif line.startswith('Neighbor Summary:'):  # show ap arm neighbors on IAP
                        self.end_of_cmd()
                        continue

                    if line == '':          # end of a contents section
                        self.in_cont = False
                        continue

                    #
                    #   split columns and add them to a list
                    #
                    # row = [line[idx[i]:idx[i + 1]].rstrip() for i in range(len(idx) - 1)]
                    # row.append(line[idx[-1]:].rstrip())
                    row = _split_cols_by_utf8_bytes(line, idx)

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

                    if self.fromfile:
                        row.append(fileinput.filename())        # add filename column
                    self.cur_table.append(row)
                    continue



                #
                #   inside supported show command output, but not in a content section
                #

                if self.cur_cmd == 'show datapath bridge' and line.startswith('--- '):
                    continue    # skip the first table

                if re.match("-+ +-", line):  # beginning of a content section
                    self.in_cont = True
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
                        if self.fromfile:
                            row.append("filename")  # add filename column
                        # add header row
                        self.cur_table.append(row)

                else:
                    prev_line = line

            # EOF
            if self.in_cmd:
                self.end_of_cmd()

        except UnicodeDecodeError as e:
            fileinput.close()
            raise e

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
            return list(_get_cols_gen(self.tables[cmd][0], *cols))
        return self.tables[cmd][0]


    def get_table_header(self, cmd):
        '''
        コマンドの最初の結果テーブルのヘッダを取得(カラムのリスト)
        :param cmd: コマンド
        :return: コマンド結果テーブルのヘッダ行
        '''
        if cmd not in self.tables or len(self.tables[cmd])==0:
            return None
        return self.tables[cmd][0][0]


    def get_table_key(self, cmd, key, val, *cols):
        '''
        コマンドの結果テーブルから key==val の列をすべて取得する
        :param cmd: コマンド
        :param cols: 取得したい列名
        :return: コマンド結果テーブル
        '''
        if len(cols)==0 or cmd not in self.tables or len(self.tables[cmd])==0:
            return None
        tbl = self.tables[cmd][0]
        r = []
        idx = [tbl[0].index(col) for col in cols]
        kidx = tbl[0].index(key)
        for row in tbl[1:]:
            if row[kidx] == val:
                r.append([row[i] for i in idx])

        return r


    def get_tables(self, cmd, *cols):
        '''
        コマンドの結果テーブルを複数取得する
        :param cmd: コマンド
        :param cols: 取得したい列名
        :return: コマンド結果テーブルのリスト (generatorのリスト)
        '''
        if cmd not in self.tables or len(self.tables[cmd])==0:
            return None
        if len(cols) != 0:
            return [_get_cols_gen(tbl, *cols) for tbl in self.tables[cmd]]
        return self.tables[cmd]

    def dedup(self, cmd, keycol):
        '''
        指定したコマンドのテーブルを keycol 列で重複排除する
        :param cmd: コマンド
        :param keycol: 重複排除に使用する列名
        :return: 重複排除後のレコード数
        '''
        if cmd not in self.tables or len(self.tables[cmd])==0:
            return 0

        tbl = self.tables[cmd][0]
        try:
            idx = tbl[0].index(keycol)
        except ValueError as e:
            log.err(f"Column not found: {e}")
            return 0
        seen = set()
        new_tbl = [tbl[0]]   # ヘッダ行

        for row in tbl[1:]:
            key = row[idx]
            if key in seen:
                continue
            seen.add(key)
            new_tbl.append(row)

        self.tables[cmd][0] = new_tbl
        return len(new_tbl)-1


    def dedup2(self, cmd, *keycol):
        '''
        指定したコマンドのテーブルを keycol 列で重複排除する。複数の列を指定可能
        :param cmd: コマンド
        :param keycol: 重複排除に使用する列名のリスト
        :return: 重複排除後のレコード数
        '''
        if cmd not in self.tables or len(self.tables[cmd])==0:
            return 0

        tbl = self.tables[cmd][0]
        try:
            idx = [tbl[0].index(col) for col in keycol]
        except ValueError as e:
            log.err(f"Column not found: {e}")
            return 0
        seen = set()
        new_tbl = [tbl[0]]   # ヘッダ行

        for row in tbl[1:]:
            key = tuple([row[i] for i in idx])
            if key in seen:
                continue
            seen.add(key)
            new_tbl.append(row)

        self.tables[cmd][0] = new_tbl
        return len(new_tbl)-1

    def change_colname(self, cmd, col_nam):
        if cmd not in self.tables or len(self.tables[cmd])==0:
            return
        cols = self.tables[cmd][0][0]
        for i, col in enumerate(cols):
            if col in col_nam:
                cols[i] = col_nam[col]

