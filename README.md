# Penguin Post

A lightweight Python utility for local network discovery and messaging via UDP broadcast, built with system tray integration and seamless auto-update capabilities via GitHub Releases.

## Features

- **Local Network Discovery:** Automatically discovers and communicates with other instances running on your local network using UDP broadcasting.
- **System Tray Integration:** Runs quietly in the background without cluttering your taskbar.
- **GitHub Auto-Updates:** Checks for newer versions on GitHub and helps keep your client up to date.
- **Persistent Configuration:** Automatically saves and loads your machine settings locally using a robust absolute path configuration.

---

## Usage (For Normal Users)

If you just want to run Penguin Post without messing with code:
1. Head over to the [Releases](https://github.com/HypnoticPenguin/penguin-post/releases) page.
2. Download the latest `penguin_post.exe`.
3. Place the executable in a folder of your choice and double-click to run it!
4. On its first run, you will be prompted to set a **machine name**, which will be saved locally.

---

## Installation for Development

If you want to run from source or contribute:

**Clone the Repository:**
```bash
git clone https://github.com/HypnoticPenguin/penguin-post.git
cd penguin-post
```

**Install Dependencies:**
Make sure you have Python installed, then install the required packages:
```bash
pip install -r requirements.txt
```

**Run the Application:**
```bash
python penguin_post.py
```

---

## Building an Executable

If you want to package the script into a standalone `.exe` using PyInstaller:

```bash
pyinstaller --noconsole --onefile penguin_post.py
```

*Note: Ensure your `penguin_config.json` is kept in the same directory as your executable.*

---

## Configuration

On its first run, the application will prompt you to set a **machine name**. This is stored locally in `penguin_config.json`.