import os
import usb.core
import usb.util
import time
from datetime import datetime
import cv2
from google.cloud import storage

# USB Pump Control Configuration
VENDOR_ID = 0x1234  # Remplacez par le Vendor ID de votre pompe
PRODUCT_ID = 0x5678  # Remplacez par le Product ID de votre pompe

# Google Cloud Storage Configuration
BUCKET_NAME = "eaukey-v1.appspot.com"

# Trouver le périphérique USB
def get_usb_device():
    device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if device is None:
        raise ValueError("Périphérique USB non trouvé")
    device.set_configuration()
    return device

# Activer et désactiver la pompe USB
def activer_pompe(device):
    print("activation de la pompe")

def desactiver_pompe(device):
    print("pompe desactivé")

# Prendre une photo
def prendre_photo():
    camera = cv2.VideoCapture(0)  # Utilise la première caméra connectée
    if not camera.isOpened():
        raise ValueError("Impossible d'accéder à la caméra")

    ret, frame = camera.read()
    if not ret:
        raise ValueError("Échec de la capture d'image")

    # Nom du fichier basé sur l'heure actuelle
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"photo_{timestamp}.jpg"
    cv2.imwrite(file_name, frame)
    camera.release()
    print(f"Photo capturée : {file_name}")
    return file_name

# Envoyer une photo sur Google Cloud Storage
def envoyer_photo(file_name):
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(file_name)

    blob.upload_from_filename(file_name)
    print(f"Photo {file_name} envoyée à {BUCKET_NAME}")

    # Supprimer le fichier local après l'envoi
    os.remove(file_name)

# Programme principal
def main():
    try:
        # Initialiser le périphérique USB
        #device = get_usb_device()

        # Activer la pompe
        activer_pompe(device)
        time.sleep(2)  # Attendre 2 secondes que la pompe fonctionne

        # Prendre une photo
        file_name = prendre_photo()

        # Désactiver la pompe
        desactiver_pompe(device)

        # Envoyer la photo sur le cloud
        envoyer_photo(file_name)

    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    main()
