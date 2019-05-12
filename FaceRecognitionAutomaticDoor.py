import picamera   # Module to control Pi Camera
import csv      # Module to read CSV credentials file
import boto3    # Module to access Amazon Web Services (Rekognition)
import os      # Module use to delete Operative System Files
import time
import RPi.GPIO as GPIO  # Module to Control GPIO on Raspberry Pi


# Global Variables
global video
global preview
global isRecording
global camera
global doorOpenned        

isRecording = False
camera = picamera.PiCamera()
camera.vflip = True
doorOpened = False


# GPIO Input Pins
OutSensor = 8    
captureButton = 10
servoMotor = 12


# Initialize GPIO Pins
GPIO.setwarnings (False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup (OutSensor, GPIO.IN)
GPIO.setup (captureButton, GPIO.IN)
GPIO.setup (servoMotor, GPIO.OUT)


# Check for Motion
def checkMotionSensor():

    global isRecording
    global doorOpened

    if GPIO.input(OutSensor) == False: # Person detected
        
        if GPIO.input(captureButton) == True:
                print("Button Pressed")
                takePhoto()
                authorisedUser = comparePhotos()
                if authorisedUser == True:
                    
                    #GPIO.output(servoMotor, 1)
                    if doorOpened == False:    # Only Change Servomotor to 90 if angle is 0
                        setAngle(90)
                        doorOpened = True
                
                
        if isRecording == False:
            # Start Recording
            removeOldVideo()
            recordVideo(True)
            
                    
    else:                                 # No Person detected
        authorisedUser = False
        
        #GPIO.output(servoMotor, 0)
        if doorOpened == True:            # Only Change Servomotor to 0 if angle is 90         
            setAngle(0)
            doorOpened = False

        if isRecording == True:
            # Stop Recording
            recordVideo(False)
            print("No motion")
    
# Record Video and Start Preview
def recordVideo(recordingVideo):
    
    global camera   
    global isRecording
    
    if recordingVideo == True:
        camera.start_preview(fullscreen = False, window = (400,100,800,840))  # Create a preview of camera at 800x840
        camera.start_recording("Video.h264")
        isRecording = True
        print("start vide")


    else:
        camera.stop_preview()
        camera.stop_recording()
        isRecording = False
        print("stop video")
        
def removeOldPhoto():

    try:
        # Delete Previous Capture Picture
        os.remove("capturedPicture.jpg")
        print("Previous Image Deleted")
    except FileNotFoundError:
        print("No Previuos Image")

def removeOldVideo():
    try:
        # Delete Previous Capture Video
        os.remove("Video.h264")
        print("Previous Video Deleted")
    except FileNotFoundError:
        print("No Previuos Video")


# Capture Photo 
def takePhoto():
    global camera
    # Capture Image with Button Press
    removeOldPhoto()

    camera.capture("capturedPicture.jpg")
    print("Photo Captured")

# Compare Captured Image with Base Picture
def comparePhotos():
    # Read credentials for AWS
    with open('credentials.csv', 'r') as input:
        next(input)  # this will skipped the first row
        reader = csv.reader(input)
        for line in reader:
            access_key_id = line[2]
            secret_access_key = line[3]

    masterPhoto = 'Master_image.jpg'  # Face of Authorize User
    capturedPhoto = 'capturedPicture.jpg'

    # Specific the Service used from Amazon Web Service
    client = boto3.client('rekognition', 
                      aws_access_key_id = access_key_id, 
                      aws_secret_access_key = secret_access_key, 
                      region_name = 'us-west-2')


    # This will encode to based64-encoded image bytes 
    with open (masterPhoto, 'rb') as source_image:
        source_byte =  source_image.read()
    
    # This will encode to based64-encoded image bytes 
    with open (capturedPhoto, 'rb') as source_image2:
        source_byte2 =  source_image2.read()

    try: 
        response = client.compare_faces(SourceImage = {"Bytes": source_byte}, TargetImage = {"Bytes" : source_byte2} )

        for key, value in response.items():
            print("\n")
            if key in ("FaceMatches", "UnmatchedFaces"):
                print(key)
                for att in value:            
                    try:               # Default match is at 85%
                        if att["Similarity"] >=95:   # Specify level of desired accuracy. 
                            authorisedUser = True
                            print("Face Matched Almost 100%")
                        else :
                            authorisedUser = False
                            print("Face matched Is Below 95%")
                            
                    except KeyError:     # If there is not matching face found 
                        authorisedUser = False
                        print("Unauthorised Person")
                        
    except client.exceptions.ClientError:    # If there is not face detected 
        authorisedUser = False
        print("No Person In Photo")
                    
    return authorisedUser

# This function is used to change  the angle of the servo motor (Open and Close Door)
def setAngle(angle):
    duty = angle/18 +2
    doorIn = GPIO.PWM(servoMotor, 50)      # Set Duty Cycle of Servomotor to 50 Hz        
    doorIn.start(0)         
    doorIn.ChangeDutyCycle(duty)
    time.sleep(0.2)
    doorIn.stop()


while True:
    checkMotionSensor()  # Keep this function in infinite loop


