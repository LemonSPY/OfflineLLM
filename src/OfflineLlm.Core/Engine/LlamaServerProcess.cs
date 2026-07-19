using System.Diagnostics;
using System.Net.Sockets;

namespace OfflineLlm.Core.Engine;

public enum ServerLifecycleKind
{
    /// <summary>Serves saved-mode chats. Started lazily, kept running while any saved chat is open.</summary>
    Saved,

    /// <summary>Serves a single offline session. Logging disabled; killed the moment the session ends.</summary>
    Offline,
}

/// <summary>
/// Manages one llama-server.exe child process bound to 127.0.0.1 on a locally-chosen port.
/// Never binds to a non-loopback address — this is a local-only inference backend, not a
/// network service.
/// </summary>
public sealed class LlamaServerProcess : IAsyncDisposable
{
    private readonly string _llamaServerExePath;
    private Process? _process;

    public ServerLifecycleKind Kind { get; }
    public ModelInfo Model { get; }
    public int Port { get; private set; }
    public Uri BaseAddress => new($"http://127.0.0.1:{Port}/");

    public LlamaServerProcess(string llamaServerExePath, ModelInfo model, ServerLifecycleKind kind)
    {
        _llamaServerExePath = llamaServerExePath;
        Model = model;
        Kind = kind;
    }

    public async Task StartAsync(int gpuLayers = 999, int contextSize = 8192, CancellationToken ct = default)
    {
        if (_process is not null)
        {
            throw new InvalidOperationException("Server already started.");
        }

        if (!File.Exists(_llamaServerExePath))
        {
            throw new FileNotFoundException(
                "llama-server.exe not found. Run build/build-llama.ps1 first.", _llamaServerExePath);
        }

        Port = FindFreeLoopbackPort();

        var args = new List<string>
        {
            "--model", Model.FilePath,
            "--host", "127.0.0.1",
            "--port", Port.ToString(),
            "--n-gpu-layers", gpuLayers.ToString(),
            "--ctx-size", contextSize.ToString(),
        };

        // Offline sessions must leave no trace: no request/response logging, no slot save files.
        if (Kind == ServerLifecycleKind.Offline)
        {
            args.Add("--log-disable");
            args.Add("--no-slot-save-path");
        }

        var psi = new ProcessStartInfo
        {
            FileName = _llamaServerExePath,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = Kind != ServerLifecycleKind.Offline,
            RedirectStandardError = Kind != ServerLifecycleKind.Offline,
        };
        foreach (var arg in args)
        {
            psi.ArgumentList.Add(arg);
        }

        _process = Process.Start(psi)
            ?? throw new InvalidOperationException("Failed to start llama-server.exe.");

        await WaitForHealthyAsync(ct);
    }

    private async Task WaitForHealthyAsync(CancellationToken ct)
    {
        using var http = new HttpClient { BaseAddress = BaseAddress, Timeout = TimeSpan.FromSeconds(5) };
        var deadline = DateTime.UtcNow.AddSeconds(60);

        while (DateTime.UtcNow < deadline)
        {
            ct.ThrowIfCancellationRequested();

            if (_process is { HasExited: true })
            {
                throw new InvalidOperationException(
                    $"llama-server.exe exited early with code {_process.ExitCode}.");
            }

            try
            {
                var response = await http.GetAsync("health", ct);
                if (response.IsSuccessStatusCode)
                {
                    return;
                }
            }
            catch (HttpRequestException)
            {
                // server not accepting connections yet
            }

            await Task.Delay(250, ct);
        }

        throw new TimeoutException("llama-server.exe did not become healthy within 60 seconds.");
    }

    private static int FindFreeLoopbackPort()
    {
        using var listener = new TcpListener(System.Net.IPAddress.Loopback, 0);
        listener.Start();
        var port = ((System.Net.IPEndPoint)listener.LocalEndpoint).Port;
        listener.Stop();
        return port;
    }

    public async ValueTask DisposeAsync()
    {
        if (_process is null)
        {
            return;
        }

        try
        {
            if (!_process.HasExited)
            {
                _process.Kill(entireProcessTree: true);
                await _process.WaitForExitAsync();
            }
        }
        catch (InvalidOperationException)
        {
            // process already gone
        }
        finally
        {
            _process.Dispose();
            _process = null;
        }
    }
}
