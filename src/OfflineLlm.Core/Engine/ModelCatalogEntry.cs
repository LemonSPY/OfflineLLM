namespace OfflineLlm.Core.Engine;

/// <summary>
/// A downloadable model listing. SourceUrl points directly at a .gguf file (Hugging
/// Face's /resolve/main/ links work well here since they redirect straight to the
/// file bytes). Catalog entries are a convenience starting point, not a locked-in
/// list - file names and repos on Hugging Face do change over time, so treat
/// ModelCatalog.Curated as "known good as of when this was written" and prefer
/// letting the user paste any direct .gguf URL too (see ModelDownloadService).
/// </summary>
public sealed record ModelCatalogEntry(
    string Id,
    string DisplayName,
    string Description,
    string SourceUrl,
    double ApproxSizeGiB);
