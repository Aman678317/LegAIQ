using System.Globalization;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using RxMatch = System.Text.RegularExpressions.Match;

namespace Inga.Recognizers.Text;

/// <summary>Extracts cardinal and ordinal numbers.
/// Digit numbers honor per-culture decimal marks, group separators and
/// grouping style (western 1,234,567 vs Indian 1,23,45,678). Word numbers
/// come from a per-culture atom/scale table composed with a sequence
/// algorithm. Chinese additionally supports hanzi numerals (三千五百)
/// and digit-hanzi mixes (3万).</summary>
internal sealed class NumberFamily
{
    public const string TypeName = "number";
    public const int Priority = 80;

    private static readonly Dictionary<char, char> DevanagariDigits = new()
    {
        ['०'] = '0', ['१'] = '1', ['२'] = '2', ['३'] = '3', ['४'] = '4',
        ['५'] = '5', ['६'] = '6', ['७'] = '7', ['८'] = '8', ['९'] = '9',
    };

    public const string ZhNumeralChars = "〇零一二三四五六七八九两十百千万萬亿億壹贰叁肆伍陆柒捌玖拾佰仟";

    // hanzi allowed to directly follow a numeral run (unit starters like 天/岁);
    // other following hanzi mean the run is part of a longer word (统一, 一下)
    private static readonly HashSet<char> ZhRightOk = new("天周岁个月次倍元亩万億亿點点".ToCharArray());

    private static readonly Dictionary<char, long> ZhValue = new()
    {
        ['〇'] = 0, ['零'] = 0, ['一'] = 1, ['二'] = 2, ['两'] = 2, ['三'] = 3,
        ['四'] = 4, ['五'] = 5, ['六'] = 6, ['七'] = 7, ['八'] = 8, ['九'] = 9,
        ['十'] = 10, ['百'] = 100, ['千'] = 1000, ['万'] = 10000, ['萬'] = 10000,
        ['亿'] = 100000000, ['億'] = 100000000, ['壹'] = 1, ['贰'] = 2, ['叁'] = 3,
        ['肆'] = 4, ['伍'] = 5, ['陆'] = 6, ['柒'] = 7, ['捌'] = 8, ['玖'] = 9,
        ['拾'] = 10, ['佰'] = 100, ['仟'] = 1000,
    };

    private static readonly HashSet<char> ZhScale = new() { '十', '拾', '百', '佰', '千', '仟' };

    private readonly string _cultureKey;
    private readonly JsonElement _num;
    private readonly string _decimal;
    private readonly string _group;
    private readonly Regex _digitRe;
    private Regex? _tokenRe;
    private Regex? _ordinalDigitRe;
    private Regex? _zhRunRe;
    private Regex? _zhMixedRe;
    private Regex? _zhOrdinalRe;
    private readonly bool _isZh;
    private readonly Dictionary<string, long> _wordValues = new();
    private readonly List<string> _negativeWords = new();
    private readonly List<string> _connectors = new();
    private readonly HashSet<string> _articleNumerals = new();
    private readonly Dictionary<string, long> _ordinalWords = new();
    private static readonly Regex AdjacentGap = new(@"^[\s\-]*$", RegexOptions.Compiled);

    public NumberFamily(string cultureKey, JsonDocument cfg)
    {
        _cultureKey = cultureKey;
        _num = cfg.Section("number");
        _decimal = _num.GetString("decimalMark", ".");
        _group = _num.GetString("groupMark", ",");
        _isZh = cultureKey is "zh" or "zh-cn" or "zh-tw";

        // single-char currency symbols, degree sign and % may precede a
        // number ("$1,200.50", "30°C", Turkish "%30")
        var extra = "°%";
        foreach (var e in cfg.Section("currency").Entries())
            foreach (var s in e.GetStrings("symbols"))
                if (s.Length == 1 && !extra.Contains(s)) extra += Regex.Escape(s);

        _digitRe = BuildDigitRegex(_num, extra, _isZh);
        CompileWords();
        CompileZh();
    }

    public static string TranslateDigits(string text, string culture)
    {
        if (culture != "hi") return text;
        var sb = new StringBuilder(text.Length);
        foreach (var ch in text) sb.Append(DevanagariDigits.TryGetValue(ch, out var d) ? d : ch);
        return sb.ToString();
    }

    private static Regex BuildDigitRegex(JsonElement num, string extraLeft, bool zhStyle)
    {
        var d = Regex.Escape(num.GetString("decimalMark", "."));
        var g = Regex.Escape(num.GetString("groupMark", ","));
        var grouping = num.GetString("grouping", "western");
        string grouped = grouping == "indian"
            ? $@"\d{{1,2}}(?:{g}\d{{2}})*{g}\d{{3}}"
            : num.GetBool("spaceGroup")
                ? $@"\d{{1,3}}(?:[{g}\u00a0 ]\d{{3}})+"
                : $@"\d{{1,3}}(?:{g}\d{{3}})+";
        var dec = $@"{d}\d+";
        var core = $@"(?:{grouped}(?:{dec})?|\d+{dec}|\d+)";
        // Sign only binds when clearly standalone (start, whitespace, bracket);
        // guards stop the matcher inside "5-3", "1.5", "1,23", "v2.0".
        // zh_style relaxes the left guard: Chinese glues digits to hanzi
        // ("租金为1,234元") without word boundaries.
        var left = zhStyle
            ? @"(?:^|(?<=[^\d.,;:A-Za-z%]))"
            : $@"(?:^|(?<=[\s(\[{extraLeft}]))";
        return new Regex($@"{left}([-+])?{core}(?!\d)(?![{d}{g}]\d)", RegexOptions.Compiled);
    }

    private (string value, bool isDecimal) ParseDigitValue(string raw)
    {
        var body = raw;
        var negative = body.StartsWith('-');
        if (body.Length > 0 && (body[0] == '+' || body[0] == '-')) body = body.Substring(1);
        if (_num.GetBool("spaceGroup"))
        {
            var sepClass = $"[{Regex.Escape(_group)}\\u00a0 ]";
            body = Regex.Replace(body, $"{sepClass}(?=\\d{{3}}(?!\\d))", "");
        }
        var isDecimal = body.Contains(_decimal);
        var sepRemove = _num.GetBool("spaceGroup")
            ? new Regex($"[{Regex.Escape(_group)}\\u00a0 ]")
            : new Regex(Regex.Escape(_group));
        body = sepRemove.Replace(body, "");
        var parts = body.Split(new[] { _decimal }, 2, StringSplitOptions.None);
        var intPart = parts[0];
        var fracPart = parts.Length > 1 ? parts[1] : "";
        var intNorm = NormalizeInt(intPart);
        string value;
        if (isDecimal)
        {
            var fracNorm = fracPart.TrimEnd('0');
            value = fracNorm.Length > 0 ? $"{intNorm}.{fracNorm}" : intNorm;
        }
        else
        {
            value = intNorm;
        }
        if (negative && value != "0") value = "-" + value;
        return (value, isDecimal);
    }

    private static string NormalizeInt(string intPart)
    {
        if (intPart.Length == 0) return "0";
        if (long.TryParse(intPart, NumberStyles.Integer, CultureInfo.InvariantCulture, out var n))
            return n.ToString(CultureInfo.InvariantCulture);
        var t = intPart.TrimStart('0');
        return t.Length == 0 ? "0" : t;
    }

    internal static long ZhNumeralValue(string chars)
    {
        long total = 0, section = 0, current = 0;
        foreach (var ch in chars)
        {
            var v = ZhValue[ch];
            if (v is 10000 or 100000000)
            {
                section = (section + current) * v;
                total += section;
                section = 0; current = 0;
            }
            else if (ZhScale.Contains(ch))
            {
                if (current == 0) current = 1;
                section += current * ZhValue[ch];
                current = 0;
            }
            else current = v;
        }
        return total + section + current;
    }

    private void CompileWords()
    {
        _ordinalDigitRe = null;
        foreach (var kv in _num.GetWordMap("atoms")) _wordValues[kv.Key] = kv.Value;
        foreach (var kv in _num.GetWordMap("scales")) _wordValues[kv.Key] = kv.Value;
        _negativeWords.AddRange(_num.GetStrings("negativeWords"));
        _connectors.AddRange(_num.GetStrings("connectors"));
        _articleNumerals.UnionWith(_num.GetStrings("articleNumerals"));
        foreach (var kv in _num.GetWordMap("ordinalWords")) _ordinalWords[kv.Key] = kv.Value;

        var vocab = new HashSet<string>(_wordValues.Keys);
        vocab.UnionWith(_negativeWords);
        vocab.UnionWith(_connectors);
        vocab.UnionWith(_ordinalWords.Keys);
        if (vocab.Count == 0) { _tokenRe = null; return; }

        var (pre, post) = RegexBuilder.WordBoundaries(_cultureKey);
        _tokenRe = new Regex($@"{pre}(?:{RegexBuilder.Alt(vocab)}){post}",
            RegexOptions.Compiled | RegexOptions.IgnoreCase);

        var suffixes = _num.GetStrings("ordinalSuffixes");
        if (suffixes.Count > 0)
        {
            var altS = RegexBuilder.Alt(suffixes);
            var body = suffixes.Any(s => s.Trim() == ".")
                // Bare-dot ordinals (de/tr "1.") must not swallow decimals
                // or the leading day of "5. Januar" (datetime wins by priority).
                ? $@"(?<![\w.])(\d+)(?:{altS}|\.)(?!\d)"
                : $@"(?<![\w])(\d+)(?:{altS})(?![A-Za-z])";
            _ordinalDigitRe = new Regex(body, RegexOptions.Compiled);
        }
    }

    private void CompileZh()
    {
        if (!_isZh) return;
        _zhRunRe = new Regex($@"[{ZhNumeralChars}]+(?:点[{ZhNumeralChars}]+)?", RegexOptions.Compiled);
        _zhMixedRe = new Regex(@"(\d+(?:\.\d+)?)([万亿萬億])", RegexOptions.Compiled);
        _zhOrdinalRe = new Regex($@"第(\d+|[{ZhNumeralChars}]+)", RegexOptions.Compiled);
    }

    private static bool IsHanzi(char ch) => ch >= '\u4e00' && ch <= '\u9fff';

    public List<Match> Extract(string text)
    {
        var results = new List<Match>();
        results.AddRange(ExtractDigitNumbers(text));
        results.AddRange(ExtractWordNumbers(text));
        results.AddRange(ExtractOrdinals(text));
        if (_isZh)
        {
            results.AddRange(ExtractZhNumerals(text));
            results.AddRange(ExtractZhMixed(text));
        }
        return results;
    }

    private List<Match> ExtractDigitNumbers(string text)
    {
        var results = new List<Match>();
        foreach (RxMatch m in _digitRe.Matches(text))
        {
            var raw = m.Value.TrimStart(' ', '(', '[');
            var (value, isDecimal) = ParseDigitValue(raw);
            results.Add(new Match
            {
                Text = raw, Start = m.Index, End = m.Index + raw.Length - 1,
                TypeName = TypeName, Priority = Priority,
                Resolution = { ["subtype"] = isDecimal ? "decimal" : "integer", ["value"] = value },
            });
        }
        return results;
    }

    private List<Match> ExtractWordNumbers(string text)
    {
        var results = new List<Match>();
        if (_tokenRe is null) return results;
        var tokens = new List<RxMatch>();
        foreach (System.Text.RegularExpressions.Match t in _tokenRe.Matches(text)) tokens.Add(t);
        int i = 0;
        while (i < tokens.Count)
        {
            var runStart = i;
            var negative = false;
            var firstWord = tokens[i].Value.ToLowerInvariant();
            if (_negativeWords.Contains(firstWord))
            {
                negative = true;
                i += 1;
                if (i >= tokens.Count) { i = runStart + 1; continue; }
            }
            var values = new List<long>();
            var spans = new List<RxMatch>();
            int j = i;
            int? lastEnd = null;
            while (j < tokens.Count)
            {
                var word = tokens[j].Value.ToLowerInvariant();
                if (_wordValues.TryGetValue(word, out var v))
                {
                    if (lastEnd.HasValue)
                    {
                        // only continue the run when tokens are adjacent
                        // ("twenty-three"); a long gap means unrelated words
                        // ("un 15 ... ciento")
                        var gap = text.Substring(lastEnd.Value, tokens[j].Index - lastEnd.Value);
                        if (!AdjacentGap.IsMatch(gap)) break;
                    }
                    values.Add(v);
                    spans.Add(tokens[j]);
                    lastEnd = tokens[j].Index + tokens[j].Length;
                    j += 1;
                    continue;
                }
                // one connector ("and"/"y"/"e") may sit between value words
                if (_connectors.Contains(word) && lastEnd.HasValue
                    && j + 1 < tokens.Count
                    && _wordValues.ContainsKey(tokens[j + 1].Value.ToLowerInvariant()))
                {
                    var g1 = text.Substring(lastEnd.Value, tokens[j].Index - lastEnd.Value);
                    var g2 = text.Substring(tokens[j].Index + tokens[j].Length,
                        tokens[j + 1].Index - (tokens[j].Index + tokens[j].Length));
                    if (AdjacentGap.IsMatch(g1) && AdjacentGap.IsMatch(g2))
                    {
                        lastEnd = tokens[j].Index + tokens[j].Length;
                        j += 1;
                        continue;
                    }
                }
                break;
            }
            var singleArticle = values.Count == 1
                && _articleNumerals.Contains(spans[0].Value.ToLowerInvariant());
            if (values.Count > 0 && !singleArticle)
            {
                long value = Compose(values);
                if (negative) value = -value;
                results.Add(new Match
                {
                    Text = text.Substring(spans[0].Index, spans[^1].Index + spans[^1].Length - spans[0].Index),
                    Start = spans[0].Index,
                    End = spans[^1].Index + spans[^1].Length - 1,
                    TypeName = TypeName, Priority = Priority,
                    Resolution = { ["subtype"] = "integer", ["value"] = value.ToString(CultureInfo.InvariantCulture) },
                });
                i = j;
            }
            else
            {
                i = runStart + 1;
            }
        }
        return results;
    }

    internal static long Compose(IReadOnlyList<long> values)
    {
        long total = 0, current = 0;
        foreach (var v in values)
        {
            if (v >= 1000) { total += (current == 0 ? 1 : current) * v; current = 0; }
            else if (v >= 100) current = current < 100 ? (current == 0 ? 1 : current) * v : current + v;
            else current += v;
        }
        return total + current;
    }

    private List<Match> ExtractOrdinals(string text)
    {
        var results = new List<Match>();
        if (_ordinalDigitRe is not null)
        {
            foreach (RxMatch m in _ordinalDigitRe.Matches(text))
            {
                results.Add(new Match
                {
                    Text = m.Value, Start = m.Index, End = m.Index + m.Length - 1,
                    TypeName = TypeName, Priority = Priority,
                    Resolution = { ["subtype"] = "ordinal", ["value"] = m.Groups[1].Value },
                });
            }
        }
        if (_ordinalWords.Count > 0)
        {
            var (pre, post) = RegexBuilder.WordBoundaries(_cultureKey);
            var re = new Regex($@"{pre}(?:{RegexBuilder.Alt(_ordinalWords.Keys)}){post}",
                RegexOptions.IgnoreCase);
            foreach (RxMatch m in re.Matches(text))
            {
                results.Add(new Match
                {
                    Text = m.Value, Start = m.Index, End = m.Index + m.Length - 1,
                    TypeName = TypeName, Priority = Priority,
                    Resolution =
                    {
                        ["subtype"] = "ordinal",
                        ["value"] = _ordinalWords[m.Value.ToLowerInvariant()].ToString(CultureInfo.InvariantCulture),
                    },
                });
            }
        }
        if (_isZh && _zhOrdinalRe is not null)
        {
            foreach (RxMatch m in _zhOrdinalRe.Matches(text))
            {
                var body = m.Groups[1].Value;
                var value = body.All(char.IsDigit)
                    ? NormalizeInt(body)
                    : ZhNumeralValue(body).ToString(CultureInfo.InvariantCulture);
                results.Add(new Match
                {
                    Text = m.Value, Start = m.Index, End = m.Index + m.Length - 1,
                    TypeName = TypeName, Priority = Priority,
                    Resolution = { ["subtype"] = "ordinal", ["value"] = value },
                });
            }
        }
        return results;
    }

    private List<Match> ExtractZhNumerals(string text)
    {
        var results = new List<Match>();
        if (_zhRunRe is null) return results;
        foreach (RxMatch m in _zhRunRe.Matches(text))
        {
            var s = m.Index;
            var e = m.Index + m.Length;
            var raw = m.Value;
            if (raw == "万一") continue; // adverb, never a number
            var nxt = e < text.Length ? text[e].ToString() : "";
            var isMinutes = text.Substring(e, Math.Min(2, text.Length - e)) == "分钟";
            // "十分钟" is a duration; bare "十分" is the adverb "very"
            if (nxt == "分" && !isMinutes) continue;
            // a single hanzi numeral directly after another hanzi is usually
            // part of a word (统一, 一下); longer runs are legitimate (今年三十岁)
            if (s > 0 && IsHanzi(text[s - 1]) && raw.Length < 2 && !isMinutes) continue;
            if (nxt.Length > 0 && IsHanzi(nxt[0]) && !ZhRightOk.Contains(nxt[0]) && nxt != "分") continue;

            string value;
            string subtype;
            if (raw.Contains('点'))
            {
                var halves = raw.Split('点', 2);
                var intVal = halves[0].Length > 0 ? ZhNumeralValue(halves[0]) : 0;
                var fracDigits = new StringBuilder();
                foreach (var c in halves[1]) fracDigits.Append(ZhValue[c]);
                value = ($"{intVal}.{fracDigits}").TrimEnd('0').TrimEnd('.');
                subtype = "decimal";
            }
            else
            {
                value = ZhNumeralValue(raw).ToString(CultureInfo.InvariantCulture);
                subtype = "integer";
            }
            if ((value is "" or "0") && raw is not ("零" or "〇")) continue;
            results.Add(new Match
            {
                Text = raw, Start = s, End = e - 1,
                TypeName = TypeName, Priority = Priority,
                Resolution = { ["subtype"] = subtype, ["value"] = value },
            });
        }
        return results;
    }

    private List<Match> ExtractZhMixed(string text)
    {
        var results = new List<Match>();
        if (_zhMixedRe is null) return results;
        foreach (RxMatch m in _zhMixedRe.Matches(text))
        {
            var num = double.Parse(m.Groups[1].Value, CultureInfo.InvariantCulture);
            var scale = ZhValue[m.Groups[2].Value[0]];
            results.Add(new Match
            {
                Text = m.Value, Start = m.Index, End = m.Index + m.Length - 1,
                TypeName = TypeName, Priority = Priority,
                Resolution =
                {
                    ["subtype"] = "integer",
                    ["value"] = RegexBuilder.FormatNumber(num * scale),
                },
            });
        }
        return results;
    }
}
