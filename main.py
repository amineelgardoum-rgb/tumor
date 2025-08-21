from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import os
import numpy as np
from keras.preprocessing.image import load_img, img_to_array
from tensorflow.keras.models import load_model

import kagglehub
import shutil

app = FastAPI()

UPLOAD_FOLDER = "./uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_FOLDER), name="uploads")
templates = Jinja2Templates(directory="templates")

class_labels = ['pituitary', 'glioma', 'notumor', 'meningioma']

# Download model via KaggleHub
def download_model():
    path = kagglehub.model_download("noorsaeed/mri_brain_tumor_model/keras/default")
    print("Downloaded model to:", path)
    return os.path.join(path, "model.h5")  # adjust based on the actual filename

MODEL_PATH = download_model()
model = load_model(MODEL_PATH)

def predict_tumor(image_path):
    img = load_img(image_path, target_size=(128, 128))
    img_array = img_to_array(img) / 255
    img_array = np.expand_dims(img_array, axis=0)

    predictions = model.predict(img_array)
    predicted_class_index = np.argmax(predictions, axis=1)[0]
    confidence_score = np.max(predictions, axis=1)[0]

    if class_labels[predicted_class_index] == 'notumor':
        return "No Tumor", confidence_score
    else:
        return f"Tumor: {class_labels[predicted_class_index]}", confidence_score

@app.get("/", response_class=HTMLResponse)
async def form_get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "result": None})

@app.post("/", response_class=HTMLResponse)
async def form_post(request: Request, file: UploadFile = File(...)):
    filename = file.filename if file.filename is not None else "uploaded_file"
    file_location = os.path.join(UPLOAD_FOLDER, filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result, confidence = predict_tumor(file_location)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "result": result,
        "confidence": f"{confidence*100:.2f}",
        "file_path": f"/uploads/{file.filename}"
    })

if __name__=="__main__":
    import uvicorn
    uvicorn.run("main:app",host="127.0.0.1",port=8000,reload=True)