using OfflineLlm.Core.Chat;

namespace OfflineLlm.App.ViewModels;

/// <summary>Sidebar list item for a saved-mode session.</summary>
public sealed class ChatSessionSummary
{
    public required Guid Id { get; init; }
    public required string Title { get; init; }
    public required ChatSessionStatus Status { get; init; }
}
