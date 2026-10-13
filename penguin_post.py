import socket
import threading
import time
import json
import os
import sys
import subprocess
import urllib.request
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from PIL import Image, ImageDraw
import pystray

# Configuration
PORT = 50005
BROADCAST_IP = '<broadcast>'
CURRENT_VERSION = "v1.0.6"
GITHUB_REPO = "HypnoticPenguin/penguin-post"

# Ensure config file resolves relative to the script/exe location, not the working directory
if getattr(sys, 'frozen', False):
    CONFIG_FILE = os.path.join(os.path.dirname(sys.executable), 'penguin_config.json')
else:
    CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'penguin_config.json')

app_running = True
tray_icon = None
my_ip = ""
machine_name = ""

active_peers = {}
peers_lock = threading.Lock()

def get_local_ip():
    """Gets the local machine's IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def manage_windows_startup(enable=True):
    """Adds or removes the compiled .exe from the Windows Startup folder."""
    if not getattr(sys, 'frozen', False):
        return  # Only works when compiled as an .exe

    try:
        startup_folder = os.path.join(os.environ['APPDATA'], r'Microsoft\Windows\Start Menu\Programs\Startup')
        shortcut_path = os.path.join(startup_folder, 'PenguinPost.lnk')
        exe_path = sys.executable

        if enable:
            ps_script = f"""
            $WshShell = New-Object -comObject WScript.Shell
            $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
            $Shortcut.TargetPath = "{exe_path}"
            $Shortcut.Save()
            """
            subprocess.run(["powershell", "-Command", ps_script], capture_output=True)
        else:
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
    except Exception as e:
        print(f"Startup configuration failed: {e}")

def check_startup_status():
    """Checks if the startup shortcut currently exists."""
    if not getattr(sys, 'frozen', False):
        return False
    startup_folder = os.path.join(os.environ['APPDATA'], r'Microsoft\Windows\Start Menu\Programs\Startup')
    return os.path.exists(os.path.join(startup_folder, 'PenguinPost.lnk'))

def load_or_prompt_name():
    """Loads machine name and configures startup on first run."""
    global machine_name
    config_exists = os.path.exists(CONFIG_FILE)
    
    if config_exists:
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                if "machine_name" in data:
                    machine_name = data["machine_name"]
                    return
        except Exception:
            pass
            
    default_name = socket.gethostname()
    
    def prompt():
        global machine_name
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        name = simpledialog.askstring("PenguinPost Setup", "Enter a friendly name for this machine:", initialvalue=default_name, parent=root)
        machine_name = name if name else default_name
        root.destroy()
        
        manage_windows_startup(enable=True)
        
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({"machine_name": machine_name}, f)
        except Exception:
            pass

    prompt()

def toggle_startup(icon, item):
    """Toggles the Windows startup setting from the tray menu."""
    current_status = check_startup_status()
    manage_windows_startup(enable=not current_status)

def check_for_updates():
    """Checks GitHub releases for a newer version and updates automatically if packaged."""
    if not getattr(sys, 'frozen', False):
        return

    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(url, headers={'User-Agent': 'PenguinPost-App'})
        
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            latest_version = data.get("tag_name")
            
            if latest_version and latest_version != CURRENT_VERSION:
                download_url = None
                for asset in data.get("assets", []):
                    if asset["name"].endswith(".exe"):
                        download_url = asset["browser_download_url"]
                        break
                
                if download_url:
                    exe_path = sys.executable
                    temp_path = exe_path + ".new"
                    
                    urllib.request.urlretrieve(download_url, temp_path)
                    
                    batch_script = f"""
                    @echo off
                    timeout /t 2 /nobreak > nul
                    move /y "{temp_path}" "{exe_path}"
                    start "" "{exe_path}"
                    del "%~f0"
                    """
                    bat_path = os.path.join(os.path.dirname(exe_path), "update.bat")
                    with open(bat_path, "w") as b:
                        b.write(batch_script)
                        
                    subprocess.Popen([bat_path], shell=True)
                    os._exit(0)
    except Exception as e:
        print(f"Update check failed: {e}")

def show_large_alert(sender_name, sender_ip, message):
    """Pops up a large, prominent window cleanly without flashing."""
    def alert_window():
        root = tk.Tk()
        root.withdraw()
        root.title(f"PenguinPost Alert ({CURRENT_VERSION})")
        root.geometry("500x300")
        root.attributes('-topmost', True)
        root.configure(bg="#2c3e50")
        
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')

        header = tk.Label(root, text=f"📢 Message from {sender_name} ({sender_ip})", fg="#f1c40f", bg="#2c3e50", font=("Arial", 13, "bold"))
        header.pack(pady=20)

        msg_frame = tk.Frame(root, bg="#34495e")
        msg_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        msg_label = tk.Label(msg_frame, text=message, fg="white", bg="#34495e", font=("Arial", 15), wraplength=450, justify="center")
        msg_label.pack(expand=True, fill="both", padx=10, pady=10)

        btn = tk.Button(root, text="Dismiss", command=root.destroy, bg="#e74c3c", fg="white", font=("Arial", 11, "bold"), relief="flat", padx=20, pady=5)
        btn.pack(pady=15)

        root.deiconify()
        root.mainloop()

    threading.Thread(target=alert_window, daemon=True).start()

def send_network_message(target_ip, message):
    """Sends a UDP message either as a broadcast or unicast to a specific IP."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        payload = f"MSG|{machine_name}|{message}".encode('utf-8')
        
        if target_ip == "ALL":
            sock.sendto(payload, (BROADCAST_IP, PORT))
            show_large_alert(f"{machine_name} (You)", my_ip, message)
        elif target_ip == my_ip:
            sock.sendto(payload, (target_ip, PORT))
            show_large_alert(f"{machine_name} (You)", my_ip, message)
        else:
            sock.sendto(payload, (target_ip, PORT))
        sock.close()
    except Exception as e:
        print(f"Error sending message: {e}")

def network_announcer():
    """Periodically broadcasts presence so other machines find us."""
    while app_running:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            payload = f"ANNOUNCE|{machine_name}".encode('utf-8')
            sock.sendto(payload, (BROADCAST_IP, PORT))
            sock.close()
        except Exception:
            pass
        time.sleep(4)

def listen_for_messages():
    """Background listener for incoming network messages and peer announcements."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(('', PORT))
    except Exception as e:
        print(f"Could not bind to port {PORT}: {e}")
        return

    while app_running:
        try:
            sock.settimeout(1.0)
            data, addr = sock.recvfrom(1024)
            decoded = data.decode('utf-8')
            sender_ip = addr[0]
            
            parts = decoded.split("|", 2)
            msg_type = parts[0]
            
            if msg_type == "ANNOUNCE":
                if len(parts) >= 2 and sender_ip != my_ip:
                    peer_name = parts[1]
                    with peers_lock:
                        active_peers[sender_ip] = {
                            "name": peer_name,
                            "last_seen": time.time()
                        }
            elif msg_type == "MSG":
                if len(parts) >= 3:
                    sender_name = parts[1]
                    message = parts[2]
                    if sender_ip != my_ip:
                        show_large_alert(sender_name, sender_ip, message)
            else:
                if sender_ip != my_ip:
                    show_large_alert("Unknown", sender_ip, decoded)
                    
        except socket.timeout:
            now = time.time()
            with peers_lock:
                stale = [ip for ip, info in active_peers.items() if now - info["last_seen"] > 12]
                for ip in stale:
                    del active_peers[ip]
            continue
        except Exception:
            break
    sock.close()

def open_composer_dialog(icon, item):
    """Opens a custom UI dialog cleanly without flashing."""
    def run_dialog():
        win = tk.Tk()
        win.withdraw()
        win.title(f"PenguinPost {CURRENT_VERSION} - ({machine_name})")
        win.geometry("420x350")
        win.attributes('-topmost', True)
        win.configure(bg="#ecf0f1")
        
        win.update_idletasks()
        width = win.winfo_width()
        height = win.winfo_height()
        x = (win.winfo_screenwidth() // 2) - (width // 2)
        y = (win.winfo_screenheight() // 2) - (height // 2)
        win.geometry(f'{width}x{height}+{x}+{y}')

        tk.Label(win, text="Send Target:", bg="#ecf0f1", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=(15, 0))
        
        target_var = tk.StringVar(value="ALL")
        frame_radio = tk.Frame(win, bg="#ecf0f1")
        frame_radio.pack(anchor="w", padx=20, pady=5)
        
        tk.Radiobutton(frame_radio, text="All Machines (Broadcast)", variable=target_var, value="ALL", bg="#ecf0f1", font=("Arial", 9)).pack(anchor="w")
        tk.Radiobutton(frame_radio, text="Specific Machine:", variable=target_var, value="SPECIFIC", bg="#ecf0f1", font=("Arial", 9)).pack(anchor="w")

        with peers_lock:
            peer_items = [f"{info['name']} ({ip})" for ip, info in active_peers.items()]
        
        if not peer_items:
            peer_items = ["No other machines detected yet..."]

        combo_var = tk.StringVar()
        dropdown = ttk.Combobox(win, textvariable=combo_var, values=peer_items, state="readonly", font=("Arial", 10))
        dropdown.pack(fill="x", padx=40, pady=2)
        if peer_items:
            dropdown.current(0)

        tk.Label(win, text="Message:", bg="#ecf0f1", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=(10, 0))
        msg_entry = tk.Entry(win, font=("Arial", 11))
        msg_entry.pack(fill="x", padx=20, pady=5)
        msg_entry.focus()

        def on_send():
            target_type = target_var.get()
            message_text = msg_entry.get().strip()
            
            if not message_text:
                messagebox.showerror("Error", "Message cannot be empty!", parent=win)
                return
                
            win.destroy()
            
            if target_type == "ALL":
                send_network_message("ALL", message_text)
            else:
                selected_str = combo_var.get()
                if not selected_str or "No other machines" in selected_str:
                    messagebox.showerror("Error", "Please select a valid machine from the dropdown!")
                    return
                target_ip = selected_str.split("(")[-1].rstrip(")")
                send_network_message(target_ip, message_text)

        send_btn = tk.Button(win, text="Send Notification", command=on_send, bg="#27ae60", fg="white", font=("Arial", 10, "bold"), relief="flat", pady=8)
        send_btn.pack(fill="x", padx=20, pady=10)

        # Version footer label inside the composer window
        version_label = tk.Label(win, text=f"PenguinPost {CURRENT_VERSION}", fg="#7f8c8d", bg="#ecf0f1", font=("Arial", 8))
        version_label.pack(side="bottom", pady=5)

        win.deiconify()
        win.mainloop()

    threading.Thread(target=run_dialog, daemon=True).start()

def create_tray_image():
    image = Image.new('RGB', (64, 64), color="#2c3e50")
    dc = ImageDraw.Draw(image)
    dc.rectangle((12, 20, 52, 44), outline="white", width=2)
    dc.line((12, 20, 32, 34), fill="white", width=2)
    dc.line((52, 20, 32, 34), fill="white", width=2)
    return image

def on_quit(icon, item):
    global app_running
    app_running = False
    icon.stop()

def main():
    global my_ip
    my_ip = get_local_ip()
    load_or_prompt_name()

    threading.Thread(target=check_for_updates, daemon=True).start()
    threading.Thread(target=listen_for_messages, daemon=True).start()
    threading.Thread(target=network_announcer, daemon=True).start()

    image = create_tray_image()
    menu = pystray.Menu(
        pystray.MenuItem(f"Send Message ({machine_name})...", open_composer_dialog, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Run at Startup", 
            toggle_startup, 
            checked=lambda item: check_startup_status()
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit)
    )

    # Tray tooltip now includes version number clearly
    tray_tooltip = f"PenguinPost {CURRENT_VERSION} - {machine_name} ({my_ip})"
    tray_icon = pystray.Icon("PenguinPost", image, tray_tooltip, menu)
    tray_icon.run()

if __name__ == '__main__':
    main()