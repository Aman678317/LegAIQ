using System.Reflection;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Inga.Recognizers.Text;

/// <summary>Loads the shared per-culture JSON definitions embedded as assembly
/// resources. The JSON files under text_recognizer/cultures are the single
/// source of truth for every port of this library (Python, .NET, future
/// TypeScript), which keeps behavior in lockstep across versions.</summary>
public static class CultureLoader
{
    private const string Fallback = "en";
    private static readonly Dictionary<string, JsonDocument> Cache = new();

    /// <summary>Culture codes with an embedded definition.</summary>
    public static IReadOnlyList<string> AvailableCultures()
    {
        var names = new List<string>();
        foreach (var rn in Assembly.GetExecutingAssembly().GetManifestResourceNames())
        {
            const string prefix = "Inga.Recognizers.Text.cultures.";
            if (rn.StartsWith(prefix, StringComparison.Ordinal) && rn.EndsWith(".json", StringComparison.Ordinal))
            {
                names.Add(rn.Substring(prefix.Length, rn.Length - prefix.Length - 5));
            }
        }
        names.Sort();
        return names;
    }

    /// <summary>Load a culture definition; unknown cultures fall back to English.</summary>
    public static JsonDocument Load(string? culture)
    {
        var key = (culture ?? Fallback).ToLowerInvariant();
        lock (Cache)
        {
            if (Cache.TryGetValue(key, out var cached)) return cached;
            var doc = LoadFromResources(key) ?? LoadFromResources(Fallback)!;
            Cache[key] = doc;
            return doc;
        }
    }

    private static JsonDocument? LoadFromResources(string name)
    {
        var stream = Assembly.GetExecutingAssembly()
            .GetManifestResourceStream($"Inga.Recognizers.Text.cultures.{name}.json");
        if (stream is null) return null;
        using (stream)
            return JsonDocument.Parse(stream, new JsonDocumentOptions { AllowTrailingCommas = true });
    }
}

/// <summary>Small helpers over JsonElement for the culture schema.</summary>
internal static class JsonElementExtensions
{
    public static JsonElement Section(this JsonDocument doc, string name)
        => doc.RootElement.TryGetProperty(name, out var el) ? el : default;

    public static JsonElement Section(this JsonElement el, string name)
        => el.ValueKind != JsonValueKind.Undefined && el.TryGetProperty(name, out var sub) ? sub : default;

    public static string GetString(this JsonElement el, string name, string fallback)
        => el.ValueKind != JsonValueKind.Undefined && el.TryGetProperty(name, out var p) && p.ValueKind == JsonValueKind.String
            ? p.GetString()! : fallback;

    public static bool GetBool(this JsonElement el, string name, bool fallback = false)
        => el.ValueKind != JsonValueKind.Undefined && el.TryGetProperty(name, out var p) && p.ValueKind == JsonValueKind.True;

    public static List<string> GetStrings(this JsonElement el, string name)
    {
        var list = new List<string>();
        if (el.ValueKind != JsonValueKind.Undefined && el.TryGetProperty(name, out var p) && p.ValueKind == JsonValueKind.Array)
            foreach (var item in p.EnumerateArray()) list.Add(item.GetString()!);
        return list;
    }

    public static List<string> GetStringsAt(this JsonElement el)
    {
        var list = new List<string>();
        if (el.ValueKind == JsonValueKind.Array)
            foreach (var item in el.EnumerateArray()) list.Add(item.GetString()!);
        return list;
    }

    public static Dictionary<string, long> GetWordMap(this JsonElement el, string name)
    {
        var map = new Dictionary<string, long>(StringComparer.Ordinal);
        if (el.ValueKind != JsonValueKind.Undefined && el.TryGetProperty(name, out var p) && p.ValueKind == JsonValueKind.Object)
            foreach (var prop in p.EnumerateObject())
                if (prop.Value.ValueKind == JsonValueKind.Number)
                    map[prop.Name] = (long)prop.Value.GetDouble();
        return map;
    }

    public static Dictionary<string, string> GetStringMap(this JsonElement el, string name)
    {
        var map = new Dictionary<string, string>(StringComparer.Ordinal);
        if (el.ValueKind != JsonValueKind.Undefined && el.TryGetProperty(name, out var p) && p.ValueKind == JsonValueKind.Object)
            foreach (var prop in p.EnumerateObject())
                map[prop.Name] = prop.Value.GetString()!;
        return map;
    }

    public static Dictionary<string, int> GetStringMapLong(this JsonElement el)
    {
        var map = new Dictionary<string, int>(StringComparer.Ordinal);
        if (el.ValueKind == JsonValueKind.Object)
            foreach (var prop in el.EnumerateObject())
                if (prop.Value.ValueKind == JsonValueKind.Number)
                    map[prop.Name] = (int)prop.Value.GetDouble();
        return map;
    }

    public static List<JsonElement> Entries(this JsonElement el)
    {
        var list = new List<JsonElement>();
        if (el.ValueKind == JsonValueKind.Array)
            list.AddRange(el.EnumerateArray());
        return list;
    }
}

internal static class RegexBuilder
{
    /// <summary>Longest-first de-duplicated alternation, matching the Python
    /// engine's ordering so both ports prefer the same token.</summary>
    public static string Alt(IEnumerable<string> words)
    {
        var distinct = words.Distinct().OrderByDescending(w => w.Length).ThenBy(w => w, StringComparer.Ordinal);
        return string.Join("|", distinct.Select(Regex.Escape));
    }

    /// <summary>Word-boundary guards per script: \b assumes \w on both sides,
    /// which fails for Devanagari matras (दो, रुपये end with combining marks)
    /// and is meaningless for hanzi.</summary>
    public static (string pre, string post) WordBoundaries(string culture)
    {
        if (culture == "hi") return (@"(?<![\u0900-\u097F])", @"(?![\u0900-\u097F])");
        if (culture is "zh" or "zh-cn" or "zh-tw") return ("", "");
        return (@"\b", @"\b");
    }

    public static string FormatNumber(double value)
    {
        if (value == Math.Floor(value) && Math.Abs(value) < 1e15) return ((long)value).ToString();
        var s = value.ToString("F10", System.Globalization.CultureInfo.InvariantCulture).TrimEnd('0').TrimEnd('.');
        return s;
    }
}
