using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using OfflineLlm.Core.Engine;

namespace OfflineLlm.Core.Chat;

/// <summary>
/// Streams chat completions from a running llama-server instance's OpenAI-compatible
/// /v1/chat/completions endpoint (localhost only).
/// </summary>
public sealed class ChatEngine
{
    private readonly HttpClient _http;

    public ChatEngine(LlamaServerProcess server)
    {
        _http = new HttpClient { BaseAddress = server.BaseAddress };
    }

    public async IAsyncEnumerable<string> StreamReplyAsync(
        IReadOnlyList<ChatMessage> history,
        [System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken ct = default)
    {
        var payload = new
        {
            model = "local",
            stream = true,
            messages = history.Select(m => new
            {
                role = m.Role switch
                {
                    ChatRole.User => "user",
                    ChatRole.Assistant => "assistant",
                    ChatRole.System => "system",
                    _ => "user",
                },
                content = m.Content,
            }),
        };

        using var request = new HttpRequestMessage(HttpMethod.Post, "v1/chat/completions")
        {
            Content = JsonContent.Create(payload),
        };

        using var response = await _http.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, ct);
        response.EnsureSuccessStatusCode();

        await using var stream = await response.Content.ReadAsStreamAsync(ct);
        using var reader = new StreamReader(stream, Encoding.UTF8);

        while (!reader.EndOfStream)
        {
            var line = await reader.ReadLineAsync(ct);
            if (string.IsNullOrWhiteSpace(line) || !line.StartsWith("data:"))
            {
                continue;
            }

            var data = line["data:".Length..].Trim();
            if (data == "[DONE]")
            {
                yield break;
            }

            using var doc = JsonDocument.Parse(data);
            var delta = doc.RootElement
                .GetProperty("choices")[0]
                .GetProperty("delta");

            if (delta.TryGetProperty("content", out var contentEl) && contentEl.ValueKind == JsonValueKind.String)
            {
                var chunk = contentEl.GetString();
                if (!string.IsNullOrEmpty(chunk))
                {
                    yield return chunk;
                }
            }
        }
    }
}
