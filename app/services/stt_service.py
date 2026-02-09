from pydub import AudioSegment
import whisper

DEVICE = "cpu"
model = whisper.load_model("small", device=DEVICE)

def convert_webm_to_wav(webm_path: str, wav_path: str) -> None:
    audio = AudioSegment.from_file(webm_path, format="webm")
    audio = audio.set_frame_rate(16000).set_channels(1)
    audio.export(wav_path, format="wav")

def transcribe_audio_file(file_path: str) -> str:
    result = model.transcribe(file_path, fp16=False, verbose=False)
    return result["text"]
