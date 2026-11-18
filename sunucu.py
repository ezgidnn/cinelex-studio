import os
import json
import re
import httpx
import requests
import urllib3
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from groq import Groq
from dotenv import load_dotenv
from kelime_secici import hedef_kelimeyi_bul

urllib3.disable_warnings()
eski_request = requests.Session.request
def yeni_request(self, *a, **kw):
    kw["verify"] = False
    return eski_request(self, *a, **kw)
requests.Session.request = yeni_request

load_dotenv()

uygulama = FastAPI(title="CineLex Studio Sunucusu")

uygulama.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

groq_anahtari = os.getenv("GROQ_API_KEY", "").strip()
groq_istemcisi = None
if groq_anahtari and "buraya_groq" not in groq_anahtari:
    groq_istemcisi = Groq(
        api_key=groq_anahtari,
        http_client=httpx.Client(verify=False)
    )

kelime_onbellegi = {
    "gonna": {"ana": "-ecek / -acak", "diger": ["going to (kısaltma)"]},
    "wanna": {"ana": "istemek", "diger": ["want to (kısaltma)"]},
    "gotta": {"ana": "zorunda olmak", "diger": ["got to (kısaltma)"]},
    "the": {"ana": "(belirli tanımlık)", "diger": ["o, bu, şu"]},
    "a": {"ana": "bir", "diger": ["herhangi bir"]},
    "an": {"ana": "bir", "diger": ["herhangi bir"]},
    "some": {"ana": "biraz / bazı", "diger": ["birkaç", "bir miktar"]}
}

class VideoIstegi(BaseModel):
    youtube_linki: str
    seviye_filtresi: Optional[str] = "HEPSI"

class TekKelimeIstegi(BaseModel):
    kelime: str
    cumle: Optional[str] = ""

def video_id_ayikla(link: str) -> str:
    desen = r"(?:v=|\/|youtu\.be\/|shorts\/)([0-9A-Za-z_-]{11})"
    eslesme = re.search(desen, link)
    if not eslesme:
        raise ValueError("Geçersiz YouTube linki girdiniz.")
    return eslesme.group(1)

def altyazilari_cek(video_id: str) -> list:
    yt_api = YouTubeTranscriptApi()
    if hasattr(yt_api, "fetch"):
        ham_veri = yt_api.fetch(video_id, languages=['en', 'en-US', 'en-GB'])
        ham_parcalar = [
            {
                "baslangic": round(s.start, 2),
                "bitis": round(s.start + s.duration, 2),
                "metin": re.sub(r"\s+", " ", s.text).strip()
            }
            for s in ham_veri
        ]
    else:
        ham_veri = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US', 'en-GB'])
        ham_parcalar = [
            {
                "baslangic": round(s["start"], 2),
                "bitis": round(s["start"] + s["duration"], 2),
                "metin": re.sub(r"\s+", " ", s["text"]).strip()
            }
            for s in ham_veri
        ]

    # Sadece gerçek metin içeren parçaları al
    temiz_parcalar = [
        p for p in ham_parcalar
        if p["metin"] and not p["metin"].startswith("[") and not p["metin"].startswith("(")
    ]

    # Noktasına (. ? !) veya doğal cümle sonuna kadar birleştir,
    # AMA her alt parçanın zaman damgasını 'parcalar' listesinde koru!
    tam_cumleler = []
    aktif_grup = None

    for i, p in enumerate(temiz_parcalar):
        if aktif_grup is None:
            aktif_grup = {
                "baslangic": p["baslangic"],
                "bitis": p["bitis"],
                "metin": p["metin"],
                "parcalar": [dict(p)]
            }
        else:
            bosluk_suresi = p["baslangic"] - aktif_grup["bitis"]
            onceki_bitti = aktif_grup["metin"].endswith((".", "?", "!"))
            yeni_buyuk_harf = p["metin"][0].isupper() and not p["metin"].startswith("I ") and p["metin"] != "I"
            kelime_sayisi = len(aktif_grup["metin"].split())

            # Cümle noktalandıysa, uzun nefes arası varsa veya otomatik altyazı 22 kelimeyi aştıysa yeni cümleye geç
            if onceki_bitti or bosluk_suresi > 1.3 or (yeni_buyuk_harf and kelime_sayisi >= 6) or kelime_sayisi >= 22:
                tam_cumleler.append(aktif_grup)
                aktif_grup = {
                    "baslangic": p["baslangic"],
                    "bitis": p["bitis"],
                    "metin": p["metin"],
                    "parcalar": [dict(p)]
                }
            else:
                aktif_grup["metin"] += " " + p["metin"]
                aktif_grup["bitis"] = max(aktif_grup["bitis"], p["bitis"])
                aktif_grup["parcalar"].append(dict(p))

    if aktif_grup:
        tam_cumleler.append(aktif_grup)

    return tam_cumleler

def google_sozluk_detayli(kelime: str) -> dict:
    temiz = kelime.lower().strip()
    if temiz in kelime_onbellegi:
        return kelime_onbellegi[temiz]
    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": "en",
                "tl": "tr",
                "dt": ["t", "bd"],
                "q": temiz
            },
            timeout=4
        )
        veri = r.json()
        anlamlar = []
        if len(veri) > 1 and veri[1]:
            for grup in veri[1][:3]:
                for sozcuk in grup[1][:3]:
                    w = sozcuk.lower().strip()
                    if w and w not in anlamlar:
                        anlamlar.append(w)
        if veri[0] and veri[0][0] and veri[0][0][0]:
            ana = veri[0][0][0].lower().strip()
            if ana and ana not in anlamlar:
                anlamlar.insert(0, ana)

        ana_anlam = anlamlar[0] if anlamlar else "—"
        diger_anlamlar = anlamlar[1:4]
        sonuc = {"ana": ana_anlam, "diger": diger_anlamlar}
        kelime_onbellegi[temiz] = sonuc
        return sonuc
    except Exception:
        return {"ana": "—", "diger": []}

def turkce_anlamlari_getir(sorular: list) -> dict:
    if not sorular:
        return {}

    if groq_istemcisi:
        try:
            satirlar = [
                f"{sira}. Cümle: \"{item['cumle']}\" | Hedef Kelime: \"{item['hedef_kelime']}\""
                for sira, item in enumerate(sorular)
            ]
            komut = (
                "Aşağıdaki İngilizce repliklerde geçen hedef kelimelerin, "
                "SADECE o cümledeki bağlamına uygun kısa Türkçe karşılığını (1-3 kelime) yaz.\n"
                "Yanıtı yalnızca JSON formatında ver. Örnek: {\"0\": \"fondöten\", \"1\": \"başlamak\"}\n\n"
                + "\n".join(satirlar)
            )
            yanit = groq_istemcisi.chat.completions.create(
                messages=[{"role": "user", "content": komut}],
                model="llama-3.3-70b-versatile",
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            return json.loads(yanit.choices[0].message.content)
        except Exception as e:
            print("Groq çeviri hatası:", e)

    sonuclar = {}
    for sira, item in enumerate(sorular[:40]):
        detay = google_sozluk_detayli(item["hedef_kelime"])
        sonuclar[str(sira)] = detay["ana"]
    return sonuclar

@uygulama.post("/kelime-cevir")
async def tek_kelime_cevir(istek: TekKelimeIstegi):
    temiz = re.sub(r"[^a-zA-Z'-]", "", istek.kelime).lower()
    if not temiz:
        return {"ana": "", "diger": []}

    detay = google_sozluk_detayli(temiz)

    # Eğer Groq aktifse bağlamsal en doğru anlamı en üste koy
    if groq_istemcisi and istek.cumle:
        try:
            komut = f"'{istek.cumle}' cümlesindeki '{temiz}' kelimesinin bu cümledeki Türkçe karşılığını SADECE 1-2 kelime olarak yaz."
            yanit = groq_istemcisi.chat.completions.create(
                messages=[{"role": "user", "content": komut}],
                model="llama-3.3-70b-versatile",
                temperature=0.1,
                max_tokens=15
            )
            baglamsal = yanit.choices[0].message.content.strip().strip('"').lower()
            if baglamsal:
                diger = [d for d in [detay["ana"]] + detay["diger"] if d != baglamsal][:3]
                return {"ana": baglamsal, "diger": diger}
        except Exception:
            pass

    return detay

@uygulama.post("/video-hazirla")
async def video_hazirla(istek: VideoIstegi):
    try:
        video_id = video_id_ayikla(istek.youtube_linki)
        tam_cumleler = altyazilari_cek(video_id)
    except Exception as hata:
        raise HTTPException(status_code=400, detail=f"Altyazı çekilemedi: {str(hata)}")

    islenmis = []
    ceviri_bekleyenler = []

    for satir in tam_cumleler:
        cumle = satir["metin"]
        hedef_kelime, seviye = hedef_kelimeyi_bul(cumle, istek.seviye_filtresi)

        # Her alt parçanın içinde hedef kelime geçiyorsa o parçada da boşluklu halini hazırla
        islenmis_parcalar = []
        kelime_gizlendi = False
        for p in satir["parcalar"]:
            p_metin = p["metin"]
            if hedef_kelime and not kelime_gizlendi and re.search(rf"\b{re.escape(hedef_kelime)}\b", p_metin):
                p_bosluklu = re.sub(rf"\b{re.escape(hedef_kelime)}\b", "_____", p_metin, count=1)
                kelime_gizlendi = True
            else:
                p_bosluklu = p_metin
            islenmis_parcalar.append({
                "baslangic": p["baslangic"],
                "bitis": p["bitis"],
                "tam_metin": p_metin,
                "bosluklu_metin": p_bosluklu
            })

        veri = {
            "baslangic": satir["baslangic"],
            "bitis": satir["bitis"],
            "tam_cumle": cumle,
            "parcalar": islenmis_parcalar,
            "soru_var_mi": bool(hedef_kelime and kelime_gizlendi),
            "hedef_kelime": hedef_kelime if kelime_gizlendi else None,
            "seviye": seviye if kelime_gizlendi else None,
            "turkce_ipucu": None
        }

        if veri["soru_var_mi"]:
            ceviri_bekleyenler.append({
                "liste_sirasi": len(islenmis),
                "cumle": cumle,
                "hedef_kelime": hedef_kelime
            })

        islenmis.append(veri)

    grup = ceviri_bekleyenler[:45]
    if grup:
        ceviriler = turkce_anlamlari_getir(grup)
        for sira_str, tr_anlam in ceviriler.items():
            idx = int(sira_str)
            if idx < len(grup):
                ilgili_soru = grup[idx]
                islenmis[ilgili_soru["liste_sirasi"]]["turkce_ipucu"] = tr_anlam

    return {
        "video_id": video_id,
        "toplam_satir": len(islenmis),
        "soru_sayisi": len(ceviri_bekleyenler),
        "altyazilar": islenmis
    }

@uygulama.get("/")
async def ana_sayfa():
    return FileResponse("../ekran-arayuzu/index.html")