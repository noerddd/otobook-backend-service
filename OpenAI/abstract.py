from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai import Credentials
import json
import os

# Ambil ini dari IBM Cloud dashboard setelah bikin project watsonx.ai
API_KEY = "YOUR_API_KEY"
PROJECT_ID = "YOUR_PROJECT_ID"

creds = Credentials(
    url="https://jp-tok.ml.cloud.ibm.com",
    api_key=API_KEY
)

params = {
    "decoding_method": "greedy",
    "max_new_tokens": 200,
    "temperature": 0.7,
}

# Pilih model Granite gratis yang ada di watsonx.ai
model = ModelInference(
    model_id="ibm/granite-3-8b-instruct",   # lebih baru
    params=params,
    credentials=creds,
    project_id=PROJECT_ID
)

cache_file = "./Damy/cache_abstract.json"
if os.path.exists(cache_file):
    with open(cache_file, "r") as f:
        cache = json.load(f)
else:
    cache = {}

def generate_abstract_watsonx(synopsis: str):
    # Cek cache
    if synopsis in cache:
        return cache[synopsis]

    prompt = f"""
    Buatkan abstrak singkat dalam Bahasa Indonesia
    berdasarkan sinopsis buku berikut:

    {synopsis}
    """

    # Panggil model Granite
    response = model.generate_text(prompt=prompt)

    # Ambil hasil teks
    abstract = response['results'][0]['generated_text'].strip()

    # Simpan ke cache
    cache[synopsis] = abstract
    with open(cache_file, "w") as f:
        json.dump(cache, f)

    return abstract
