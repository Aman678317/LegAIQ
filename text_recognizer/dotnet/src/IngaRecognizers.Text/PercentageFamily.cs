using System.Text.Json;
using System.Text.RegularExpressions;

namespace Inga.Recognizers.Text;

/// <summary>Percentage recognition: "15%", "fünfzehn Prozent", "yüzde 30",
/// "百分之20". Works on top of the number family: every number match is
/// checked for a percentage token attached before (prefix) or after (suffix).</summary>
internal sealed class PercentageFamily
{
    public const string TypeName = "percentage";
    public const int Priority = 20;

    private readonly List<string> _suffixes;
    private readonly List<string> _prefixes;
    private readonly bool _isZh;
    private readonly string _pre;
    private readonly string _post;
    private static readonly Regex ZhPrefix = new(@"百分之(\d+(?:\.\d+)?|[〇零一二三四五六七八九两十百千万萬亿億壹贰叁肆伍陆柒捌玖拾佰仟]+)", RegexOptions.Compiled);

    public PercentageFamily(string cultureKey, JsonDocument cfg)
    {
        var pct = cfg.Section("percentage");
        _suffixes = pct.GetStrings("suffixes").OrderByDescending(s => s.Length).ToList();
        _prefixes = pct.GetStrings("prefixes").OrderByDescending(s => s.Length).ToList();
        _isZh = cultureKey is "zh" or "zh-cn" or "zh-tw";
        // Chinese "百分之X" needs the hanzi-numeral parser, handled separately
        if (_isZh) _prefixes.RemoveAll(p => p == "百分之");
        (_pre, _post) = RegexBuilder.WordBoundaries(cultureKey);
    }

    public List<Match> Extract(string text, List<Match> numbers)
    {
        var results = new List<Match>();
        foreach (var num in numbers)
        {
            var m = MatchSuffix(text, num) ?? MatchPrefix(text, num);
            if (m is not null) results.Add(m);
        }
        if (_isZh) results.AddRange(MatchZhPrefix(text));
        return results;
    }

    private Match? MatchSuffix(string text, Match num)
    {
        var after = text.Substring(num.End + 1);
        foreach (var token in _suffixes)
        {
            var pat = token switch
            {
                "%" => Regex.Escape(token),
                _ when _isZh => Regex.Escape(token),
                _ => $"{_pre}{Regex.Escape(token)}{_post}",
            };
            var m = Regex.Match(after, $@"\s*{pat}", RegexOptions.IgnoreCase);
            if (m.Success)
            {
                var end = num.End + 1 + m.Length;
                return new Match
                {
                    Text = text.Substring(num.Start, end - num.Start), Start = num.Start, End = end - 1,
                    TypeName = TypeName, Priority = Priority,
                    Resolution = { ["value"] = num.Resolution["value"], ["unit"] = "%" },
                };
            }
        }
        return null;
    }

    private Match? MatchPrefix(string text, Match num)
    {
        var before = text.Substring(0, num.Start);
        foreach (var token in _prefixes)
        {
            var pat = !char.IsLetter(token[0]) || _isZh
                ? Regex.Escape(token)
                : $"{_pre}{Regex.Escape(token)}{_post}";
            var m = Regex.Match(before, $@"{pat}\s*$", RegexOptions.IgnoreCase);
            if (m.Success)
            {
                var start = m.Index;
                return new Match
                {
                    Text = text.Substring(start, num.End + 1 - start), Start = start, End = num.End,
                    TypeName = TypeName, Priority = Priority,
                    Resolution = { ["value"] = num.Resolution["value"], ["unit"] = "%" },
                };
            }
        }
        return null;
    }

    private static List<Match> MatchZhPrefix(string text)
    {
        var results = new List<Match>();
        foreach (System.Text.RegularExpressions.Match m in ZhPrefix.Matches(text))
        {
            var body = m.Groups[1].Value;
            string value;
            if (body.All(char.IsDigit) || body.Contains('.'))
                value = body;
            else
                value = NumberFamily.ZhNumeralValue(body)
                    .ToString(System.Globalization.CultureInfo.InvariantCulture);
            results.Add(new Match
            {
                Text = m.Value, Start = m.Index, End = m.Index + m.Length - 1,
                TypeName = TypeName, Priority = Priority,
                Resolution = { ["value"] = value, ["unit"] = "%" },
            });
        }
        return results;
    }
}
