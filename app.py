import time
import streamlit as st
import zipfile
import os
import random
import tempfile
from pathlib import Path
from yt_dlp import YoutubeDL
from pydub import AudioSegment
from moviepy.editor import ImageSequenceClip, AudioFileClip
from typing import List
from io import BytesIO

# Given utility function
def download_youtube_video_as_mp3(url: str, output_path: str) -> str:
    attempt = 0
    MAX_RETRIES = 3
    while attempt < MAX_RETRIES:
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': f'{output_path}.%(ext)s',
                'noplaylist': True,
            }

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            mp3_filename = f"{output_path}.mp3"
            if not os.path.exists(mp3_filename):
                raise OSError("Conversion to MP3 failed.")

            return mp3_filename

        except Exception as e:
            attempt += 1
            time.sleep(2 ** attempt)
    raise OSError(f"Failed to download YouTube video after {MAX_RETRIES} attempts.")

# Function to extract images from zip file
def extract_images(zip_path: str, extract_to: str) -> List[str]:
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    return [str(path) for path in Path(extract_to).rglob('*') if path.is_file()]

def create_video(images: List[str], audio_path: str, output_path: str):
    # Create video from images
    clip = ImageSequenceClip(images, fps=1)  # 1 frame per second
    audio_clip = AudioFileClip(audio_path).subclip(0, min(30, clip.duration))
    video = clip.set_audio(audio_clip)
    video = video.subclip(0, 30)  # Ensure the video is exactly 30 seconds long
    video.write_videofile(output_path, codec='libx264', audio_codec='aac')

def zip_videos(videos: List[str], output_zip_path: str):
    with zipfile.ZipFile(output_zip_path, 'w') as zipf:
        for video in videos:
            zipf.write(video, os.path.basename(video))

def main():
    st.title("Image & Audio Mixer")

    st.write("Upload a zip file containing images.")
    uploaded_zip = st.file_uploader("Choose a zip file", type="zip")

    st.write("Provide a comma-separated list of YouTube URLs.")
    youtube_urls = st.text_input("YouTube URLs")

    if st.button("Process"):
        if uploaded_zip is not None and youtube_urls:
            with tempfile.TemporaryDirectory() as tmpdirname:
                images_dir = os.path.join(tmpdirname, "images")
                os.makedirs(images_dir, exist_ok=True)
                zip_path = os.path.join(tmpdirname, uploaded_zip.name)
                
                # Save the uploaded zip file to the temporary directory
                with open(zip_path, 'wb') as f:
                    f.write(uploaded_zip.getvalue())
                
                # Extract images
                images = extract_images(zip_path, images_dir)

                # Download audio files
                urls = [url.strip() for url in youtube_urls.split(',')]
                audio_files = []
                for i, url in enumerate(urls):
                    try:
                        audio_path = download_youtube_video_as_mp3(url, os.path.join(tmpdirname, f"audio_{i}"))
                        audio_files.append(audio_path)
                    except OSError as e:
                        st.error(f"Failed to download from URL: {url} - {e}")

                if images and audio_files:
                    output_videos = []
                    for idx, image in enumerate(images):
                        output_video_path = os.path.join(tmpdirname, f"output_{idx}.mp4")
                        random_audio = random.choice(audio_files)
                        create_video([image] * 30, random_audio, output_video_path)
                        output_videos.append(output_video_path)
                        st.video(output_video_path)

                    # Zip the videos for bulk download
                    zip_videos_path = os.path.join(tmpdirname, "processed_videos.zip")
                    zip_videos(output_videos, zip_videos_path)

                    # Provide download link
                    with open(zip_videos_path, "rb") as f:
                        bytes_data = f.read()
                    st.download_button(
                        label="Download all videos as zip",
                        data=bytes_data,
                        file_name="processed_videos.zip",
                        mime="application/zip"
                    )
                else:
                    st.error("No images or audio files found to process.")

if __name__ == "__main__":
    main()