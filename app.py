
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

import os
import json
import queue
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
from flask import Flask, render_template, request
import sounddevice as sd
import vosk

# Flask сервер
app = Flask(__name__)

# Класс для распознавания речи
class SpeechToText:
    def __init__(self, model_dir):
        self.model_dir = model_dir
        self.recognizer = None
        self.q = queue.Queue()
        self.stop_flag = threading.Event()
        self.is_recording = False
        logging.debug("DEBUG LOG: SpeechToText инициализирован.")

    def load_model(self, language):
        """Загружает модель для выбранного языка."""
        model_path = os.path.join(self.model_dir, language)
        logging.info(f"DEBUG INFO: Попытка загрузки модели: {language}")
        if not os.path.exists(model_path):
            logging.error(f" DEBUG ERR: Модель {language} не найдена в {model_path}")
            raise ValueError(f"Модель {language} не найдена в {model_path}")
        self.recognizer = vosk.KaldiRecognizer(vosk.Model(model_path), 16000)
        logging.info(f"DEBUG INFO: Модель {language} успешно загружена.")

    def callback(self, indata, frames, time, status):
        """Обработка аудиопотока."""
        if status:
            logging.warning(f"DEBUG WAR: Статус ошибки: {status}")
            print(f"Статус ошибки: {status}")
        if self.is_recording:
            self.q.put(bytes(indata))
            logging.debug("DEBUG LOG: Аудиоданные добавлены в очередь.")

    def recognize(self, device=None):
        """Распознает речь с использованием выбранной модели."""
        if not self.recognizer:
            logging.error("DEBUG ERR: Модель не загружена. Сначала вызовите load_model().")
            raise RuntimeError("Модель не загружена. Сначала вызовите load_model().")

        result_text = []
        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16",
                               channels=1, callback=self.callback, device=device):
            print("Запись началась...")
            logging.info("DEBUG INFO: Запись началась.")
            while not self.stop_flag.is_set():
                data = self.q.get()
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    logging.debug(f"Распознанный текст: {result}")
                    result_text.append(result.get("text", ""))
            print("Запись завершена.")
            logging.info("DEBUG INFO: Запись завершена.")
        return " ".join(result_text)

# Создаем экземпляр распознавателя
MODEL_DIR = "model"
stt = SpeechToText(MODEL_DIR)

# Flask маршруты
@app.route("/")
async def home():
    """Главная страница."""
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
async def submit():
    """Обработка отправки текста."""
    data = await request.get_json()
    text = data.get("text", "")
    logging.info(f"Получен текст: {text}")
    return {"status": "success", "message": f"Текст успешно получен: {text}"}

# Класс для GUI
class SpeechApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Распознавание речи")

        # Параметры для модели
        self.languages = {
            "Русский": "vosk-model-ru-0.42",
            "Английский": "vosk-model-en-us-0.42-gigaspeech",
            "Китайский": "vosk-model-cn-kaldi-multicn-0.15",
        }
        self.selected_language = tk.StringVar(value="Русский")

        # Параметры для микрофона
        self.microphones = sd.query_devices()
        self.selected_mic = tk.StringVar(value="Default Microphone")
        self.recording_thread = None  # Поток для записи

        self.create_widgets()

    def create_widgets(self):
        # Заголовок
        logging.debug("DEBUG LOG: Создание GUI элементов.")
        title = tk.Label(self.root, text="Распознавание речи", font=("Arial", 18))
        title.pack(pady=10)

        # Выбор языка
        lang_label = tk.Label(self.root, text="Выберите язык:", font=("Arial", 12))
        lang_label.pack()

        lang_combobox = ttk.Combobox(
            self.root, textvariable=self.selected_language, values=list(self.languages.keys()), state="readonly"
        )
        lang_combobox.pack(pady=5)

        # Выбор микрофона
        mic_label = tk.Label(self.root, text="Выберите микрофон:", font=("Arial", 12))
        mic_label.pack()

        mic_combobox = ttk.Combobox(
            self.root, textvariable=self.selected_mic, values=self.get_microphone_names(), state="readonly"
        )
        mic_combobox.pack(pady=5)

        # Кнопка "Начать запись"
        self.record_button = tk.Button(
            self.root, text="Начать запись", font=("Arial", 14), bg="green", fg="white",
            command=self.toggle_recording, height=2, width=20
        )
        self.record_button.pack(pady=20)

        # Кнопка "Открыть веб-приложение"
        open_browser_button = tk.Button(
            self.root, text="Открыть приложение в браузере", font=("Arial", 12),
            command=self.open_browser
        )
        open_browser_button.pack(pady=10)

    def get_microphone_names(self):
        """Возвращает список доступных микрофонов."""
        return [device['name'] for device in self.microphones]

    def toggle_recording(self):
        """Переключает запись."""
        if not stt.is_recording:
            logging.info("DEBUG INFO: Начало записи.")
            self.start_recording()
        else:
            logging.info("DEBUG INFO: Остановка записи.")
            self.stop_recording()

    def start_recording(self):
        """Начинает запись."""
        try:
            selected_lang = self.selected_language.get()
            lang_model = self.languages[selected_lang]
            logging.info(f"DEBUG INFO: Выбран язык: {selected_lang}, модель: {lang_model}")
            stt.load_model(lang_model)

            mic_name = self.selected_mic.get()
            logging.info(f"DEBUG INFO: Выбран микрофон: {mic_name}")
            messagebox.showinfo("Информация", f"Язык: {selected_lang}, Микрофон: {mic_name}")

            stt.is_recording = True
            stt.stop_flag.clear()
            self.recording_thread = threading.Thread(target=self.process_audio, args=(mic_name,), daemon=True)
            self.recording_thread.start()

            self.record_button.config(text="Остановить запись", bg="red")
        except Exception as e:
            logging.error(f" DEBUG ERR: Ошибка при начале записи: {e}")
            messagebox.showerror("Ошибка", str(e))

    def stop_recording(self):
        """Останавливает запись."""
        stt.is_recording = False
        stt.stop_flag.set()
        self.record_button.config(text="Начать запись", bg="green")
        logging.info("DEBUG INFO: Запись остановлена.")

    def process_audio(self, mic_name):
        """Процесс распознавания и отправки текста."""
        try:
            text = stt.recognize()
            self.send_text_to_server(text)
            logging.info(f"DEBUG INFO: Распознанный текст: {text}")
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка обработки", str(e)))
            logging.error(f" DEBUG ERR: Ошибка обработки аудио: {e}")
            
    def send_text_to_server(self, text):
        """Отправляет распознанный текст на сервер."""
        import requests
        try:
            logging.info("DEBUG INFO: Отправка текста на сервер.")
            response = requests.post("http://127.0.0.1:5000/submit", json={"text": text})
            if response.status_code == 200:
                messagebox.showinfo("Успех", f"Текст отправлен на сервер: {text}")
                logging.info(f"DEBUG INFO: Текст успешно отправлен: {text}")
            else:
                messagebox.showerror("Ошибка", "Не удалось отправить текст на сервер")
                logging.error("DEBUG ERR: Ошибка отправки текста на сервер.")
        except Exception as e:
            logging.error(f" DEBUG ERR: Ошибка сети: {e}")
            messagebox.showerror("Ошибка сети", str(e))

    def open_browser(self):
        """Открывает веб-приложение в браузере."""
        logging.error(f" DEBUG ERR: Ошибка открытия веб-приложения.")
        webbrowser.open("http://127.0.0.1:5000")

# Инициализация модели в фоновом потоке
def preload_models():
    for lang, model_path in app_gui.languages.items():
        try:
            stt.load_model(model_path)
            print(f"Модель {lang} успешно загружена.")
        except Exception as e:
            print(f"Ошибка загрузки модели {lang}: {e}")

# Запуск GUI и Flask
if __name__ == "__main__":
    # Создаем окно для GUI
    root = tk.Tk()
    app_gui = SpeechApp(root)

    # Предварительная загрузка моделей
    threading.Thread(target=preload_models, daemon=True).start()

    # Запускаем Flask в отдельном потоке
    threading.Thread(target=lambda: app.run(debug=False, use_reloader=False), daemon=True).start()

    # Запуск GUI
    root.mainloop()
