using Microsoft.UI.Xaml;
using Microsoft.Windows.ApplicationModel.DynamicDependency;

namespace OfflineLlm.App;

/// <summary>
/// Explicit entry point because this app is deployed unpackaged (no MSIX, installed
/// via the WiX MSI instead) — the Windows App SDK bootstrapper has to be initialized
/// by hand before any WinUI type is touched.
/// </summary>
public static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        Bootstrap.Initialize(0x00010005, "1.5");

        try
        {
            Application.Start(_ =>
            {
                var context = new global::Microsoft.UI.Dispatching.DispatcherQueueSynchronizationContext(
                    global::Microsoft.UI.Dispatching.DispatcherQueue.GetForCurrentThread());
                System.Threading.SynchronizationContext.SetSynchronizationContext(context);
                _ = new App();
            });
        }
        finally
        {
            Bootstrap.Shutdown();
        }

        return 0;
    }
}
