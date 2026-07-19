using OfflineLlm.Core.Storage;

namespace OfflineLlm.Core.Chat;

/// <summary>
/// Drives a saved-mode chat: every user/assistant message is appended to the
/// IChatStore as it's produced, so the conversation survives app restarts and shows
/// up in the archive/delete list.
/// </summary>
public sealed class SavedSessionEngine
{
    private readonly IChatStore _store;
    private readonly ChatEngine _chatEngine;
    private readonly ChatSession _session;

    public SavedSessionEngine(IChatStore store, ChatEngine chatEngine, ChatSession session)
    {
        _store = store;
        _chatEngine = chatEngine;
        _session = session;
    }

    public async IAsyncEnumerable<string> SendAsync(
        string userMessage,
        [System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken ct = default)
    {
        var userChatMessage = new ChatMessage { Role = ChatRole.User, Content = userMessage };
        _session.Messages.Add(userChatMessage);
        await _store.AppendMessageAsync(_session.Id, userChatMessage, ct);

        var assistantMessage = new ChatMessage { Role = ChatRole.Assistant, Content = string.Empty };
        _session.Messages.Add(assistantMessage);

        await foreach (var chunk in _chatEngine.StreamReplyAsync(_session.Messages, ct))
        {
            assistantMessage.Content += chunk;
            yield return chunk;
        }

        await _store.AppendMessageAsync(_session.Id, assistantMessage, ct);
    }
}
