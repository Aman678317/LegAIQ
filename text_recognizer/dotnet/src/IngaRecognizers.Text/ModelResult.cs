using System.Text.Json.Serialization;

namespace Inga.Recognizers.Text;

/// <summary>A single recognized entity. Field names mirror the shared JSON
/// spec format (Text/TypeName/Start/End/Resolution) so the exact same spec
/// files drive every language port of this library.</summary>
public sealed class ModelResult
{
    [JsonPropertyName("Text")] public string Text { get; set; } = "";
    [JsonPropertyName("TypeName")] public string TypeName { get; set; } = "";
    [JsonPropertyName("Start")] public int Start { get; set; }
    /// <summary>Inclusive end offset into the input text.</summary>
    [JsonPropertyName("End")] public int End { get; set; }
    [JsonPropertyName("Resolution")] public Dictionary<string, string> Resolution { get; set; } = new();
}

/// <summary>Internal carrier used while families extract candidates.</summary>
internal sealed class Match
{
    public string? Text;              // null for datetime hits; filled from span
    public int Start;
    public int End;                   // inclusive
    public string TypeName = "";
    public Dictionary<string, string> Resolution = new();
    public int Priority;

    public ModelResult ToResult(string source)
    {
        var text = Text ?? source.Substring(Start, End - Start + 1);
        return new ModelResult
        {
            Text = text,
            TypeName = TypeName,
            Start = Start,
            End = End,
            Resolution = Resolution,
        };
    }
}
