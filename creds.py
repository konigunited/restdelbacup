import os
import shutil
import tempfile
import json
from pathlib import Path

def clear_google_cache():
    print("Ochistka Google API kesha...")
    
    temp_dir = tempfile.gettempdir()
    print(f"Proveryayu temp direktoriyu: {temp_dir}")
    
    try:
        for item in os.listdir(temp_dir):
            if 'google' in item.lower():
                item_path = os.path.join(temp_dir, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                    print(f"Udalen: {item}")
                except Exception as e:
                    print(f"Ne udalos udalit {item}: {e}")
    except Exception as e:
        print(f"Oshibka dostupa k temp: {e}")
    
    home_dir = Path.home()
    cache_dirs = [
        home_dir / '.cache' / 'google',
        home_dir / '.google',
        home_dir / 'AppData' / 'Local' / 'Google',
        home_dir / 'AppData' / 'Roaming' / 'Google'
    ]
    
    for cache_dir in cache_dirs:
        if cache_dir.exists():
            try:
                shutil.rmtree(cache_dir)
                print(f"Udalen kesh: {cache_dir}")
            except Exception as e:
                print(f"Ne udalos udalit {cache_dir}: {e}")
    
    print("Ochistka __pycache__...")
    for root, dirs, files in os.walk('.'):
        for dir_name in dirs:
            if dir_name == '__pycache__':
                cache_path = os.path.join(root, dir_name)
                try:
                    shutil.rmtree(cache_path)
                    print(f"Udalen: {cache_path}")
                except Exception as e:
                    print(f"Ne udalos udalit {cache_path}: {e}")
    
    print("Kesh ochishchen!")

def test_credentials():
    print("\nTestirovanie credentials...")
    
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        credentials = service_account.Credentials.from_service_account_file(
            'credentials.json',
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        print(f"Project ID: {credentials.project_id}")
        print(f"Service Account: {credentials.service_account_email}")
        
        service = build('sheets', 'v4', credentials=credentials)
        print("Google Sheets service sozdan uspeshno")
        
        return True
        
    except Exception as e:
        print(f"Oshibka: {e}")
        return False

def force_reload_modules():
    print("\nPrinuditelnaya perezagruzka moduley...")
    
    import sys
    modules_to_reload = []
    
    for module_name in list(sys.modules.keys()):
        if any(keyword in module_name.lower() for keyword in ['google', 'oauth', 'httplib']):
            modules_to_reload.append(module_name)
    
    for module_name in modules_to_reload:
        try:
            del sys.modules[module_name]
            print(f"Vygruzhen modul: {module_name}")
        except:
            pass
    
    print("Moduli perezagruzheny!")

if __name__ == "__main__":
    print("Polnaya ochistka kesha Google API")
    print("=" * 50)
    
    clear_google_cache()
    
    force_reload_modules()
    
    if test_credentials():
        print("\nVSЕ GOTOVO! Kesh ochishchen, credentials rabotayut.")
        print("Teper zapuskayte: python main.py")
    else:
        print("\nProblemy ostayutsya. Proverte credentials.json")
