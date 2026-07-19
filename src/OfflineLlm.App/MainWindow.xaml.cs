using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Input;
using OfflineLlm.App.ViewModels;
using Windows.System;

namespace OfflineLlm.App;

public sealed partial class MainWindow : Window
{
    public MainViewModel ViewModel { get; } = new();

    public MainWindow()
    {
        InitializeComponent();
        Closed += OnWindowClosed;
        _ = ViewModel.RefreshSavedSessionsAsync();
    }

    private async void OnDownloadModelsClick(object sender, RoutedEventArgs e)
    {
        var dialog = new DownloadModelsDialog(ViewModel) { XamlRoot = Content.XamlRoot };
        await dialog.ShowAsync();
    }

    private async void OnNewSavedChatClick(object sender, RoutedEventArgs e)
    {
        try
        {
            await ViewModel.StartNewSavedChatAsync();
        }
        catch (Exception ex)
        {
            await ShowErrorAsync(ex.Message);
        }
    }

    private async void OnNewOfflineChatClick(object sender, RoutedEventArgs e)
    {
        try
        {
            await ViewModel.StartNewOfflineChatAsync();
        }
        catch (Exception ex)
        {
            await ShowErrorAsync(ex.Message);
        }
    }

    private async void OnSavedChatSelected(object sender, SelectionChangedEventArgs e)
    {
        if (SavedChatsList.SelectedItem is ChatSessionSummary summary)
        {
            try
            {
                await ViewModel.OpenSavedChatAsync(summary.Id);
            }
            catch (Exception ex)
            {
                await ShowErrorAsync(ex.Message);
            }
        }
    }

    private async void OnSessionOverflowClick(object sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: ChatSessionSummary summary })
        {
            return;
        }

        var flyout = new MenuFlyout();

        var archiveItem = new MenuFlyoutItem { Text = summary.Status == Core.Chat.ChatSessionStatus.Archived ? "Unarchive" : "Archive" };
        archiveItem.Click += async (_, _) =>
            await ViewModel.ArchiveSessionAsync(summary.Id, summary.Status != Core.Chat.ChatSessionStatus.Archived);
        flyout.Items.Add(archiveItem);

        var deleteItem = new MenuFlyoutItem { Text = "Delete" };
        deleteItem.Click += async (_, _) => await ViewModel.DeleteSessionAsync(summary.Id);
        flyout.Items.Add(deleteItem);

        flyout.ShowAt((FrameworkElement)sender);
    }

    private async void OnShowArchivedToggled(object sender, RoutedEventArgs e)
    {
        ViewModel.ShowArchived = ShowArchivedToggle.IsOn;
        await ViewModel.RefreshSavedSessionsAsync();
    }

    private async void OnSendClick(object sender, RoutedEventArgs e)
    {
        await SendCurrentInputAsync();
    }

    private async void OnMessageInputKeyDown(object sender, KeyRoutedEventArgs e)
    {
        if (e.Key == VirtualKey.Enter)
        {
            e.Handled = true;
            await SendCurrentInputAsync();
        }
    }

    private async Task SendCurrentInputAsync()
    {
        var text = MessageInput.Text;
        MessageInput.Text = string.Empty;

        try
        {
            await ViewModel.SendMessageAsync(text);
        }
        catch (Exception ex)
        {
            await ShowErrorAsync(ex.Message);
        }
    }

    private async void OnWindowClosed(object sender, WindowEventArgs e)
    {
        // Closing the app must tear down any offline session so nothing lingers.
        await ViewModel.DisposeAsync();
    }

    private async Task ShowErrorAsync(string message)
    {
        var dialog = new ContentDialog
        {
            Title = "Something went wrong",
            Content = message,
            CloseButtonText = "OK",
            XamlRoot = Content.XamlRoot,
        };
        await dialog.ShowAsync();
    }
}
