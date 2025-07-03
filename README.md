
# sunnah.com_scraper

This is a simple Python-based scraper for extracting Hadith data from [sunnah.com](https://sunnah.com).  
It scrapes **book titles, chapters, hadith, its english translation and the reference** and saves the content to structured JSON/CSV files locally.

---

## Features

- Scrapes book metadata, chapters, hadith, english translations, and reference
- Outputs clean, structured JSON/CSV files
- Super simple CLI interface (prompt-based)
- Designed to work smoothly on **Windows**

---

## How to Use (Windows-friendly steps)

1. Clone the repo or download the ZIP.
2. Make sure you have **Python 3.8+** installed.
3. Open a terminal or PowerShell in the project folder.
4. Install required packages:
    ```sh
    pip install -r requirements.txt
    ```
5. Run the scraper:
    ```sh
    python scraper.py
    ```
6. Follow the prompts.
7. The JSON/CSV files will be saved in the `scraped/` folder.

---

## Output

Each run will generate:
- `book_name.json`/ `book_name.csv` — list of books in the collection
- Individual JSON / CSV files for each book (e.g., `Book_1.json`, `Book_1.csv`, etc.)
- All files are saved under the `scraped/` directory

---

## Support

If you found this project helpful and want to support it, feel free to leave a tip:

**Bitcoin:**
```
bc1pd8kf8d7up4wkdq78mrjxt2vuzsu5ckg3lqrywe4vxc9pxfj2k9dqc6vuvt
```

**SOL:**
```
JF1u4jfEdfW2F9uQAZZg2ArbsbiErqkVmGeetzDHYGq
```

**EVM:**
```
0x0110D3c55DB3D6A8Daee8c0e98aC314657F6D943
```

**TRON:**
```
TQQfthgodRRmGzEeLzdwfNPqpn2i6AX8Ee
```

---

## Credits

Built with care by [Atif](https://github.com/meeAtif)  
Sourced from [sunnah.com](https://sunnah.com) (All rights belong to their respective owners)

---