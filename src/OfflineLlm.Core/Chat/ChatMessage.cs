namespace OfflineLlm.Core.Chat;

public enum ChatRole
{
    User,
    Assistant,
    System,
}

public sealed class ChatMessage
{
    public required ChatRole Role { get; init; }
    public required string Content { get; set; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
}
