"""求职 / IT 工作 / 办事（Behörde）专题词。字段：lemma, art, pl_full, pos, zh, ex, ex_zh, aux, p2, gov, tag"""
import json
import sys
from pathlib import Path

N = "n"; V = "v"; A = "adj"; P = "phr"

# (tag, pos, art, lemma, pl_full, zh, ex, ex_zh, extra)
ROWS = [
 # —— 求职 ——
 ("求职", N, "die", "Bewerbung", "die Bewerbungen", "申请；求职信", "Ich habe meine Bewerbung per E-Mail geschickt.", "我已经通过电子邮件发送了申请。", {}),
 ("求职", V, None, "sich bewerben", "", "申请（职位）", "Ich bewerbe mich um die Stelle als Softwareentwickler.", "我申请软件开发员这个职位。", {"aux": "hat", "p2": "beworben", "gov": "sich bewerben um + Akk. / bei + Dat."}),
 ("求职", N, "das", "Anschreiben", "die Anschreiben", "求职信", "Das Anschreiben sollte nicht länger als eine Seite sein.", "求职信不应超过一页。", {}),
 ("求职", N, "der", "Lebenslauf", "die Lebensläufe", "简历", "Bitte schicken Sie uns Ihren Lebenslauf.", "请把您的简历发给我们。", {}),
 ("求职", N, "das", "Vorstellungsgespräch", "die Vorstellungsgespräche", "面试", "Morgen habe ich ein Vorstellungsgespräch bei Bosch.", "明天我在博世有个面试。", {}),
 ("求职", N, "die", "Stellenanzeige", "die Stellenanzeigen", "招聘广告", "Ich habe die Stellenanzeige auf LinkedIn gesehen.", "我在 LinkedIn 上看到了这则招聘广告。", {}),
 ("求职", N, "die", "Stelle", "die Stellen", "职位；岗位", "Die Stelle ist ab sofort zu besetzen.", "该职位即刻招人。", {}),
 ("求职", N, "die", "Anforderung", "die Anforderungen", "要求", "Erfüllen Sie alle Anforderungen der Stelle?", "您满足这个职位的所有要求吗？", {}),
 ("求职", N, "die", "Voraussetzung", "die Voraussetzungen", "前提条件", "Gute Deutschkenntnisse sind Voraussetzung.", "良好的德语水平是前提条件。", {}),
 ("求职", N, "die", "Kenntnisse (Pl.)", "", "知识；技能（复数）", "Sie haben sehr gute Kenntnisse in Python.", "您的 Python 技能非常好。", {}),
 ("求职", N, "die", "Berufserfahrung", "", "工作经验", "Wir suchen jemanden mit drei Jahren Berufserfahrung.", "我们在找有三年工作经验的人。", {}),
 ("求职", N, "die", "Erfahrung", "die Erfahrungen", "经验", "Ich habe Erfahrung mit Datenbanken.", "我有数据库方面的经验。", {"gov": "Erfahrung mit + Dat."}),
 ("求职", N, "der", "Abschluss", "die Abschlüsse", "毕业；学位", "Ich habe meinen Abschluss in Informatik gemacht.", "我获得了计算机科学学位。", {}),
 ("求职", N, "das", "Zeugnis", "die Zeugnisse", "证书；成绩单", "Bitte legen Sie Ihre Zeugnisse bei.", "请附上您的证书。", {}),
 ("求职", N, "das", "Arbeitszeugnis", "die Arbeitszeugnisse", "工作证明（离职评语）", "Mein alter Chef hat mir ein gutes Arbeitszeugnis geschrieben.", "我以前的老板给我写了一份很好的工作证明。", {}),
 ("求职", N, "die", "Anlage", "die Anlagen", "附件", "In der Anlage finden Sie meinen Lebenslauf.", "附件中是我的简历。", {}),
 ("求职", N, "die", "Absage", "die Absagen", "拒绝；拒信", "Leider habe ich eine Absage bekommen.", "可惜我收到了拒信。", {}),
 ("求职", N, "die", "Zusage", "die Zusagen", "录用；答应", "Nach dem zweiten Gespräch bekam ich die Zusage.", "第二轮面试后我被录用了。", {}),
 ("求职", N, "der", "Arbeitgeber", "die Arbeitgeber", "雇主", "Mein Arbeitgeber zahlt das Deutschlandticket.", "我的雇主报销德国票。", {}),
 ("求职", N, "der", "Arbeitnehmer", "die Arbeitnehmer", "雇员", "Arbeitnehmer haben ein Recht auf Urlaub.", "雇员有权休假。", {}),
 ("求职", N, "der", "Arbeitsvertrag", "die Arbeitsverträge", "劳动合同", "Ich habe den Arbeitsvertrag unterschrieben.", "我签了劳动合同。", {}),
 ("求职", N, "die", "Probezeit", "die Probezeiten", "试用期", "Die Probezeit dauert sechs Monate.", "试用期为六个月。", {}),
 ("求职", N, "die", "Kündigungsfrist", "die Kündigungsfristen", "解约通知期", "Die Kündigungsfrist beträgt drei Monate.", "解约通知期为三个月。", {}),
 ("求职", V, None, "kündigen", "", "辞职；解雇", "Er hat seine Stelle gekündigt.", "他辞去了工作。", {"aux": "hat", "p2": "gekündigt"}),
 ("求职", N, "das", "Gehalt", "die Gehälter", "薪水", "Das Gehalt wird am Monatsende überwiesen.", "薪水在月底转账。", {}),
 ("求职", N, "die", "Gehaltsvorstellung", "die Gehaltsvorstellungen", "期望薪资", "Bitte nennen Sie Ihre Gehaltsvorstellung.", "请说明您的期望薪资。", {}),
 ("求职", N, "das", "Bruttogehalt", "die Bruttogehälter", "税前工资", "Das Bruttogehalt liegt bei 55.000 Euro im Jahr.", "税前年薪约 5.5 万欧元。", {}),
 ("求职", N, "der", "Eintrittstermin", "die Eintrittstermine", "入职日期", "Mein frühestmöglicher Eintrittstermin ist der 1. Januar.", "我最早可以 1 月 1 日入职。", {}),
 ("求职", N, "die", "Vollzeit", "", "全职", "Die Stelle ist in Vollzeit.", "这是全职岗位。", {}),
 ("求职", N, "die", "Teilzeit", "", "兼职；非全时", "Ich arbeite 20 Stunden pro Woche in Teilzeit.", "我每周兼职工作 20 小时。", {}),
 ("求职", N, "der", "Werkstudent", "die Werkstudenten", "工读生", "Ich arbeite als Werkstudent bei FIZ Karlsruhe.", "我在 FIZ 卡尔斯鲁厄做工读生。", {}),
 ("求职", N, "das", "Praktikum", "die Praktika", "实习", "Sie hat ein Praktikum bei SAP gemacht.", "她在 SAP 做过实习。", {}),
 ("求职", P, None, "befristet / unbefristet", "", "有期限的 / 无期限的", "Der Vertrag ist auf zwei Jahre befristet.", "合同期限为两年。", {}),
 ("求职", N, "die", "Weiterbildung", "die Weiterbildungen", "进修；培训", "Die Firma bietet viele Weiterbildungen an.", "公司提供很多进修机会。", {}),
 ("求职", N, "die", "Stärke", "die Stärken", "优点；强项", "Was sind Ihre Stärken und Schwächen?", "您的优点和缺点是什么？", {}),
 ("求职", N, "die", "Schwäche", "die Schwächen", "缺点；弱点", "Meine Schwäche ist, dass ich manchmal zu genau bin.", "我的缺点是有时太较真。", {}),
 ("求职", A, None, "teamfähig", "", "有团队精神的", "Wir suchen eine teamfähige Kollegin.", "我们在找一位有团队精神的同事。", {}),
 ("求职", A, None, "belastbar", "", "抗压的", "Sie sollten belastbar und flexibel sein.", "您应当抗压且灵活。", {}),
 ("求职", A, None, "zuverlässig", "", "可靠的", "Er ist ein sehr zuverlässiger Mitarbeiter.", "他是一位非常可靠的员工。", {}),
 ("求职", N, "die", "Verantwortung", "die Verantwortungen", "责任", "In diesem Projekt hatte ich die Verantwortung für das Backend.", "在这个项目里我负责后端。", {"gov": "Verantwortung für + Akk."}),
 ("求职", V, None, "zuständig sein", "", "负责（某事）", "Wer ist für die Bewerbungen zuständig?", "谁负责处理申请？", {"aux": "ist", "p2": "zuständig gewesen", "gov": "zuständig für + Akk."}),
 ("求职", N, "der", "Ansprechpartner", "die Ansprechpartner", "联系人", "Ihr Ansprechpartner ist Herr Schmidt.", "您的联系人是施密特先生。", {}),
 ("求职", P, None, "Mit freundlichen Grüßen", "", "此致敬礼（信尾）", "Mit freundlichen Grüßen, Zilong Yan", "此致敬礼，Zilong Yan", {}),
 ("求职", P, None, "Sehr geehrte Damen und Herren", "", "尊敬的女士们先生们", "Sehr geehrte Damen und Herren, hiermit bewerbe ich mich …", "尊敬的女士们先生们，我特此申请……", {}),
 ("求职", N, "die", "Agentur für Arbeit", "", "联邦劳动局", "Ich habe mich bei der Agentur für Arbeit gemeldet.", "我在劳动局做了登记。", {}),
 ("求职", V, None, "sich arbeitssuchend melden", "", "登记为求职者", "Sie müssen sich drei Monate vorher arbeitssuchend melden.", "您必须提前三个月登记为求职者。", {"aux": "hat", "p2": "gemeldet"}),
 # —— IT 工作 ——
 ("IT", N, "die", "Softwareentwicklung", "", "软件开发", "Ich interessiere mich für Softwareentwicklung.", "我对软件开发感兴趣。", {}),
 ("IT", N, "der", "Entwickler", "die Entwickler", "开发者", "Das Team besteht aus fünf Entwicklern.", "团队由五名开发者组成。", {}),
 ("IT", N, "die", "Anwendung", "die Anwendungen", "应用程序；应用", "Wir entwickeln eine Anwendung für Ärzte.", "我们为医生开发一个应用。", {}),
 ("IT", N, "die", "Schnittstelle", "die Schnittstellen", "接口", "Die Schnittstelle liefert die Daten im JSON-Format.", "该接口以 JSON 格式提供数据。", {}),
 ("IT", N, "die", "Datenbank", "die Datenbanken", "数据库", "Die Daten werden in einer Datenbank gespeichert.", "数据保存在数据库里。", {}),
 ("IT", V, None, "speichern", "", "保存；存储", "Hast du die Datei gespeichert?", "你保存文件了吗？", {"aux": "hat", "p2": "gespeichert"}),
 ("IT", N, "die", "Datei", "die Dateien", "文件", "Ich schicke dir die Datei per E-Mail.", "我把文件用邮件发给你。", {}),
 ("IT", N, "der", "Fehler", "die Fehler", "错误；故障", "Im Code ist ein Fehler.", "代码里有个错误。", {}),
 ("IT", V, None, "beheben", "", "排除；修复", "Wir haben den Fehler schnell behoben.", "我们很快修复了这个错误。", {"aux": "hat", "p2": "behoben"}),
 ("IT", V, None, "umsetzen", "", "实施；实现", "Wir setzen das Projekt in drei Monaten um.", "我们在三个月内实施这个项目。", {"aux": "hat", "p2": "umgesetzt"}),
 ("IT", N, "die", "Umsetzung", "die Umsetzungen", "实施；实现", "Die Umsetzung hat länger gedauert als geplant.", "实施比计划花了更长时间。", {}),
 ("IT", V, None, "entwickeln", "", "开发", "Ich habe ein Tool in Python entwickelt.", "我用 Python 开发了一个工具。", {"aux": "hat", "p2": "entwickelt"}),
 ("IT", N, "die", "Anforderungsanalyse", "die Anforderungsanalysen", "需求分析", "Am Anfang steht die Anforderungsanalyse.", "一开始是需求分析。", {}),
 ("IT", N, "die", "Benutzeroberfläche", "die Benutzeroberflächen", "用户界面", "Die Benutzeroberfläche ist sehr übersichtlich.", "用户界面很清晰。", {}),
 ("IT", N, "der", "Server", "die Server", "服务器", "Der Server läuft wieder.", "服务器又正常运行了。", {}),
 ("IT", N, "die", "Rechenleistung", "", "算力", "Für das Modell braucht man viel Rechenleistung.", "这个模型需要大量算力。", {}),
 ("IT", N, "der", "Wissensgraph", "die Wissensgraphen", "知识图谱", "Wir bauen einen Wissensgraphen aus Forschungsdaten.", "我们用科研数据构建知识图谱。", {}),
 ("IT", N, "die", "Künstliche Intelligenz", "", "人工智能", "Künstliche Intelligenz verändert viele Berufe.", "人工智能正在改变许多职业。", {}),
 ("IT", N, "das", "Sprachmodell", "die Sprachmodelle", "语言模型", "Wir testen verschiedene Sprachmodelle.", "我们在测试不同的语言模型。", {}),
 ("IT", N, "die", "Besprechung", "die Besprechungen", "会议；讨论", "Die Besprechung beginnt um zehn Uhr.", "会议十点开始。", {}),
 ("IT", N, "die", "Rückmeldung", "die Rückmeldungen", "反馈；回复", "Ich freue mich auf Ihre Rückmeldung.", "期待您的回复。", {}),
 ("IT", N, "der", "Ablauf", "die Abläufe", "流程", "Können Sie den Ablauf kurz erklären?", "您能简单解释一下流程吗？", {}),
 ("IT", N, "die", "Aufgabe", "die Aufgaben", "任务；职责", "Zu meinen Aufgaben gehörte das Testen.", "我的职责包括测试。", {}),
 ("IT", N, "die", "Abteilung", "die Abteilungen", "部门", "Ich arbeite in der IT-Abteilung.", "我在 IT 部门工作。", {}),
 ("IT", V, None, "einhalten", "", "遵守（期限等）", "Wir müssen die Frist unbedingt einhalten.", "我们必须严格遵守期限。", {"aux": "hat", "p2": "eingehalten"}),
 ("IT", N, "das", "Homeoffice", "", "居家办公", "Zwei Tage pro Woche arbeite ich im Homeoffice.", "我每周有两天居家办公。", {}),
 # —— 办事 ——
 ("办事", N, "die", "Ausländerbehörde", "die Ausländerbehörden", "外管局", "Ich habe einen Termin bei der Ausländerbehörde.", "我在外管局有个预约。", {}),
 ("办事", N, "der", "Aufenthaltstitel", "die Aufenthaltstitel", "居留许可", "Mein Aufenthaltstitel läuft im Dezember ab.", "我的居留许可 12 月到期。", {}),
 ("办事", N, "die", "Aufenthaltserlaubnis", "die Aufenthaltserlaubnisse", "居留许可", "Ich brauche eine Aufenthaltserlaubnis zur Arbeitssuche.", "我需要一个找工作的居留许可。", {}),
 ("办事", N, "die", "Blaue Karte EU", "", "欧盟蓝卡", "Mit dem Arbeitsvertrag kann ich die Blaue Karte beantragen.", "有了劳动合同我就能申请蓝卡。", {}),
 ("办事", V, None, "beantragen", "", "申请（办理）", "Ich möchte eine Verlängerung beantragen.", "我想申请延期。", {"aux": "hat", "p2": "beantragt"}),
 ("办事", N, "der", "Antrag", "die Anträge", "申请（表）", "Haben Sie den Antrag schon ausgefüllt?", "您已经填好申请表了吗？", {}),
 ("办事", V, None, "verlängern", "", "延长", "Ich muss meinen Pass verlängern lassen.", "我得去延长护照。", {"aux": "hat", "p2": "verlängert"}),
 ("办事", N, "die", "Verlängerung", "die Verlängerungen", "延期", "Die Verlängerung kostet 100 Euro.", "延期费用 100 欧元。", {}),
 ("办事", N, "die", "Anmeldung", "die Anmeldungen", "登记；注册", "Für die Anmeldung brauchen Sie die Wohnungsgeberbestätigung.", "登记户口需要房东确认书。", {}),
 ("办事", V, None, "sich anmelden", "", "登记；报名", "Nach dem Umzug muss man sich innerhalb von zwei Wochen anmelden.", "搬家后必须在两周内登记。", {"aux": "hat", "p2": "angemeldet"}),
 ("办事", N, "das", "Bürgerbüro", "die Bürgerbüros", "市民办事处", "Das Bürgerbüro ist montags geschlossen.", "市民办事处周一关门。", {}),
 ("办事", N, "der", "Termin", "die Termine", "预约；约会", "Online kann man einen Termin vereinbaren.", "可以在网上预约。", {}),
 ("办事", V, None, "vereinbaren", "", "约定；商定", "Wir haben einen Termin für Dienstag vereinbart.", "我们约好了周二。", {"aux": "hat", "p2": "vereinbart"}),
 ("办事", N, "die", "Unterlagen (Pl.)", "", "材料；文件", "Bringen Sie bitte alle Unterlagen mit.", "请带齐所有材料。", {}),
 ("办事", N, "der", "Nachweis", "die Nachweise", "证明", "Sie brauchen einen Nachweis über Ihre Krankenversicherung.", "您需要医保证明。", {}),
 ("办事", N, "die", "Bescheinigung", "die Bescheinigungen", "证明（书）", "Die Uni stellt eine Bescheinigung aus.", "大学会开一份证明。", {}),
 ("办事", N, "die", "Krankenversicherung", "die Krankenversicherungen", "医疗保险", "Die Krankenversicherung ist in Deutschland Pflicht.", "在德国医疗保险是强制的。", {}),
 ("办事", N, "die", "Steuer", "die Steuern", "税", "Wie viel Steuern zahlst du?", "你交多少税？", {}),
 ("办事", N, "die", "Steuer-ID", "", "税号", "Für den Arbeitgeber brauchen Sie Ihre Steuer-ID.", "雇主需要您的税号。", {}),
 ("办事", N, "die", "Steuererklärung", "die Steuererklärungen", "报税", "Ich mache meine Steuererklärung mit einer App.", "我用 App 报税。", {}),
 ("办事", N, "das", "Finanzamt", "die Finanzämter", "税务局", "Das Finanzamt hat mir Geld zurückgezahlt.", "税务局退给我钱了。", {}),
 ("办事", N, "der", "Bescheid", "die Bescheide", "通知；决定书", "Ich habe noch keinen Bescheid bekommen.", "我还没收到通知。", {}),
 ("办事", N, "die", "Frist", "die Fristen", "期限", "Beachten Sie die Frist von vier Wochen.", "请注意四周的期限。", {}),
 ("办事", N, "das", "Formular", "die Formulare", "表格", "Füllen Sie bitte dieses Formular aus.", "请填写这张表格。", {}),
 ("办事", V, None, "ausfüllen", "", "填写", "Ich habe das Formular schon ausgefüllt.", "我已经填好表了。", {"aux": "hat", "p2": "ausgefüllt"}),
 ("办事", V, None, "unterschreiben", "", "签字", "Bitte unterschreiben Sie hier.", "请在这里签字。", {"aux": "hat", "p2": "unterschrieben"}),
 ("办事", N, "die", "Unterschrift", "die Unterschriften", "签名", "Hier fehlt noch Ihre Unterschrift.", "这里还缺您的签名。", {}),
 ("办事", N, "der", "Wohnsitz", "die Wohnsitze", "住所", "Mein Wohnsitz ist in Konstanz.", "我的住所在康斯坦茨。", {}),
 ("办事", N, "die", "Miete", "die Mieten", "房租", "Die Miete ist am Monatsanfang fällig.", "房租在月初到期。", {}),
 ("办事", N, "die", "Kaution", "die Kautionen", "押金", "Die Kaution beträgt drei Monatsmieten.", "押金是三个月的房租。", {}),
 ("办事", N, "der", "Mietvertrag", "die Mietverträge", "租房合同", "Der Mietvertrag ist unbefristet.", "租房合同是无期限的。", {}),
 ("办事", N, "die", "Nebenkosten (Pl.)", "", "杂费（水电暖等）", "Die Nebenkosten sind in der Miete enthalten.", "杂费包含在房租里。", {}),
 ("办事", N, "der", "Rundfunkbeitrag", "", "广播电视费", "Jede Wohnung zahlt den Rundfunkbeitrag.", "每户都要交广播电视费。", {}),
 ("办事", N, "die", "Überweisung", "die Überweisungen", "转账", "Ich habe die Überweisung gestern gemacht.", "我昨天转账了。", {}),
 ("办事", V, None, "überweisen", "", "转账", "Bitte überweisen Sie den Betrag bis Freitag.", "请在周五前转账。", {"aux": "hat", "p2": "überwiesen"}),
 ("办事", N, "das", "Konto", "die Konten", "账户", "Ich möchte ein Konto eröffnen.", "我想开个账户。", {}),
 ("办事", N, "der", "Betrag", "die Beträge", "金额", "Der Betrag wird abgebucht.", "这笔金额会被扣款。", {}),
 ("办事", N, "die", "Rechnung", "die Rechnungen", "账单；发票", "Die Rechnung ist noch nicht bezahlt.", "账单还没付。", {}),
 ("办事", N, "die", "Mahnung", "die Mahnungen", "催款单", "Wenn Sie nicht zahlen, bekommen Sie eine Mahnung.", "如果不付款，您会收到催款单。", {}),
 ("办事", N, "die", "Staatsangehörigkeit", "die Staatsangehörigkeiten", "国籍", "Welche Staatsangehörigkeit haben Sie?", "您是什么国籍？", {}),
 ("办事", N, "die", "Einbürgerung", "die Einbürgerungen", "入籍", "Für die Einbürgerung braucht man Deutsch auf B1-Niveau.", "入籍需要 B1 德语水平。", {}),
]


def main():
    out = []
    seen = set()
    for i, (tag, pos, art, lemma, pl, zh, ex, ex_zh, extra) in enumerate(ROWS):
        if (lemma, tag) in seen:
            continue
        seen.add((lemma, tag))
        e = {"id": f"x{i:03d}", "lv": tag, "kind": "noun" if pos == N else "verb" if pos == V else "other",
             "lemma": lemma, "pos": pos, "zh": zh, "ex": [ex], "ex_zh": ex_zh}
        if art:
            e["art"] = art
        if pl:
            e["pl_full"] = pl
        e.update(extra)
        out.append(e)
    Path(sys.argv[1]).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(out))


main()
