#!/usr/bin/env python3
"""append_expansion.py — 批量追加「上游供应链扩充」数据到新能源汽车供应链整合数据模型。

用法:
  python3 append_expansion.py <xlsx路径> <payload.json> [--backup-dir <目录>]

行为:
  - 动手前先备份 xlsx 到 backup-dir（默认 历史备份）。
  - 只追加，绝不修改既有行。
  - 自动延续编号：企业 ENT-、产品 PRD-、关系 REL-、审计 AUD-、来源 WEB-。
  - 按 企业 → 证据 → 产品 → 关系 → 审计 → 来源清单 的正确顺序写入。
  - 自动写超链接：产品表 产品名称→自身行、企业ID→企业表；供应链核心 供方/需方→企业表、零部件→产品表。
  - 企业引用可按「简称/品牌」解析：payload 里 产品.企业ID、关系.供方企业ID/需方企业ID 既可写 ENT- 编号，
    也可写企业简称（本次新增的，或企业表中已存在的），脚本自动解析为 ENT 编号。

payload.json 结构（字段见 references/schema.md）:
{
  "来源工作簿": "网络公开检索（上游扩充-2026）",
  "企业":  [ {"简称/品牌":"均胜电子","企业全称":"...","供应链角色":"零部件供应商","国家/地区":"中国",...}, ... ],
  "证据":  [ {"原始来源编号":"WEB-xx","来源类型":"官方","发布方":"...","文件/页面标题":"...","发布日期":"...","可验证事项":"...","原始URL":"https://...","访问/授权":"公开","状态":"有效"}, ... ],
  "产品":  [ {"名称":"...","归属ID":"04.05.01.01","企业ID":"均胜电子","产品类型":"...","状态":"量产","产品说明":"..."}, ... ],
  "关系":  [ {"供方企业ID":"均胜电子","需方企业ID":"ENT-0065","归属ID":"04.05.01.01","零部件":"...","车型/版本":"...","层级":"T1","关系类型":"供应","证据等级":"A","核验状态":"有效","有效起始":"2024-01-01","公开关系摘要":"...","来源编号":"WEB-xx"}, ... ],
  "审计":  [ {"日期":"2026-09-28","事件类型":"供应链上游扩充","对象类型":"...","关联对象":"...","处理状态":"已录入","责任角色":"研究员","说明":"..."}, ... ]
}
字段缺省值：归属名称/产品路径 从 产品归属 树自动补齐；核验状态按证据等级 A/B/C 自动给。
"""

import argparse, datetime, json, os, re, shutil, sys

import openpyxl


def find_header_row(ws, anchor):
    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=30, values_only=True), start=1):
        if row and row[0] == anchor:
            return i
    raise RuntimeError(f"sheet '{ws.title}' 未找到表头锚点 '{anchor}'")


def max_num(ws, header_row, prefix, col=0):
    m = 0
    for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
        v = row[col]
        if isinstance(v, str):
            mm = re.match(rf"^{re.escape(prefix)}(\d+)", v.strip())
            if mm:
                m = max(m, int(mm.group(1)))
    return m


def next_id(ws, header_row, prefix, col=0):
    return f"{prefix}{max_num(ws, header_row, prefix, col) + 1:04d}"


def last_data_row(ws, header_row):
    n = header_row
    for i, row in enumerate(ws.iter_rows(min_row=header_row + 1), start=header_row + 1):
        if any(c is not None and str(c).strip() for c in row):
            n = i
    return n


def put(ws, row, col, value):
    ws.cell(row=row, column=col + 1, value=value)


def build_tree_map(wb):
    ws = wb["产品归属"]
    hr = find_header_row(ws, "归属ID")
    tree = {}
    for i, row in enumerate(ws.iter_rows(min_row=hr + 1, values_only=True), start=hr + 1):
        gid = row[0]
        if not gid:
            continue
        segs = [s.strip() for s in (row[4] or "").split("/") if s.strip()]
        tree[str(gid)] = {"归属名称": segs[-1] if segs else "",
                          "产品路径": (row[4] or "").strip(),
                          "行号": i}
    return tree


def existing_enterprise_map(ws, header_row):
    """企业表 已有企业：简称/品牌 -> ENT id；全称 -> ENT id。"""
    m = {}
    for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
        ent = row[0]
        if not ent:
            continue
        short = row[2]
        full = row[1]
        if short:
            m[str(short)] = ent
        if full:
            m[str(full)] = ent
    return m


def main():
    ap = argparse.ArgumentParser(description="追加上游供应链扩充数据到数据模型 xlsx")
    ap.add_argument("xlsx")
    ap.add_argument("payload")
    ap.add_argument("--backup-dir", default="历史备份")
    args = ap.parse_args()

    with open(args.payload, encoding="utf-8") as f:
        data = json.load(f)
    src_wb = data.get("来源工作簿", "网络公开检索（上游扩充-2026）")

    os.makedirs(args.backup_dir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = os.path.join(args.backup_dir, os.path.splitext(os.path.basename(args.xlsx))[0] + f"_备份_{stamp}.xlsx")
    shutil.copy2(args.xlsx, bak)
    print(f"备份: {bak}")

    wb = openpyxl.load_workbook(args.xlsx)
    tree = build_tree_map(wb)

    # ---------- 企业表 ----------
    ws = wb["企业表"]; hr = find_header_row(ws, "统一企业ID")
    ent_by_name = existing_enterprise_map(ws, hr)      # 已有企业
    ent_row = {}                                        # ENT id -> 企业表行号
    new_ent_name = {}                                   # 简称 -> ENT id（本次新增）
    new_ent_name_inv = {}                               # ENT id -> 简称（本次新增）
    if data.get("企业"):
        cur = last_data_row(ws, hr)
        for e in data["企业"]:
            ent = next_id(ws, hr, "ENT-")
            ent_row[ent] = cur + 1
            new_ent_name[e.get("简称/品牌")] = ent
            new_ent_name_inv[ent] = e.get("简称/品牌")
            cur += 1
            vals = [ent, e.get("企业全称"), e.get("简称/品牌"), e.get("供应链角色"),
                    e.get("国家/地区", "中国"), e.get("所属集团"), e.get("状态", "存续"),
                    e.get("业务说明"), e.get("原始企业ID"), e.get("来源编号", src_wb)]
            for j, v in enumerate(vals):
                if v is not None:
                    put(ws, cur, j, v)
            print(f"  企业 {ent}: {e.get('简称/品牌')}")

    def resolve_ent(ref, default_name=None):
        """ref 可为 ENT id 或企业简称/全称，返回 (ent_id, 显示名)。"""
        if not ref:
            return None, default_name
        ref = str(ref)
        is_name = not re.fullmatch(r"ENT-\d+", ref)
        if ref in ent_row:                       # ENT id，本次新增
            return ref, default_name or (new_ent_name_inv.get(ref, ""))
        if ref in new_ent_name:                  # 企业简称，本次新增
            return new_ent_name[ref], ref
        if ref in ent_by_name:                   # 企业简称/全称，已有企业
            return ent_by_name[ref], ref
        if is_name:
            return None, ref                      # 未匹配到档案：ID 留空，仅显示名
        return ref, default_name

    # ---------- 证据与核验 ----------
    ws = wb["证据与核验"]; hr = find_header_row(ws, "统一来源ID")
    src_id_map = {}
    if data.get("证据"):
        cur = last_data_row(ws, hr)
        for s in data["证据"]:
            sid = s.get("原始来源编号") or f"WEB-{max_num(ws, hr, 'WEB-', 2) + 1:02d}"
            src_id_map[sid] = cur + 1
            cur += 1
            vals = [None, src_wb, sid, s.get("来源类型"), s.get("发布方"), s.get("文件/页面标题"),
                    s.get("发布日期"), s.get("可验证事项"), s.get("原始URL"), s.get("访问/授权", "公开"),
                    s.get("状态", "有效")]
            for j, v in enumerate(vals):
                if v is not None:
                    put(ws, cur, j, v)
            print(f"  证据 {sid}")

    # ---------- 产品表 ----------
    ws = wb["产品表"]; hr = find_header_row(ws, "统一产品ID")
    prd_row = {}
    if data.get("产品"):
        cur = last_data_row(ws, hr)
        for p in data["产品"]:
            prd = next_id(ws, hr, "PRD-")
            prd_row[p["名称"]] = cur + 1
            cur += 1
            node = tree.get(p["归属ID"], {"归属名称": "", "产品路径": ""})
            ent_id, disp = resolve_ent(p.get("企业ID"), p.get("企业显示名"))
            put(ws, cur, 0, prd)
            put(ws, cur, 2, p["归属ID"])
            put(ws, cur, 3, f'=HYPERLINK("#\'产品归属\'!A{node.get("行号")}","{node["归属名称"]}")')
            put(ws, cur, 4, node["产品路径"])
            put(ws, cur, 5, f'=HYPERLINK("#\'产品表\'!A{cur}","{p["名称"]}")')
            put(ws, cur, 6, p.get("产品类型"))
            put(ws, cur, 7, p.get("年款"))
            put(ws, cur, 8, p.get("版本/范围"))
            put(ws, cur, 9, p.get("状态", "量产"))
            put(ws, cur, 10, p.get("产品说明"))
            put(ws, cur, 11, p.get("来源编号") or next(iter(src_id_map), None))
            put(ws, cur, 16, ent_id)
            if ent_id and ent_id in ent_row and disp:
                put(ws, cur, 17, f'=HYPERLINK("#\'企业表\'!A{ent_row[ent_id]}","{disp}")')
            elif ent_id and disp:
                put(ws, cur, 17, disp)
            print(f"  产品 {prd}: {p['名称']} @ {p['归属ID']} -> {ent_id}({disp})")

    # ---------- 供应链核心 ----------
    ws = wb["供应链核心"]; hr = find_header_row(ws, "统一关系ID")
    if data.get("关系"):
        cur = last_data_row(ws, hr)
        for r in data["关系"]:
            rel = next_id(ws, hr, "REL-")
            cur += 1
            sup_id, sup_disp = resolve_ent(r.get("供方企业ID"), r.get("供方企业"))
            need_id, need_disp = resolve_ent(r.get("需方企业ID"), r.get("需方企业"))
            node = tree.get(r["归属ID"], {"归属名称": ""})
            put(ws, cur, 0, rel)
            put(ws, cur, 1, src_wb)
            put(ws, cur, 2, r.get("原始主张ID"))
            put(ws, cur, 3, r.get("关系方向", "上游供货"))
            put(ws, cur, 4, sup_id)
            put(ws, cur, 5, f'=HYPERLINK("#\'企业表\'!A{ent_row[sup_id]}","{sup_disp}")' if sup_id in ent_row and sup_disp else (sup_disp or sup_id))
            put(ws, cur, 6, need_id)
            put(ws, cur, 7, f'=HYPERLINK("#\'企业表\'!A{ent_row[need_id]}","{need_disp}")' if need_id in ent_row and need_disp else (need_disp or need_id))
            put(ws, cur, 8, r["归属ID"])
            put(ws, cur, 9, f'=HYPERLINK("#\'产品归属\'!A{node.get("行号")}","{node["归属名称"]}")')
            zjb = r["零部件"]
            lnk = prd_row.get(zjb)
            put(ws, cur, 10, f'=HYPERLINK("#\'产品表\'!A{lnk}","{zjb}")' if lnk else zjb)
            put(ws, cur, 11, r.get("车型/版本"))
            put(ws, cur, 12, r.get("层级", "T1"))
            put(ws, cur, 13, r.get("关系类型", "供应"))
            put(ws, cur, 14, r.get("证据等级", "C"))
            put(ws, cur, 15, r.get("核验状态") or {"A": "有效", "B": "待复核", "C": "待核验"}.get(r.get("证据等级", "C"), "待核验"))
            put(ws, cur, 16, r.get("有效起始"))
            put(ws, cur, 17, r.get("有效结束"))
            put(ws, cur, 18, r.get("公开关系摘要"))
            put(ws, cur, 19, r.get("来源编号"))
            print(f"  关系 {rel}: {sup_disp or sup_id} -> {need_disp or need_id} | {zjb}")

    # ---------- 审计 ----------
    ws = wb["时效与审计"]; hr = find_header_row(ws, "统一审计ID")
    if data.get("审计"):
        cur = last_data_row(ws, hr)
        for a in data["审计"]:
            cur += 1
            put(ws, cur, 0, next_id(ws, hr, "AUD-"))
            put(ws, cur, 1, "新能源汽车供应链整合数据模型")
            put(ws, cur, 2, a.get("原始审计ID"))
            put(ws, cur, 3, a.get("日期"))
            put(ws, cur, 4, a.get("事件类型", "供应链上游扩充"))
            put(ws, cur, 5, a.get("对象类型", "供应链关系/企业/证据/产品"))
            put(ws, cur, 6, a.get("关联对象"))
            put(ws, cur, 7, a.get("处理状态", "已录入"))
            put(ws, cur, 8, a.get("责任角色", "研究员"))
            put(ws, cur, 9, a.get("说明"))

    # ---------- 来源清单 ----------
    ws = wb["来源清单"]; hr = find_header_row(ws, "来源工作簿")
    n_ent, n_prd = len(data.get("企业", [])), len(data.get("产品", []))
    n_rel, n_evi = len(data.get("关系", [])), len(data.get("证据", []))
    n_aud = len(data.get("审计", []))
    found = None
    for i, row in enumerate(ws.iter_rows(min_row=hr + 1, values_only=True), start=hr + 1):
        if row and row[0] == src_wb:
            found = i; break
    if found:
        for col, n in ((2, n_ent), (3, n_prd), (4, n_rel), (5, n_evi), (6, n_aud)):
            old = ws.cell(row=found, column=col + 1).value
            put(ws, found, col, (old or 0) + n)
    else:
        cur = last_data_row(ws, hr)
        put(ws, cur + 1, 0, src_wb)
        put(ws, cur + 1, 1, "网络检索，无本地工作簿文件")
        put(ws, cur + 1, 2, n_ent); put(ws, cur + 1, 3, n_prd); put(ws, cur + 1, 4, n_rel)
        put(ws, cur + 1, 5, n_evi); put(ws, cur + 1, 6, n_aud)

    wb.save(args.xlsx)
    print(f"完成：企业+{n_ent} 产品+{n_prd} 关系+{n_rel} 证据+{n_evi} 审计+{n_aud}，已写入 {args.xlsx}")
    print("请用 verify_expansion.py 对照备份自检。")


if __name__ == "__main__":
    main()
