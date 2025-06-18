from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from bs4 import BeautifulSoup
import csv
import os
import re
import glob

# Türkiye'deki 81 ilin listesi
turkiye_illeri = {
    "adana", "adıyam", "afyonkarahisar", "ağrı", "amasya", "ankara", "antalya", "artvin", "aydın", "balıkesir",
    "bilecik", "bingöl", "bitlis", "bolu", "burdur", "bursa", "çanakkale", "çankırı", "çorum", "denizli", "diyarbakır",
    "edirne", "elazığ", "erzincan", "erzurum", "eskişehir", "gaziantep", "giresun", "gümüşhane", "hakkari", "hatay",
    "ısparta", "mersin", "istanbul", "izmir", "kars", "kastamonu", "kayseri", "kırklareli", "kırşehir", "kocaeli",
    "konya", "kütahya", "malatya", "manisa", "kahramanmaraş", "mardin", "muğla", "muş", "nevşehir", "niğde", "ordu",
    "rize", "sakarya", "samsun", "siirt", "sinop", "sivas", "tekirdağ", "tokat", "trabzon", "tunceli", "şanlıurfa",
    "uşak", "van", "yozgat", "zonguldak", "aksaray", "bayburt", "karaman", "kırıkkale", "batman", "şırnak", "bartın",
    "ardahan", "ığdır", "yalova", "karabük", "kilis", "osmaniye", "düzce"
}

def get_jokey_surname(jokey_name):
    if " " in jokey_name:
        return jokey_name.split()[-1].strip()
    elif "." in jokey_name:
        return jokey_name.split(".")[-1].strip()
    return jokey_name.strip()

def parse_table_for_k_and_average(table_soup):
    if not table_soup:
        return "veri yok", "veri yok"
    tbody = table_soup.find("tbody")
    if not tbody:
        return "veri yok", "veri yok"
    rows = tbody.find_all("tr", class_=lambda c: c and ("even" in c or "odd" in c))
    total_K = total_weight = total_count = 0
    for row in rows:
        if "Toplam" in row.get_text():
            continue
        cols = row.find_all("td")
        if len(cols) < 7:
            continue
        try:
            k_value = int(''.join(filter(str.isdigit, cols[1].get_text(strip=True))))
        except:
            k_value = 0
        finishes = []
        for i in range(2, 7):
            try:
                finishes.append(int(''.join(filter(str.isdigit, cols[i].get_text(strip=True)))))
            except:
                finishes.append(0)
        total_K += k_value
        weight = sum((pos + 1) * finishes[pos] for pos in range(5))
        count = sum(finishes)
        total_weight += weight
        total_count += count
    if total_count == 0:
        return str(total_K), "veri yok"
    avg_pos = round(total_weight / total_count, 2)
    return str(total_K), str(avg_pos)

def parse_city_specific_stats(detail_soup, current_city):
    try:
        stats_table = detail_soup.find("table", class_="tablesorter", style="width:95%")
        if not stats_table:
            return ["veri yok"] * 7
        tbody = stats_table.find("tbody")
        rows = tbody.find_all("tr", class_=lambda c: c and ("even" in c or "odd" in c))
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 8:
                continue
            city_in_table = cols[0].get_text(strip=True).lower()
            if city_in_table == current_city.lower():
                return [cols[i].get_text(strip=True) for i in range(1, 8)]
        return ["veri yok"] * 7
    except:
        return ["veri yok"] * 7

def parse_jokey_stats(detail_soup, target_jokey):
    try:
        target_surname = get_jokey_surname(target_jokey).lower()
        jokey_header = detail_soup.find("h3", string=lambda s: s and "Jokey" in s)
        if not jokey_header:
            return "veri yok", "veri yok"
        jokey_container = jokey_header.find_parent("div", class_="grid_12 alpha omega kunye")
        if not jokey_container:
            return "veri yok", "veri yok"
        jokey_table = jokey_container.find("table", class_="tablesorter", style=lambda s: s and "width:95%" in s)
        if not jokey_table:
            return "veri yok", "veri yok"
        rows = jokey_table.find("tbody").find_all("tr", class_=lambda c: c and ("even" in c or "odd" in c))
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 8:
                continue
            if get_jokey_surname(cols[0].get_text()).lower() == target_surname:
                try:
                    total_runs = int(cols[1].get_text(strip=True))
                    counts = [int(cols[i].get_text(strip=True)) for i in range(2, 7)]
                except:
                    total_runs = 0
                    counts = [0]*5
                extra = max(0, total_runs - sum(counts))
                weighted = sum((i+1)*counts[i] for i in range(5)) + 8*extra
                avg = round(weighted/total_runs, 2) if total_runs > 0 else "veri yok"
                return str(total_runs), str(avg)
        return "veri yok", "veri yok"
    except:
        return "veri yok", "veri yok"

def parse_surface_stats(detail_soup, filter_surface):
    try:
        pist_h3 = detail_soup.find("h3", string=lambda text: text and "Pist" in text)
        if not pist_h3:
            return "veri yok", "veri yok"
        pist_div = pist_h3.find_parent("div", class_="grid_12 alpha omega kunye")
        table = pist_div.find("table", class_="tablesorter", style="width:95%")
        tbody = table.find("tbody")
        rows = tbody.find_all("tr", class_=lambda x: x and (x in ["even", "odd"]))
        total_runs = total_weighted_sum = 0
        for row in rows:
            tds = row.find_all("td")
            if len(tds) < 8:
                continue
            if tds[0].get_text(strip=True).lower() == filter_surface.lower():
                try:
                    runs = int(''.join(filter(str.isdigit, tds[2].get_text(strip=True))))
                    counts = [int(''.join(filter(str.isdigit, tds[i].get_text(strip=True)))) for i in range(3, 8)]
                except:
                    runs = 0
                    counts = [0]*5
                extra = max(0, runs - sum(counts))
                weighted = sum((i+1)*counts[i] for i in range(5)) + 8*extra
                total_runs += runs
                total_weighted_sum += weighted
        if total_runs == 0:
            return "0", "veri yok"
        return str(total_runs), str(round(total_weighted_sum/total_runs, 2))
    except:
        return "veri yok", "veri yok"

# --- YENİ EKLENDİ: Mesafe-<surface> istatistikleri ---
def parse_distance_stats(detail_soup, surface, distance):
    """
    <h3>Mesafe - Surface</h3> altındaki table'dan distance değerine ait tr'yi bulur,
    koşu sayısı ve ortalama derece döndürür.
    """
    try:
        h3 = detail_soup.find("h3", string=lambda s: s and re.search(rf"Mesafe\s*-\s*{surface}", s, re.IGNORECASE))
        if not h3:
            return "veri yok", "veri yok"
        table = h3.find_next("table", class_="tablesorter", style="width:95%")
        tbody = table.find("tbody")
        rows = tbody.find_all("tr", class_=lambda c: c and (c in ["even","odd"]))
        for row in rows:
            cols = row.find_all("td")
            if not cols:
                continue
            dist_txt = cols[0].get_text(strip=True)
            if re.sub(r"\D","", dist_txt) == distance:
                try:
                    runs = int(re.sub(r"\D","", cols[1].get_text(strip=True)))
                except:
                    runs = 0
                counts = []
                for i in range(2, 7):
                    try:
                        counts.append(int(re.sub(r"\D","", cols[i].get_text(strip=True))))
                    except:
                        counts.append(0)
                extra = max(0, runs - sum(counts))
                weighted = sum((i+1)*counts[i] for i in range(5)) + 8*extra
                avg = round(weighted/runs, 2) if runs > 0 else "veri yok"
                return str(runs), str(avg)
        return "veri yok", "veri yok"
    except:
        return "veri yok", "veri yok"

def parse_race_config(race_config_tag):
    text = race_config_tag.get_text(separator=" ", strip=True)
    m = re.search(r'\b(\d{3,4})\b', text)
    distance = m.group(1) if m else "veri yok"
    lower = text.lower()
    for s in ["kum", "çim", "sentetik"]:
        if re.search(rf'\b{s}\b', lower):
            track_type = s.capitalize()
            filter_word = track_type
            break
    else:
        track_type = filter_word = "veri yok"
    return distance, track_type, filter_word

# -------------------------------------------------------------------------------------------
# Selenium ile veriyi çekip ilgili istatistikleri CSV'ye yazacak ana döngü
# (geri kalan kod tam olarak senin gönderdiğin haliyle, hiçbir başka değişiklik yok)
# -------------------------------------------------------------------------------------------

driver = webdriver.Chrome()
driver.get("https://www.tjk.org/TR/YarisSever/Info/Page/GunlukYarisProgrami#")
num_days = 2  # İşlenecek gün sayısı

for day in range(num_days):
    print(f"\n=== {day + 1}. Gün İşlemi Başlıyor ===")
    turkiye_sehir_sayaci = 0
    while turkiye_sehir_sayaci < 2:
        try:
            sehir_elementleri = WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@href, 'SehirId')]"))
            )
            sehir_linkleri = [(el.text.strip(), el.get_attribute("href")) for el in sehir_elementleri]
        except Exception as e:
            print("Şehir linkleri yüklenemedi, sayfa yenileniyor...", e)
            driver.refresh()
            time.sleep(5)
            continue

        for sehir_adi, sehir_linki in sehir_linkleri:
            if turkiye_sehir_sayaci >= 2:
                break
            sehir_adi_clean = sehir_adi.lower().split(" (")[0]
            if sehir_adi_clean in turkiye_illeri:
                print(f"✔ Türkiye şehri bulundu: {sehir_adi}")
                turkiye_sehir_sayaci += 1
                try:
                    driver.get(sehir_linki)
                    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    time.sleep(3)
                except Exception:
                    print(f"{sehir_adi} sayfasına girerken hata oluştu, atlanıyor...")
                    continue

                city_html = driver.page_source
                city_soup = BeautifulSoup(city_html, "html.parser")
                race_config_tags = city_soup.find_all("h3", class_="race-config")
                all_tables = city_soup.find_all("table", summary="Kosular", class_="tablesorter")
                if not all_tables:
                    print(f"{sehir_adi} sayfasında 'Kosular' tablosu bulunamadı.")
                    continue

                race_count = 0
                for table_idx, table in enumerate(all_tables, start=1):
                    distance, track_type, filter_word = "veri yok", "veri yok", "veri yok"
                    if len(race_config_tags) >= table_idx:
                        distance, track_type, filter_word = parse_race_config(race_config_tags[table_idx - 1])

                    tbody = table.find("tbody")
                    if not tbody:
                        continue
                    rows = tbody.find_all("tr", class_=lambda c: c and ("even" in c or "odd" in c))
                    if not rows:
                        continue
                    race_data = []

                    for row in rows:
                        jokey_td = row.find("td", class_="gunluk-GunlukYarisProgrami-JokeAdi")
                        if jokey_td:
                            jokey_a = jokey_td.find("a")
                            jokey_name_main = jokey_a.get_text(strip=True) if jokey_a else "veri yok"
                        else:
                            jokey_name_main = "veri yok"
                        target_jokey_surname = get_jokey_surname(jokey_name_main)

                        sira_id_td = row.find("td", class_="gunluk-GunlukYarisProgrami-SiraId")
                        if not sira_id_td:
                            continue
                        sira_id_text = sira_id_td.get_text(strip=True)

                        # Yeni yarışı yazmadan önce, '1' ile başlayan bir önceki yarış varsa CSV'le
                        if sira_id_text == "1" and race_data:
                            race_count += 1
                            header = [
                                "At Adı", "K", "Ortalama", "Pist", "Yarış Tipi",
                                f"{sehir_adi} Hipodromu Koşu Sayısı", f"{sehir_adi} Hipodromu Ortalama Derecesi",
                                "Aktif Jokey Koşu Sayısı", "Aktif Jokey Ortalama Derece",
                                f"{track_type} Pist Koşu Sayısı", f"{track_type} Pist Ortalama Derece",
                                f"{distance} Mesafede Koşu Sayısı", f"{distance} Mesafede Ortalama Derece",
                                "Filtre Kelimesi"
                            ]
                            fn = f"{sehir_adi.capitalize()}_Race_{race_count}.csv"
                            with open(fn, "w", newline="", encoding="utf-8") as f:
                                writer = csv.writer(f)
                                writer.writerow(header)
                                writer.writerows(race_data)
                            print(f"  -> {fn} dosyasına {len(race_data)} at yazıldı.")
                            race_data = []

                        at_td = row.find("td", class_="gunluk-GunlukYarisProgrami-AtAdi")
                        a_tag = at_td.find("a", href=lambda x: x and "QueryParameter_AtId" in x) if at_td else None
                        if not a_tag:
                            continue
                        horse_href = a_tag.get("href")
                        if horse_href.startswith("/"):
                            horse_href = "https://www.tjk.org" + horse_href
                        horse_name_raw = a_tag.get_text(strip=True)

                        main_window = driver.current_window_handle
                        try:
                            driver.execute_script("window.open(arguments[0]);", horse_href)
                            WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)
                            new_tab = [h for h in driver.window_handles if h != main_window][0]
                            driver.switch_to.window(new_tab)
                            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                            time.sleep(20)  # orijinal bekleme süresi
                            try:
                                detayli_btn = WebDriverWait(driver, 7).until(
                                    EC.element_to_be_clickable((By.XPATH, "//a[@id='AtKosuIstatistik']"))
                                )
                                detayli_btn.click()
                            except Exception:
                                print("Detaylı İstatistikler butonu bulunamadı.")
                            time.sleep(20)

                            detail_soup = BeautifulSoup(driver.page_source, "html.parser")
                            horse_name_tag = detail_soup.find("h2", class_="tableTitle")
                            horse_name = horse_name_tag.get_text(strip=True) if horse_name_tag else horse_name_raw

                            # (A) Genel at istatistikleri
                            stat_table = detail_soup.find("table", class_="tablesorter", attrs={"style": "width:99%"})
                            total_K, avg_position = parse_table_for_k_and_average(stat_table)

                            # (B) Hipodrom istatistikleri
                            city_stats = parse_city_specific_stats(detail_soup, sehir_adi_clean)
                            if city_stats[0] == "veri yok":
                                hip_kosu, hip_avg = "veri yok", "veri yok"
                            else:
                                try:
                                    nr = int(city_stats[0])
                                    cnts = list(map(int, city_stats[1:6]))
                                    extra = max(0, nr - sum(cnts))
                                    wsum = sum((i+1)*cnts[i] for i in range(5)) + 8*extra
                                    hip_kosu, hip_avg = str(nr), str(round(wsum/nr, 2))
                                except:
                                    hip_kosu, hip_avg = "veri yok", "veri yok"

                            # (C) Jokey istatistikleri
                            jokey_runs, jokey_avg = parse_jokey_stats(detail_soup, jokey_name_main)

                            # (D) Pist istatistikleri
                            x_surface_runs, x_surface_avg = parse_surface_stats(detail_soup, filter_word)

                            # (E) Mesafe-<surface> istatistikleri
                            dist_runs, dist_avg = parse_distance_stats(detail_soup, filter_word, distance)

                            race_data.append([
                                horse_name,
                                total_K,
                                avg_position,
                                sehir_adi,
                                track_type,
                                hip_kosu,
                                hip_avg,
                                jokey_runs,
                                jokey_avg,
                                x_surface_runs,
                                x_surface_avg,
                                dist_runs,
                                dist_avg,
                                filter_word
                            ])

                            driver.close()
                            driver.switch_to.window(main_window)
                        except Exception as ex:
                            print("At detay sayfasında hata oluştu:", ex)
                            try:
                                driver.close()
                            except:
                                pass
                            driver.switch_to.window(main_window)
                            continue

                    # Son yarış biterken
                    if race_data:
                        race_count += 1
                        header = [
                            "At Adı", "K", "Ortalama", "Pist", "Yarış Tipi",
                            f"{sehir_adi} Hipodromu Koşu Sayısı", f"{sehir_adi} Hipodromu Ortalama Derecesi",
                            "Aktif Jokey Koşu Sayısı", "Aktif Jokey Ortalama Derece",
                            f"{track_type} Pist Koşu Sayısı", f"{track_type} Pist Ortalama Derece",
                            f"{distance} Mesafede Koşu Sayısı", f"{distance} Mesafede Ortalama Derece",
                            "Filtre Kelimesi"
                        ]
                        fn = f"{sehir_adi.capitalize()}_Race_{race_count}.csv"
                        with open(fn, "w", newline="", encoding="utf-8") as f:
                            writer = csv.writer(f)
                            writer.writerow(header)
                            writer.writerows(race_data)
                        print(f"  -> {fn} dosyasına {len(race_data)} at yazıldı.")

                # Ana sayfaya dön
                driver.get("https://www.tjk.org/TR/YarisSever/Info/Page/GunlukYarisProgrami#")
                WebDriverWait(driver, 20).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@href, 'SehirId')]"))
                )
                time.sleep(5)
        if turkiye_sehir_sayaci < 2:
            print("İstenen sayıda şehir bulunamadı, tekrar deneniyor...")
            break
    if day < num_days - 1:
        try:
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[@title='Sonraki Gün']"))
            )
            next_button.click()
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(5)
            print("Sonraki güne geçildi.\n")
        except Exception:
            print("Sonraki gün butonu bulunamadı! Sayfa yenileniyor...")
            driver.refresh()
            time.sleep(5)

driver.quit()

# -------------------------------------------------------------------------------------------
# --- ANALİZ AŞAMASI: Oluşturulan her Race_X.csv için Race_X_Analiz.csv ve genel özet CSV ----
# -------------------------------------------------------------------------------------------

summary = []

# Tüm Race_*.csv dosyalarını bul
race_files = [f for f in os.listdir() if re.match(r'.+_Race_\d+\.csv$', f)]

for raw in race_files:
    # Her bir raw CSV'yi oku
    with open(raw, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    analiz_rows = []
    for row in rows:
        total_runs = 0
        total_weighted = 0.0
        # ko�u say� ve derece çiftleri header indeksleri: 5,6 | 7,8 | 9,10 | 11,12
        for i in [5, 7, 9, 11]:
            try:
                runs = int(row[i])
                avg  = float(row[i+1])
                total_runs += runs
                total_weighted += runs * avg
            except:
                continue
        if total_runs > 0:
            gen_avg = round(total_weighted / total_runs, 2)
        else:
            gen_avg = None
        analiz_rows.append((row[0], gen_avg))

    # Sıralama: None en sona
    analiz_rows.sort(key=lambda x: (x[1] is None, x[1]))

    # Race_X_Analiz.csv oluştur
    analiz_fn = raw.replace('.csv', '_Analiz.csv')
    with open(analiz_fn, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Başlık: 1. At Adı, 1. Genel Ortalama, 2. At Adı, 2. Genel Ortalama, vs.
        başlık = []
        for idx, _ in enumerate(analiz_rows, start=1):
            başlık += [f"{idx}. At Adı", f"{idx}. Genel Ortalama"]
        writer.writerow(başlık)

        # Tek satırda tüm atlar
        satır = []
        for name, avg in analiz_rows:
            satır += [name, avg if avg is not None else '?']
        writer.writerow(satır)

    # Özet için ilk 3'ü kaydet
    top3 = analiz_rows[:3]
    summary.append((raw, top3))

# Tüm yarışların favori ilk 3 atını içeren CSV
with open('TumYarislar_EnIyi3.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow([
        "Race",
        "1. At Adı","1. Genel Ortalama",
        "2. At Adı","2. Genel Ortalama",
        "3. At Adı","3. Genel Ortalama"
    ])
    for raw, top3 in summary:
        row = [raw]
        for i in range(3):
            if i < len(top3):
                name, avg = top3[i]
                row += [name, avg if avg is not None else '?']
            else:
                row += ["",""]
        writer.writerow(row)
