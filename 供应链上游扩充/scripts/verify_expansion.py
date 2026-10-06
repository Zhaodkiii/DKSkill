#!/usr/bin/env python3
"""verify_expansion.py — 校验「上游供应链扩充」写入是否符合规范。

用法:
  python3 verify_expansion.py <当前xlsx> <备份xlsx>

检查项:
  1. 原行 0 差异：10 个 sheet，备份中每个 sheet 的所有数据行，与当前文件逐格比对，必须完全一致。
  2. 只追加：当前文件每个 sheet 数据行数 >= 备份。
  3. 新增产品规范（仅本次新增行）：企业ID 非空且存在、产品名称/归属名称是 HYPERLINK 公式、归属名称与树一致。
  4. 新增关系规范（仅本次新增行）：零部件是 HYPERLINK(产品表)、归属名称与树一致。
  5. 编号连续性：企业 ENT-、产品 PRD-、关系 REL- 序号连续无跳跃。

退出码 0=通过；1=有差异。
"""
import re
import sys

import openpyxl

ANCHORS = {"企业表": "统一企业ID", "产品表": "统一产品ID", "供应链核心": "统一关系ID",
           "证据与核验": "统一来源ID", "时效与审计": "统一审计ID", "来源清单": "来源工作簿",
           "产品归属": "归属ID", "品牌表": "统一品牌ID", "企业品牌关系": "统一关系ID"}


def find_header(ws, anchor):
    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=30, values_only=True), start=1):
        if row and row[0] == anchor:
            return i
    return None


def data_rows(ws, hr):
    return list(ws.iter_rows(min_row=hr + 1, values_only=True))


def norm(v):
    return "" if v is None else str(v).strip()


def display(v):
    """抽取 HYPERLINK 公式的显示文本，否则返回原值。"""
    s = norm(v)
    if s.startswith("=HYPERLINK("):
        m = re.findall(r'"([^"]*)"\s*\)\s*$', s)
        return m[-1] if m else s
    return s


def main():
    if len(sys.argv) != 3:
        print("用法: python3 verify_expansion.py <当前xlsx> <备份xlsx>")
        return 2
    cur_p, bak_p = sys.argv[1], sys.argv[2]
    wb = openpyxl.load_workbook(cur_p)
    wbb = openpyxl.load_workbook(bak_p)
    errors = []

    # 备份各 sheet 数据行数（用于识别“本次新增行”）
    bak_counts = {}
    for sh in wb.sheetnames:
        anchor = ANCHORS.get(sh)
        if not anchor:
            continue
        ha = find_header(wb[sh], anchor)
        hb = find_header(wbb[sh], anchor)
        if ha and hb:
            bak_counts[sh] = len(data_rows(wbb[sh], hb))

    # 1&2. 原行 0 差异 + 只追加
    for sh in wb.sheetnames:
        a, b = wb[sh], wbb[sh]
        anchor = ANCHORS.get(sh)
        if not anchor:
            continue
        ha, hb = find_header(a, anchor), find_header(b, anchor)
        if ha is None or hb is None:
            continue
        da, db = data_rows(a, ha), data_rows(b, hb)
        if len(da) < len(db):
            errors.append(f"[{sh}] 行数少于备份（追加失败）")
            continue
        for i in range(len(db)):
            ra, rb = da[i], db[i]
            for j in range(max(len(ra), len(rb))):
                va = norm(ra[j]) if j < len(ra) else ""
                vb = norm(rb[j]) if j < len(rb) else ""
                if va != vb:
                    errors.append(f"[{sh}] 第{ha+1+i}行 第{j+1}列 原行被改: '{vb[:20]}' -> '{va[:20]}'")

    # 树节点（归属ID -> 归属名称）
    hrp = find_header(wbb["产品归属"], "归属ID")
    tree = {}
    for r in wbb["产品归属"].iter_rows(min_row=hrp + 1, values_only=True):
        if r[0]:
            segs = [s.strip() for s in (r[4] or "").split("/") if s.strip()]
            tree[str(r[0])] = segs[-1] if segs else ""

    def check_new(sheet, anchor, checks):
        """仅对本次新增行（超出备份行数的）执行 checks(row, idx)。"""
        hb = find_header(wbb[sheet], anchor)
        ha = find_header(wb[sheet], anchor)
        db = data_rows(wbb[sheet], hb) if hb else []
        da = data_rows(wb[sheet], ha) if ha else []
        for i in range(len(db), len(da)):
            checks(da[i], i)

    # 3. 新增产品规范
    def chk_prd(r, i):
        if not r[0]:
            return
        if not r[16]:
            errors.append(f"[产品表] {r[0]} 缺企业ID")
        elif not re.fullmatch(r"ENT-\d+", str(r[16])):
            errors.append(f"[产品表] {r[0]} 企业ID非常规: {r[16]}")
        if not (r[5] and norm(r[5]).startswith("=HYPERLINK")):
            errors.append(f"[产品表] {r[0]} 产品名称非超链接: {r[5]}")
        if not (r[3] and norm(r[3]).startswith("=HYPERLINK")):
            errors.append(f"[产品表] {r[0]} 归属名称非超链接: {r[3]}")
        elif r[2] and tree.get(str(r[2])) and display(r[3]) != tree[str(r[2])]:
            errors.append(f"[产品表] {r[0]} 归属名称不一致: '{display(r[3])}' != '{tree[str(r[2])]}'")

    # 4. 新增关系规范
    def chk_rel(r, i):
        if not r[0]:
            return
        zjb = r[10]
        if not (zjb and norm(zjb).startswith("=HYPERLINK") and "产品表" in norm(zjb)):
            errors.append(f"[供应链核心] {r[0]} 零部件未指向产品表: {zjb}")
        if not (r[9] and norm(r[9]).startswith("=HYPERLINK")):
            errors.append(f"[供应链核心] {r[0]} 归属名称非超链接: {r[9]}")
        elif r[8] and tree.get(str(r[8])) and display(r[9]) != tree[str(r[8])]:
            errors.append(f"[供应链核心] {r[0]} 归属名称不一致: '{display(r[9])}' != '{tree[str(r[8])]}'")
        # 关系方向/层级/关系类型/证据等级 非空
        for col, name in ((3, "关系方向"), (12, "层级"), (13, "关系类型"), (14, "证据等级"), (15, "核验状态")):
            if not r[col]:
                errors.append(f"[供应链核心] {r[0]} {name} 为空")

    check_new("产品表", "统一产品ID", chk_prd)
    check_new("供应链核心", "统一关系ID", chk_rel)

    # 5. 编号连续性（全量）
    for sheet, prefix, col in (("企业表", "ENT-", 0), ("产品表", "PRD-", 0), ("供应链核心", "REL-", 0)):
        ws = wb[sheet]; hr = find_header(ws, ANCHORS[sheet])
        nums = []
        for r in ws.iter_rows(min_row=hr + 1, values_only=True):
            if r[col] and norm(r[col]).startswith(prefix):
                nums.append(int(str(r[col])[len(prefix):]))
        nums.sort()
        if nums:
            for expect, actual in zip(range(nums[0], nums[-1] + 1), nums):
                if expect != actual:
                    errors.append(f"[{sheet}] 编号不连续: {prefix}{actual:04d} 应为 {prefix}{expect:04d}")
                    break

    if errors:
        print("校验未通过，共 %d 处问题:" % len(errors))
        for e in errors[:60]:
            print("  -", e)
        if len(errors) > 60:
            print(f"  …另有 {len(errors)-60} 处")
        return 1
    print("校验通过：原行 0 差异、只追加、新增行格式/超链接/归属一致、编号连续。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
