import os
import cv2
from google.cloud import storage
import io
from datetime import datetime
import psycopg2
import time
import numpy as np
from tensorflow.keras.models import load_model
from PIL import Image
import serial  # Bibliothèque pour communiquer avec le port série

# Nom du bucket Google Cloud Storage
bucket_name = 'eaukey-v1.appspot.com'

# Charger le modèle de classification
model_path = 'photo_classifier.h5'
model = load_model(model_path)

# Configuration du port série pour le relais USB
port = 'COM6'  # Remplacez par le port utilisé par votre contacteur
baudrate = 9600

# Simulation de contrôle du relais USB (remplace GPIO)
def activer_contacteur():
    """Active le contacteur via USB"""
    try:
        with serial.Serial(port, baudrate, timeout=1) as ser:
            ser.write(bytes([0xA0, 0x01, 0x01, 0xA2]))  # Commande pour activer
            print("Contacteur activé (USB allumé)")
    except Exception as e:
        print(f"Erreur lors de l'activation du contacteur : {e}")

def desactiver_contacteur():
    """Désactive le contacteur via USB"""
    try:
        with serial.Serial(port, baudrate, timeout=1) as ser:
            ser.write(bytes([0xA0, 0x01, 0x00, 0xA1]))  # Commande pour désactiver
            print("Contacteur désactivé (USB éteint)")
    except Exception as e:
        print(f"Erreur lors de la désactivation du contacteur : {e}")

# Configuration du client Google Cloud Storage
def get_gcs_client(path='C:\\Users\\eauke\\eaukey\\credentials.json'):
    return storage.Client.from_service_account_json(path)

# Fonction pour uploader une image vers Google Cloud Storage
def upload_image_to_gcs(bucket_name, image_data, destination_blob_name):
    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_file(image_data, content_type='image/jpeg')
    return blob.public_url

# Détecter les indices des caméras disponibles
def find_index(nb_camera=1):
    index = []
    index_test = 0
    while len(index) < nb_camera:
        cap = cv2.VideoCapture(index_test)
        if cap.isOpened():
            index.append(index_test)
            cap.release()
        index_test += 1
        if index_test > 10:
            break
    return index 

# Prétraitement de l'image pour le modèle
def preprocess_image(image_data, target_size=(224, 224)):
    image = Image.open(image_data).convert("RGB")
    image_resized = image.resize(target_size)
    image_array = np.array(image_resized) / 255.0  # Normalisation
    return np.expand_dims(image_array, axis=0)  # Ajouter une dimension batch

# Capture d'image avec OpenCV
def capture_image(index):
    cap = cv2.VideoCapture(index)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise Exception("Failed to capture image")

    is_success, buffer = cv2.imencode(".jpg", frame)
    if not is_success:
        raise Exception("Failed to encode image")

    image_data = io.BytesIO(buffer)
    return image_data

# Connexion à la base de données
def get_connection():
    conn = psycopg2.connect(
        dbname=os.getenv('DBNAME'),
        user=os.getenv('USER'),
        password=os.getenv('PASSWORD').strip('"'),
        host=os.getenv('HOST')
    )
    return conn

# Envoi des métadonnées à la base de données
def send_url(conn, url, timestamp, numero_automate, predicted_class):
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO urls_images (url, timestamp, numero_automate, predicted_class) 
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (url, timestamp, numero_automate, predicted_class))
        conn.commit()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        cursor.close()

# Détection des caméras
indexs = find_index()

# État de fonctionnement de la boucle
state = False

# Boucle infinie pour capturer des images et gérer les contacteurs
while not state:
    try:
        desactiver_contacteur()  # Désactive toujours le contacteur au début de la boucle
        time.sleep(30)
        for index in indexs:
            try:
                # Capture de l'image
                image_data = capture_image(index)
                # Prétraitement de l'image
                processed_image = preprocess_image(image_data)
                # Prédiction avec le modèle
                predicted_class = np.argmax(model.predict(processed_image), axis=1)[0]

                # Téléchargement de l'image vers GCS
                destination_blob_name = f'captured_image_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
                image_url = upload_image_to_gcs(bucket_name, image_data, destination_blob_name)

                # Envoi des métadonnées à la base de données
                conn = get_connection()
                timestamp = datetime.now()
                numero_automate = int(os.getenv('NUMERO_AUTOMATE'))
                send_url(conn, image_url, timestamp, numero_automate, int(predicted_class))
                conn.close()

                time.sleep(2)
                print('One picture taken, classified, and uploaded.')
            except Exception as e:
                print(f"Error during image processing: {e}")

        # Activer le contacteur après la boucle de capture d'image
        activer_contacteur()
        time.sleep(270)

    except Exception as e:
        print(f"Erreur inattendue dans la boucle principale : {e}")

    finally:
        # Toujours désactiver le contacteur en fin de cycle, même en cas d'erreur
        desactiver_contacteur()
