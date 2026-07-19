using OfflineLlm.Core.Engine;

namespace OfflineLlm.Core.Chat;

/// <summary>
/// An ephemeral chat session: messages live only in this object's memory for the
/// lifetime of the session. Nothing here is ever handed to an IChatStore, written to a
/// file, or logged. When the session ends, call DisposeAsync — the backing
/// llama-server process is killed and, once this object is released, there is nothing
/// left on disk or in a database that could reveal the conversation happened.
/// </summary>
public sealed class OfflineSessionEngine : IAsyncDisposable
{
    private readonly List<ChatMessage> _messages = new();
    private readonly LlamaServerProcess _server;
    private readonly ChatEngine _chatEngine;

    public IReadOnlyList<ChatMessage> Messages => _messages;

    private OfflineSessionEngine(LlamaServerProcess server)
    {
        _server = server;
        _chatEngine = new ChatEngine(server);
    }

    public static async Task<OfflineSessionEngine> StartAsync(
        string llamaServerExePath, ModelInfo model, CancellationToken ct = default)
    {
        var server = new LlamaServerProcess(llamaServerExePath, model, ServerLifecycleKind.Offline);
        await server.StartAsync(ct: ct);
        return new OfflineSessionEngine(server);
    }

    public async IAsyncEnumerable<string> SendAsync(
        string userMessage,
        [System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken ct = default)
    {
        _messages.Add(new ChatMessage { Role = ChatRole.User, Content = userMessage });

        var assistantMessage = new ChatMessage { Role = ChatRole.Assistant, Content = string.Empty };
        _messages.Add(assistantMessage);

        await foreach (var chunk in _chatEngine.StreamReplyAsync(_messages, ct))
        {
            assistantMessage.Content += chunk;
            yield return chunk;
        }
    }

    /// <summary>
    /// Ends the session: kills the offline llama-server process and clears the
    /// in-memory transcript. After this returns, no artifact of the conversation
    /// remains anywhere.
    /// </summary>
    public async ValueTask DisposeAsync()
    {
        await _server.DisposeAsync();
        _messages.Clear();
    }
}
