using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using OfflineLlm.Core;
using OfflineLlm.Core.Chat;
using OfflineLlm.Core.Engine;
using OfflineLlm.Core.Storage;

namespace OfflineLlm.App.ViewModels;

public enum ChatMode
{
    None,
    Saved,
    Offline,
}

public sealed partial class MainViewModel : ObservableObject, IAsyncDisposable
{
    private readonly SqliteChatStore _chatStore = new(AppPaths.ChatDatabasePath);
    private readonly ModelManager _modelManager = new(AppPaths.ModelsDirectory);

    private LlamaServerProcess? _sharedSavedServer;
    private SavedSessionEngine? _savedEngine;
    private OfflineSessionEngine? _offlineEngine;

    public ObservableCollection<ChatSessionSummary> SavedSessions { get; } = new();
    public ObservableCollection<ChatMessage> CurrentMessages { get; } = new();
    public ObservableCollection<ModelInfo> AvailableModels { get; } = new();

    [ObservableProperty]
    private ModelInfo? _selectedModel;

    [ObservableProperty]
    private ChatMode _mode = ChatMode.None;

    [ObservableProperty]
    private bool _showArchived;

    private Guid? _activeSavedSessionId;

    public string CurrentModeLabel => Mode switch
    {
        ChatMode.Saved => "Saved chat",
        ChatMode.Offline => "Offline chat (no trace — closes when you leave)",
        _ => "No chat open",
    };

    public MainViewModel()
    {
        foreach (var model in _modelManager.ListAvailableModels())
        {
            AvailableModels.Add(model);
        }
    }

    public async Task RefreshSavedSessionsAsync()
    {
        SavedSessions.Clear();
        var sessions = await _chatStore.ListSessionsAsync(includeArchived: ShowArchived);
        foreach (var s in sessions)
        {
            SavedSessions.Add(new ChatSessionSummary { Id = s.Id, Title = s.Title, Status = s.Status });
        }
    }

    public async Task StartNewSavedChatAsync()
    {
        if (SelectedModel is null)
        {
            throw new InvalidOperationException("Select a model first.");
        }

        var session = await _chatStore.CreateSessionAsync("New chat", SelectedModel.Id);
        await OpenSavedChatAsync(session.Id);
        await RefreshSavedSessionsAsync();
    }

    public async Task OpenSavedChatAsync(Guid sessionId)
    {
        await EnsureOfflineSessionClosedAsync();

        var session = await _chatStore.GetSessionAsync(sessionId)
            ?? throw new InvalidOperationException("Session not found.");

        var model = _modelManager.FindById(session.ModelId)
            ?? throw new InvalidOperationException($"Model '{session.ModelId}' is no longer available.");

        await EnsureSharedSavedServerAsync(model);

        var chatEngine = new Core.Chat.ChatEngine(_sharedSavedServer!);
        _savedEngine = new SavedSessionEngine(_chatStore, chatEngine, session);
        _activeSavedSessionId = sessionId;
        Mode = ChatMode.Saved;

        CurrentMessages.Clear();
        foreach (var m in session.Messages)
        {
            CurrentMessages.Add(m);
        }
    }

    public async Task StartNewOfflineChatAsync()
    {
        if (SelectedModel is null)
        {
            throw new InvalidOperationException("Select a model first.");
        }

        await EnsureOfflineSessionClosedAsync();

        _offlineEngine = await OfflineSessionEngine.StartAsync(AppPaths.LlamaServerExePath, SelectedModel);
        _activeSavedSessionId = null;
        Mode = ChatMode.Offline;
        CurrentMessages.Clear();
    }

    public async Task SendMessageAsync(string text)
    {
        if (string.IsNullOrWhiteSpace(text))
        {
            return;
        }

        if (Mode == ChatMode.Offline && _offlineEngine is not null)
        {
            var userMsg = new ChatMessage { Role = ChatRole.User, Content = text };
            CurrentMessages.Add(userMsg);
            var assistantMsg = new ChatMessage { Role = ChatRole.Assistant, Content = string.Empty };
            CurrentMessages.Add(assistantMsg);

            await foreach (var chunk in _offlineEngine.SendAsync(text))
            {
                assistantMsg.Content += chunk;
            }
        }
        else if (Mode == ChatMode.Saved && _savedEngine is not null)
        {
            var userMsg = new ChatMessage { Role = ChatRole.User, Content = text };
            CurrentMessages.Add(userMsg);
            var assistantMsg = new ChatMessage { Role = ChatRole.Assistant, Content = string.Empty };
            CurrentMessages.Add(assistantMsg);

            await foreach (var chunk in _savedEngine.SendAsync(text))
            {
                assistantMsg.Content += chunk;
            }

            await RefreshSavedSessionsAsync();
        }
    }

    public async Task ArchiveSessionAsync(Guid sessionId, bool archived)
    {
        await _chatStore.SetArchivedAsync(sessionId, archived);
        await RefreshSavedSessionsAsync();
    }

    public async Task DeleteSessionAsync(Guid sessionId)
    {
        if (_activeSavedSessionId == sessionId)
        {
            await CloseCurrentChatAsync();
        }

        await _chatStore.DeleteSessionAsync(sessionId);
        await RefreshSavedSessionsAsync();
    }

    /// <summary>
    /// Leaving an offline chat (closing it or navigating away) tears down its
    /// server process and discards its transcript immediately — that's the
    /// entire point of offline mode.
    /// </summary>
    public async Task CloseCurrentChatAsync()
    {
        await EnsureOfflineSessionClosedAsync();
        _savedEngine = null;
        _activeSavedSessionId = null;
        Mode = ChatMode.None;
        CurrentMessages.Clear();
    }

    private async Task EnsureOfflineSessionClosedAsync()
    {
        if (_offlineEngine is not null)
        {
            await _offlineEngine.DisposeAsync();
            _offlineEngine = null;
        }
    }

    private async Task EnsureSharedSavedServerAsync(ModelInfo model)
    {
        if (_sharedSavedServer is not null && _sharedSavedServer.Model.Id == model.Id)
        {
            return;
        }

        if (_sharedSavedServer is not null)
        {
            await _sharedSavedServer.DisposeAsync();
        }

        _sharedSavedServer = new LlamaServerProcess(AppPaths.LlamaServerExePath, model, ServerLifecycleKind.Saved);
        await _sharedSavedServer.StartAsync();
    }

    public async ValueTask DisposeAsync()
    {
        await EnsureOfflineSessionClosedAsync();

        if (_sharedSavedServer is not null)
        {
            await _sharedSavedServer.DisposeAsync();
        }

        _chatStore.Dispose();
    }
}
