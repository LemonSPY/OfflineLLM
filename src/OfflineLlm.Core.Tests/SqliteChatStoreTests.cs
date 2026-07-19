using OfflineLlm.Core.Chat;
using OfflineLlm.Core.Storage;
using Xunit;

namespace OfflineLlm.Core.Tests;

public sealed class SqliteChatStoreTests : IDisposable
{
    private readonly string _dbPath;
    private readonly SqliteChatStore _store;

    public SqliteChatStoreTests()
    {
        _dbPath = Path.Combine(Path.GetTempPath(), $"offlinellm-test-{Guid.NewGuid()}.db");
        _store = new SqliteChatStore(_dbPath);
    }

    [Fact]
    public async Task CreateSession_thenGet_roundTripsFields()
    {
        var created = await _store.CreateSessionAsync("Test chat", "qwen2.5-14b");

        var fetched = await _store.GetSessionAsync(created.Id);

        Assert.NotNull(fetched);
        Assert.Equal("Test chat", fetched!.Title);
        Assert.Equal("qwen2.5-14b", fetched.ModelId);
        Assert.Equal(ChatSessionStatus.Active, fetched.Status);
        Assert.Empty(fetched.Messages);
    }

    [Fact]
    public async Task AppendMessage_persistsInOrder()
    {
        var session = await _store.CreateSessionAsync("Test chat", "qwen2.5-14b");

        await _store.AppendMessageAsync(session.Id, new ChatMessage { Role = ChatRole.User, Content = "hi" });
        await _store.AppendMessageAsync(session.Id, new ChatMessage { Role = ChatRole.Assistant, Content = "hello" });

        var fetched = await _store.GetSessionAsync(session.Id);

        Assert.Equal(2, fetched!.Messages.Count);
        Assert.Equal(ChatRole.User, fetched.Messages[0].Role);
        Assert.Equal("hi", fetched.Messages[0].Content);
        Assert.Equal(ChatRole.Assistant, fetched.Messages[1].Role);
        Assert.Equal("hello", fetched.Messages[1].Content);
    }

    [Fact]
    public async Task SetArchived_excludesFromActiveList()
    {
        var session = await _store.CreateSessionAsync("Archive me", "qwen2.5-14b");

        await _store.SetArchivedAsync(session.Id, archived: true);

        var activeOnly = await _store.ListSessionsAsync(includeArchived: false);
        var all = await _store.ListSessionsAsync(includeArchived: true);

        Assert.DoesNotContain(activeOnly, s => s.Id == session.Id);
        Assert.Contains(all, s => s.Id == session.Id && s.Status == ChatSessionStatus.Archived);
    }

    [Fact]
    public async Task DeleteSession_removesSessionAndMessages()
    {
        var session = await _store.CreateSessionAsync("Delete me", "qwen2.5-14b");
        await _store.AppendMessageAsync(session.Id, new ChatMessage { Role = ChatRole.User, Content = "hi" });

        await _store.DeleteSessionAsync(session.Id);

        var fetched = await _store.GetSessionAsync(session.Id);
        Assert.Null(fetched);
    }

    public void Dispose()
    {
        _store.Dispose();
        if (File.Exists(_dbPath))
        {
            File.Delete(_dbPath);
        }
    }
}
