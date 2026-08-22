using System.Text.Json;
using Inga.Recognizers.Text;
using Xunit;
using Xunit.Abstractions;

namespace IngaRecognizers.Text.Tests;

public sealed record ExpectedResult(string Text, string TypeName, int Start, int End,
    Dictionary<string, string> Resolution);

public sealed record SpecCase(string File, int Index, string Culture, string Input,
    List<ExpectedResult> Results);

/// <summary>Spec-driven tests: the same JSON spec files drive the pytest and
/// xUnit suites, so both ports must produce identical results.</summary>
public class SpecTests
{
    private static readonly DateTime Reference = new(2026, 8, 22, 12, 0, 0);
    private readonly ITestOutputHelper _output;

    public SpecTests(ITestOutputHelper output) => _output = output;

    private static List<SpecCase> LoadSpecs()
    {
        var all = new List<SpecCase>();
        var specsDir = Path.Combine(AppContext.BaseDirectory, "specs");
        foreach (var file in Directory.GetFiles(specsDir, "*.json").OrderBy(f => f, StringComparer.Ordinal))
        {
            using var doc = JsonDocument.Parse(File.ReadAllText(file));
            var idx = 0;
            foreach (var testCase in doc.RootElement.EnumerateArray())
            {
                var results = new List<ExpectedResult>();
                foreach (var r in testCase.GetProperty("Results").EnumerateArray())
                {
                    var resolution = new Dictionary<string, string>();
                    foreach (var prop in r.GetProperty("Resolution").EnumerateObject())
                        resolution[prop.Name] = prop.Value.GetString()!;
                    results.Add(new ExpectedResult(
                        r.GetProperty("Text").GetString()!,
                        r.GetProperty("TypeName").GetString()!,
                        r.GetProperty("Start").GetInt32(),
                        r.GetProperty("End").GetInt32(),
                        resolution));
                }
                all.Add(new SpecCase(
                    Path.GetFileNameWithoutExtension(file), idx++,
                    testCase.GetProperty("Culture").GetString()!,
                    testCase.GetProperty("Input").GetString()!,
                    results));
            }
        }
        return all;
    }

    public static TheoryData<string, int> AllCases
    {
        get
        {
            var data = new TheoryData<string, int>();
            foreach (var c in LoadSpecs()) data.Add(c.File, c.Index);
            return data;
        }
    }

    [Fact]
    public void SpecsContainAtLeast100Cases() => Assert.True(LoadSpecs().Count >= 100);

    [Fact]
    public void AllCulturesAvailable()
    {
        var cultures = Recognizers.AvailableCultures();
        foreach (var expected in new[] { "en", "zh", "fr", "es", "pt", "de", "it", "tr", "hi", "nl" })
            Assert.Contains(expected, cultures);
    }

    [Fact]
    public void UnknownCultureFallsBackToEnglish()
    {
        var results = Recognizers.Recognize("walk 3 km", "xx-YY", reference: Reference);
        var r = Assert.Single(results);
        Assert.Equal("dimension", r.TypeName);
        Assert.Equal("Kilometer", r.Resolution["unit"]);
    }

    [Fact]
    public void TypeFilterReturnsBareNumbers()
    {
        var results = Recognizers.Recognize("a 15% rise over 3 km", "en",
            types: new[] { "number" }, reference: Reference);
        Assert.Equal(new[] { "15", "3" }, results.Select(r => r.Text).ToArray());
    }

    [Fact]
    public void EmptyInputYieldsNoResults()
    {
        Assert.Empty(Recognizers.Recognize("", "en"));
        Assert.Empty(Recognizers.Recognize("   ", "en"));
    }

    [Fact]
    public void QuickStartReadmeExample()
    {
        var results = Recognizers.Recognize(
            "Rent is $1,200.50 for 12 months from March 1st, 2026 at 3pm", "en", reference: Reference);
        Assert.Equal(3, results.Count);
        var fee = results[0];
        Assert.Equal("currency", fee.TypeName);
        Assert.Equal("1200.5", fee.Resolution["value"]);
        Assert.Equal("USD", fee.Resolution["iso"]);
        var combo = results.Single(r => r.TypeName == "datetime");
        Assert.Equal("2026-03-01T15:00", combo.Resolution["timex"]);
        Assert.Equal("2026-03-01T15:00:00", combo.Resolution["value"]);
    }

    [Theory]
    [MemberData(nameof(AllCases))]
    public void SpecCaseHolds(string file, int index)
    {
        var spec = LoadSpecs().First(c => c.File == file && c.Index == index);
        var actual = Recognizers.Recognize(spec.Input, spec.Culture, reference: Reference);

        if (actual.Count != spec.Results.Count)
        {
            _output.WriteLine($"input:    {spec.Input}");
            _output.WriteLine($"expected: {string.Join(", ", spec.Results.Select(e => $"{e.Text}:{e.TypeName}"))}");
            _output.WriteLine($"actual:   {string.Join(", ", actual.Select(a => $"{a.Text}:{a.TypeName}"))}");
        }
        Assert.Equal(spec.Results.Count, actual.Count);

        for (var i = 0; i < spec.Results.Count; i++)
        {
            var exp = spec.Results[i];
            var act = actual[i];
            Assert.Equal(exp.Text, act.Text);
            Assert.Equal(exp.TypeName, act.TypeName);
            Assert.Equal(exp.Start, act.Start);
            Assert.Equal(exp.End, act.End);
            Assert.Equal(exp.Resolution.Count, act.Resolution.Count);
            foreach (var kv in exp.Resolution)
            {
                Assert.True(act.Resolution.TryGetValue(kv.Key, out var value),
                    $"{act.Text}: missing resolution key {kv.Key}");
                Assert.Equal(kv.Value, value);
            }
        }
    }
}
