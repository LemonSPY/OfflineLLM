namespace OfflineLlm.Core.Chat;

public enum ChatSessionStatus
{
    Active,
    Archived,
}

/// <summary>
/// A saved-mode conversation. Offline-mode conversations never become a ChatSession
/// and are never persisted — see OfflineSessionEngine.
/// </summary>
public sealed class ChatSession
{
    public required Guid Id { get; init; }
    public required string Title { get; set; }
    public required string ModelId { get; set; }
    public ChatSessionStatus Status { get; set; } = ChatSessionStatus.Active;
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
    public List<ChatMessage> Messages { get; init; } = new();
}
