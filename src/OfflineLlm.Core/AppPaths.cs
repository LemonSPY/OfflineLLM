namespace OfflineLlm.Core;

/// <summary>
/// Central place for the on-disk locations saved-mode data lives in. Offline-mode
/// sessions never use any of these — that's the whole point of offline mode.
/// </summary>
public static class AppPaths
{
    private static string BaseDirectory =>
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "OfflineLlm");

    public static string ChatDatabasePath => Path.Combine(BaseDirectory, "chats.db");

    public static string ModelsDirectory => Path.Combine(BaseDirectory, "models");

    public static string LlamaServerExePath =>
        Path.Combine(AppContext.BaseDirectory, "engine", "llama-server.exe");
}
