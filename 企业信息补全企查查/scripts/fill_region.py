# -*- coding: utf-8 -*-
"""给工作簿企业表补充 所属省份/所属城市/所属区县(从注册地址解析)。

用法:
    python3 fill_region.py <目标xlsx> <企业表sheet名> <表头行> [--addr-col 16] [--prov-col 17] [--city-col 18] [--dist-col 19]

只在对应省/市/区县列为空时填充; 境外主体(开曼群岛/特拉华州等)解析为空, 跳过。
"""
import openpyxl, re, sys
from parse_region import parse_addr


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(2)
    tgt, sheet, hdr_row = sys.argv[1:4]
    hdr_row = int(hdr_row)
    addr_col, prov_col, city_col, dist_col = 16, 17, 18, 19
    for a in sys.argv[4:]:
        if a.startswith('--addr-col='): addr_col = int(a.split('=', 1)[1])
        if a.startswith('--prov-col='): prov_col = int(a.split('=', 1)[1])
        if a.startswith('--city-col='): city_col = int(a.split('=', 1)[1])
        if a.startswith('--dist-col='): dist_col = int(a.split('=', 1)[1])

    wb = openpyxl.load_workbook(tgt)
    ws = wb[sheet]
    filled = 0
    for r in range(hdr_row + 1, ws.max_row + 1):
        if not ws.cell(r, 1).value:
            continue
        if ws.cell(r, prov_col).value:
            continue  # 已有省
        addr = ws.cell(r, addr_col).value
        prov, city, dist = parse_addr(addr or '')
        if prov:
            for col, v in ((prov_col, prov), (city_col, city), (dist_col, dist)):
                ws.cell(r, col, v if v else None)
            filled += 1
    wb.save(tgt)
    print(f'补充省市区企业: {filled}')


if __name__ == '__main__':
    main()
