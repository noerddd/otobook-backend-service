import json
import sys
import os
from fuzzywuzzy import fuzz

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai import Credentials

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

# Pilih model Granite
model = ModelInference(
    model_id="ibm/granite-3-8b-instruct",   # lebih baru
    params=params,
    credentials=creds,
    project_id=PROJECT_ID
)

def is_synopsis_match(synopsis, narasi_klasifikasi, subject):
    if narasi_klasifikasi:     
        match_ratio = fuzz.token_set_ratio(synopsis.lower(), narasi_klasifikasi.lower())
    else:
        match_ratio = 0
    
    if subject:
        match_ratio_subject = fuzz.token_set_ratio(synopsis.lower(), subject.lower())
    else:
        match_ratio_subject = 0
    
    return match_ratio_subject >= 70 or  match_ratio >= 70 

# Cek apakah file cache ada
cache_file = './Damy/cache.json'
if os.path.exists(cache_file):
    with open(cache_file, 'r') as file:
        cache = json.load(file)
else:
    cache = {}

def generate_keywords_watsonx(synopsis):
    from app import app, KlasifikasiBuku

    # Kalau ada di cache, return langsung
    if synopsis in cache:
        return cache[synopsis]

    with app.app_context():
        klasifikasi_buku = KlasifikasiBuku.query.all()
        matches = []

        prompt = f"""
        Buatkan daftar keywords (maksimal 2 kalimat ringkas)
        untuk sinopsis buku berikut dalam Bahasa Indonesia.

        Sinopsis:
        {synopsis}

        Format output: pisahkan setiap keyword dengan koma.
        """

        # Panggil Granite
        response = model.generate_text(prompt=prompt)
        keywords_text = response['results'][0]['generated_text'].strip()

        try:
            keywords_list = [keyword.strip() for keyword in keywords_text.split(',')]
            keywords = ', '.join(keywords_list)
        except Exception as e:
            print(f"Error parsing keywords: {e}")
            keywords = "error"
            keywords_list = []

        # Simpan ke cache
        cache[synopsis] = keywords
        with open(cache_file, 'w') as file:
            json.dump(cache, file)

        # Pencocokan dengan DB
        for klasifikasi in klasifikasi_buku:
            for keyword in keywords_list:
                if is_synopsis_match(keyword, klasifikasi.narasi_klasifikasi, klasifikasi.subject):
                    matches.append({
                        'deweyNoClass': klasifikasi.deweyNoClass,
                        'narasiKlasifikasi': klasifikasi.narasi_klasifikasi,
                        'subject': klasifikasi.subject
                    })
                    break

        if matches:
            return {
                'keywords': keywords,
                'deweyNoClass': matches[0]['deweyNoClass'],
                'subject': matches[0]['subject'],
                'source': 'from database'
            }
        else:
            return {
                'keywords': keywords,
                'message': "keywords tidak ada di database"
            }
