# One-shot generator for the shared JSON spec files. Expected Text/TypeName/
# Resolution values are hand-authored truth; Start/End are derived by locating
# each expected Text in the Input (engine-independent), so the specs can drive
# pytest, xUnit and any future port from the exact same files.
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "specs"

R = lambda v: {"subtype": "integer", "value": v}
RD = lambda v: {"subtype": "decimal", "value": v}
RO = lambda v: {"subtype": "ordinal", "value": v}
PCT = lambda v: {"value": v, "unit": "%"}

def num(text, value, decimal=False, ordinal=False):
    if ordinal:
        return (text, "number", RO(value))
    return (text, "number", RD(value) if decimal else R(value))

def dim(text, value, unit, norm=None, nunit=None):
    res = {"value": value, "unit": unit}
    if norm is not None:
        res["normalizedValue"] = norm
        res["normalizedUnit"] = nunit
    return (text, "dimension", res)

def dur(text, value, unit, norm, nunit="Second"):
    return (text, "duration", {"value": value, "unit": unit, "normalizedValue": norm, "normalizedUnit": nunit})

def cur(text, value, unit, iso):
    return (text, "currency", {"value": value, "unit": unit, "iso": iso})

def temp(text, value, unit, norm):
    return (text, "temperature", {"value": value, "unit": unit, "normalizedValue": norm, "normalizedUnit": "Kelvin"})

def age(text, value):
    return (text, "age", {"value": value, "unit": "Year"})

def dt(text, timex, value):
    return (text, "datetime", {"timex": timex, "value": value})

NUMBER = [
    # ---- English
    ("en", "I have twenty-three apples.", [num("twenty-three", "23")]),
    ("en", "one hundred and twenty three reasons", [num("one hundred and twenty three", "123")]),
    ("en", "two thousand five hundred seats", [num("two thousand five hundred", "2500")]),
    ("en", "a total of 1,234 items and 3.5 liters left", [num("1,234", "1234"), dim("3.5 liters", "3.5", "Liter")]),
    ("en", "temperature dropped to -7 degrees", [num("-7", "-7")]),
    ("en", "she finished 1st and he finished 21st", [num("1st", "1", ordinal=True), num("21st", "21", ordinal=True)]),
    ("en", "the first attempt", [num("first", "1", ordinal=True)]),
    ("en", "chapter 7", [num("7", "7")]),
    ("en", "an unrelated sentence", []),
    ("en", "malformed 1,23 stays out", []),
    ("en", "version v2.0 is not a number", []),
    # ---- German
    ("de", "insgesamt 1.234 Besucher", [num("1.234", "1234")]),
    ("de", "Preis 1.234,56 Euro", [cur("1.234,56 Euro", "1234.56", "Euro", "EUR")]),
    ("de", "dreiundzwanzig Personen", [num("dreiundzwanzig", "23")]),
    ("de", "den 3. Platz", [num("3.", "3", ordinal=True)]),
    ("de", "das erste Mal", [num("erste", "1", ordinal=True)]),
    # ---- French
    ("fr", "1 234 habitants", [num("1 234", "1234")]),
    ("fr", "un total de 1 234,56 euros", [cur("1 234,56 euros", "1234.56", "Euro", "EUR")]),
    ("fr", "quatre-vingt-dix-neuf pages", [num("quatre-vingt-dix-neuf", "99")]),
    ("fr", "vingt et un élèves", [num("vingt et un", "21")]),
    ("fr", "le 1er étage", [num("1er", "1", ordinal=True)]),
    ("fr", "le premier ministre", [num("premier", "1", ordinal=True)]),
    # ---- Spanish
    ("es", "un total de 1.234,56 euros", [cur("1.234,56 euros", "1234.56", "Euro", "EUR")]),
    ("es", "veintiuno", [num("veintiuno", "21")]),
    ("es", "treinta y dos días de plazo", [dur("treinta y dos días", "32", "Dia", "2764800")]),
    ("es", "gana un millón al año", [num("un millón", "1000000")]),
    ("es", "una casa nueva", []),
    ("es", "el primero de la lista", [num("primero", "1", ordinal=True)]),
    # ---- Portuguese
    ("pt", "quarenta e dois anos de serviço", [dur("quarenta e dois anos", "42", "Ano", "1325391984")]),
    ("pt", "quarenta e dois livros", [num("quarenta e dois", "42")]),
    ("pt", "um milhão de reais", [num("um milhão", "1000000")]),
    ("pt", "uma casa nova", []),
    # ---- Italian
    ("it", "1.234,56 in contanti", [num("1.234,56", "1234.56", decimal=True)]),
    ("it", "ventitré persone", [num("ventitré", "23")]),
    ("it", "due mila spettatori", [num("due mila", "2000")]),
    ("it", "il primo posto", [num("primo", "1", ordinal=True)]),
    # ---- Turkish
    ("tr", "1.234,56 ceza", [num("1.234,56", "1234.56", decimal=True)]),
    ("tr", "yirmi beş kişi", [num("yirmi beş", "25")]),
    ("tr", "iki yüz sayfa", [num("iki yüz", "200")]),
    ("tr", "bir ev aldı", []),
    ("tr", "birinci sınıf", [num("birinci", "1", ordinal=True)]),
    # ---- Hindi
    ("hi", "कुल 1,23,456 रुपये", [cur("1,23,456 रुपये", "123456", "Rupee", "INR")]),
    ("hi", "१,२३,४५६ रुपये मिले", [cur("१,२३,४५६ रुपये", "123456", "Rupee", "INR")]),
    ("hi", "पचास किताबें", [num("पचास", "50")]),
    ("hi", "दो सौ रुपये दिए", [cur("दो सौ रुपये", "200", "Rupee", "INR")]),
    ("hi", "तीन हज़ार किताबें", [num("तीन हज़ार", "3000")]),
    # ---- Dutch
    ("nl", "1.234,56 gepind", [num("1.234,56", "1234.56", decimal=True)]),
    ("nl", "tweeëntwintig boeken", [num("tweeëntwintig", "22")]),
    ("nl", "honderd jaar geleden", [dur("honderd jaar", "100", "Jaar", "3155695200")]),
    ("nl", "een huis aan de gracht", []),
    ("nl", "de eerste plaats", [num("eerste", "1", ordinal=True)]),
    # ---- Chinese
    ("zh", "总投资三千五百万元", [cur("三千五百万元", "35000000", "ChineseYuan", "CNY")]),
    ("zh", "增长了三点五个百分点", [num("三点五", "3.5", decimal=True)]),
    ("zh", "销量达3万件", [num("3万", "30000")]),
    ("zh", "第5条条款", [num("第5", "5", ordinal=True)]),
    ("zh", "第三被告", [num("第三", "3", ordinal=True)]),
    ("zh", "位于统一路", []),
    ("zh", "统一意见很重要", []),
]

PERCENTAGE = [
    ("en", "a rise of 15% last year", [("15%", "percentage", PCT("15"))]),
    ("en", "fifty percent of voters", [(("fifty percent"), "percentage", PCT("50"))]),
    ("en", "15 percent more", [(("15 percent"), "percentage", PCT("15"))]),
    ("de", "eine Erhöhung um 15 Prozent", [("15 Prozent", "percentage", PCT("15"))]),
    ("fr", "une hausse de 15 pour cent", [("15 pour cent", "percentage", PCT("15"))]),
    ("es", "un aumento del 15 por ciento", [("15 por ciento", "percentage", PCT("15"))]),
    ("pt", "um aumento de 15 por cento", [("15 por cento", "percentage", PCT("15"))]),
    ("it", "un aumento del 15 per cento", [("15 per cento", "percentage", PCT("15"))]),
    ("tr", "yüzde 15 artış", [("yüzde 15", "percentage", PCT("15"))]),
    ("tr", "zam oranı %30", [("%30", "percentage", PCT("30"))]),
    ("hi", "15 प्रतिशत वृद्धि", [("15 प्रतिशत", "percentage", PCT("15"))]),
    ("hi", "३० प्रतिशत लाभ", [("३० प्रतिशत", "percentage", PCT("30"))]),
    ("nl", "een stijging van 15 procent", [("15 procent", "percentage", PCT("15"))]),
    ("zh", "涨幅为百分之三十", [("百分之三十", "percentage", PCT("30"))]),
    ("zh", "涨幅为30%", [("30%", "percentage", PCT("30"))]),
    ("en", "no ratios in here at all", []),
]

UNIT = [
    # ---- English
    ("en", "the tunnel is 3 km long", [dim("3 km", "3", "Kilometer", "3000", "Meter")]),
    ("en", "a parcel weighing 2.5 kg", [dim("2.5 kg", "2.5", "Kilogram")]),
    ("en", "it was 30 °C outside", [temp("30 °C", "30", "Celsius", "303.15")]),
    ("en", "the fee is $1,200.50", [cur("$1,200.50", "1200.5", "Dollar", "USD")]),
    ("en", "costs 2000 dollars", [cur("2000 dollars", "2000", "Dollar", "USD")]),
    ("en", "my son is 7 years old", [age("7 years old", "7")]),
    ("en", "runs for 30 minutes", [dur("30 minutes", "30", "Minute", "1800")]),
    ("en", "speeding at 60 mph", [dim("60 mph", "60", "MilePerHour", "96.56064", "KilometerPerHour")]),
    ("en", "an area of 100 sq ft", [dim("100 sq ft", "100", "SquareFoot", "9.290304", "SquareMeter")]),
    ("en", "a tank of 4 gallons", [dim("4 gallons", "4", "Gallon", "15.141647136", "Liter")]),
    ("en", "a file of 500 MB", [dim("500 MB", "500", "Megabyte", "500000000", "Byte")]),
    ("en", "rent is ₹2,500 per month", [cur("₹2,500", "2500", "Rupee", "INR")]),
    # ---- German
    ("de", "5 Kilometer entfernt", [dim("5 Kilometer", "5", "Kilometer", "5000", "Meter")]),
    ("de", "dreizehn Kilogramm Gepäck", [dim("dreizehn Kilogramm", "13", "Kilogramm")]),
    ("de", "20 °C im Sommer", [temp("20 °C", "20", "Celsius", "293.15")]),
    ("de", "1.234,56 Euro Gebühr", [cur("1.234,56 Euro", "1234.56", "Euro", "EUR")]),
    ("de", "er ist 3 Jahre alt", [age("3 Jahre alt", "3")]),
    ("de", "zwei Stunden warten", [dur("zwei Stunden", "2", "Stunde", "7200")]),
    # ---- French
    ("fr", "10 kilomètres à pied", [dim("10 kilomètres", "10", "Kilometre", "10000", "Metre")]),
    ("fr", "il fait 25 °C", [temp("25 °C", "25", "Celsius", "298.15")]),
    ("fr", "un enfant de trois ans", [age("trois ans", "3")]),
    ("fr", "5 heures de route", [dur("5 heures", "5", "Heure", "18000")]),
    ("fr", "2 500 euros de loyer", [cur("2 500 euros", "2500", "Euro", "EUR")]),
    # ---- Spanish
    ("es", "10 kilómetros de distancia", [dim("10 kilómetros", "10", "Kilometro", "10000", "Metro")]),
    ("es", "un niño de 5 años de edad", [age("5 años de edad", "5")]),
    ("es", "2 horas de espera", [dur("2 horas", "2", "Hora", "7200")]),
    ("es", "cuesta 5 dólares", [cur("5 dólares", "5", "Dolar", "USD")]),
    # ---- Portuguese
    ("pt", "10 quilômetros de distância", [dim("10 quilômetros", "10", "Quilometro", "10000", "Metro")]),
    ("pt", "uma criança de 5 anos de idade", [age("5 anos de idade", "5")]),
    ("pt", "2 horas de espera", [dur("2 horas", "2", "Hora", "7200")]),
    # ---- Italian
    ("it", "10 chilometri di distanza", [dim("10 chilometri", "10", "Chilometro", "10000", "Metro")]),
    ("it", "un bambino di 5 anni di età", [age("5 anni di età", "5")]),
    ("it", "2 ore di attesa", [dur("2 ore", "2", "Ora", "7200")]),
    # ---- Turkish
    ("tr", "10 kilometre uzaklıkta", [dim("10 kilometre", "10", "Kilometre", "10000", "Metre")]),
    ("tr", "5 yaşında bir çocuk", [age("5 yaşında", "5")]),
    ("tr", "2 saat bekleme", [dur("2 saat", "2", "Saat", "7200")]),
    ("tr", "1.000 lira ceza", [cur("1.000 lira", "1000", "TurkLirasi", "TRY")]),
    # ---- Hindi
    ("hi", "5 किलोमीटर दूर", [dim("5 किलोमीटर", "5", "Kilometer", "5000", "Meter")]),
    ("hi", "१० किलोमीटर दूरी", [dim("१० किलोमीटर", "10", "Kilometer", "10000", "Meter")]),
    ("hi", "बेटी ५ साल की है", [age("५ साल की", "5")]),
    ("hi", "2 घंटे का सफर", [dur("2 घंटे", "2", "Hour", "7200")]),
    ("hi", "कुल ५०० रुपये", [cur("५०० रुपये", "500", "Rupee", "INR")]),
    # ---- Dutch
    ("nl", "10 kilometer verderop", [dim("10 kilometer", "10", "Kilometer", "10000", "Meter")]),
    ("nl", "hij is 3 jaar oud", [age("3 jaar oud", "3")]),
    ("nl", "2 uur wachten", [dur("2 uur", "2", "Uur", "7200")]),
    ("nl", "€25 per dag", [cur("€25", "25", "Euro", "EUR")]),
    # ---- Chinese
    ("zh", "面积约3万平方米", [dim("3万平方米", "30000", "SquareMeter")]),
    ("zh", "限速60公里", [dim("60公里", "60", "Kilometer", "60000", "Meter")]),
    ("zh", "气温30摄氏度", [temp("30摄氏度", "30", "Celsius", "303.15")]),
    ("zh", "租金500元", [cur("500元", "500", "ChineseYuan", "CNY")]),
    ("zh", "租期12个月", [dur("12个月", "12", "Month", "31556952")]),
    ("zh", "他花了十分钟", [dur("十分钟", "10", "Minute", "600")]),
    ("zh", "他今年三十岁", [age("三十岁", "30")]),
    ("zh", "面积5亩", [dim("5亩", "5", "Mu", "3333.3333333333", "SquareMeter")]),
]

# reference instant: 2026-08-22T12:00:00 (Saturday); weeks start Monday
DATETIME = [
    # ---- English (MDY)
    ("en", "due on 05/22/2026", [dt("05/22/2026", "2026-05-22", "2026-05-22T00:00:00")]),
    ("en", "on August 22, 2026 at 3pm", [dt("August 22, 2026 at 3pm", "2026-08-22T15:00", "2026-08-22T15:00:00")]),
    ("en", "signed 22 August 2026", [dt("22 August 2026", "2026-08-22", "2026-08-22T00:00:00")]),
    ("en", "deadline March 1st, 2026", [dt("March 1st, 2026", "2026-03-01", "2026-03-01T00:00:00")]),
    ("en", "meeting on Jan 5", [dt("Jan 5", "XXXX-01-05", "2026-01-05T00:00:00")]),
    ("en", "arrives at 14:30", [dt("14:30", "T14:30", "2026-08-22T14:30:00")]),
    ("en", "see you tomorrow", [dt("tomorrow", "2026-08-23", "2026-08-23T00:00:00")]),
    ("en", "we met yesterday", [dt("yesterday", "2026-08-21", "2026-08-21T00:00:00")]),
    ("en", "the filing is due Monday", [dt("Monday", "2026-08-17", "2026-08-17T00:00:00")]),
    ("en", "as of 2026-08-22", [dt("2026-08-22", "2026-08-22", "2026-08-22T00:00:00")]),
    # ---- German (DMY)
    ("de", "gültig ab 22.08.2026", [dt("22.08.2026", "2026-08-22", "2026-08-22T00:00:00")]),
    ("de", "ab dem 5. Januar 2026 um 14:30", [dt("5. Januar 2026 um 14:30", "2026-01-05T14:30", "2026-01-05T14:30:00")]),
    ("de", "heute ist Freitag", [dt("heute", "2026-08-22", "2026-08-22T00:00:00"), dt("Freitag", "2026-08-21", "2026-08-21T00:00:00")]),
    ("de", "um 14 Uhr", [dt("14 Uhr", "T14:00", "2026-08-22T14:00:00")]),
    ("de", "am Montag", [dt("Montag", "2026-08-17", "2026-08-17T00:00:00")]),
    # ---- French (DMY)
    ("fr", "signé le 22/08/2026", [dt("22/08/2026", "2026-08-22", "2026-08-22T00:00:00")]),
    ("fr", "du 5 janvier 2026 à 14h30", [dt("5 janvier 2026 à 14h30", "2026-01-05T14:30", "2026-01-05T14:30:00")]),
    ("fr", "réunion à 2 h 30 du matin", [dt("2 h 30 du matin", "T02:30", "2026-08-22T02:30:00")]),
    ("fr", "aujourd'hui", [dt("aujourd'hui", "2026-08-22", "2026-08-22T00:00:00")]),
    # ---- Spanish (DMY)
    ("es", "desde el 22/08/2026", [dt("22/08/2026", "2026-08-22", "2026-08-22T00:00:00")]),
    ("es", "el 5 de enero de 2026 a las 3 de la tarde", [dt("5 de enero de 2026 a las 3 de la tarde", "2026-01-05T15:00", "2026-01-05T15:00:00")]),
    ("es", "hoy no hay audiencia", [dt("hoy", "2026-08-22", "2026-08-22T00:00:00")]),
    ("es", "hasta mañana", [dt("mañana", "2026-08-23", "2026-08-23T00:00:00")]),
    # ---- Portuguese (DMY)
    ("pt", "desde 22/08/2026", [dt("22/08/2026", "2026-08-22", "2026-08-22T00:00:00")]),
    ("pt", "5 de janeiro de 2026 às 14:30", [dt("5 de janeiro de 2026 às 14:30", "2026-01-05T14:30", "2026-01-05T14:30:00")]),
    ("pt", "hoje", [dt("hoje", "2026-08-22", "2026-08-22T00:00:00")]),
    # ---- Italian (DMY)
    ("it", "dal 22/08/2026", [dt("22/08/2026", "2026-08-22", "2026-08-22T00:00:00")]),
    ("it", "il 5 gennaio 2026 alle 14:30", [dt("5 gennaio 2026 alle 14:30", "2026-01-05T14:30", "2026-01-05T14:30:00")]),
    ("it", "oggi", [dt("oggi", "2026-08-22", "2026-08-22T00:00:00")]),
    # ---- Turkish (DMY)
    ("tr", "22.08.2026 tarihinde", [dt("22.08.2026", "2026-08-22", "2026-08-22T00:00:00")]),
    ("tr", "5 Ocak 2026 saat 14:30", [dt("5 Ocak 2026 saat 14:30", "2026-01-05T14:30", "2026-01-05T14:30:00")]),
    ("tr", "yarın mahkeme", [dt("yarın", "2026-08-23", "2026-08-23T00:00:00")]),
    ("tr", "bugün", [dt("bugün", "2026-08-22", "2026-08-22T00:00:00")]),
    # ---- Hindi (DMY, Devanagari digits)
    ("hi", "22/08/2026 से", [dt("22/08/2026", "2026-08-22", "2026-08-22T00:00:00")]),
    ("hi", "५ जनवरी २०२६ को", [dt("५ जनवरी २०२६", "2026-01-05", "2026-01-05T00:00:00")]),
    ("hi", "शाम 3 बजे मीटिंग", [dt("शाम 3 बजे", "T15:00", "2026-08-22T15:00:00")]),
    ("hi", "आज छुट्टी है", [dt("आज", "2026-08-22", "2026-08-22T00:00:00")]),
    ("hi", "सोमवार को सुनवाई", [dt("सोमवार", "2026-08-17", "2026-08-17T00:00:00")]),
    # ---- Dutch (DMY)
    ("nl", " geldig vanaf 22-08-2026", [dt("22-08-2026", "2026-08-22", "2026-08-22T00:00:00")]),
    ("nl", "op 5 januari 2026 om 14.30 uur", [dt("5 januari 2026 om 14.30", "2026-01-05T14:30", "2026-01-05T14:30:00")]),
    ("nl", "vandaag", [dt("vandaag", "2026-08-22", "2026-08-22T00:00:00")]),
    ("nl", "morgen", [dt("morgen", "2026-08-23", "2026-08-23T00:00:00")]),
    # ---- Chinese (YMD)
    ("zh", "2026年8月22日开庭", [dt("2026年8月22日", "2026-08-22", "2026-08-22T00:00:00")]),
    ("zh", "8月22日截止", [dt("8月22日", "XXXX-08-22", "2026-08-22T00:00:00")]),
    ("zh", "2026年1月5日下午3点提交", [dt("2026年1月5日下午3点", "2026-01-05T15:00", "2026-01-05T15:00:00")]),
    ("zh", "今天休息", [dt("今天", "2026-08-22", "2026-08-22T00:00:00")]),
    ("zh", "明天见", [dt("明天", "2026-08-23", "2026-08-23T00:00:00")]),
    ("zh", "星期一开庭", [dt("星期一", "2026-08-17", "2026-08-17T00:00:00")]),
    ("zh", "下午3点30分开始", [dt("下午3点30分", "T15:30", "2026-08-22T15:30:00")]),
    # ---- negatives
    ("en", "no dates around here", []),
    ("en", "the ratio 24/7 is not a date", [num("24", "24")]),
]


def build_entries(cases):
    entries = []
    for culture, inp, expected in cases:
        results = []
        cursor = 0
        for exp in expected:
            text, type_name, resolution = exp
            idx = inp.find(text, cursor)
            if idx < 0:
                raise SystemExit(f"SPEC BUG: {culture!r} cannot locate {text!r} in {inp!r}")
            cursor = idx + len(text)
            results.append({
                "Text": text, "TypeName": type_name, "Start": idx,
                "End": idx + len(text) - 1, "Resolution": resolution,
            })
        results.sort(key=lambda r: r["Start"])
        entries.append({"Culture": culture, "Input": inp, "Results": results})
    return entries


for fname, cases in [("Number", NUMBER), ("Percentage", PERCENTAGE), ("Unit", UNIT), ("DateTime", DATETIME)]:
    path = OUT / f"{fname}.json"
    path.write_text(json.dumps(build_entries(cases), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path}: {len(cases)} cases")
