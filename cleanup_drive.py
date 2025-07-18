import logging
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Configuration ---
CREDENTIALS_FILE = 'credentials.json'
TEMPLATE_FILE_ID = '1poO2idpiXsC8kN5C3EuuXycyPGQU-LWy1t7Mzs6dEtM' # ID of the template to NOT delete
# --- End Configuration ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_drive_service():
    """Initializes and returns the Google Drive service client."""
    try:
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        logging.info("Successfully initialized drive service.")
        return service
    except Exception as e:
        logging.error(f"Failed to initialize drive service: {e}")
        raise

def list_and_delete_owned_files(service):
    """Lists and deletes all files owned by the service account, except the template."""
    page_token = None
    file_count = 0
    deleted_count = 0
    
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            creds_json = json.load(f)
        owner_email = creds_json['client_email']
    except FileNotFoundError:
        logging.error(f"'{CREDENTIALS_FILE}' not found. Please ensure it's in the correct path.")
        return
    except (json.JSONDecodeError, KeyError):
        logging.error(f"Could not read service account email from '{CREDENTIALS_FILE}'.")
        return

    logging.info(f"Searching for files owned by: {owner_email}")
    
    try:
        while True:
            response = service.files().list(
                q=f"'{owner_email}' in owners",
                spaces='drive',
                fields='nextPageToken, files(id, name, parents)',
                pageToken=page_token
            ).execute()
            
            files = response.get('files', [])
            if not files and page_token is None:
                logging.info("No files found owned by the service account.")
                break

            file_count += len(files)
            logging.info(f"Found {len(files)} files in this batch.")

            for file in files:
                file_id = file.get('id')
                file_name = file.get('name')
                
                if file_id == TEMPLATE_FILE_ID:
                    logging.info(f"Skipping deletion of template file: '{file_name}' (ID: {file_id})")
                    continue

                logging.info(f"Deleting file: '{file_name}' (ID: {file_id})")
                try:
                    service.files().delete(fileId=file_id).execute()
                    logging.info(f"  -> Successfully deleted.")
                    deleted_count += 1
                except HttpError as e:
                    logging.error(f"  -> Failed to delete file {file_id}: {e}")

            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
                
    except Exception as e:
        logging.error(f"An error occurred while listing/deleting files: {e}")

    logging.info(f"\n--- Cleanup Summary ---")
    logging.info(f"Total files found: {file_count}")
    logging.info(f"Total files deleted: {deleted_count}")
    logging.info(f"----------------------")

if __name__ == '__main__':
    drive_service = get_drive_service()
    if drive_service:
        list_and_delete_owned_files(drive_service)
