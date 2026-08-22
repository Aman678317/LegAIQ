# Inga Recognizers Text

Multilingual recognition of **numbers, percentages, units (dimension,
currency, temperature, age, duration), dates and times** from plain text,
with clean normalized results.

First-class cultures: **English, Chinese, French, Spanish, Portuguese,
German, Italian, Turkish, Hindi, Dutch**. Any other culture code falls
back to English behavior instead of failing.

The design is deliberately friendly to the other language versions in
this repo: one shared **culture data** directory and one shared **JSON
spec suite** drive every port, so the .NET, Python (and future
TypeScript) implementations stay in behavioral lockstep.

```
text_recognizer/
├── cultures/           # single source of truth: per-language definitions
├── specs/              # shared test specs (drive pytest AND xUnit)
├── dotnet/             # C#/.NET library + xUnit tests  (primary)
├── python/             # Python port + pytest tests
└── tools/              # one-shot generators for cultures/specs
```

## Quick start (.NET)

```bash
cd text_recognizer/dotnet
dotnet test                     # runs the 185-case spec suite
```

Reference the `Inga.Recognizers.Text` project (or the packed
`Inga.Recognizers.Text` NuGet package) and:

```csharp
using Inga.Recognizers.Text;

var results = Recognizers.Recognize(
    "Rent is $1,200.50 for 12 months from March 1st, 2026 at 3pm",
    culture: "en",
    reference: new DateTime(2026, 8, 22, 12, 0, 0));

foreach (var r in results)
    Console.WriteLine($"{r.TypeName,-12} {r.Text,-28} {r.Start}..{r.End}");
// currency     $1,200.50                   8..16   {value:1200.5, unit:Dollar, iso:USD}
// duration     12 months                   22..30  {value:12, unit:Month, normalizedValue:31556952, normalizedUnit:Second}
// datetime     March 1st, 2026 at 3pm      37..58  {timex:2026-03-01T15:00, value:2026-03-01T15:00:00}
```

Pass `types: new[] { "number", "percentage" }` to restrict output, and
`reference:` to pin relative date resolution ("today", "tomorrow",
weekdays) for deterministic results.

## Quick start (Python)

```bash
cd text_recognizer/python
python -m pytest          # runs the 189-case suite (180 spec + engine tests)
```

```python
from datetime import datetime
from inga_recognizers import recognize

results = recognize(
    "Rent is $1,200.50 for 12 months from March 1st, 2026 at 3pm",
    "en",
    reference=datetime(2026, 8, 22, 12, 0, 0),
)
for r in results:
    print(r["TypeName"], r["Text"], r["Resolution"])
```

## What gets recognized

| TypeName | Examples (per culture) | Resolution |
|---|---|---|
| `number` | `1,234.56` · `1.234,56` (de) · `1 234,56` (fr) · `1,23,456` (hi) · `twenty-three` · `dreiundzwanzig` · `三千五百万` · `3万` · `1st / 1er / 1. / 第5` (ordinals) | `subtype` (integer/decimal/ordinal), `value` |
| `percentage` | `15%` · `15 Prozent` · `15 pour cent` · `15 por ciento` · `yüzde 15` / `%30` (tr) · `15 प्रतिशत` · `百分之三十` | `value`, `unit: %` |
| `dimension` | `3 km` → `3000 Meter` · `2.5 kg` · `100 sq ft` · `60 mph` → `96.56064 KilometerPerHour` | `value`, `unit`, `normalizedValue`, `normalizedUnit` |
| `duration` | `30 minutes` → `1800 Second` · `2 Stunden` · `2 uur` · `12个月` | `value`, `unit`, `normalizedValue` (seconds), `normalizedUnit` |
| `currency` | `$1,200.50` · `1.234,56 Euro` · `₹2,500` · `500元` | `value`, `unit`, `iso` |
| `temperature` | `30 °C` → `303.15 Kelvin` · `30摄氏度` | `value`, `unit`, `normalizedValue` (Kelvin), `normalizedUnit` |
| `age` | `7 years old` · `3 Jahre alt` · `3 años de edad` · `三十岁` | `value`, `unit: Year` |
| `datetime` | `05/22/2026` (MDY) / `22.08.2026` (DMY) / `2026年8月22日` · `August 22, 2026 at 3pm` · `14h30` · `下午3点30分` · `शाम 3 बजे` · `today/tomorrow/Monday` | `timex` (language-independent), `value` (resolved ISO) |

Normalization guarantees:

- Culture-correct decimal/group marks; German `1.234,56` and English
  `1,234.56` both normalize to `1234.56`. Hindi uses Indian grouping
  (`1,23,456` → `123456`) and Devanagari digits (`१२३` → `123`, with the
  original text preserved in `Text`).
- Dimensions and durations convert to the category base unit; temperatures
  convert to Kelvin (including the Fahrenheit offset); currencies report
  an ISO 4217 code.
- Date/times expose a TIMEX-style normalization plus a concrete ISO value
  resolved against the reference instant. Weekdays resolve to their date in
  the reference week (Monday-start); dates without a year use the
  reference year (`XXXX-05-01` in timex).
- Overlap resolution is deterministic: a number contained in a recognized
  percentage/unit/currency/date is never double-reported.

## Design notes & porting

- **Cultures are data, not code.** `cultures/<code>.json` describes decimal
  marks, number words, unit tables, month/weekday names, relative-day words,
  am/pm tokens, date orders and connectors. Both implementations compile
  these into regexes at load time and cache them per culture.
- **Specs are shared.** `specs/*.json` cases (`Culture`, `Input`, expected
  `Results` with `Text`/`TypeName`/`Start`/`End`/`Resolution`) assert the
  FULL pipeline output. The same files are consumed by
  `python/tests/test_specs.py` and `dotnet/tests/.../SpecTests.cs`, which is
  how cross-port parity is enforced (185 xUnit + 189 pytest tests).
- **Adding a language** = add `cultures/<code>.json` (copy an existing file
  as a template) plus spec cases; both ports pick it up with no code
  changes. Regenerate `de`/`nl` compound number words with
  `tools/gen_cultures.py` if needed.
- **Adding a port** (e.g. TypeScript for the frontend): read `cultures/`
  and `specs/` and mirror `python/inga_recognizers` — the family pipeline is
  number → (percentage, age, temperature, currency, dimension, duration,
  datetime) → overlap resolution by priority.

### Known scope limits

- Date/time ranges, seasons, holidays and currency names with connecting
  words (`un millón de euros`) are not matched.
- German/Dutch compound hundreds (`zweihundertfünfzig`) are not composed;
  use digits or the 0–99 word forms. Written Hindi compounds beyond the
  atom table (इक्कीस) are not matched.
- Locale variants: `es`/`pt` use Spain-style `1.234,56` numbers;
  `en` uses US-style month-day-year dates.
- The Python package loads `../cultures` relative to the module (override
  with `INGA_RECOGNIZERS_CULTURES`); the .NET library embeds the same
  files as assembly resources.
