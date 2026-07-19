namespace OfflineLlm.Core.Engine;

/// <summary>
/// Discovers locally available .gguf models. Model choice is deliberately left to the
/// user rather than a hardcoded default — this just lists what's on disk.
/// </summary>
public sealed class ModelManager
{
    private readonly string _modelsDirectory;

    public ModelManager(string modelsDirectory)
    {
        _modelsDirectory = modelsDirectory;
        Directory.CreateDirectory(_modelsDirectory);
    }

    public IReadOnlyList<ModelInfo> ListAvailableModels()
    {
        if (!Directory.Exists(_modelsDirectory))
        {
            return Array.Empty<ModelInfo>();
        }

        return Directory.EnumerateFiles(_modelsDirectory, "*.gguf", SearchOption.AllDirectories)
            .Select(path =>
            {
                var fi = new FileInfo(path);
                var id = Path.GetFileNameWithoutExtension(path);
                return new ModelInfo(id, id, path, fi.Length);
            })
            .OrderBy(m => m.DisplayName, StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    public ModelInfo? FindById(string id) =>
        ListAvailableModels().FirstOrDefault(m => string.Equals(m.Id, id, StringComparison.OrdinalIgnoreCase));
}
