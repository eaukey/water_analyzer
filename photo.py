import os
import cv2
from google.cloud import storage
import io
from datetime import datetime
import psycopg2
import time

# Nom du bucket Google Cloud Storage
bucket_name = 'eaukey-v1.appspot.com'

# Simulation de contrôle du relais USB (remplace GPIO)
def activer_contacteur():
    print("Contacteur activé (USB allumé)")

def desactiver_contacteur():
    print("Contacteur désactivé (USB éteint)")

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
        password=os.getenv('PASSWORD').strip('"',
        host=os.getenv('HOST')
    )
    return conn

# Envoi des métadonnées à la base de données
def send_url(conn, url, timestamp, numero_automate):
    try:
        cursor = conn.cursor()
        query = "INSERT INTO urls_images (url, timestamp, numero_automate) VALUES (%s, %s, %s)"
        cursor.execute(query, (url, timestamp, numero_automate))
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
    desactiver_contacteur()
    time.sleep(30)
    for index in indexs:
        try:
            image_data = capture_image(index)
            destination_blob_name = f'captured_image_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
            image_url = upload_image_to_gcs(bucket_name, image_data, destination_blob_name)

            conn = get_connection()
            timestamp = datetime.now()
            numero_automate = int(os.getenv('NUMERO_AUTOMATE'))
            send_url(conn, image_url, timestamp, numero_automate)
            conn.close()

            time.sleep(2)
            print('One picture taken and uploaded.')
        except Exception as e:
            print(f"Error during image processing: {e}")

    activer_contacteur()
    time.sleep(270)
