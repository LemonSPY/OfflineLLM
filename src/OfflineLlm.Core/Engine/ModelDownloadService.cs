namespace OfflineLlm.Core.Engine;

public sealed record DownloadProgressInfo(long BytesReceived, long? TotalBytes)
{
    public double? FractionComplete => TotalBytes is > 0 ? (double)BytesReceived / TotalBytes.Value : null;
}

/// <summary>
/// Downloads a .gguf model file into the models directory that ModelManager scans.
/// Writes to a ".partial" file and only renames it to the final name once the
/// download completes successfully, so a cancelled/failed download never shows up
/// as a selectable (but truncated/corrupt) model.
/// </summary>
public sealed class ModelDownloadService
{
    private static readonly HttpClient Http = new()
    {
        Timeout = Timeout.InfiniteTimeSpan,
    };

    private readonly string _modelsDirectory;

    public ModelDownloadService(string modelsDirectory)
    {
        _modelsDirectory = modelsDirectory;
        Directory.CreateDirectory(_modelsDirectory);
    }

    public async Task<string> DownloadAsync(
        string sourceUrl,
        string fileName,
        IProgress<DownloadProgressInfo>? progress = null,
        CancellationToken ct = default)
    {
        if (!fileName.EndsWith(".gguf", StringComparison.OrdinalIgnoreCase))
        {
            fileName += ".gguf";
        }

        var finalPath = Path.Combine(_modelsDirectory, fileName);
        var partialPath = finalPath + ".partial";

        using var response = await Http.GetAsync(sourceUrl, HttpCompletionOption.ResponseHeadersRead, ct);
        response.EnsureSuccessStatusCode();

        var totalBytes = response.Content.Headers.ContentLength;

        await using (var httpStream = await response.Content.ReadAsStreamAsync(ct))
        await using (var fileStream = new FileStream(partialPath, FileMode.Create, FileAccess.Write, FileShare.None, bufferSize: 1 << 20, useAsync: true))
        {
            var buffer = new byte[1 << 20];
            long bytesReceived = 0;
            int read;

            while ((read = await httpStream.ReadAsync(buffer, ct)) > 0)
            {
                await fileStream.WriteAsync(buffer.AsMemory(0, read), ct);
                bytesReceived += read;
                progress?.Report(new DownloadProgressInfo(bytesReceived, totalBytes));
            }
        }

        File.Move(partialPath, finalPath, overwrite: true);
        return finalPath;
    }
}
