namespace OfflineLlm.Core.Engine;

/// <summary>
/// A small curated starting list of well-known instruction-tuned models in
/// quantized GGUF form, sized against a 16GB GPU memory budget. This is deliberately
/// short and editable rather than an exhaustive catalog - the app also accepts any
/// direct .gguf URL the user provides (see the "custom URL" path in the model
/// download UI), so an out-of-date entry here is an inconvenience, not a hard
/// dependency.
/// </summary>
public static class ModelCatalog
{
    public static IReadOnlyList<ModelCatalogEntry> Curated { get; } = new[]
    {
        new ModelCatalogEntry(
            Id: "qwen2.5-14b-instruct-q4_k_m",
            DisplayName: "Qwen2.5 14B Instruct (Q4_K_M)",
            Description: "Strong all-rounder for chat, coding, and reasoning. ~9GB - fits a 16GB GPU with room for a large context.",
            SourceUrl: "https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-GGUF/resolve/main/qwen2.5-14b-instruct-q4_k_m.gguf",
            ApproxSizeGiB: 8.9),

        new ModelCatalogEntry(
            Id: "llama-3.1-8b-instruct-q4_k_m",
            DisplayName: "Llama 3.1 8B Instruct (Q4_K_M)",
            Description: "Smaller footprint, leaves more headroom for a longer context window. ~5GB.",
            SourceUrl: "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
            ApproxSizeGiB: 4.9),

        new ModelCatalogEntry(
            Id: "mistral-7b-instruct-v0.3-q4_k_m",
            DisplayName: "Mistral 7B Instruct v0.3 (Q4_K_M)",
            Description: "Lightweight general-purpose model. ~4.4GB.",
            SourceUrl: "https://huggingface.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF/resolve/main/Mistral-7B-Instruct-v0.3-Q4_K_M.gguf",
            ApproxSizeGiB: 4.4),

        new ModelCatalogEntry(
            Id: "phi-3.5-mini-instruct-q4_k_m",
            DisplayName: "Phi-3.5 Mini Instruct (Q4_K_M)",
            Description: "Small and fast, good for quick answers on modest hardware. ~2.4GB.",
            SourceUrl: "https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/resolve/main/Phi-3.5-mini-instruct-Q4_K_M.gguf",
            ApproxSizeGiB: 2.4),
    };
}
