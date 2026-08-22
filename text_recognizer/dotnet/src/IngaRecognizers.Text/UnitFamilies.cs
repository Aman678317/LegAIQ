using System.Globalization;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Inga.Recognizers.Text;

// stop a unit token from matching when glued to a longer word ("3 merger")
internal static class UnitGuard
{
    public const string Word = "(?![A-Za-zÀ-ÿ\\u0400-\\u04ff\\u0600-\\u06ff\\u0900-\\u097f])";
}

internal sealed class UnitEntry
{
    public string Canonical = "";
    public string? Base;
    public double? Factor;
    public double Offset;
    public List<string> Patterns = new();
    public List<string> Symbols = new();
    public List<string> Names = new();
    public string? Iso;
}

/// <summary>Base for "number + unit token" families
/// (dimension/duration/temperature).</summary>
internal abstract class SuffixUnitFamilyBase
{
    public abstract string TypeName { get; }
    public abstract int Priority { get; }

    private readonly List<UnitEntry> _entries = new();
    private readonly Regex? _suffixRe;

    protected SuffixUnitFamilyBase(List<UnitEntry> entries)
    {
        _entries = entries;
        var flat = entries.SelectMany(e => e.Patterns).ToList();
        if (flat.Count > 0)
        {
            _suffixRe = new Regex($@"\s?({RegexBuilder.Alt(flat)}){UnitGuard.Word}",
                RegexOptions.Compiled | RegexOptions.IgnoreCase);
        }
    }

    public static List<UnitEntry> ReadEntries(JsonElement el)
    {
        var list = new List<UnitEntry>();
        foreach (var e in el.Entries())
        {
            var entry = new UnitEntry
            {
                Canonical = e.GetString("canonical", ""),
                Base = e.TryGetProperty("base", out var b) ? b.GetString() : null,
                Factor = e.TryGetProperty("factor", out var f) ? f.GetDouble() : null,
                Offset = e.TryGetProperty("offset", out var o) ? o.GetDouble() : 0.0,
                Patterns = e.GetStrings("patterns"),
                Symbols = e.GetStrings("symbols"),
                Names = e.GetStrings("names"),
                Iso = e.TryGetProperty("iso", out var i) ? i.GetString() : null,
            };
            list.Add(entry);
        }
        return list;
    }

    public List<Match> Extract(string text, List<Match> numbers)
    {
        var results = new List<Match>();
        if (_suffixRe is null) return results;
        foreach (var num in numbers)
        {
            if (num.End + 1 >= text.Length) continue;
            var m = _suffixRe.Match(text, num.End + 1);
            if (!m.Success || m.Index != num.End + 1) continue;
            var entry = EntryFor(m.Groups[1].Value);
            if (entry is null) continue;
            results.Add(new Match
            {
                Text = text.Substring(num.Start, m.Index + m.Length - num.Start),
                Start = num.Start,
                End = m.Index + m.Length - 1,
                TypeName = TypeName,
                Priority = Priority,
                Resolution = BuildResolution(num, entry),
            });
        }
        return results;
    }

    private UnitEntry? EntryFor(string token)
    {
        var low = token.ToLowerInvariant();
        return _entries.FirstOrDefault(e => e.Patterns.Any(p => p.ToLowerInvariant() == low));
    }

    protected virtual Dictionary<string, string> BuildResolution(Match num, UnitEntry entry)
    {
        var value = double.Parse(num.Resolution["value"], CultureInfo.InvariantCulture);
        var res = new Dictionary<string, string> { ["value"] = RegexBuilder.FormatNumber(value), ["unit"] = entry.Canonical };
        if (!string.IsNullOrEmpty(entry.Base) && entry.Base != entry.Canonical && entry.Factor.HasValue)
        {
            res["normalizedValue"] = RegexBuilder.FormatNumber(value * entry.Factor.Value);
            res["normalizedUnit"] = entry.Base!;
        }
        return res;
    }
}

internal sealed class DimensionFamily : SuffixUnitFamilyBase
{
    public override string TypeName => "dimension";
    public override int Priority => 50;
    public DimensionFamily(JsonDocument cfg) : base(ReadEntries(cfg.Section("dimension"))) { }
}

internal sealed class DurationFamily : SuffixUnitFamilyBase
{
    public override string TypeName => "duration";
    public override int Priority => 60;
    public DurationFamily(JsonDocument cfg) : base(ReadEntries(cfg.Section("duration"))) { }
}

internal sealed class TemperatureFamily : SuffixUnitFamilyBase
{
    public override string TypeName => "temperature";
    public override int Priority => 30;
    public TemperatureFamily(JsonDocument cfg) : base(ReadEntries(cfg.Section("temperature"))) { }

    protected override Dictionary<string, string> BuildResolution(Match num, UnitEntry entry)
    {
        var value = double.Parse(num.Resolution["value"], CultureInfo.InvariantCulture);
        var kelvin = value * (entry.Factor ?? 1.0) + entry.Offset;
        return new Dictionary<string, string>
        {
            ["value"] = RegexBuilder.FormatNumber(value),
            ["unit"] = entry.Canonical,
            ["normalizedValue"] = RegexBuilder.FormatNumber(kelvin),
            ["normalizedUnit"] = "Kelvin",
        };
    }
}

/// <summary>Currency symbol adjacent to the number, or currency name with space.</summary>
internal sealed class CurrencyFamily
{
    public const string TypeName = "currency";
    public const int Priority = 40;

    private readonly List<UnitEntry> _entries = new();
    private readonly Regex? _symAfter;
    private readonly Regex? _symBefore;
    private readonly Regex? _nameAfter;
    private readonly Regex? _nameBefore;

    public CurrencyFamily(JsonDocument cfg)
    {
        _entries = SuffixUnitFamilyBase.ReadEntries(cfg.Section("currency"));
        var symbols = _entries.SelectMany(e => e.Symbols).ToList();
        var names = _entries.SelectMany(e => e.Names).ToList();
        if (symbols.Count > 0)
        {
            _symAfter = new Regex($@"\s?({RegexBuilder.Alt(symbols)})", RegexOptions.Compiled);
            _symBefore = new Regex($@"({RegexBuilder.Alt(symbols)})\s?$", RegexOptions.Compiled);
        }
        if (names.Count > 0)
        {
            _nameAfter = new Regex($@"\s({RegexBuilder.Alt(names)}){UnitGuard.Word}",
                RegexOptions.Compiled | RegexOptions.IgnoreCase);
            _nameBefore = new Regex($@"({RegexBuilder.Alt(names)})\s?$",
                RegexOptions.Compiled | RegexOptions.IgnoreCase);
        }
    }

    public List<Match> Extract(string text, List<Match> numbers)
    {
        var results = new List<Match>();
        foreach (var num in numbers)
        {
            var m = MatchAfter(text, num) ?? MatchBefore(text, num);
            if (m is not null) results.Add(m);
        }
        return results;
    }

    private Match? MatchAfter(string text, Match num)
    {
        if (num.End + 1 < text.Length && _symAfter is not null)
        {
            var m = _symAfter.Match(text, num.End + 1);
            if (m.Success && m.Index == num.End + 1)
            {
                var entry = EntryFor(m.Groups[1].Value, symbol: true);
                if (entry is not null)
                    return Make(text, num, entry, num.Start, m.Index + m.Length - 1);
            }
        }
        if (num.End + 1 < text.Length && _nameAfter is not null)
        {
            var m = _nameAfter.Match(text, num.End + 1);
            if (m.Success && m.Index == num.End + 1)
            {
                var entry = EntryFor(m.Groups[1].Value, symbol: false);
                if (entry is not null)
                    return Make(text, num, entry, num.Start, m.Index + m.Length - 1);
            }
        }
        return null;
    }

    private Match? MatchBefore(string text, Match num)
    {
        if (_symBefore is not null)
        {
            var m = _symBefore.Match(text, 0, num.Start);
            if (m.Success && m.Index + m.Length == num.Start)
            {
                var entry = EntryFor(m.Groups[1].Value, symbol: true);
                if (entry is not null)
                    return Make(text, num, entry, m.Index, num.End);
            }
        }
        if (_nameBefore is not null)
        {
            var m = _nameBefore.Match(text, 0, num.Start);
            if (m.Success && m.Index + m.Length == num.Start)
            {
                var entry = EntryFor(m.Groups[1].Value, symbol: false);
                if (entry is not null)
                    return Make(text, num, entry, m.Index, num.End);
            }
        }
        return null;
    }

    private UnitEntry? EntryFor(string token, bool symbol)
    {
        if (symbol) return _entries.FirstOrDefault(e => e.Symbols.Contains(token));
        var low = token.ToLowerInvariant();
        return _entries.FirstOrDefault(e => e.Names.Any(n => n.ToLowerInvariant() == low));
    }

    private static Match Make(string text, Match num, UnitEntry entry, int start, int end)
    {
        var res = new Dictionary<string, string> { ["value"] = num.Resolution["value"], ["unit"] = entry.Canonical };
        if (entry.Iso is not null) res["iso"] = entry.Iso;
        return new Match
        {
            Text = text.Substring(start, end - start + 1), Start = start, End = end,
            TypeName = TypeName, Priority = Priority, Resolution = res,
        };
    }
}

/// <summary>Age expressions: "3 years old", "3 Jahre alt", "3 años", "3岁".</summary>
internal sealed class AgeFamily
{
    public const string TypeName = "age";
    public const int Priority = 25;

    private readonly Regex? _re;
    private readonly string _unit;

    public AgeFamily(JsonDocument cfg)
    {
        var age = cfg.Section("age");
        _unit = age.GetString("unit", "Year");
        var patterns = age.GetStrings("patterns");
        // patterns are regex fragments so cultures can write "years? old"
        if (patterns.Count > 0)
            _re = new Regex($@"\s?({string.Join("|", patterns)}){UnitGuard.Word}",
                RegexOptions.Compiled | RegexOptions.IgnoreCase);
    }

    public List<Match> Extract(string text, List<Match> numbers)
    {
        var results = new List<Match>();
        if (_re is null) return results;
        foreach (var num in numbers)
        {
            if (num.End + 1 >= text.Length) continue;
            var m = _re.Match(text, num.End + 1);
            if (!m.Success || m.Index != num.End + 1) continue;
            results.Add(new Match
            {
                Text = text.Substring(num.Start, m.Index + m.Length - num.Start),
                Start = num.Start,
                End = m.Index + m.Length - 1,
                TypeName = TypeName,
                Priority = Priority,
                Resolution = { ["value"] = num.Resolution["value"], ["unit"] = _unit },
            });
        }
        return results;
    }
}
