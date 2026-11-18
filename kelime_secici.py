from a2_b1_kelimeler import KELIME_LISTESI, DUZENSIZ_KOKLER

def hedef_kelimeyi_bul(cumle: str, seviye_filtresi: str = "HEPSI"):
    temiz_kelimeler = [
        "".join(harf for harf in kelime if harf.isalpha())
        for kelime in cumle.split()
    ]
    for orijinal_kelime in temiz_kelimeler:
        if len(orijinal_kelime) < 4:
            continue
        kucuk = orijinal_kelime.lower()
        bulunan_seviye = None

        if kucuk in KELIME_LISTESI:
            bulunan_seviye = KELIME_LISTESI[kucuk]
        elif kucuk in DUZENSIZ_KOKLER and DUZENSIZ_KOKLER[kucuk] in KELIME_LISTESI:
            bulunan_seviye = KELIME_LISTESI[DUZENSIZ_KOKLER[kucuk]]
        else:
            for ek in ["s", "es", "ed", "ing", "d", "ly", "er", "est"]:
                if kucuk.endswith(ek) and len(kucuk) > len(ek) + 2:
                    kok = kucuk[:-len(ek)]
                    if kok in KELIME_LISTESI:
                        bulunan_seviye = KELIME_LISTESI[kok]
                        break
                    if (kok + "e") in KELIME_LISTESI:
                        bulunan_seviye = KELIME_LISTESI[kok + "e"]
                        break

        if bulunan_seviye:
            if seviye_filtresi == "HEPSI" or bulunan_seviye == seviye_filtresi:
                return orijinal_kelime, bulunan_seviye

    return None, None
