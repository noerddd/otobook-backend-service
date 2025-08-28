from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai import Credentials
import json
import os

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

cache_file = "cache_watsonx.json"
if os.path.exists(cache_file):
    with open(cache_file, "r") as f:
        cache = json.load(f)
else:
    cache = {}

def generate_keywords_watsonx(sinopsis: str):
    try:
        prompt = f"""
        Buatkan hanya 3 klasifikasi Dewey Decimal dan subject paling relevan
        dalam Bahasa Indonesia untuk sinopsis berikut:

        {sinopsis}

        Output hanya berupa daftar dipisahkan koma.
        Contoh format:
        006.3, Teknologi, Kecerdasan Buatan
        """

        response = model.generate(
            prompt,
            params={"decoding_method": "greedy", "max_new_tokens": 150}
        )

        text = response['results'][0]['generated_text'].strip()
        text = text.replace("\n", ",").replace(";", ",")
        parts = [p.strip() for p in text.split(",") if p.strip()]
        top3 = parts[:3]
        keywords_text = ", ".join(top3)

        return {"keywords": keywords_text}
    except Exception as e:
        print("ERROR di generate_keywords_watsonx:", e)
        return {"keywords": ""}
