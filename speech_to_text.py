import vosk
import queue
import sounddevice as sd
import json
import os

class SpeechToText:
    def __init__(self, model_dir):
        self.model_dir = model_dir
        self.recognizer = None
        self.q = queue.Queue()

    def load_model(self, language):
        """Загружает модель для выбранного языка."""
        model_path = os.path.join(self.model_dir, language)
        if not os.path.exists(model_path):
            raise ValueError(f"Модель {language} не найдена в {model_path}")
        self.recognizer = vosk.KaldiRecognizer(vosk.Model(model_path), 16000)

    def callback(self, indata, frames, time, status):
        """Обработка аудиопотока."""
        if status:
            print(f"Статус ошибки: {status}")
        self.q.put(bytes(indata))

    def recognize(self, device=None):
        """Распознает речь с использованием выбранной модели."""
        if not self.recognizer:
            raise RuntimeError("Модель не загружена. Сначала вызовите load_model().")

        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16",
                               channels=1, callback=self.callback, device=device):
            print("Говорите...")
            while True:
                data = self.q.get()
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    return result.get("text", "")
