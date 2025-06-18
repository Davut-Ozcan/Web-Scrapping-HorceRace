# Web Scraping – Horse Race

🏇 This project scrapes horse racing data using Python.

---

## 📌 New Version Available: [`v2`](./v2)

Version 2 introduces a completely redesigned scraping logic focused on **future races** rather than past results.  
Instead of endlessly collecting outdated data, this version selectively targets upcoming races and fetches **detailed statistics** of only the **horses that are scheduled to run**.

This results in:
- 🚀 **Improved efficiency** by skipping unnecessary data
- 🧠 **More meaningful data** by focusing only on relevant entries
- 🕒 **Significant time savings**

In addition, the saved time is now utilized for **deeper analysis**:  
For each horse, it analyzes their historical performance specifically on the same track, with the same jockey, and at the same distance — **leading to more accurate and actionable insights**.

The original version (`main.py`) is still available, but v2 provides much smarter, faster, and cleaner data scraping.

---

## 📁 Folder Structure

- `main.py`: Original version (v1)
- `v2/main.py`: New version (v2)

---

## 🛠️ Requirements

To run this project, install the required libraries:

```bash
pip install requests beautifulsoup4 pandas
