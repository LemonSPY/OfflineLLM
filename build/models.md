# Adding models

`ModelManager` (see [src/OfflineLlm.Core/Engine/ModelManager.cs](../src/OfflineLlm.Core/Engine/ModelManager.cs)) scans `%LocalAppData%\OfflineLlm\models\` for `.gguf` files and lists whatever it finds in the app's model picker — there's no hardcoded default model.

To add a model:

1. Download a quantized `.gguf` model file (Hugging Face hosts many pre-quantized GGUF conversions of popular open models).
2. Drop it into `%LocalAppData%\OfflineLlm\models\`.
3. Restart the app or reopen the model picker — it re-scans the directory each time it's listed.

## Sizing against 16GB of GPU memory

Rule of thumb: leave headroom for the KV-cache on top of the model file's size. As a rough guide for a 16GB budget:

- Q4-quantized ~13-14B parameter models land around 8-9GB — comfortable, leaves several GB for a large context window.
- Q4-quantized ~8B parameter models land around 5-6GB — more headroom, useful for longer contexts or running alongside other GPU workloads.
- Avoid Q4-quantized 30B+ models on a 16GB budget unless using a very short context length — they'll leave little to no room for KV-cache.

`ModelInfo.FileSizeGiB` is surfaced in the picker precisely so this tradeoff is visible before you load a model.
