# Lone Wolf Action Assistant 3.1.2

## Installation

The installer asks whether to install for the current Windows user or everyone using the computer.

- **Current user:** no administrator access is normally required. The app and books belong to that Windows account.
- **All users:** administrator approval is required. The application is installed under Program Files and books are shared through ProgramData.

Every player's saves and preferences remain private under that player's Local AppData folder, even in an all-users installation.

## WebView2

The desktop window requires Microsoft Edge WebView2 Runtime. Windows 11 normally includes it.

If setup cannot find WebView2, it offers to run Microsoft's Evergreen Bootstrapper. You may accept, or stop setup and install WebView2 yourself before trying again.

## Adding books

Project Aon book files are not included.

During installation, you may select:

- A folder containing extracted Project Aon books.
- A downloaded Project Aon ZIP.

You can also add books later:

1. Open **Install Books** in the application.
2. Choose **Import ZIP Files** or **Import Extracted Folder**.
3. The app validates each book and copies it into managed storage.

A valid book folder includes at least `title.htm` and `sect1.htm`. The expected layout resembles:

```text
books\lw\01fftd\title.htm
books\lw\01fftd\sect1.htm
```

Use **Open Managed Books Folder** when you need direct access to the selected storage location.

## Saves and upgrades

Saves are stored separately from the installed program. Upgrading or uninstalling the application does not intentionally remove books or player saves.

The app automatically creates missing state folders on launch. Diagnostic logs are under:

```text
%LOCALAPPDATA%\Lone Wolf Action Assistant\logs
```

## Embedded terminal

The Assistant page retains the original Lone Wolf command-line terminal. It runs inside the desktop application through a local WebSocket and Windows pseudo-terminal. No separate Python installation is required.
