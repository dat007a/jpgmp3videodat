import os
import subprocess
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
from mutagen.mp3 import MP3
import random

def get_duration(mp3_path):
    audio = MP3(mp3_path)
    return audio.info.length

def create_video_with_ffmpeg(input_folder, zoom_count, pan_count, shake_count, progress_callback, log_callback):
    try:
        files = os.listdir(input_folder)
        images = {os.path.splitext(f)[0]: os.path.join(input_folder, f) for f in files if f.lower().endswith('.jpg')}
        audios = {os.path.splitext(f)[0]: os.path.join(input_folder, f) for f in files if f.lower().endswith('.mp3')}

        keys = sorted(set(images.keys()) & set(audios.keys()), key=lambda x: int(x))
        temp_folder = os.path.join(input_folder, "temp")
        os.makedirs(temp_folder, exist_ok=True)

        available_keys = keys.copy()
        random.shuffle(available_keys)

        zoom_keys = set(str(k) for k in available_keys[:zoom_count])
        pan_keys = set(str(k) for k in available_keys[zoom_count:zoom_count + pan_count])
        shake_keys = set(str(k) for k in available_keys[zoom_count + pan_count:zoom_count + pan_count + shake_count])

        video_parts = []
        total = len(keys)

        for i, key in enumerate(keys):
            log_callback(f"\n🎞️ Processing segment: {key}")
            img = images[key]
            mp3 = audios[key]
            duration = get_duration(mp3)
            output_part = os.path.join(temp_folder, f"part_{key}.mp4")

            effect_applied = False

            if key in zoom_keys and duration > 6:
                log_callback(f"👉 Applying ZOOM to segment {key}")
                cmd = [
                    'ffmpeg', '-y',
                    '-loop', '1', '-i', img,
                    '-i', mp3,
                    '-filter_complex',
                    f"[0:v]scale=1400:788,zoompan=z='min(zoom+0.0015,1.2)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1280x720,format=yuv420p[v]",
                    '-map', '[v]', '-map', '1:a',
                    '-t', str(duration),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', output_part
                ]
                subprocess.run(cmd)
                effect_applied = True

            elif key in pan_keys:
                log_callback(f"👉 Applying PAN to segment {key}")
                cmd = [
                    'ffmpeg', '-y',
                    '-loop', '1', '-i', img,
                    '-i', mp3,
                    '-filter_complex',
                    f"[0:v]scale=1500:720,crop=1280:720:x='(in_w-out_w)*t/{duration}':y=0,format=yuv420p[v]",
                    '-map', '[v]', '-map', '1:a',
                    '-t', str(duration),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', output_part
                ]
                subprocess.run(cmd)
                effect_applied = True

            elif key in shake_keys:
                log_callback(f"👉 Applying SHAKE to segment {key}")
                cmd = [
                    'ffmpeg', '-y',
                    '-loop', '1', '-i', img,
                    '-i', mp3,
                    '-filter_complex',
                    f"[0:v]scale=1280:720,crop=1280:720:x='5*sin(2*PI*t*3)':y='5*cos(2*PI*t*3)',format=yuv420p[v]",
                    '-map', '[v]', '-map', '1:a',
                    '-t', str(duration),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', output_part
                ]
                subprocess.run(cmd)
                effect_applied = True

            if not effect_applied:
                log_callback(f"⚪ No effect applied to segment {key}")
                cmd = [
                    'ffmpeg', '-y',
                    '-loop', '1', '-i', img,
                    '-i', mp3,
                    '-t', str(duration),
                    '-vf', 'scale=1280:720',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', output_part
                ]
                subprocess.run(cmd)

            if os.path.exists(output_part):
                video_parts.append(f"file '{output_part}'")
            else:
                log_callback(f"❌ Failed to create video for segment {key}")

            progress_callback((i + 1) / total * 100)

        concat_list = os.path.join(temp_folder, "file_list.txt")
        with open(concat_list, 'w', encoding='utf-8') as f:
            f.write('\n'.join(video_parts))

        output_path = os.path.join(input_folder, "output_video.mp4")
        subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_list, '-c', 'copy', output_path])

        log_callback("\n✅ Done! Output video created: output_video.mp4")
        messagebox.showinfo("Success", "Video created successfully!")
    except Exception as e:
        log_callback(f"Error: {str(e)}")
        messagebox.showerror("Error", str(e))

# ----------------- GUI BELOW -------------------

def start_process():
    folder = folder_var.get()
    if not folder:
        messagebox.showwarning("Missing Input", "Please select an input folder.")
        return

    try:
        zoom_count = int(zoom_entry.get())
        pan_count = int(pan_entry.get())
        shake_count = int(shake_entry.get())
    except ValueError:
        messagebox.showerror("Error", "Please enter valid numbers for effects.")
        return

    progress_bar["value"] = 0
    log_text.delete("1.0", tk.END)

    def progress_callback(percent):
        progress_bar["value"] = percent

    def log_callback(message):
        log_text.insert(tk.END, message + "\n")
        log_text.see(tk.END)

    thread = threading.Thread(target=create_video_with_ffmpeg, args=(folder, zoom_count, pan_count, shake_count, progress_callback, log_callback))
    thread.start()

def select_folder():
    folder = filedialog.askdirectory()
    if folder:
        folder_var.set(folder)

# GUI setup
root = tk.Tk()
root.title("FFmpeg Video Creator Tool")
root.geometry("700x500")

folder_var = tk.StringVar()

frame = tk.Frame(root)
frame.pack(pady=10)

folder_entry = tk.Entry(frame, textvariable=folder_var, width=50)
folder_entry.pack(side=tk.LEFT, padx=5)

select_button = tk.Button(frame, text="Select Input Folder", command=select_folder)
select_button.pack(side=tk.LEFT)

options_frame = tk.Frame(root)
options_frame.pack(pady=10)

tk.Label(options_frame, text="Zoompan:").grid(row=0, column=0, padx=5)
zoom_entry = tk.Entry(options_frame, width=5)
zoom_entry.insert(0, "2")
zoom_entry.grid(row=0, column=1, padx=5)

tk.Label(options_frame, text="Pan Slide:").grid(row=0, column=2, padx=5)
pan_entry = tk.Entry(options_frame, width=5)
pan_entry.insert(0, "2")
pan_entry.grid(row=0, column=3, padx=5)

tk.Label(options_frame, text="Shake:").grid(row=0, column=4, padx=5)
shake_entry = tk.Entry(options_frame, width=5)
shake_entry.insert(0, "2")
shake_entry.grid(row=0, column=5, padx=5)

action_button = tk.Button(root, text="Create Video", bg="green", fg="white", command=start_process, height=2, width=20)
action_button.pack(pady=10)

progress_bar = ttk.Progressbar(root, orient="horizontal", length=600, mode="determinate")
progress_bar.pack(pady=10)

log_text = tk.Text(root, height=12, width=85)
log_text.pack(pady=10)

root.mainloop()
