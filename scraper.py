import requests
from bs4 import BeautifulSoup
import json
import time
import re
import csv
import os
import argparse
import logging

BOOKS = {
    "1": ("Sahih al-Bukhari", "https://sunnah.com/bukhari/"),
    "2": ("Sahih Muslim", "https://sunnah.com/muslim/"),
    "3": ("Sunan an-Nasa'i", "https://sunnah.com/nasai/"),
    "4": ("Sunan Abi Dawud", "https://sunnah.com/abudawud/"),
    "5": ("Jami` at-Tirmidhi", "https://sunnah.com/tirmidhi/"),
    "6": ("Sunan Ibn Majah", "https://sunnah.com/ibnmajah/")
}

def select_books(cli_books=None):
    if cli_books:
        if cli_books == ['all']:
            return list(BOOKS.values())
        selected = []
        for num in cli_books:
            if num in BOOKS:
                selected.append(BOOKS[num])
            else:
                logging.warning(f"Book number {num} not found, skipping.")
        return selected
    print("     Available books to scrape:")
    for k, v in BOOKS.items():
        print(f"{k}. {v[0]}")
    print("A. All books")
    choice = input("Enter book numbers separated by comma (e.g., 1,3) or 'A' for all: ").strip().lower()
    if choice == "a":
        return list(BOOKS.values())
    else:
        selected = []
        for num in choice.split(","):
            num = num.strip()
            if num in BOOKS:
                selected.append(BOOKS[num])
        return selected

def select_output_format(cli_format=None):
    if cli_format:
        return cli_format
    print("\n       Choose output file format:")
    print("1. JSON")
    print("2. CSV")
    choice = input("Enter 1 for JSON or 2 for CSV: ").strip()
    if choice == "2":
        return "csv"
    return "json"

def save_data(data, filename, file_format, outdir):
    os.makedirs(outdir, exist_ok=True)
    filepath = os.path.join(outdir, filename)
    if file_format == "csv":
        if not data:
            logging.warning("No data to save.")
            return
        keys = data[0].keys()
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)
    else:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

def show_progress_bar(current, total, bar_length=30):
    percent = current / total
    filled = int(bar_length * percent)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"\r      Chapter {current}/{total} |{bar}| {percent*100:5.1f}% complete", end="", flush=True)

def extract_hadiths_from_chapter(soup, chapter, chapter_name_en, chapter_name_ar, book_name):
    output = []
    for hadith_div in soup.find_all("div", class_="actualHadithContainer"):
        arabic_text = ""
        english_text = ""
        arabic_div = hadith_div.find("div", class_="arabic_hadith_full")
        if arabic_div:
            arabic_text = arabic_div.get_text(separator=" ", strip=True)
        eng_div = hadith_div.find("div", class_="english_hadith_full")
        if eng_div:
            english_text = eng_div.get_text(separator=" ", strip=True)
        grade = ""
        grade_div = hadith_div.find("span", class_="hadith_grade") or hadith_div.find("div", class_="hadith_grade")
        if grade_div:
            grade = grade_div.get_text(separator=" ", strip=True)
        reference_url = ""
        in_book_ref = ""
        bottom = hadith_div.find("div", class_="bottomItems")
        if bottom:
            ref_table = bottom.find("table", class_="hadith_reference")
            if ref_table:
                for row in ref_table.find_all("tr"):
                    tds = row.find_all("td")
                    if len(tds) != 2:
                        continue
                    label = tds[0].get_text(separator=" ", strip=True).lower()
                    value = tds[1].get_text(separator=" ", strip=True)
                    if "reference" in label and not "in-book" in label:
                        a_tag = tds[1].find("a")
                        if a_tag and a_tag.has_attr("href"):
                            reference_url = "https://sunnah.com" + a_tag["href"]
                    elif "in-book reference" in label:
                        in_book_ref = re.sub(r"^[:\s]+", "", value)
        if not grade and bottom:
            annotation = bottom.find("div", class_="hadith_annotation")
            if annotation:
                gradetable = annotation.find("table", class_="gradetable")
                if gradetable:
                    rows = gradetable.find_all("tr")
                    for row in rows:
                        tds = row.find_all("td", class_="english_grade")
                        if len(tds) >= 2:
                            grade = tds[1].get_text(separator=" ", strip=True)
                            break
        if not reference_url:
            anchor = hadith_div.find_previous("a", attrs={"name": True})
            if anchor and anchor["name"].isdigit():
                hadith_number = anchor["name"]
                reference_url = f"https://sunnah.com/{book_name.lower()}:{hadith_number}"
        hadith_obj = {
            "Book": book_name,
            "Chapter_Number": chapter,
            "Chapter_Title_Arabic": chapter_name_ar,
            "Chapter_Title_English": chapter_name_en,
            "Arabic_Text": arabic_text,
            "English_Text": english_text,
            "Grade": grade,
            "Reference": reference_url,
            "In-book reference": in_book_ref,
        }
        output.append(hadith_obj)
    return output

def get_num_chapters(book_url):
    try:
        r = requests.get(book_url, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        chapter_links = soup.select('div.book_page a[href^="' + book_url.replace("https://sunnah.com/", "/") + '"]')
        if not chapter_links:
            book_slug = book_url.rstrip('/').split('/')[-1]
            chapter_links = soup.select(f'a[href^="/{book_slug}/"]')
        chapter_numbers = set()
        for a in chapter_links:
            href = a.get("href", "")
            match = re.search(r"/(\d+)$", href)
            if match:
                chapter_numbers.add(int(match.group(1)))
        if chapter_numbers:
            return max(chapter_numbers)
        else:
            logging.warning(f"Could not detect chapters for {book_url}, defaulting to 1.")
            return 1
    except Exception as e:
        logging.error(f"Error detecting chapters for {book_url}: {e}")
        return 1

def get_with_retry(url, max_retries=5, backoff_factor=2, timeout=15):
    delay = 1
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                return response
            else:
                logging.warning(f"Attempt {attempt}: Received status code {response.status_code} for {url}")
        except requests.exceptions.RequestException as e:
            logging.warning(f"Attempt {attempt}: Error fetching {url}: {e}")
        if attempt < max_retries:
            time.sleep(delay)
            delay *= backoff_factor
    logging.error(f"Failed to fetch {url} after {max_retries} attempts.")
    return None

def scrape_book(book_name, base_url, file_format, outdir):
    num_chapters = get_num_chapters(base_url)
    output = []
    logging.info(f"Starting to scrape {book_name} ({num_chapters} chapters detected)...")
    for idx, chapter in enumerate(range(1, num_chapters + 1), start=1):
        show_progress_bar(idx, num_chapters)
        url = f"{base_url}{chapter}"
        try:
            r = get_with_retry(url)
            if r is None or r.status_code != 200:
                logging.warning(f"Failed to fetch chapter {chapter}, skipping...")
                continue
        except requests.exceptions.RequestException as e:
            logging.warning(f"Network error for chapter {chapter}: {e}, skipping...")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        chapter_div = soup.find("div", class_="chapter")
        chapter_name_en = ""
        chapter_name_ar = ""
        if chapter_div:
            en = chapter_div.find("div", class_="englishchapter")
            ar = chapter_div.find("div", class_="arabicchapter")
            chapter_name_en = en.text.strip() if en else ""
            chapter_name_ar = ar.text.strip() if ar else ""
        if not chapter_name_en and not chapter_name_ar:
            chapter_heading = soup.find("div", class_="chapter_heading")
            if chapter_heading:
                en = chapter_heading.find("span", class_="en")
                ar = chapter_heading.find("span", class_="ar")
                chapter_name_en = en.text.strip() if en else ""
                chapter_name_ar = ar.text.strip() if ar else ""
        chapter_hadiths = extract_hadiths_from_chapter(soup, chapter, chapter_name_en, chapter_name_ar, book_name)
        output.extend(chapter_hadiths)
        save_data(output, f"{book_name}.{file_format}", file_format, outdir)
        time.sleep(1)
    print()
    logging.info(f"Done! Total hadith saved: {len(output)}")
    logging.info(f"Output saved to {os.path.join(outdir, f'{book_name}.{file_format}')}")

def main():
    parser = argparse.ArgumentParser(description="Scrape ahadees from sunnah.com")
    parser.add_argument('--format', choices=['json', 'csv'], help='Output file format')
    parser.add_argument('--books', nargs='+', help='Book numbers to scrape (e.g. 1 3 5) or "all"')
    parser.add_argument('--outdir', default='output_files', help='Output directory (default: output_files)')
    parser.add_argument('--log', default='INFO', help='Logging level (default: INFO)')
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log.upper(), logging.INFO),
        format='[%(levelname)s] %(message)s'
    )

    output_format = select_output_format(args.format)
    selected_books = select_books(args.books)
    for book_name, base_url in selected_books:
        scrape_book(book_name, base_url, output_format, args.outdir)

if __name__ == "__main__":
    main()