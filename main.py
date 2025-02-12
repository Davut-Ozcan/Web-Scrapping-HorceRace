from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import unicodedata
import re
import time
import matplotlib.pyplot as plt

def fix_text(text):
    return unicodedata.normalize("NFKD", text).strip()

def clean_name(name):
    name = fix_text(name)
    name = re.sub(r"\s*\([^)]*\)", "", name)
    name = re.sub(r"\b(KG|DB|SK|YP|GKR)\b", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def safe_int(value):
    try:
        return int(value)
    except ValueError:
        return None

def change_page(driver):
    try:
        back_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "form.query a"))
        )
        driver.execute_script("arguments[0].click();", back_button)
        time.sleep(2)  # Sayfanın tamamen yüklenmesini bekle
    except Exception as e:
        print("Sayfa değiştirilemedi veya buton bulunamadı:", e)

def scrap_page(driver):
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "td.gunluk-GunlukYarisSonuclari-AtAdi3"))
        )
    except Exception as e:
        print("Sayfa yükleme hatası:", e)
        return [], [], []

    positions = driver.find_elements(By.CSS_SELECTOR, 'td.gunluk-GunlukYarisSonuclari-SONUCNO')
    names = driver.find_elements(By.CSS_SELECTOR, "td.gunluk-GunlukYarisSonuclari-AtAdi3")
    j_names = driver.find_elements(By.CSS_SELECTOR, "td.gunluk-GunlukYarisSonuclari-JokeAdi")


    pos_list = []
    name_list = []
    jokey_list = []


    for pos, name, jokey in zip(positions, names, j_names):
        pos_text = safe_int(fix_text(pos.text))
        name_text = clean_name(fix_text(name.text)).split("(")[0].strip()  # Parantezden öncesini alıyoruz
        jokey_text = clean_name(fix_text(jokey.text))

        if pos_text is not None and pos_text > 0 and name_text and jokey_text:  # Pozisyon 0 veya None ise dahil etme
            pos_list.append(pos_text)
            name_list.append(name_text)
            jokey_list.append(jokey_text)

    return pos_list, name_list, jokey_list

url = "https://www.tjk.org/TR/yarissever/Info/Page/GunlukYarisSonuclari"
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_experimental_option("detach", True)
driver = webdriver.Chrome(options=options)
driver.get(url)

data_list = []
num_pages = 100

for _ in range(num_pages):
    pos_list, name_list, jokey_list = scrap_page(driver)
    if pos_list and name_list and jokey_list:
        data_list.extend(zip(pos_list, name_list, jokey_list))
    change_page(driver)

driver.quit()


df = pd.DataFrame(data_list, columns=["Pozisyon", "At İsmi", "Jokey"])


df = df[df["Pozisyon"] > 0]

if df.empty:
    print("Hiç veri alınamadı, lütfen tekrar deneyin!")
    exit()

# At istatistikleri
at_stats = df.groupby("At İsmi").agg(
    Ortalama_Pozisyon=("Pozisyon", "mean"),
    Yarış_Sayısı=("At İsmi", "size")
).sort_values("Ortalama_Pozisyon")

at_stats_filtered = at_stats[at_stats["Yarış_Sayısı"] >= 4]

# Jokey istatistikleri
jokey_stats = df.groupby("Jokey").agg(
    Ortalama_Pozisyon=("Pozisyon", "mean"),
    Yarış_Sayısı=("Jokey", "size")
).sort_values("Ortalama_Pozisyon")

jokey_stats_filtered = jokey_stats[jokey_stats["Yarış_Sayısı"] >= 10]

# At-Jokey birlikteliği
birliktelik = df.groupby(["At İsmi", "Jokey"]).agg(
    Ortalama_Pozisyon=("Pozisyon", "mean"),
    Yarış_Sayısı=("Pozisyon", "size")
).sort_values("Ortalama_Pozisyon")


birliktelik_filtered = birliktelik[birliktelik["Yarış_Sayısı"] >= 3]

print("\nEn Başarılı Atlar (Min 4 Yarış):")
print(at_stats_filtered)

print("\nEn Başarılı Jokeyler (Min 10 Yarış):")
print(jokey_stats_filtered)

print("\nEn Başarılı At-Jokey Birliktelikleri (Min 3 Yarış):")
print(birliktelik_filtered)

# CSV kayıtları
at_stats.to_csv("en_basarili_atlar.csv", encoding="utf-8-sig")
jokey_stats.to_csv("en_basarili_jokeyler.csv", encoding="utf-8-sig")
birliktelik.to_csv("en_basarili_at_jokey_birliktelikleri.csv", encoding="utf-8-sig")

# Grafikler
plt.figure(figsize=(18, 6))

#En iyi atlar
plt.subplot(1, 3, 1)
at_stats_filtered["Ortalama_Pozisyon"].head(10).plot(kind="bar", color="blue", alpha=0.7)
plt.title("En Başarılı Atlar (Min 4 Yarış)")
plt.ylabel("Ortalama Pozisyon (Düşük Daha İyi)")
plt.xticks(rotation=45)

# En iyi jokeyler
plt.subplot(1, 3, 2)
jokey_stats_filtered["Ortalama_Pozisyon"].head(10).plot(kind="bar", color="green", alpha=0.7)
plt.title("En Başarılı Jokeyler (Min 10 Yarış)")
plt.ylabel("Ortalama Pozisyon (Düşük Daha İyi)")
plt.xticks(rotation=45)

# En iyi At-Jokey Birliktelikleri
plt.subplot(1, 3, 3)
birliktelik_filtered["Ortalama_Pozisyon"].head(10).plot(kind="bar", color="red", alpha=0.7)
plt.title("En Başarılı At-Jokey Birliktelikleri (Min 3 Yarış)")
plt.ylabel("Ortalama Pozisyon (Düşük Daha İyi)")
plt.xticks(rotation=45)

plt.tight_layout()
plt.show()
