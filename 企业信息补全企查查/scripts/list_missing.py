# -*- coding: utf-8 -*-
"""列出目标工作簿企业表中缺少企查查信息的统一企业ID与企业全称(去HYPERLINK)。

用法:
    python3 list_missing.py <目标xlsx> <企业表sheet名> <表头行> [--code-col 11]

输出: 每行 "统一企业ID\t企业全称\t搜索关键词建议"
- 企业全称自动去备注括号/品牌标注生成搜索关键词
- --code-col 指定信用代码列号, 该列非空视为已有信息
"""
import openpyxl, re, sys


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(2)
    tgt, sheet, hdr_row = sys.argv[1:4]
    hdr_row = int(hdr_row)
    code_col = 11
    for a in sys.argv[4:]:
        if a.startswith('--code-col='): code_col = int(a.split('=', 1)[1])

    wb = openpyxl.load_workbook(tgt, data_only=True)
    ws = wb[sheet]

    def display_name(raw):
        if isinstance(raw, str) and raw.startswith('=HYPERLINK'):
            m = re.search(r'"([^"]*)"\)\s*$', raw)
            return m.group(1) if m else raw
        return raw or ''

    def keyword(name):
        s = re.sub(r'（[^）]*）\s*$', '', name.strip())
        s = re.sub(r'\([^)]*\)\s*$', '', s)
        return s

    for r in range(hdr_row + 1, ws.max_row + 1):
        eid = ws.cell(r, 1).value
        if not eid:
            continue
        if ws.cell(r, code_col).value:
            continue
        name = display_name(ws.cell(r, 2).value)
        print(f'{eid}\t{name}\t{keyword(name)}')


if __name__ == '__main__':
    main()
