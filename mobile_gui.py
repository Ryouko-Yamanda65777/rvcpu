import PySimpleGUI as sg
import os
import numpy as np
from pydub import AudioSegment
from rvcpu import VoiceClone
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--share', action='store_true', help='Share the PySimpleGUI app', default=False)
args = parser.parse_args()

vc = None
weight_root = os.environ.get('weight_root', '')
index_root = os.environ.get('index_root', '')
model_files = [f for f in os.listdir(weight_root) if f.endswith('.pth')] if os.path.exists(weight_root) else []
index_files = []

for root, dirs, files in os.walk(index_root):
    for file in files:
        if file.endswith('.index'):
            index_files.append(os.path.join(root, file))

def initialize_vc(model, index):
    global vc
    if model in model_files:
        vc = VoiceClone(model, os.path.basename(index))
        sg.popup("Model Loaded: " + model)
        return True
    else:
        sg.popup("Invalid model selection. Please choose a valid model.")
        return None

def find_matching_index(model_path):
    model_name = os.path.splitext(os.path.basename(model_path))[0]
    for index_file in index_files:
        if model_name in index_file:
            return index_file
    return None

def convert_audio(audio_path, use_chunks, chunk_size, f0up_key, f0method, index_rate, protect, model_dropdown, index_dropdown):
    global vc
    if vc is None:
        model_name, index_name = model_dropdown, index_dropdown
        initialize_vc(model_name, index_name)
    
    vc.f0up_key = f0up_key
    vc.f0method = f0method
    vc.index_rate = index_rate
    vc.protect = protect
    
    if use_chunks:
        rate, data = vc.convert_chunks(audio_path, chunk_size=chunk_size)
    else:
        rate, data = vc.convert(audio_path)
    return (rate, np.array(data))

def stereo(audio_path, delay_ms=0.6):
    sample_rate, audio_array = audio_path
    if len(audio_array.shape) == 1:
        audio_bytes = audio_array.tobytes()
        mono_audio = AudioSegment(
            data=audio_bytes,
            sample_width=audio_array.dtype.itemsize,
            frame_rate=sample_rate,
            channels=1
        )
        samples = np.array(mono_audio.get_array_of_samples())
        delay_samples = int(mono_audio.frame_rate * (delay_ms / 1000.0))
        left_channel = np.zeros_like(samples)
        right_channel = samples
        left_channel[delay_samples:] = samples[:-delay_samples]
        stereo_samples = np.column_stack((left_channel, right_channel))
        return (sample_rate, stereo_samples.astype(np.int16))
    else:
        return audio_path

# Define PySimpleGUI layout
layout = [
    [sg.Text("VoiceCloner", font=("Helvetica", 16), justification="center")],
    [sg.Text("Select Model:"), sg.Combo(model_files, key="model", readonly=True)],
    [sg.Text("Select Index:"), sg.Combo(index_files, key="index", readonly=True)],
    [sg.Text("Input Audio File:"), sg.Input(key="audio_path"), sg.FileBrowse()],
    [sg.Checkbox("Use Chunks", key="use_chunks", default=True)],
    [sg.Text("Chunk Size (seconds):"), sg.Slider(range=(1, 30), default_value=10, orientation="h", key="chunk_size")],
    [sg.Text("Pitch Shift:"), sg.Slider(range=(-12, 12), default_value=0, orientation="h", key="f0up_key")],
    [sg.Text("F0 Method:"), sg.Combo(["pm", "rmvpe"], default_value="pm", key="f0method")],
    [sg.Text("Index Rate:"), sg.Slider(range=(0, 1), resolution=0.01, default_value=0.66, orientation="h", key="index_rate")],
    [sg.Text("Protect:"), sg.Slider(range=(0, 0.5), resolution=0.01, default_value=0.33, orientation="h", key="protect")],
    [sg.Button("Convert"), sg.Button("Exit")],
    [sg.Text("Output Audio:", font=("Helvetica", 14))],
    [sg.Multiline(size=(30, 10), key="output_audio", disabled=True)]
]

# Create the window
window = sg.Window("VoiceCloner Mobile UI", layout, finalize=True)

# Event Loop
while True:
    event, values = window.read()
    
    if event in (sg.WINDOW_CLOSED, "Exit"):
        break

    if event == "Convert":
        model = values["model"]
        index = values["index"]
        audio_path = values["audio_path"]
        use_chunks = values["use_chunks"]
        chunk_size = values["chunk_size"]
        f0up_key = values["f0up_key"]
        f0method = values["f0method"]
        index_rate = values["index_rate"]
        protect = values["protect"]
        
        if model and index and audio_path:
            initialize_vc(model, index)
            rate, converted_audio = convert_audio(audio_path, use_chunks, chunk_size, f0up_key, f0method, index_rate, protect, model, index)
            stereo_audio = stereo((rate, converted_audio))
            window["output_audio"].update(f"Converted audio at {rate}Hz with stereo effect.")
        else:
            sg.popup("Please ensure all fields are selected.")

window.close()
