import logging
import os
import pathlib
import socket
import sys
import time
import traceback
import typing
import urllib.request

from datetime import datetime
from urllib.error import HTTPError

logger = logging.getLogger(__name__)

WORD_LIST_URL = "https://raw.githubusercontent.com/dwyl/english-words/refs/heads/master/words.txt"
WORD_LIST_FILE = "words.txt"
ETAG_FILE = "etag.txt"
ENGLISH_CHARACTERS = "abcdefghijklmnopqrstuvwxyz"


def download_if_updated():
    logger.debug("Checking for updates to words list...")
    req = urllib.request.Request(WORD_LIST_URL, method="GET")

    if os.path.exists(ETAG_FILE):
        with open(ETAG_FILE, "r") as f:
            etag = f.read().strip()
            if etag:
                req.add_header("If-None-Match", etag)

    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                logger.debug('Updating words list...')
                new_etag = response.getheader("ETag", "")
                content = response.read()
                with open(WORD_LIST_FILE, "wb") as f:
                    f.write(content)
                if new_etag:
                    with open(ETAG_FILE, "w") as f:
                        f.write(new_etag)
                logger.debug("Words list updated.")
    except HTTPError as e:
        if e.code == 304:
            logger.debug("Word list has not modified. Using cached version.")
        else:
            logger.debug(f"Error downloading word list: {e}")
    except Exception as e:
        logger.debug(f"Unknown error occurred: {e}")


def load_words(file_path):
    logger.debug(f"Loading words list...")
    words = []
    with open(file_path, "r") as f:
        for word in f:
            word = word.strip().lower()
            if len(word) == 5 and word.isalpha():
                words.append(word)
    logger.debug(f"{len(words)} 5-letter words loaded.")
    return words


def generate_words(greens, yellows, grays, english_words):
    green_chars = list(greens.values())
    yellow_chars = list(set(char for chars in yellows.values() for char in chars))
    gray_chars = grays
    available_chars = green_chars + yellow_chars + gray_chars

    chars_by_index = {
        "1": available_chars[:],
        "2": available_chars[:],
        "3": available_chars[:],
        "4": available_chars[:],
        "5": available_chars[:],
    }
    if len(greens) > 0:
        for index, char in greens.items():
            chars_by_index[str(index)] = [char]
    if len(yellows) > 0:
        for index, chars in yellows.items():
            for char in chars:
                if char in chars_by_index[str(index)]:
                    chars_by_index[str(index)].remove(char)

    n_letter_combinations = len(chars_by_index["1"]) * len(chars_by_index["2"]) * len(chars_by_index["3"]) * len(chars_by_index["4"]) * len(chars_by_index["5"])
    logger.debug(f"Generating {n_letter_combinations} possible letter combinations...")
    generated_words = []
    for i in chars_by_index["1"]:
        for j in chars_by_index["2"]:
            for k in chars_by_index["3"]:
                for l in chars_by_index["4"]:
                    for m in chars_by_index["5"]:
                        generated_word = f"{i}{j}{k}{l}{m}"
                        if not all(char in generated_word for char in yellow_chars):
                            continue
                        if generated_word not in english_words:
                            continue
                        if generated_word not in generated_words:
                            generated_words.append(generated_word)
    logger.debug(f"Generated {len(generated_words)} possible words.")
    return generated_words


def main() -> None:
    green = input("\n🟩 Which letters are correct? Use '_' for unknowns. E.g. '__a__'\n>>> ").strip().lower()
    yellow = input("\n🟨 Which letters are used but in the wrong positions? Format being 'a1 b3' meaning 'a not in pos 1, b not in pos 3'\n>>> ").strip().lower()
    gray = input("⬜ Which letters are still availble? Just list them. E.g. 'xqz'\n>>> ").strip().lower()

    start_time = time.perf_counter()
    logger.info("Starting operation...")

    download_if_updated()
    if not os.path.exists(WORD_LIST_FILE):
        logger.debug("❌ 'words.txt' not found. Aborting.")
        return

    english_words = load_words(WORD_LIST_FILE)

    # Process greens
    greens = {}
    for i, char in enumerate(green, start=1):
        if char != '_':
            greens[str(i)] = char
    logger.debug(f'Green: {green}')
    logger.debug(f"Greens: {greens}")

    # Process yellows
    yellows = {}
    for part in yellow.split():
        letter = part[0]
        number = part[1:]
        yellows.setdefault(number, []).append(letter)
    logger.debug(f'Yellow: {yellow}')
    logger.debug(f"Yellows: {yellows}")

    # Process grays
    grays = list(gray)
    logger.debug(f'Gray: {gray}')
    logger.debug(f"Grays: {grays}")

    generated_words = generate_words(greens, yellows, grays, english_words)

    if len(generated_words) > 0:
        logger.info(f"Generated the following possible words:")
        for word in generated_words:
            logger.info(f"- {word}")
    else:
        logger.info("No possible words found with the given constraints.")

    end_time = time.perf_counter()
    duration = end_time - start_time
    logger.info(f"Completed operation in {duration:.4f}s.")


def setup_logging(
        logger: logging.Logger,
        log_file_path: typing.Union[str, pathlib.Path],
        number_of_logs_to_keep: typing.Union[int, None] = None,
        console_logging_level: int = logging.DEBUG,
        file_logging_level: int = logging.DEBUG,
        log_message_format: str = "%(asctime)s.%(msecs)03d %(levelname)s [%(funcName)s] [%(name)s]: %(message)s",
        date_format: str = "%Y-%m-%d %H:%M:%S") -> None:
    # Ensure log_dir is a Path object
    log_file_path = pathlib.Path(log_file_path)
    log_dir = log_file_path.parent
    log_dir.mkdir(parents=True, exist_ok=True)  # Create logs dir if it does not exist

    # Limit # of logs in logs folder
    if number_of_logs_to_keep is not None:
        log_files = sorted([f for f in log_dir.glob("*.log")], key=lambda f: f.stat().st_mtime)
        if len(log_files) >= number_of_logs_to_keep:
            for file in log_files[:len(log_files) - number_of_logs_to_keep + 1]:
                file.unlink()

    logger.setLevel(file_logging_level)  # Set the overall logging level

    # File Handler for date-based log file
    file_handler_date = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler_date.setLevel(file_logging_level)
    file_handler_date.setFormatter(logging.Formatter(log_message_format, datefmt=date_format))
    logger.addHandler(file_handler_date)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_logging_level)
    console_handler.setFormatter(logging.Formatter(log_message_format, datefmt=date_format))
    logger.addHandler(console_handler)

    # Set specific logging levels if needed
    # logging.getLogger("requests").setLevel(logging.INFO)


if __name__ == "__main__":
    pc_name = socket.gethostname()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    script_name = pathlib.Path(__file__).stem
    log_dir = pathlib.Path(f"{script_name} Logs")
    log_file_name = f"{timestamp}_{pc_name}.log"
    log_file_path = log_dir / log_file_name
    setup_logging(logger, log_file_path, number_of_logs_to_keep=100, log_message_format="%(asctime)s.%(msecs)03d %(levelname)s [%(funcName)s]: %(message)s")

    error = 0
    try:
        main()
    except Exception as e:
        logger.warning(f"A fatal error has occurred: {repr(e)}\n{traceback.format_exc()}")
        error = 1
    finally:
        sys.exit(error)
