using System.Collections.Concurrent;

namespace Inga.Recognizers.Text;

/// <summary>Recognition engine: orchestrates all families and resolves overlaps.</summary>
internal sealed class RecognitionEngine
{
    private static readonly ConcurrentDictionary<string, Families> FamilyCache = new();

    private sealed record Families(
        NumberFamily Number,
        PercentageFamily Percentage,
        DimensionFamily Dimension,
        DurationFamily Duration,
        CurrencyFamily Currency,
        TemperatureFamily Temperature,
        AgeFamily Age,
        DateTimeFamily DateTime);

    public static readonly string[] AllTypes =
    {
        "number", "percentage", "dimension", "duration",
        "currency", "temperature", "age", "datetime",
    };

    private static Families GetFamilies(string cultureKey)
    {
        return FamilyCache.GetOrAdd(cultureKey, k =>
        {
            var cfg = CultureLoader.Load(k);
            return new Families(
                new NumberFamily(k, cfg),
                new PercentageFamily(k, cfg),
                new DimensionFamily(cfg),
                new DurationFamily(cfg),
                new CurrencyFamily(cfg),
                new TemperatureFamily(cfg),
                new AgeFamily(cfg),
                new DateTimeFamily(k, cfg));
        });
    }

    /// <summary>Recognize numbers, percentages, units, dates and times in
    /// <paramref name="text"/>. Unknown cultures fall back to English.</summary>
    public static List<ModelResult> Recognize(
        string text,
        string culture = "en",
        IReadOnlyCollection<string>? types = null,
        DateTime? reference = null)
    {
        if (string.IsNullOrEmpty(text)) return new List<ModelResult>();
        var referenceValue = reference ?? DateTime.Now;
        var cultureKey = (culture ?? "en").ToLowerInvariant();
        var fam = GetFamilies(cultureKey);
        bool Want(string t) => types is null || types.Contains(t);

        var transformed = NumberFamily.TranslateDigits(text, cultureKey);
        var numbers = fam.Number.Extract(transformed);

        var candidates = new List<Match>();
        if (Want("datetime")) candidates.AddRange(fam.DateTime.Extract(transformed, referenceValue));
        if (Want("percentage")) candidates.AddRange(fam.Percentage.Extract(transformed, numbers));
        if (Want("age")) candidates.AddRange(fam.Age.Extract(transformed, numbers));
        if (Want("temperature")) candidates.AddRange(fam.Temperature.Extract(transformed, numbers));
        if (Want("currency")) candidates.AddRange(fam.Currency.Extract(transformed, numbers));
        if (Want("dimension")) candidates.AddRange(fam.Dimension.Extract(transformed, numbers));
        if (Want("duration")) candidates.AddRange(fam.Duration.Extract(transformed, numbers));
        if (Want("number")) candidates.AddRange(numbers);

        var kept = ResolveOverlaps(candidates);
        // spans refer to the digit-translated text, which is 1:1 with the
        // original, so slice the ORIGINAL text to keep native digits in Text
        return kept
            .OrderBy(m => m.Start).ThenBy(m => m.End)
            .Select(m =>
            {
                var r = m.ToResult(transformed);
                r.Text = text.Substring(m.Start, m.End - m.Start + 1);
                return r;
            })
            .ToList();
    }

    /// <summary>Drop matches fully contained inside a higher-precedence match.
    /// Equal spans across families also resolve by precedence ("2 uur" is the
    /// Dutch duration, not "2 o'clock"; "trois ans" is an age, not a duration).</summary>
    private static List<Match> ResolveOverlaps(List<Match> candidates)
    {
        var ordered = candidates
            .OrderBy(m => m.Priority)
            .ThenBy(m => m.Start)
            .ThenBy(m => -(m.End - m.Start))
            .ToList();
        var kept = new List<Match>();
        foreach (var m in ordered)
        {
            var contained = false;
            foreach (var k in kept)
            {
                if (k.Start <= m.Start && m.End <= k.End)
                {
                    if (k.Priority < m.Priority) contained = true;
                    else if (k.Priority == m.Priority && (k.Start, k.End) != (m.Start, m.End)) contained = true;
                }
                if (contained) break;
            }
            if (!contained) kept.Add(m);
        }
        return kept;
    }
}

/// <summary>Public entry point mirroring the Python package API.</summary>
public static class Recognizers
{
    /// <summary>Recognize numbers, percentages, units, dates and times in
    /// plain text and return normalized results.</summary>
    /// <param name="text">Input text in any supported language.</param>
    /// <param name="culture">Culture code ("en", "de", "zh", "hi", ...). Unknown cultures fall back to English.</param>
    /// <param name="types">Restrict output to these type names (subset of <see cref="RecognitionEngine.AllTypes"/>).</param>
    /// <param name="reference">Reference instant for relative date/time resolution; defaults to now.</param>
    public static List<ModelResult> Recognize(
        string text,
        string culture = "en",
        IReadOnlyCollection<string>? types = null,
        DateTime? reference = null)
        => RecognitionEngine.Recognize(text, culture, types, reference);

    /// <summary>Culture codes with an embedded definition.</summary>
    public static IReadOnlyList<string> AvailableCultures() => CultureLoader.AvailableCultures();
}
