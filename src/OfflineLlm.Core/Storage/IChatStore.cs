using OfflineLlm.Core.Chat;

namespace OfflineLlm.Core.Storage;

/// <summary>
/// Persistence for saved-mode chats only. Offline-mode sessions must never be
/// passed to an IChatStore implementation.
/// </summary>
public interface IChatStore
{
    Task<ChatSession> CreateSessionAsync(string title, string modelId, CancellationToken ct = default);

    Task<IReadOnlyList<ChatSession>> ListSessionsAsync(bool includeArchived, CancellationToken ct = default);

    Task<ChatSession?> GetSessionAsync(Guid id, CancellationToken ct = default);

    Task AppendMessageAsync(Guid sessionId, ChatMessage message, CancellationToken ct = default);

    Task RenameSessionAsync(Guid sessionId, string newTitle, CancellationToken ct = default);

    Task SetArchivedAsync(Guid sessionId, bool archived, CancellationToken ct = default);

    Task DeleteSessionAsync(Guid sessionId, CancellationToken ct = default);
}
