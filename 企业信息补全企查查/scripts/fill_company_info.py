# -*- coding: utf-8 -*-
"""把企查查信息写入目标工作簿的企业表。

数据来源二选一(按企业优先):
- master 总表 xlsx(企查查高级搜索_合并总表.xlsx, 36列): 企业全称精确匹配
- qcc jsonl(浏览器抓取结果, 每行 {"id","kw","data"}): 按统一企业ID匹配

用法:
    python3 fill_company_info.py <目标xlsx> <企业表sheet名> <表头行> <总表xlsx> <qcc_jsonl>
    --scope-ids ENT-0106,ENT-0107,...    # 只处理指定ID(新增企业), 留空处理所有空行
    --src-col <起始列号=11> --dst-col <终止列号=33>

列映射: 目标列 -> (总表36字段idx, 企查查字段key)
支持 HYPERLINK 公式(企业全称B列)解析出显示文本用于匹配。
"""
import openpyxl, json, re, sys
from copy import copy

COL = {
    11: (5,  '统一社会信用代码'), 12: (1, '登记状态'), 13: (2, '法定代表人'), 14: (3, '注册资本'),
    15: (4, '成立日期'), 16: (6, '注册地址'), 17: (7, None), 18: (8, None), 19: (9, None),
    20: (13, '企业类型'), 21: (14, '纳税人识别号'), 22: (15, '工商注册号'), 23: (16, '组织机构代码'),
    24: (17, '参保人数'), 25: (19, '营业期限'), 26: (20, '国标行业'), 27: (30, '英文名'),
    28: (28, '企业规模'), 29: (31, '官网'), 30: (10, '电话'), 31: (12, '邮箱'), 32: (34, '简介'),
    33: (35, '经营范围'),
}


def norm(v):
    return re.sub(r'[\s（）()]', '', str(v or '')).casefold()


def clean(v):
    if v is None:
        return ''
    s = str(v).strip().replace('\u3000', '').replace('复制', '').replace('近期', '').strip()
    s = re.sub(r'\s+', '', s)
    if s in ('-', '—', 'None'):
        return ''
    return s


def strip_extra(name):
    s = name.strip()
    s = re.sub(r'（[^）]*）\s*$', '', s)
    s = re.sub(r'\([^)]*\)\s*$', '', s)
    return s


def master_keys(name):
    s = name.strip()
    keys = {norm(s), norm(strip_extra(s))}
    keys.add(norm(s.replace('股份有限公司', '').replace('有限公司', '')))
    keys.add(norm(strip_extra(s).replace('股份有限公司', '').replace('有限公司', '')))
    return keys


def load_master(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    next(it)  # 跳过表头
    master = {}
    for row in it:
        if row[0]:
            master.setdefault(norm(row[0]), row)
    wb.close()
    return master


def load_qcc(path):
    qcc = {}
    for l in open(path):
        r = json.loads(l)
        qcc[r['id']] = r['data']
    return qcc


def main():
    if len(sys.argv) < 6:
        print(__doc__)
        sys.exit(2)
    tgt, sheet, hdr_row, master_path, qcc_path = sys.argv[1:6]
    hdr_row = int(hdr_row)
    scope_ids = None
    for a in sys.argv[6:]:
        if a.startswith('--scope-ids='):
            scope_ids = set(a.split('=', 1)[1].split(','))
    master = load_master(master_path)
    qcc = load_qcc(qcc_path)

    wb = openpyxl.load_workbook(tgt)
    ow = wb[sheet]
    tpl = ow.cell(hdr_row + 1, 11)  # 数据格样式模板

    filled = 0
    for r in range(hdr_row + 1, ow.max_row + 1):
        eid = ow.cell(r, 1).value
        if not eid:
            continue
        if scope_ids and eid not in scope_ids:
            continue
        if ow.cell(r, 11).value:
            continue  # 已填跳过
        nraw = ow.cell(r, 2).value
        name = nraw
        if isinstance(nraw, str) and nraw.startswith('=HYPERLINK'):
            m = re.search(r'"([^"]*)"\)\s*$', nraw)
            name = m.group(1) if m else nraw
        row = None
        if name:
            for k in master_keys(name):
                if k in master:
                    row = master[k]
                    break
        d = qcc.get(eid) or {}
        for col, (mi, qk) in COL.items():
            if row is not None:
                v = clean(row[mi]) if mi is not None else ''
            else:
                v = clean(d.get(qk)) if qk else ''
            cell = ow.cell(r, col, v if v else None)
            if cell.has_style is False:
                cell.font = copy(tpl.font)
                cell.alignment = copy(tpl.alignment)
                cell.border = copy(tpl.border)
                cell.number_format = tpl.number_format
        filled += 1
    wb.save(tgt)
    print(f'已填充企业: {filled}')


if __name__ == '__main__':
    main()
