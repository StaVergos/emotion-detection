import torch



import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import seaborn as sns
from tqdm import tqdm

from moviepy import VideoFileClip, ImageSequenceClip

import torch
from facenet_pytorch import MTCNN

from transformers import (
    AutoFeatureExtractor,
    AutoModelForImageClassification,
    AutoConfig,
)

from PIL import Image, ImageDraw

# Set device to GPU if available, otherwise use CPU
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(f"Running on device: {device}")

# Load your video
scene = "accent.mp4"
clip = VideoFileClip(scene)

# Save video frames per second
vid_fps = clip.fps

# Get the video (as frames)
video = clip.without_audio()
video_data = np.array(list(video.iter_frames()))

mtcnn = MTCNN(
    image_size=160,
    margin=0,
    min_face_size=200,
    thresholds=[0.6, 0.7, 0.7],
    factor=0.709,
    post_process=True,
    keep_all=False,
    device=device,
)

# Load the pre-trained model and feature extractor
extractor = AutoFeatureExtractor.from_pretrained("trpakov/vit-face-expression")
model = AutoModelForImageClassification.from_pretrained("trpakov/vit-face-expression")


def detect_emotions(image):
    """
    Detect emotions from a given image, displays the detected
    face and the emotion probabilities in a bar plot.

    Parameters:
    image (PIL.Image): The input image.

    Returns:
    PIL.Image: The cropped face from the input image.
    """

    # Create a copy of the image to draw on
    temporary = image.copy()

    # Use the MTCNN model to detect faces in the image
    sample = mtcnn.detect(temporary)

    # If a face is detected
    if sample[0] is not None:

        # Get the bounding box coordinates of the face
        box = sample[0][0]

        # Crop the detected face from the image
        face = temporary.crop(box)

        # Pre-process the cropped face to be fed into the
        # emotion detection model
        inputs = extractor(images=face, return_tensors="pt")

        # Pass the pre-processed face through the model to
        # get emotion predictions
        outputs = model(**inputs)

        # Apply softmax to the logits to get probabilities
        probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)

        # Retrieve the id2label attribute from the configuration
        id2label = AutoConfig.from_pretrained("trpakov/vit-face-expression").id2label

        # Convert probabilities tensor to a Python list
        probabilities = probabilities.detach().numpy().tolist()[0]

        # Map class labels to their probabilities
        class_probabilities = {
            id2label[i]: prob for i, prob in enumerate(probabilities)
        }

        # Define colors for each emotion
        colors = {
            "angry": "red",
            "disgust": "green",
            "fear": "gray",
            "happy": "yellow",
            "neutral": "purple",
            "sad": "blue",
            "surprise": "orange",
        }
        palette = [colors[label] for label in class_probabilities.keys()]

        # Prepare a figure with 2 subplots: one for the face image,
        # one for the bar plot
        fig, axs = plt.subplots(1, 2, figsize=(15, 6))

        # Display the cropped face in the left subplot
        axs[0].imshow(np.array(face))
        axs[0].axis("off")

        # Create a horizontal bar plot of the emotion probabilities in
        # the right subplot
        sns.barplot(
            ax=axs[1],
            y=list(class_probabilities.keys()),
            x=[prob * 100 for prob in class_probabilities.values()],
            palette=palette,
            orient="h",
        )
        axs[1].set_xlabel("Probability (%)")
        axs[1].set_title("Emotion Probabilities")
        axs[1].set_xlim([0, 100])  # Set x-axis limits to show percentages

        # Show the plot
        # plt.show()
        plt.savefig("emotion_probabilities.png")
        plt.close(fig)


# frame = video_data[10]  # choosing the 10th frame

# # Convert the frame to a PIL image and display it
# image = Image.fromarray(frame)
# detect_emotions(image)


def detect_emotions(image):
    """
    Detect emotions from a given image.
    Returns a tuple of the cropped face image and a
    dictionary of class probabilities.
    """
    temporary = image.copy()

    # Detect faces in the image using the MTCNN group model
    sample = mtcnn.detect(temporary)
    if sample[0] is not None:
        box = sample[0][0]

        # Crop the face
        face = temporary.crop(box)

        # Pre-process the face
        inputs = extractor(images=face, return_tensors="pt")

        # Run the image through the model
        outputs = model(**inputs)

        # Apply softmax to the logits to get probabilities
        probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)

        # Retrieve the id2label attribute from the configuration
        config = AutoConfig.from_pretrained("trpakov/vit-face-expression")
        id2label = config.id2label

        # Convert probabilities tensor to a Python list
        probabilities = probabilities.detach().numpy().tolist()[0]

        # Map class labels to their probabilities
        class_probabilities = {
            id2label[i]: prob for i, prob in enumerate(probabilities)
        }

        return face, class_probabilities
    return None, None


def create_combined_image(face, class_probabilities):
    """
    Create an image combining the detected face and a barplot
    of the emotion probabilities.

    Parameters:
    face (PIL.Image): The detected face.
    class_probabilities (dict): The probabilities of each
        emotion class.

    Returns:
    np.array: The combined image as a numpy array.
    """
    # Define colors for each emotion
    colors = {
        "angry": "red",
        "disgust": "green",
        "fear": "gray",
        "happy": "yellow",
        "neutral": "purple",
        "sad": "blue",
        "surprise": "orange",
    }
    palette = [colors[label] for label in class_probabilities.keys()]
    labels = list(class_probabilities.keys())
    probs = [p * 100 for p in class_probabilities.values()]

    # Create a figure with 2 subplots: one for the
    # face image, one for the barplot
    fig, axs = plt.subplots(1, 2, figsize=(15, 6))

    # Display face on the left subplot
    axs[0].imshow(np.array(face))
    axs[0].axis("off")

    # Create a barplot of the emotion probabilitiesa
    # on the right subplot
    sns.barplot(
        ax=axs[1],
        y=labels,
        x=probs,
        hue=labels,
        palette=palette,
        orient="h",
        legend=False,
    )
    axs[1].set_xlabel("Probability (%)")
    axs[1].set_title("Emotion Probabilities")
    axs[1].set_xlim([0, 100])  # Set x-axis limits

    # Convert the figure to a numpy array
    canvas = FigureCanvas(fig)
    canvas.draw()
    img = np.frombuffer(canvas.tostring_argb(), dtype="uint8")
    img = img.reshape(canvas.get_width_height()[::-1] + (4,))
    # fig.canvas.draw()
    # w, h = fig.canvas.get_width_height()
    # img = np.frombuffer(fig.canvas.tostring_rgb(), dtype="uint8")
    # img = img.reshape((h, w, 3))

    plt.close(fig)
    return img


skips = 2
reduced_video = []

for i in tqdm(range(0, len(video_data), skips)):
    reduced_video.append(video_data[i])

# Define a list of emotions
emotions = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]

# List to hold the combined images
combined_images = []

# Create a list to hold the class probabilities for all frames
all_class_probabilities = []

# Loop over video frames
for i, frame in tqdm(
    enumerate(reduced_video), total=len(reduced_video), desc="Processing frames"
):
    # Convert frame to uint8
    frame = frame.astype(np.uint8)

    # Call detect_emotions to get face and class probabilities
    face, class_probabilities = detect_emotions(Image.fromarray(frame))

    # If a face was found
    if face is not None:
        # Create combined image for this frame
        combined_image = create_combined_image(face, class_probabilities)

        # Append combined image to the list
        combined_images.append(combined_image)
    else:
        # If no face was found, set class probabilities to None
        class_probabilities = {emotion: None for emotion in emotions}

    # Append class probabilities to the list
    all_class_probabilities.append(class_probabilities)

# Convert list of images to video clip
clip_with_plot = ImageSequenceClip(
    combined_images, fps=vid_fps / skips
)  # Choose the frame rate (fps) according to your requirement

# Write the video to a file with a specific frame rate
clip_with_plot.write_videofile("output_video.mp4", fps=vid_fps / skips)

# Display the clip
# clip_with_plot.ipython_display(width=900)
