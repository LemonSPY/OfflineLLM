using Microsoft.Data.Sqlite;
using OfflineLlm.Core.Chat;

namespace OfflineLlm.Core.Storage;

/// <summary>
/// SQLite-backed persistence for saved-mode chats. This type is intentionally never
/// used by offline-mode sessions (see OfflineSessionEngine) — saved-mode is the only
/// mode where conversation content is written to disk.
/// </summary>
public sealed class SqliteChatStore : IChatStore, IDisposable
{
    private readonly SqliteConnection _connection;

    public SqliteChatStore(string databasePath)
    {
        var dir = Path.GetDirectoryName(databasePath);
        if (!string.IsNullOrEmpty(dir))
        {
            Directory.CreateDirectory(dir);
        }

        _connection = new SqliteConnection($"Data Source={databasePath}");
        _connection.Open();
        Initialize();
    }

    private void Initialize()
    {
        using var cmd = _connection.CreateCommand();
        cmd.CommandText =
            """
            CREATE TABLE IF NOT EXISTS Sessions (
                Id TEXT PRIMARY KEY,
                Title TEXT NOT NULL,
                ModelId TEXT NOT NULL,
                Status TEXT NOT NULL,
                CreatedAt TEXT NOT NULL,
                UpdatedAt TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS Messages (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                SessionId TEXT NOT NULL,
                Role TEXT NOT NULL,
                Content TEXT NOT NULL,
                CreatedAt TEXT NOT NULL,
                FOREIGN KEY (SessionId) REFERENCES Sessions(Id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS IX_Messages_SessionId ON Messages(SessionId);
            """;
        cmd.ExecuteNonQuery();
    }

    public Task<ChatSession> CreateSessionAsync(string title, string modelId, CancellationToken ct = default)
    {
        var session = new ChatSession
        {
            Id = Guid.NewGuid(),
            Title = title,
            ModelId = modelId,
        };

        using var cmd = _connection.CreateCommand();
        cmd.CommandText =
            "INSERT INTO Sessions (Id, Title, ModelId, Status, CreatedAt, UpdatedAt) " +
            "VALUES ($id, $title, $modelId, $status, $createdAt, $updatedAt)";
        cmd.Parameters.AddWithValue("$id", session.Id.ToString());
        cmd.Parameters.AddWithValue("$title", session.Title);
        cmd.Parameters.AddWithValue("$modelId", session.ModelId);
        cmd.Parameters.AddWithValue("$status", session.Status.ToString());
        cmd.Parameters.AddWithValue("$createdAt", session.CreatedAt.ToString("o"));
        cmd.Parameters.AddWithValue("$updatedAt", session.UpdatedAt.ToString("o"));
        cmd.ExecuteNonQuery();

        return Task.FromResult(session);
    }

    public Task<IReadOnlyList<ChatSession>> ListSessionsAsync(bool includeArchived, CancellationToken ct = default)
    {
        using var cmd = _connection.CreateCommand();
        cmd.CommandText = includeArchived
            ? "SELECT Id, Title, ModelId, Status, CreatedAt, UpdatedAt FROM Sessions ORDER BY UpdatedAt DESC"
            : "SELECT Id, Title, ModelId, Status, CreatedAt, UpdatedAt FROM Sessions WHERE Status = 'Active' ORDER BY UpdatedAt DESC";

        var results = new List<ChatSession>();
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            results.Add(ReadSessionRow(reader));
        }

        return Task.FromResult<IReadOnlyList<ChatSession>>(results);
    }

    public async Task<ChatSession?> GetSessionAsync(Guid id, CancellationToken ct = default)
    {
        using var cmd = _connection.CreateCommand();
        cmd.CommandText = "SELECT Id, Title, ModelId, Status, CreatedAt, UpdatedAt FROM Sessions WHERE Id = $id";
        cmd.Parameters.AddWithValue("$id", id.ToString());

        ChatSession? session = null;
        using (var reader = cmd.ExecuteReader())
        {
            if (reader.Read())
            {
                session = ReadSessionRow(reader);
            }
        }

        if (session is null)
        {
            return null;
        }

        using var msgCmd = _connection.CreateCommand();
        msgCmd.CommandText = "SELECT Role, Content, CreatedAt FROM Messages WHERE SessionId = $id ORDER BY Id ASC";
        msgCmd.Parameters.AddWithValue("$id", id.ToString());
        using var msgReader = msgCmd.ExecuteReader();
        while (msgReader.Read())
        {
            session.Messages.Add(new ChatMessage
            {
                Role = Enum.Parse<ChatRole>(msgReader.GetString(0)),
                Content = msgReader.GetString(1),
                CreatedAt = DateTimeOffset.Parse(msgReader.GetString(2)),
            });
        }

        return await Task.FromResult(session);
    }

    public Task AppendMessageAsync(Guid sessionId, ChatMessage message, CancellationToken ct = default)
    {
        using var cmd = _connection.CreateCommand();
        cmd.CommandText =
            "INSERT INTO Messages (SessionId, Role, Content, CreatedAt) VALUES ($sessionId, $role, $content, $createdAt); " +
            "UPDATE Sessions SET UpdatedAt = $createdAt WHERE Id = $sessionId";
        cmd.Parameters.AddWithValue("$sessionId", sessionId.ToString());
        cmd.Parameters.AddWithValue("$role", message.Role.ToString());
        cmd.Parameters.AddWithValue("$content", message.Content);
        cmd.Parameters.AddWithValue("$createdAt", message.CreatedAt.ToString("o"));
        cmd.ExecuteNonQuery();

        return Task.CompletedTask;
    }

    public Task RenameSessionAsync(Guid sessionId, string newTitle, CancellationToken ct = default)
    {
        using var cmd = _connection.CreateCommand();
        cmd.CommandText = "UPDATE Sessions SET Title = $title WHERE Id = $id";
        cmd.Parameters.AddWithValue("$title", newTitle);
        cmd.Parameters.AddWithValue("$id", sessionId.ToString());
        cmd.ExecuteNonQuery();
        return Task.CompletedTask;
    }

    public Task SetArchivedAsync(Guid sessionId, bool archived, CancellationToken ct = default)
    {
        using var cmd = _connection.CreateCommand();
        cmd.CommandText = "UPDATE Sessions SET Status = $status WHERE Id = $id";
        cmd.Parameters.AddWithValue("$status", (archived ? ChatSessionStatus.Archived : ChatSessionStatus.Active).ToString());
        cmd.Parameters.AddWithValue("$id", sessionId.ToString());
        cmd.ExecuteNonQuery();
        return Task.CompletedTask;
    }

    public Task DeleteSessionAsync(Guid sessionId, CancellationToken ct = default)
    {
        using var cmd = _connection.CreateCommand();
        cmd.CommandText = "DELETE FROM Messages WHERE SessionId = $id; DELETE FROM Sessions WHERE Id = $id";
        cmd.Parameters.AddWithValue("$id", sessionId.ToString());
        cmd.ExecuteNonQuery();
        return Task.CompletedTask;
    }

    private static ChatSession ReadSessionRow(SqliteDataReader reader) => new()
    {
        Id = Guid.Parse(reader.GetString(0)),
        Title = reader.GetString(1),
        ModelId = reader.GetString(2),
        Status = Enum.Parse<ChatSessionStatus>(reader.GetString(3)),
        CreatedAt = DateTimeOffset.Parse(reader.GetString(4)),
        UpdatedAt = DateTimeOffset.Parse(reader.GetString(5)),
    };

    public void Dispose() => _connection.Dispose();
}
