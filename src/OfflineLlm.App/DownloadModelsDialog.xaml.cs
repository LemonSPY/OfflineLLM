using System.Linq;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using OfflineLlm.App.ViewModels;
using OfflineLlm.Core.Engine;

namespace OfflineLlm.App;

public sealed partial class DownloadModelsDialog : ContentDialog
{
    public MainViewModel ViewModel { get; }

    public DownloadModelsDialog(MainViewModel viewModel)
    {
        ViewModel = viewModel;
        InitializeComponent();
    }

    private async void OnDownloadCatalogEntryClick(object sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: ModelCatalogEntry entry })
        {
            return;
        }

        try
        {
            await ViewModel.DownloadModelAsync(entry.SourceUrl, entry.Id + ".gguf");
        }
        catch (Exception ex)
        {
            await ShowDownloadErrorAsync(ex.Message);
        }
    }

    private async void OnDownloadCustomUrlClick(object sender, RoutedEventArgs e)
    {
        var url = CustomUrlInput.Text.Trim();
        if (string.IsNullOrEmpty(url))
        {
            return;
        }

        var fileName = url.Split('/', '?').LastOrDefault(segment => !string.IsNullOrWhiteSpace(segment))
            ?? $"model-{DateTime.UtcNow:yyyyMMddHHmmss}";

        try
        {
            await ViewModel.DownloadModelAsync(url, fileName);
        }
        catch (Exception ex)
        {
            await ShowDownloadErrorAsync(ex.Message);
        }
    }

    private async Task ShowDownloadErrorAsync(string message)
    {
        var dialog = new ContentDialog
        {
            Title = "Download failed",
            Content = message,
            CloseButtonText = "OK",
            XamlRoot = XamlRoot,
        };
        await dialog.ShowAsync();
    }
}
