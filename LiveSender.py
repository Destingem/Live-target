import tkinter as tk
from tkinter import filedialog, messagebox
import os
import xml.etree.ElementTree as ET
import hashlib
import time
import json
from SetaFaultHandler import SetaFaultHandler  # Updated import
import glob  # Import glob
import logging
import threading
import subprocess  # Add this import
import uuid  # Add this import for unique IDs
import datetime  # Add this import for timestamps

# Configure basic logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

fault_handler = SetaFaultHandler()  # Updated instantiation

def uloz_config():
    """Uloží aktuální nastavení do config souboru."""
    try:
        config_data = {
            "seta_adresar": seta_adresar,
            "uzivatelske_id": uzivatelske_id,
            "heslo": heslo,
            "seta_path": seta_path
        }
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_filepath = os.path.join(script_dir, "config.txt")
        with open(config_filepath, 'w') as config_file:
            json.dump(config_data, config_file)
    except Exception as e:
        messagebox.showerror("Chyba", f"Chyba při ukládání nastavení: {e}")

def vybrat_adresar():
    """Otevře dialog pro výběr adresáře a uloží cestu."""
    global seta_adresar
    adresar = filedialog.askdirectory()
    if adresar:
        seta_adresar = adresar
        cesta_entry.delete(0, tk.END)
        cesta_entry.insert(0, seta_adresar)
        uloz_config()  # Automatické uložení při změně

def vybrat_seta_exe():
    """Otevře dialog pro výběr SETA.exe."""
    global seta_path
    filepath = filedialog.askopenfilename(
        title="Vybrat SETA.exe",
        filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
    )
    if filepath:
        seta_path = filepath
        seta_path_entry.delete(0, tk.END)
        seta_path_entry.insert(0, seta_path)
        uloz_config()  # Automatické uložení při změně

def on_entry_change(*args):
    """Handler pro změny v entry polích."""
    global uzivatelske_id, heslo
    uzivatelske_id = id_entry.get()
    heslo = heslo_entry.get()
    uloz_config()  # Automatické uložení při změně

def ulozit_nastaveni():
    """Uloží nastavení a spustí monitorování."""
    global seta_adresar, uzivatelske_id, heslo, monitoring_thread, seta_path
    seta_adresar = cesta_entry.get()
    uzivatelske_id = id_entry.get()
    heslo = heslo_entry.get()
    seta_path = seta_path_entry.get()

    if not all([seta_adresar, uzivatelske_id, heslo, seta_path]):
        messagebox.showerror("Chyba", "Prosím vyplňte všechna pole.")
        return

    if not os.path.isdir(seta_adresar):
        messagebox.showerror("Chyba", "Zadaný adresář neexistuje.")
        return

    if not os.path.isfile(seta_path):
        messagebox.showerror("Chyba", "SETA.exe nebyla nalezena.")
        return

    config_data = {
        "seta_adresar": seta_adresar,
        "uzivatelske_id": uzivatelske_id,
        "heslo": heslo,
        "seta_path": seta_path
    }

    try:
        # Save config
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_filepath = os.path.join(script_dir, "config.txt")
        with open(config_filepath, 'w') as config_file:
            json.dump(config_data, config_file)

        # Clean up existing file
        monitor_filepath = get_monitor_filename(seta_adresar, uzivatelske_id)
        smaz_existujici_soubor(monitor_filepath)

        # Launch SETA.exe
        if not spust_seta(seta_path):
            return

        # Start monitoring
        if monitoring_thread and monitoring_thread.is_alive():
            stop_monitoring.set()
            monitoring_thread.join(timeout=1.0)
        
        stop_monitoring.clear()
        monitoring_thread = threading.Thread(
            target=lambda: monitoruj_a_nahravej(seta_adresar, uzivatelske_id, heslo, root),
            daemon=True
        )
        monitoring_thread.start()
        
        nastaveni_ulozeno_label.config(text="Monitoring spuštěn...")
    except Exception as e:
        messagebox.showerror("Chyba", f"Chyba při ukládání nastavení: {e}")

def spust_seta(seta_path):
    """Spustí SETA.exe aplikaci."""
    try:
        # Check if we're on Windows
        if os.name == 'nt':
            subprocess.Popen([seta_path])
            logging.info(f"SETA aplikace spuštěna: {seta_path}")
            return True
        else:
            message = "Automatické spuštění SETA.exe není na macOS podporováno.\nProsím spusťte SETA aplikaci manuálně."
            messagebox.showinfo("Informace", message)
            logging.info("macOS detekován - SETA.exe nelze automaticky spustit")
            return True  # Return True to allow monitoring to continue
    except Exception as e:
        logging.error(f"Chyba při spouštění SETA aplikace: {e}")
        messagebox.showerror("Chyba", f"Nelze spustit SETA aplikaci: {e}")
        return False

def get_monitor_filename(adresar, uzivatelske_id):
    """Vytvoří celou cestu k monitorovanému souboru."""
    filename = f"Match_{uzivatelske_id}.tch"
    return os.path.join(adresar, filename)

def smaz_existujici_soubor(filepath):
    """Smaže existující soubor pokud existuje."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logging.info(f"Existující soubor smazán: {filepath}")
    except Exception as e:
        logging.error(f"Chyba při mazání souboru: {e}")

def monitoruj_a_nahravej(adresar, uzivatelske_id, heslo, root):
    """Monitoruje konkrétní soubor a nahrává změny."""
    def update_label(text):
        root.after(0, lambda: nastaveni_ulozeno_label.config(text=text))

    monitor_filepath = get_monitor_filename(adresar, uzivatelske_id)
    last_size = 0

    print(f"Monitoruji soubor: {monitor_filepath}")
    
    while not stop_monitoring.is_set():
        try:
            if os.path.exists(monitor_filepath):
                current_size = os.path.getsize(monitor_filepath)
                if current_size > last_size:  # File has grown
                    data = parsuj_tch_soubor(monitor_filepath)
                    if data:
                        nahraj_data_do_cloudu(data, uzivatelske_id, heslo, os.path.basename(monitor_filepath))
                        print(f"Nová data nahrána z {monitor_filepath}")
                    last_size = current_size

        except Exception as e:
            logging.error(f"Chyba při monitorování souboru: {str(e)}")
        
        time.sleep(1)  # Check every second

def hash_souboru(filepath):
    """Vypočítá hash souboru pro detekci změn a duplicit."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as file:
        buf = file.read()
        hasher.update(buf)
    return hasher.hexdigest()

def parsuj_tch_soubor(filepath):
    """Parsuje .tch soubor a extrahuje data."""
    logging.debug(f"Parsování TCH souboru: {filepath}")
    try:
        # Check if file is empty or too small to be valid XML
        if os.path.getsize(filepath) < 50:  # Increased minimum size for valid SETA XML
            fault_handler.log_fault(f"Soubor je příliš malý nebo prázdný: {filepath}")
            logging.warning(f"Soubor je příliš malý: {filepath}")
            return None

        tree = ET.parse(filepath)
        root = tree.getroot()
        
        # Validate root structure and required elements
        game_info = root.find('Game_information')
        if game_info is None:
            fault_handler.log_fault(f"Chybí Game_information element: {filepath}")
            logging.warning(f"Chybí Game_information element: {filepath}")
            return None
            
        # Check if user_name is present and not empty
        user_name = game_info.find('user_name')
        if user_name is None or not user_name.text:
            fault_handler.log_fault(f"Prázdné nebo chybějící user_name: {filepath}")
            logging.warning(f"Prázdné nebo chybějící user_name: {filepath}")
            return None

        game_data = root.find('GameData')
        if game_data is None or len(game_data) == 0:
            fault_handler.log_fault(f"Prázdný nebo chybějící GameData element: {filepath}")
            logging.warning(f"Prázdný nebo chybějící GameData element: {filepath}")
            return None
            
        shots = []
        for data_element in game_data:
            try:
                shot_data = {
                    'x': float(data_element.find('x_data').text),
                    'y': float(data_element.find('y_data').text),
                    'time': data_element.find('time_stamp').text
                }
                shots.append(shot_data)
            except (ValueError, AttributeError) as e:
                fault_handler.log_fault(f"Neplatná data v záznamu {data_element.tag}: {str(e)}")
                logging.warning(f"Neplatná data v záznamu {data_element.tag}: {str(e)}")
                continue
            
        if not shots:
            fault_handler.log_fault(f"Žádná validní data nebyla nalezena: {filepath}")
            logging.warning(f"Žádná validní data nebyla nalezena: {filepath}")
            return None
                
        logging.debug(f"Data extrahována: {shots}")
        return shots
            
    except ET.ParseError as e:
        fault_handler.log_fault(f"Chyba při parsování XML souboru {filepath}: {str(e)}")
        logging.error(f"Chyba při parsování XML souboru {filepath}: {str(e)}")
        return None
    except Exception as e:
        fault_handler.log_fault(f"Neočekávaná chyba při zpracování souboru {filepath}: {str(e)}")
        logging.error(f"Neočekávaná chyba při zpracování souboru {filepath}: {str(e)}")
        return None

def nahraj_data_do_cloudu(data, uzivatelske_id, heslo, filename):
    """Nahrává data do cloudu s race_id."""
    if not race_session.is_running:
        return  # Don't send data if no race is running
        
    print(f"Simulace nahrávání dat pro uživatele {uzivatelske_id}, závod {race_session.race_id}")
    print(f"Data: {data}")
    # TODO: Add race_id to the API request when implementing real cloud upload

def find_usb_drive_config(filename="config.txt"):
    """
    Scans for connected USB drives and checks if the config file exists on any of them.
    Returns the path to the config file if found, otherwise None.
    """
    logging.debug("Hledám USB disky...")
    drives = []

    if os.name == 'nt':  # Windows
        # Improved Windows drive detection (requires pywin32)
        try:
            import win32api
            drive_letters = [d for d in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if win32api.GetDriveType(d + ":\\") == win32api.DRIVE_REMOVABLE]
            drives = [d + ":\\" for d in drive_letters]
        except ImportError:
            logging.warning("pywin32 není nainstalováno. Používám základní detekci disků.")
            drives = [d + ":\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(d + ":")]
    else:  # macOS
        volumes_path = "/Volumes"
        if os.path.exists(volumes_path):
            try:
                # Get all items in /Volumes
                items = os.listdir(volumes_path)
                logging.debug(f"Nalezené položky v /Volumes: {items}")
                
                # Filter out system volumes and hidden items
                volumes = [item for item in items 
                         if not item.startswith('.') 
                         and os.path.isdir(os.path.join(volumes_path, item))
                         and item != "Macintosh HD"]  # Skip main system drive
                
                drives = [os.path.join(volumes_path, vol) for vol in volumes]
                logging.debug(f"Filtrované disky: {drives}")
            except OSError as e:
                logging.error(f"Chyba při čtení /Volumes: {e}")
                drives = []
        else:
            logging.warning("/Volumes neexistuje")
            drives = []

    logging.debug(f"Nalezené potenciální disky: {drives}")

    for drive in drives:
        config_path = os.path.join(drive, filename)
        logging.debug(f"Kontroluji cestu: {config_path}")
        if os.path.exists(config_path):
            logging.debug(f"Konfigurační soubor nalezen na: {config_path}")
            return config_path

    logging.debug("Konfigurační soubor nenalezen na žádném USB disku.")
    return None


def nacti_nastaveni():
    """Načte nastavení z config.txt, nejprve z USB, pokud existuje, jinak z lokálního adresáře."""
    config_filepath = find_usb_drive_config()  # Check USB drives first

    if not config_filepath:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_filepath = os.path.join(script_dir, "config.txt")  # Fallback to local config

    try:
        if os.path.exists(config_filepath):
            with open(config_filepath, 'r') as config_file:
                config_data = json.load(config_file)
                global seta_adresar, uzivatelske_id, heslo, seta_path
                seta_adresar = config_data.get("seta_adresar", "")
                uzivatelske_id = config_data.get("uzivatelske_id", "")
                heslo = config_data.get("heslo", "")
                seta_path = config_data.get("seta_path", "")

                cesta_entry.delete(0, tk.END)
                cesta_entry.insert(0, seta_adresar)
                id_entry.delete(0, tk.END)
                id_entry.insert(0, uzivatelske_id)
                heslo_entry.delete(0, tk.END)
                heslo_entry.insert(0, heslo)
                seta_path_entry.delete(0, tk.END)
                seta_path_entry.insert(0, seta_path)
                
                # Pouze na Windows spouštíme SETA.exe automaticky
                if os.name == 'nt' and seta_path and os.path.isfile(seta_path):
                    spust_seta(seta_path)
                elif seta_path:
                    messagebox.showinfo("Informace", "Prosím spusťte SETA aplikaci manuálně.")
        else:
            nastaveni_ulozeno_label.config(text="Config.txt nenalezen. Výchozí nastavení.")
    except Exception as e:
        messagebox.showerror("Chyba", f"Chyba při načítání nastavení z config.txt: {e}")
        nastaveni_ulozeno_label.config(text="Chyba při načítání nastavení!")


def vytvor_token():
    """Vytvoří osobní token (config.txt) na vybraném USB disku."""
    global uzivatelske_id, heslo, seta_adresar

    # Get current settings from the GUI
    seta_adresar = cesta_entry.get()
    uzivatelske_id = id_entry.get()
    heslo = heslo_entry.get()

    if not seta_adresar or not uzivatelske_id or not heslo:
        messagebox.showerror("Chyba", "Prosím vyplňte všechna pole nastavení.")
        return

    # Ask user to select a directory (the USB drive)
    usb_drive_path = filedialog.askdirectory(title="Vyberte USB disk pro uložení tokenu")
    if not usb_drive_path:
        return  # User cancelled

    config_data = {
        "seta_adresar": seta_adresar,
        "uzivatelske_id": uzivatelske_id,
        "heslo": heslo
    }

    config_filepath = os.path.join(usb_drive_path, "config.txt")

    try:
        with open(config_filepath, 'w') as config_file:
            json.dump(config_data, config_file)
        messagebox.showinfo("Úspěch", f"Osobní token byl uložen na {usb_drive_path}")
    except Exception as e:
        messagebox.showerror("Chyba", f"Chyba při vytváření tokenu: {e}")

# Add at the top level of the script, before the GUI initialization
stop_monitoring = threading.Event()
monitoring_thread = None

class RaceSession:
    def __init__(self):
        self.race_id = None
        self.start_time = None
        self.is_running = False

    def start(self):
        """Starts a new race session with unique ID."""
        self.race_id = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        self.start_time = datetime.datetime.now()
        self.is_running = True
        return self.race_id

    def stop(self):
        """Stops current race session."""
        self.is_running = False
        self.race_id = None
        self.start_time = None

def start_recording():
    """Spustí nové nahrávání závodu."""
    global race_session, monitoring_thread
    
    if not all([seta_adresar, uzivatelske_id, heslo]):
        messagebox.showerror("Chyba", "Nejprve vyplňte všechna nastavení.")
        return

    if race_session.is_running:
        messagebox.showwarning("Varování", "Nahrávání již běží!")
        return

    try:
        # Clean up existing file and start new session
        monitor_filepath = get_monitor_filename(seta_adresar, uzivatelske_id)
        smaz_existujici_soubor(monitor_filepath)
        
        race_id = race_session.start()
        
        # Start monitoring if not already running
        if not monitoring_thread or not monitoring_thread.is_alive():
            stop_monitoring.clear()
            monitoring_thread = threading.Thread(
                target=lambda: monitoruj_a_nahravej(seta_adresar, uzivatelske_id, heslo, root),
                daemon=True
            )
            monitoring_thread.start()
        
        nastaveni_ulozeno_label.config(text=f"Nahrávání spuštěno (Závod ID: {race_id})")
        start_button.config(state=tk.DISABLED)
        stop_button.config(state=tk.NORMAL)
        
    except Exception as e:
        messagebox.showerror("Chyba", f"Chyba při spouštění nahrávání: {e}")

def stop_recording():
    """Zastaví nahrávání závodu."""
    global race_session
    
    if not race_session.is_running:
        messagebox.showwarning("Varování", "Žádné nahrávání neběží!")
        return

    try:
        race_session.stop()
        monitor_filepath = get_monitor_filename(seta_adresar, uzivatelske_id)
        smaz_existujici_soubor(monitor_filepath)
        
        nastaveni_ulozeno_label.config(text="Nahrávání zastaveno")
        start_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.DISABLED)
        
    except Exception as e:
        messagebox.showerror("Chyba", f"Chyba při zastavování nahrávání: {e}")

# Add at the top level, before GUI initialization
race_session = RaceSession()

# GUI okno
root = tk.Tk()
root.title("SETA Data Uploader")

seta_adresar = ""
uzivatelske_id = ""
heslo = ""
seta_path = ""

# Vytvoření a rozmístění GUI prvků
cesta_label = tk.Label(root, text="Cesta k adresáři SETA:")
cesta_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
cesta_entry = tk.Entry(root, width=50)
cesta_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
vybrat_button = tk.Button(root, text="Vybrat adresář", command=vybrat_adresar)
vybrat_button.grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)

id_label = tk.Label(root, text="Uživatelské ID:")
id_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
id_entry = tk.Entry(root, width=20)
id_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
id_entry.bind('<KeyRelease>', on_entry_change)

heslo_label = tk.Label(root, text="Heslo:")
heslo_label.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
heslo_entry = tk.Entry(root, width=20, show="*")
heslo_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
heslo_entry.bind('<KeyRelease>', on_entry_change)

seta_path_label = tk.Label(root, text="Cesta k SETA.exe:")
seta_path_label.grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
seta_path_entry = tk.Entry(root, width=50)
seta_path_entry.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
seta_path_button = tk.Button(root, text="Vybrat", command=vybrat_seta_exe)
seta_path_button.grid(row=3, column=2, padx=5, pady=5, sticky=tk.W)

# Frame pro tlačítka nahrávání
button_frame = tk.Frame(root)
button_frame.grid(row=4, column=0, columnspan=3, pady=10)

start_button = tk.Button(button_frame, text="Start nahrávání", command=start_recording)
start_button.pack(side=tk.LEFT, padx=5)

stop_button = tk.Button(button_frame, text="Stop nahrávání", command=stop_recording, state=tk.DISABLED)
stop_button.pack(side=tk.LEFT, padx=5)

# Label pro status
nastaveni_ulozeno_label = tk.Label(root, text="")
nastaveni_ulozeno_label.grid(row=5, column=0, columnspan=3)

# Token button
vytvorit_token_button = tk.Button(root, text="Vytvořit osobní token", command=vytvor_token)
vytvorit_token_button.grid(row=6, column=0, columnspan=3, pady=10)

nacti_nastaveni() # Načtení nastavení při spuštění

# Add before root.mainloop():
def on_closing():
    """Handler for window closing event"""
    if monitoring_thread and monitoring_thread.is_alive():
        stop_monitoring.set()
        monitoring_thread.join(timeout=1.0)
    root.destroy()

# Add just before root.mainloop():
root.protocol("WM_DELETE_WINDOW", on_closing)

root.mainloop()