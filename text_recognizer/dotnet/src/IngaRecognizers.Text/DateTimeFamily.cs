using System.Globalization;
using System.Text.Json;
using System.Text.RegularExpressions;
using RxMatch = System.Text.RegularExpressions.Match;

namespace Inga.Recognizers.Text;

internal readonly record struct DateHit(int Start, int End, int? Year, int Month, int Day);

internal readonly record struct TimeHit(int Start, int End, int Hour, int Minute, int Second);

/// <summary>Date and time recognition.
/// Supported expressions (per culture data): ISO and numeric dates in the
/// culture's field order, month-name dates, 24h/12h times, localized hour
/// words (de "14:30 Uhr", zh 下午3点30分, hi शाम 3 बजे), relative days,
/// "now", weekdays (resolved to the reference week, Monday start) and
/// date+time combinations. Results expose a TIMEX-style normalization plus
/// a concrete ISO value resolved against the reference instant.</summary>
internal sealed class DateTimeFamily
{
    public const string TypeName = "datetime";
    public const int Priority = 10;

    private readonly string _cultureKey;
    private readonly bool _isZh;
    private readonly bool _isHi;
    private readonly Dictionary<string, int> _monthWords = new(StringComparer.OrdinalIgnoreCase);
    private readonly Dictionary<string, int> _weekdayWords = new(StringComparer.OrdinalIgnoreCase);

    private Regex? _numericDateRe;
    private (string, string, string) _numericGroups; // role of groups 1..3
    private readonly Regex _isoDateRe = new(@"(?<![\d])(\d{4})-(\d{2})-(\d{2})(?!\d)", RegexOptions.Compiled);
    private Regex? _monthFirstRe;
    private Regex? _dayFirstRe;
    private Regex? _zhFullRe;
    private Regex? _zhShortRe;
    private Regex? _weekdayRe;
    private Dictionary<string, int> _zhWeekdayNum = new();
    private Regex _time24Re = null!;
    private Regex? _time12Re;
    private Regex? _amRe;
    private Regex? _pmRe;
    private Regex? _hourOnlyRe;
    private Regex? _zhTimeRe;
    private readonly HashSet<string> _zhAmWords = new();
    private readonly HashSet<string> _zhPmWords = new();
    private Regex? _hiTimeRe;
    private readonly HashSet<string> _hiAmWords = new();
    private readonly HashSet<string> _hiPmWords = new();
    private Dictionary<string, int> _relative = new();
    private Regex? _relativeRe;
    private Regex? _nowRe;
    private List<string> _connectors = new();

    private static readonly Regex ZhWeekday = new(
        @"星期一|周一|星期二|周二|星期三|周三|星期四|周四|星期五|周五|星期六|周六|星期日|周日|星期天|礼拜一|礼拜二|礼拜三|礼拜四|礼拜五|礼拜六|礼拜日|礼拜天",
        RegexOptions.Compiled);

    public DateTimeFamily(string cultureKey, JsonDocument cfg)
    {
        _cultureKey = cultureKey;
        _isZh = cultureKey is "zh" or "zh-cn" or "zh-tw";
        _isHi = cultureKey == "hi";
        var dt = cfg.Section("datetime");

        foreach (var (names, idx) in MonthList(dt)) foreach (var w in names) _monthWords[w] = idx;
        foreach (var (names, idx) in WeekdayList(dt)) foreach (var w in names) _weekdayWords[w] = idx;

        CompileDates(dt);
        CompileTimes(dt);
        CompileRelative(dt);
    }

    private static List<(List<string>, int)> MonthList(JsonElement dt)
    {
        var list = new List<(List<string>, int)>();
        var i = 1;
        foreach (var names in dt.Section("months").Entries()) list.Add((names.GetStringsAt(), i++));
        return list;
    }

    private static List<(List<string>, int)> WeekdayList(JsonElement dt)
    {
        var list = new List<(List<string>, int)>();
        var i = 1;
        foreach (var names in dt.Section("weekdays").Entries()) list.Add((names.GetStringsAt(), i++));
        return list;
    }

    // --------------------------------------------------------------- dates
    /// <summary>.NET's Regex.Escape does not escape "-", which is only
    /// special inside character classes; escape for class use explicitly.</summary>
    private static string EscapeClass(string s) =>
        s.Replace("\\", "\\\\").Replace("-", "\\-").Replace("^", "\\^").Replace("]", "\\]");

    private void CompileDates(JsonElement dt)
    {
        var order = dt.GetString("dateOrder", "DMY");
        var seps = string.Concat(dt.GetStrings("numericDateSeparators").Select(EscapeClass));
        if (seps.Length == 0) seps = @"/\-.";
        // the second separator is mandatory: "5.1.2026" is a date but the
        // German grouped number "1.234" must never match
        if (order is "MDY" or "DMY")
        {
            _numericDateRe = new Regex(
                $@"(?<![\d/{Regex.Escape(".")}\-])(\d{{1,2}})[{seps}](\d{{1,2}})[{seps}](\d{{4}}|\d{{2}})(?!\d)",
                RegexOptions.Compiled);
            _numericGroups = order == "MDY" ? ("month", "day", "year") : ("day", "month", "year");
        }

        var monthAlt = RegexBuilder.Alt(_monthWords.Keys);
        var suffixAlt = RegexBuilder.Alt(dt.GetStrings("daySuffixes"));
        var suf = suffixAlt.Length > 0 ? $@"(?:{suffixAlt})?" : "";
        var dconn = dt.GetString("dayMonthConnector", "");
        var yconn = dt.GetString("yearConnector", "");
        var dconnRe = dconn.Length > 0 ? $@"(?:{Regex.Escape(dconn)}\s+)?" : "";
        var yconnRe = yconn.Length > 0 ? $@"(?:{Regex.Escape(yconn)}\s+)?" : "";
        var ci = _isZh || _isHi ? RegexOptions.None : RegexOptions.IgnoreCase;

        var formats = dt.GetStrings("monthDayFormats");
        if (formats.Contains("month-first"))
        {
            _monthFirstRe = new Regex(
                $@"\b({monthAlt})\.?\s+(\d{{1,2}}){suf}(?:\s*,?\s*(\d{{4}}))?", ci | RegexOptions.Compiled);
        }
        if (formats.Contains("day-first"))
        {
            _dayFirstRe = new Regex(
                $@"(?<![\d])(\d{{1,2}}){suf}\.?\s*{dconnRe}({monthAlt})\.?(?:\s*,?\s*{yconnRe}(\d{{4}}))?",
                ci | RegexOptions.Compiled);
        }

        if (_isZh)
        {
            _zhFullRe = new Regex(@"(\d{4})年(\d{1,2})月(\d{1,2})[日号]?", RegexOptions.Compiled);
            _zhShortRe = new Regex(@"(?<![\d年])(\d{1,2})月(\d{1,2})[日号]", RegexOptions.Compiled);
            _zhWeekdayNum = new Dictionary<string, int>
            {
                ["星期一"] = 1, ["周一"] = 1, ["礼拜一"] = 1,
                ["星期二"] = 2, ["周二"] = 2, ["礼拜二"] = 2,
                ["星期三"] = 3, ["周三"] = 3, ["礼拜三"] = 3,
                ["星期四"] = 4, ["周四"] = 4, ["礼拜四"] = 4,
                ["星期五"] = 5, ["周五"] = 5, ["礼拜五"] = 5,
                ["星期六"] = 6, ["周六"] = 6, ["礼拜六"] = 6,
                ["星期日"] = 7, ["周日"] = 7, ["星期天"] = 7, ["礼拜日"] = 7, ["礼拜天"] = 7,
            };
        }

        if (_weekdayWords.Count > 0 && !_isZh)
        {
            var (pre, post) = RegexBuilder.WordBoundaries(_cultureKey);
            _weekdayRe = new Regex($@"{pre}({RegexBuilder.Alt(_weekdayWords.Keys)}){post}",
                RegexOptions.IgnoreCase | RegexOptions.Compiled);
        }
    }

    // --------------------------------------------------------------- times
    private void CompileTimes(JsonElement dt)
    {
        // letter separators (French "14 h 30") may carry spaces; symbol
        // separators like ":" stay glued to the digits
        static string SepPattern(string s)
        {
            var e = Regex.Escape(s);
            return s.All(char.IsLetter) ? $@"\s?{e}\s?" : e;
        }
        var seps = string.Join("|", dt.GetStrings("timeSeparators").Select(SepPattern));
        if (seps.Length == 0) seps = ":";
        _time24Re = new Regex(
            $@"(?<![\d:.\-])(\d{{1,2}})(?:{seps})(\d{{2}})(?:(?:{seps})(\d{{2}}))?(?![\d])",
            RegexOptions.Compiled);

        var ampm = dt.Section("ampm");
        var am = ampm.GetStrings("am");
        var pm = ampm.GetStrings("pm");
        if (am.Count > 0)
            _amRe = new Regex($@"^({RegexBuilder.Alt(am)})$", RegexOptions.IgnoreCase | RegexOptions.Compiled);
        if (pm.Count > 0)
            _pmRe = new Regex($@"^({RegexBuilder.Alt(pm)})$", RegexOptions.IgnoreCase | RegexOptions.Compiled);
        if (am.Count + pm.Count > 0)
        {
            _time12Re = new Regex(
                $@"(?<![\d:.])(\d{{1,2}})(?:{seps}(\d{{2}}))?(?:{seps}(\d{{2}}))?"
                + $@"\s*({RegexBuilder.Alt(am.Concat(pm))})(?![A-Za-zÀ-ÿ])",
                RegexOptions.Compiled);
        }

        var hourSuffixes = dt.GetStrings("hourSuffixes");
        if (hourSuffixes.Count > 0)
        {
            _hourOnlyRe = new Regex($@"(?<![\d])(\d{{1,2}})\s?({RegexBuilder.Alt(hourSuffixes)})",
                RegexOptions.IgnoreCase | RegexOptions.Compiled);
        }

        if (_isZh)
        {
            var zhAmpm = dt.Section("zhAmpm");
            var amWords = zhAmpm.GetStrings("am");
            var pmWords = zhAmpm.GetStrings("pm");
            _zhAmWords.UnionWith(amWords);
            _zhPmWords.UnionWith(pmWords);
            var altAmpm = string.Join("|", amWords.Concat(pmWords).OrderByDescending(w => w.Length)
                .Select(Regex.Escape));
            _zhTimeRe = new Regex(
                $@"(?:({altAmpm}))?\s*(\d{{1,2}})[点时](半|(\d{{1,2}})分?|零(\d{{1,2}})分?)?",
                RegexOptions.Compiled);
        }

        if (_isHi)
        {
            var part = dt.Section("hiPartOfDay");
            var amWords = part.GetStrings("am");
            var pmWords = part.GetStrings("pm");
            _hiAmWords.UnionWith(amWords);
            _hiPmWords.UnionWith(pmWords);
            var oclk = Regex.Escape(dt.GetString("hiOClock", "बजे"));
            var altAmpm = string.Join("|", amWords.Concat(pmWords).OrderByDescending(w => w.Length)
                .Select(Regex.Escape));
            _hiTimeRe = new Regex($@"(?:({altAmpm})\s+)?(\d{{1,2}})(?::(\d{{2}}))?\s*{oclk}",
                RegexOptions.Compiled);
        }
    }

    private void CompileRelative(JsonElement dt)
    {
        _relative = dt.Section("relativeDays").GetStringMapLong();
        var (pre, post) = RegexBuilder.WordBoundaries(_cultureKey);
        if (_relative.Count > 0)
            _relativeRe = new Regex($@"{pre}({RegexBuilder.Alt(_relative.Keys)}){post}",
                RegexOptions.IgnoreCase | RegexOptions.Compiled);
        var nowWords = dt.GetStrings("now");
        if (nowWords.Count > 0)
            _nowRe = new Regex($@"{pre}({RegexBuilder.Alt(nowWords)}){post}",
                RegexOptions.IgnoreCase | RegexOptions.Compiled);
        _connectors = dt.GetStrings("dateTimeConnectors");
    }

    // ----------------------------------------------------------- extraction
    public List<Match> Extract(string text, DateTime reference)
    {
        var dates = ExtractDates(text);
        var times = ExtractTimes(text);
        var (combined, plainDates, plainTimes) = MergeCombo(text, dates, times);
        var results = new List<Match>();
        foreach (var d in plainDates) results.Add(DateMatch(d, reference));
        foreach (var t in plainTimes) results.Add(TimeMatch(t, reference));
        foreach (var combo in combined) results.Add(ComboMatch(combo, reference));
        results.AddRange(ExtractRelative(text, reference));
        return results;
    }

    private List<DateHit> ExtractDates(string text)
    {
        var hits = new List<DateHit>();
        if (_isZh)
        {
            foreach (RxMatch m in _zhFullRe!.Matches(text))
                hits.Add(new DateHit(m.Index, m.Index + m.Length - 1,
                    int.Parse(m.Groups[1].Value, CultureInfo.InvariantCulture),
                    int.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture),
                    int.Parse(m.Groups[3].Value, CultureInfo.InvariantCulture)));
            foreach (RxMatch m in _zhShortRe!.Matches(text))
                hits.Add(new DateHit(m.Index, m.Index + m.Length - 1, null,
                    int.Parse(m.Groups[1].Value, CultureInfo.InvariantCulture),
                    int.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture)));
        }
        foreach (RxMatch m in _isoDateRe.Matches(text))
            hits.Add(new DateHit(m.Index, m.Index + m.Length - 1,
                int.Parse(m.Groups[1].Value, CultureInfo.InvariantCulture),
                int.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture),
                int.Parse(m.Groups[3].Value, CultureInfo.InvariantCulture)));
        if (_numericDateRe is not null)
        {
            foreach (RxMatch m in _numericDateRe.Matches(text))
            {
                var a = int.Parse(m.Groups[1].Value, CultureInfo.InvariantCulture);
                var b = int.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture);
                var day = _numericGroups.Item1 == "day" ? a : b;
                var month = _numericGroups.Item1 == "day" ? b : a;
                var year = ExpandYear(m.Groups[3].Value);
                if (month >= 1 && month <= 12 && day >= 1 && day <= 31)
                    hits.Add(new DateHit(m.Index, m.Index + m.Length - 1, year, month, day));
            }
        }
        if (_monthFirstRe is not null)
        {
            foreach (RxMatch m in _monthFirstRe.Matches(text))
                if (_monthWords.TryGetValue(m.Groups[1].Value, out var month))
                    hits.Add(new DateHit(m.Index, m.Index + m.Length - 1,
                        m.Groups[3].Success ? int.Parse(m.Groups[3].Value, CultureInfo.InvariantCulture) : null,
                        month, int.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture)));
        }
        if (_dayFirstRe is not null)
        {
            foreach (RxMatch m in _dayFirstRe.Matches(text))
                if (_monthWords.TryGetValue(m.Groups[2].Value, out var month))
                    hits.Add(new DateHit(m.Index, m.Index + m.Length - 1,
                        m.Groups[3].Success ? int.Parse(m.Groups[3].Value, CultureInfo.InvariantCulture) : null,
                        month, int.Parse(m.Groups[1].Value, CultureInfo.InvariantCulture)));
        }
        return hits;
    }

    private List<TimeHit> ExtractTimes(string text)
    {
        var hits = new List<TimeHit>();
        if (_isZh)
        {
            foreach (RxMatch m in _zhTimeRe!.Matches(text)) hits.Add(ZhTimeHit(m));
        }
        if (_isHi)
        {
            foreach (RxMatch m in _hiTimeRe!.Matches(text)) hits.Add(HiTimeHit(m));
        }
        foreach (RxMatch m in _time24Re.Matches(text))
        {
            var h = int.Parse(m.Groups[1].Value, CultureInfo.InvariantCulture);
            var mi = int.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture);
            var s = m.Groups[3].Success ? int.Parse(m.Groups[3].Value, CultureInfo.InvariantCulture) : 0;
            if (h <= 23 && mi <= 59 && s <= 59)
                hits.Add(new TimeHit(m.Index, m.Index + m.Length - 1, h, mi, s));
        }
        if (_time12Re is not null)
        {
            foreach (RxMatch m in _time12Re.Matches(text))
            {
                var h = int.Parse(m.Groups[1].Value, CultureInfo.InvariantCulture);
                var mi = m.Groups[2].Success ? int.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture) : 0;
                var s = m.Groups[3].Success ? int.Parse(m.Groups[3].Value, CultureInfo.InvariantCulture) : 0;
                var token = m.Groups[4].Value.Trim();
                var pm = _pmRe is not null && _pmRe.IsMatch(token);
                if (h <= 12 && mi <= 59 && s <= 59)
                {
                    var hour = (h == 12 && pm) || (h < 12 && !pm)
                        ? h
                        : (h == 12 && !pm ? 0 : h + 12);
                    hits.Add(new TimeHit(m.Index, m.Index + m.Length - 1, hour, mi, s));
                }
            }
        }
        if (_hourOnlyRe is not null)
        {
            foreach (RxMatch m in _hourOnlyRe.Matches(text))
            {
                var h = int.Parse(m.Groups[1].Value, CultureInfo.InvariantCulture);
                if (h <= 23) hits.Add(new TimeHit(m.Index, m.Index + m.Length - 1, h, 0, 0));
            }
        }
        return hits;
    }

    private TimeHit ZhTimeHit(RxMatch m)
    {
        var h = int.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture);
        var pm = m.Groups[1].Success && _zhPmWords.Contains(m.Groups[1].Value);
        var am = m.Groups[1].Success && _zhAmWords.Contains(m.Groups[1].Value);
        if (pm && h < 12) h += 12;
        else if (am && h == 12) h = 0;
        int minute = 0;
        if (m.Groups[3].Value == "半") minute = 30;
        else if (m.Groups[4].Success) minute = int.Parse(m.Groups[4].Value, CultureInfo.InvariantCulture);
        else if (m.Groups[5].Success) minute = int.Parse(m.Groups[5].Value, CultureInfo.InvariantCulture);
        return new TimeHit(m.Index, m.Index + m.Length - 1, h, minute, 0);
    }

    private TimeHit HiTimeHit(RxMatch m)
    {
        var h = int.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture);
        if (m.Groups[1].Success && _hiPmWords.Contains(m.Groups[1].Value) && h < 12) h += 12;
        var minute = m.Groups[3].Success ? int.Parse(m.Groups[3].Value, CultureInfo.InvariantCulture) : 0;
        return new TimeHit(m.Index, m.Index + m.Length - 1, h, minute, 0);
    }

    // --------------------------------------------------------------- merge
    private (List<(DateHit, TimeHit)>, List<DateHit>, List<TimeHit>) MergeCombo(
        string text, List<DateHit> dates, List<TimeHit> times)
    {
        var plainGap = new Regex(@"^[\s,;()\-–—]*$", RegexOptions.Compiled);
        var connRe = _connectors.Count > 0
            ? new Regex($@"^[\s,;()\-–—]*(?:{RegexBuilder.Alt(_connectors)})[\s,;()\-–—]*$",
                RegexOptions.IgnoreCase | RegexOptions.Compiled)
            : null;

        var used = new HashSet<int>();
        var combined = new List<(DateHit, TimeHit)>();
        foreach (var d in dates.OrderBy(d => d.Start))
        {
            for (var i = 0; i < times.Count; i++)
            {
                if (used.Contains(i) || times[i].Start <= d.End) continue;
                var gap = text.Substring(d.End + 1, times[i].Start - (d.End + 1));
                var ok = plainGap.IsMatch(gap) || (connRe is not null && connRe.IsMatch(gap));
                if (ok && times[i].Start - d.End <= 30)
                {
                    combined.Add((d, times[i]));
                    used.Add(i);
                    break;
                }
            }
        }
        var plainDates = dates.Where(d => combined.All(c => !c.Item1.Equals(d))).ToList();
        var plainTimes = times.Where((_, i) => !used.Contains(i)).ToList();
        return (combined, plainDates, plainTimes);
    }

    // ----------------------------------------------------------- resolution
    private static Match DateMatch(DateHit d, DateTime reference)
    {
        var year = d.Year ?? reference.Year;
        var timex = d.Year is not null
            ? $"{year:0000}-{d.Month:00}-{d.Day:00}"
            : $"XXXX-{d.Month:00}-{d.Day:00}";
        var value = $"{year:0000}-{d.Month:00}-{d.Day:00}T00:00:00";
        return new Match
        {
            Text = null, Start = d.Start, End = d.End,
            TypeName = TypeName, Priority = Priority,
            Resolution = { ["timex"] = timex, ["value"] = value },
        };
    }

    private Match TimeMatch(TimeHit t, DateTime reference)
    {
        var timex = $"T{t.Hour:00}:{t.Minute:00}" + (t.Second > 0 ? $":{t.Second:00}" : "");
        var value = $"{reference:yyyy-MM-dd}T{t.Hour:00}:{t.Minute:00}:{t.Second:00}";
        return new Match
        {
            Text = null, Start = t.Start, End = t.End,
            TypeName = TypeName, Priority = Priority,
            Resolution = { ["timex"] = timex, ["value"] = value },
        };
    }

    private static Match ComboMatch((DateHit d, TimeHit t) combo, DateTime reference)
    {
        var (d, t) = combo;
        var year = d.Year ?? reference.Year;
        var timex = $"{year:0000}-{d.Month:00}-{d.Day:00}T{t.Hour:00}:{t.Minute:00}"
                    + (t.Second > 0 ? $":{t.Second:00}" : "");
        var value = $"{year:0000}-{d.Month:00}-{d.Day:00}T{t.Hour:00}:{t.Minute:00}:{t.Second:00}";
        return new Match
        {
            Text = null, Start = d.Start, End = t.End,
            TypeName = TypeName, Priority = Priority,
            Resolution = { ["timex"] = timex, ["value"] = value },
        };
    }

    private List<Match> ExtractRelative(string text, DateTime reference)
    {
        var results = new List<Match>();
        if (_nowRe is not null)
        {
            foreach (RxMatch m in _nowRe.Matches(text))
            {
                results.Add(new Match
                {
                    Text = null, Start = m.Index, End = m.Index + m.Length - 1,
                    TypeName = TypeName, Priority = Priority,
                    Resolution = { ["timex"] = "PRESENT", ["value"] = reference.ToString("yyyy-MM-dd'T'HH:mm:ss", CultureInfo.InvariantCulture) },
                });
            }
        }
        if (_relativeRe is not null)
        {
            foreach (RxMatch m in _relativeRe.Matches(text))
            {
                var d = reference.Date.AddDays(_relative[m.Groups[1].Value.ToLowerInvariant()]);
                results.Add(new Match
                {
                    Text = null, Start = m.Index, End = m.Index + m.Length - 1,
                    TypeName = TypeName, Priority = Priority,
                    Resolution =
                    {
                        ["timex"] = d.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
                        ["value"] = d.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) + "T00:00:00",
                    },
                });
            }
        }
        if (_weekdayRe is not null)
        {
            foreach (RxMatch m in _weekdayRe.Matches(text))
            {
                var dow = _weekdayWords[m.Groups[1].Value.ToLowerInvariant()];
                var d = WeekdayDate(reference, dow);
                results.Add(WeekdayMatch(m, d));
            }
        }
        if (_isZh)
        {
            foreach (RxMatch m in ZhWeekday.Matches(text))
            {
                var dow = _zhWeekdayNum[m.Value];
                var d = WeekdayDate(reference, dow);
                results.Add(WeekdayMatch(m, d));
            }
        }
        return results;
    }

    private static Match WeekdayMatch(RxMatch m, DateTime d)
    {
        var iso = d.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        return new Match
        {
            Text = null, Start = m.Index, End = m.Index + m.Length - 1,
            TypeName = TypeName, Priority = Priority,
            Resolution = { ["timex"] = iso, ["value"] = iso + "T00:00:00" },
        };
    }

    private static DateTime WeekdayDate(DateTime reference, int dow)
    {
        var monday = reference.Date.AddDays(-(((int)reference.DayOfWeek + 6) % 7));
        return monday.AddDays(dow - 1);
    }

    private static int ExpandYear(string y)
    {
        var n = int.Parse(y, CultureInfo.InvariantCulture);
        if (y.Length == 2) return n >= 70 ? 1900 + n : 2000 + n;
        return n;
    }
}
