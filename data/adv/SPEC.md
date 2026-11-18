# B2 / C1 词条生成规范（给生成词条的代理看）

目标：给德语背单词 App 补 B2 和 C1 词汇。用户是在德国读硕士、找 IT 工作的中国学生（现在 A2–B1，目标 B2/C1）。释义用简体中文，**不要出现英文对应词**。

## 不要重复
`data/existing_lemmas.txt` 是 App 里已有的 3174 个词（A1–B1 + 求职/IT/办事专题）。**已有的词一律不要再出**（包括只差 sich、冠词或括号的同一个词）。同一个词也不要在你自己的文件里出现两次。

## 级别
- `B2`：B2 考试（Goethe/telc B2）和日常工作、新闻里常见的词。
- `C1`：更书面、抽象、学术或专业的常用词（报纸社论、学术文章、正式信函）。不要生僻到连母语者都很少用的词，也不要纯专业术语。

## 输出格式
一个 JSON 数组，UTF-8，写到任务里指定的文件。每个词条：

```json
{"lv": "B2", "lemma": "Auseinandersetzung", "art": "die", "pl_full": "die Auseinandersetzungen", "pos": "n",
 "zh": "争论；探讨；冲突",
 "ex": ["Die Auseinandersetzung mit dem Thema hat mir viel gebracht."],
 "ex_zh": "深入研究这个话题让我收获很多。",
 "gov": "die Auseinandersetzung mit + Dat.",
 "use": {"senses": ["争论；争执", "（深入）探讨、研究", "（武装）冲突"],
         "col": [["eine heftige Auseinandersetzung", "激烈的争论"], ["sich auf eine Auseinandersetzung einlassen", "卷入争论"]],
         "tip": "sich auseinandersetzen mit 的名词；和 Streit 比更正式"}}
```

```json
{"lv": "C1", "lemma": "beeinträchtigen", "pos": "v", "aux": "hat", "p2": "beeinträchtigt",
 "forms": "beeinträchtigt, beeinträchtigte, hat beeinträchtigt",
 "zh": "损害；妨碍", "ex": ["Der Lärm beeinträchtigt meine Konzentration."], "ex_zh": "噪音影响我集中注意力。",
 "use": {"col": [["die Gesundheit beeinträchtigen", "损害健康"], ["stark beeinträchtigt sein", "受到严重影响"]], "tip": "不可分动词；名词 die Beeinträchtigung"}}
```

字段规则：
- `lv`：`"B2"` 或 `"C1"`。
- `lemma`：词典形式。名词不带冠词（冠词放 `art`）；反身动词写 `sich …`（如 `sich auseinandersetzen`）；只有复数的名词写 `Kosten (Pl.)`，`art` 用 `"die"`。
- `pos`：`n` 名词、`v` 动词、`adj` 形容词、`adv` 副词、`conj` 连词、`prep` 介词、`phr` 固定短语/名词动词搭配（如 `in Kauf nehmen`、`zur Verfügung stehen`）。
- 名词必须有 `art`（der/die/das）和 `pl_full`（如 `"die Ergebnisse"`；没有复数就省略 `pl_full`）。
- 动词必须有 `aux`（`hat`/`ist`）、`p2`（第二分词）、`forms`（`第三人称现在时, 过去式, 完成时`，可分动词写 `fährt ab, fuhr ab, ist abgefahren`）。
- `gov`：有固定介词或格支配时写，如 `"verzichten auf + Akk."`、`"bedürfen + Gen."`。没有就省略。
- `zh`：最常用的 1–3 个中文释义，分号隔开，简短。
- `ex`：**一个**自然、地道的完整德语例句（8–18 个词，大写开头，句号结尾，必须包含这个词或它的变化形式），贴近用户生活：工作、IT、大学、办事、新闻、日常。
- `ex_zh`：例句的中文翻译。
- `use.senses`：只有多个明显不同的义项时才写（2–4 条中文），否则省略。
- `use.col`：2–3 个常用搭配，每个是 `[德语, 中文]`。
- `use.tip`：一句中文提示：易混词、词形变化陷阱、反义词、同族词、语体（口语/书面）。≤ 40 字。
- 不要任何英文。不要编造不存在的词。德语拼写按新正字法（ß/ss、daß→dass）。德国德语，不要只在奥地利/瑞士用的词。

## 质量
- 例句和搭配必须语法正确（格、词尾、动词位置、可分前缀）。写完自己检查一遍。
- 宁可少而准，不要凑数。
- 写完用 Python 校验 JSON 能解析、没有重复 lemma、每条字段齐全：`py -3.11 -I -c "import json;d=json.load(open(r'<你的文件>',encoding='utf-8'));print(len(d))"`。
- 写大文件时可以分几次：先写前半部分到 `<文件名>.part1.json`，再写后半部分，最后合并成指定文件并删掉 part 文件。

---

## 2026-11-17 补词（`freqNN`）：骨架 + 「义项与用法」

这批词是按词频找出的、App 里还缺的常用词（A1–C1 都有）。每批一个骨架文件 `wiktionary/gen/freqNN.todo.json`，**一条骨架对应一条输出**，写到 `data/adv/freqNN.json`。

### 骨架里已经填好的（来自 Wiktionary，基本可信）
- `lv`、`lemma`、`pos`：照抄。`lv` 不要改。
- 名词的 `art`、`pl_full`；动词的 `aux`、`p2`、`forms`：照抄，除非你**确定**是错的。
- `art_options`（几个冠词都出现过）：按这个词**最常用的那个意思**选一个写进 `art`，另一个冠词的意思可以写进 `tip`（如 "das Liter 也可以"）。
- `aux_options`（haben / sein 都可以）：按最常用的意思选一个写进 `aux`，另一种用法写进 `tip`（如 "表示「愈合」时用 ist geheilt"）。
- `forms_parts` = [第三人称现在时, 过去式, 第二分词]：组合成 `forms`（"heilt, heilte, hat geheilt"），缺的部分自己补。
- 动词主要以反身形式用时，`lemma` 改成 `sich …`，`forms` 里也带 sich（"erinnert sich, erinnerte sich, hat sich erinnert"），`p2` 写 "sich erinnert"。
- `hint_en` / `hint_de` 是 Wiktionary 的英文 / 德文释义，**只给你参考意思，输出里删掉**。`art_options`、`aux_options`、`forms_parts` 也删掉。

### 你要写的
`zh`、`ex`（一个）、`ex_zh`、`gov`（有就写）、`use.col`、`use.tip`，规则同上文。另外：

**`use.us` 义项与用法（仿红宝书：意思 → 句型 → 例句）**
- 只在这个词有 **2 个以上明显不同、常用**的意思或固定用法（介词搭配、格支配、反身用法、固定短语）时写，2–4 条；只有一个用法就**不写 us**。App 会拿 us 出「用法匹配题」，所以每条的中文意思必须彼此分得清。
- 每条：`{"p": 句型, "zh": 中文意思, "ex": 德语例句, "exz": 例句翻译}`
  - `p`：固定句型或搭配（可选）。格的写法用 `+ Dat.` / `+ Akk.` / `+ Gen.`，如 `"sich an + Akk. gewöhnen"`、`"Anspruch auf + Akk."`、`"in Anspruch nehmen"`。只是一个意思、没有特别句型时省略 `p`。
  - `zh`：这条的中文意思，短（2–10 字），和其他条不重复。
  - `ex`：一个自然的完整德语例句，8–16 个词，包含这个词（和句型），大写开头、句号结尾；**每条例句都不同**，也不要和顶层 `ex` 一样。
  - `exz`：例句的中文翻译。
- 顶层 `zh` 仍然写最常用的 1–3 个意思（分号隔开），和 us 不矛盾。
- 写了 us 就不要再写 `use.senses`；`col` 不要重复 us 里已有的句型。

### 不收的词
人名地名、纯粗口、只在奥地利/瑞士用的、只是另一个已有词的拼写变体：从输出里去掉，最后在回复里列出来。

### 自查
写完运行 `py -3.11 -I scripts/build_adv.py . --check data/adv/freqNN.json`（在仓库根目录 `C:\Users\Administrator\Desktop\文档\德语\Wortkarten`），把 ✗ 全部改掉再交。
