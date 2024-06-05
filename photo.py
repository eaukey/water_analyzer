import cv2 
import time
import psycopg2


def find_index(nb_camera=3):
	index = []
	index_test = 0
	while len(index) < nb_camera:
		cap = cv2.VideoCapture(index_test)
		if cap.isOpened():
			index.append(index_test)
			cap.release
		index_test = index_test + 1
		if index_test > 10:
			break
	return index 
	
def take_picture(index):
	cap = cv2.VideoCapture(index)
	ret, frame = cap.read()
	return ret, frame
	
def convert_image_to_binary(image):
	return cv2.imencode('.jpg', image)[1].tobytes()
	
	
def get_connection():
	conn = psycopg2.connect(
		dbname = "EaukeyCloudSQLv1",
		user = "romain",
		password = "Lzl?h<P@zxle6xuL",
		host = "35.195.185.218")
	
	return conn
	
	
def send_picture(conn, picture):
	cursor = conn.cursor()
	query = "INSERT INTO photos (photo) VALUES (%s)"
	
	picture = (picture,)
	cursor.execute(query, picture)
	conn.commit()
			

indexs = find_index()

state = False

while state == False:
    for index in indexs:
        ret, photo = take_picture(index)
        photo = convert_image_to_binary(photo)
        conn = get_connection()
        send_picture(conn, photo)
        time.sleep(2)
        print('one picture taken')

    time.sleep(20)
