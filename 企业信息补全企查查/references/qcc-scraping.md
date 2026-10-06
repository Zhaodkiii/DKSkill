# 企查查抓取流程细则

当总表 xlsx 精确匹配不到企业时，用本地浏览器（Browser Use，`mac_computer_use_tool` 的 `bu` plane）访问
企查查逐家抓取工商信息。本文件描述浏览器抓取的标准做法与字段解析。

## 前置条件

- 本地浏览器需已登录企查查（`qcc.com`）。若被抓到登录页 / 验证页，**下一步必须调用
  `interaction_request_action(type="browserControl")` 请求用户接管登录**，完成后重新读取页面再继续。
- 每次访问间隔 **0.5 秒**（用户明确要求；搜索→详情页之间、企业之间都要 `time.sleep(0.5)`）。

## 抓取流程（每个企业）

1. **搜索**：`bu.navigate("https://www.qcc.com/web/search?key=<关键词>")`，`bu.wait_for_load(timeout=20)`。
2. **选链接**：`bu.read_all("a[href*='/firm/']", fields=["text","href"], limit=30)`，
   优先选文本**精确等于**关键词的 firm 链接（排除 `?fp=` 的附加页链接）；
   没有精确同名时选以关键词开头的；都没有才选第一个 firm 链接。
3. **进详情页**：`time.sleep(0.5)` 后 `bu.navigate(链接)`，`bu.wait_for_load(timeout=20)`。
4. **解析**：对 `bu.get_page_text()` 用正则提取字段（见下）。

## 字段解析正则（境内主体详情页）

```python
m = re.search(r'统一社会信用代码\s*([A-Za-z0-9]+)', txt); d['统一社会信用代码'] = m.group(1) if m else ''
m = re.search(r'企业名称\s*([^\n\t]+)复制', txt);      d['企业名称'] = m.group(1).strip() if m else ''
m = re.search(r'法定代表人\s*[^\n]*?\n?([\u4e00-\u9fa5A-Za-z]{2,8})', txt); d['法定代表人'] = m.group(1) if m else ''
m = re.search(r'登记状态\s*([^\n\t]+)', txt);          d['登记状态'] = m.group(1).strip() if m else ''
m = re.search(r'成立日期\s*([0-9-]+)', txt);           d['成立日期'] = m.group(1) if m else ''
m = re.search(r'注册资本\s*([0-9.,万元美元港元]+)', txt); d['注册资本'] = m.group(1) if m else ''
m = re.search(r'组织机构代码\s*([^\s\t]+)', txt);      d['组织机构代码'] = m.group(1) if m else ''
m = re.search(r'工商注册号\s*([^\s\t]+)', txt);        d['工商注册号'] = m.group(1) if m else ''
m = re.search(r'纳税人识别号\s*([A-Za-z0-9]+)', txt);  d['纳税人识别号'] = m.group(1) if m else ''
m = re.search(r'企业类型\s*\n?\s*([^\n\t]+)', txt);    d['企业类型'] = m.group(1).strip() if m else ''
m = re.search(r'营业期限\s*([0-9\-]{4}-[0-9\-]{2}-[0-9\-]{2}[^\n\t]*)', txt); d['营业期限'] = m.group(1).strip() if m else ''
m = re.search(r'参保人数\s*([0-9]+)', txt);            d['参保人数'] = m.group(1) if m else ''
m = re.search(r'国标行业\s*\n?\s*([^\n\t]+)', txt);    d['国标行业'] = m.group(1).strip() if m else ''
m = re.search(r'英文名\s*\n?\s*([^\n\t]+)', txt);      d['英文名'] = m.group(1).strip() if m else ''
m = re.search(r'注册地址\s*([^\n（(]+)', txt);         d['注册地址'] = m.group(1).strip() if m else ''
m = re.search(r'经营范围\s*([^\n]+)', txt);            d['经营范围'] = m.group(1).strip() if m else ''
m = re.search(r'企业规模：([^\n]+)', txt);             d['企业规模'] = m.group(1).strip() if m else ''
m = re.search(r'电话：\n?\s*([^\n]+?)\n', txt);        d['电话'] = m.group(1).strip() if m else ''
m = re.search(r'邮箱：\n?\s*([^\n]+?)\n', txt);        d['邮箱'] = m.group(1).strip() if m else ''
m = re.search(r'官网：\n?\s*([^\n]+?)\n', txt);        d['官网'] = m.group(1).strip() if m else ''
m = re.search(r'简介：\n([\s\S]*?)\n\n', txt);         d['简介'] = m.group(1).strip() if m else ''
```

解析后清洗：去掉 `\u3000`、`复制`、`近期` 字样，合并连续空白。境外主体解析不到部分字段属正常。

## 结果落盘格式

每家企业一行 JSON（`/tmp/qcc_results.jsonl`）：

```json
{"id": "ENT-0107", "kw": "奥托立夫（中国）汽车安全系统有限公司", "data": { ...字段... }}
```

`id` 必须与目标工作簿的统一企业ID一致（`fill_company_info.py` 按它关联）。

## 境外 / 品牌 / 多法人主体核对

关键词直接搜索可能命中错误法人，抓取后必须核对企业名称与经营范围是否符合业务语义，常见问题：

| 原表标注 | 应抓的正确法人 | 说明 |
|---|---|---|
| 恩智浦半导体(NXP) | 恩智浦（中国）管理有限公司 | 境内总部在上海 |
| 美满电子(Marvell) | 迈威迩电子科技（上海）有限公司 | 上海母公司，美满电子是曾用名 |
| 莫仕(Molex) | 莫仕（中国）投资有限公司 | 投资主体 |
| 博通(Broadcom) | 博通集成电路（上海）股份有限公司 | 境内上市主体 |
| 联创股份(子公司华安新材) | 山东华安新材料有限公司 | 按子公司名抓 |
| 富士智能(新三板申报) | 珠海富士智能股份有限公司 | 汽车电子连接器 |
| 德州仪器(TI) | 德州仪器半导体技术（上海）有限公司 | |
| Li Auto / NVIDIA | 境外主体（开曼/特拉华） | 无统一社会信用代码，属正常 |

通用规则：优先选**境内独立法人**（股份有限公司 / 有限公司 / 中国投资），避免分公司（"XX分公司"）和
明显不相关的同名主体（如地名公司）。拿不准时用 `bu.read_all` 列出同名候选再判断，不要盲抓第一个。

## 总表 36 字段 → 目标列映射

总表表头（0-35 索引）：
`企业名称/登记状态/法定代表人/注册资本/成立日期/统一社会信用代码/注册地址/所属省份/所属城市/所属区县/有效手机号/更多电话/邮箱/企业(机构)类型/纳税人识别号/注册号/组织机构代码/参保人数/参保人数所属年报/营业期限/国标行业门类/国标行业大类/国标行业中类/国标行业小类/企查查行业门类/企查查行业大类/企查查行业中类/企查查行业小类/企业规模/曾用名/英文名/官网网址/通信地址/通信地址邮编/企业简介/经营范围`

`fill_company_info.py` 的 `COL` 已内置完整映射（11-33 列）。国标行业在总表拆成 4 级，写回时取**门类**；
企查查网页抓取给的是 4 级合并串，原样写入。
