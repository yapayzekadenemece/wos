import whisper

model = whisper.load_model("base")
result = model.transcribe("1_Kayit.mp3")
print(result["text"])