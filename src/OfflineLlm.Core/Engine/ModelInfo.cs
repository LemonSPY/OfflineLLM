namespace OfflineLlm.Core.Engine;

public sealed record ModelInfo(string Id, string DisplayName, string FilePath, long FileSizeBytes)
{
    public double FileSizeGiB => FileSizeBytes / 1024.0 / 1024.0 / 1024.0;
}
