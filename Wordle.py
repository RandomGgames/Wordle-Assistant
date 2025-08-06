import itertools
import logging
import os
import pathlib
import sys
import time
import traceback
import typing
import urllib.request

from urllib.error import HTTPError

logger = logging.getLogger(__name__)

WORD_LIST_URL = "https://raw.githubusercontent.com/dwyl/english-words/refs/heads/master/words.txt"
WORD_LIST_FILE = "words.txt"
ETAG_FILE = "etag.txt"
ENGLISH_CHARACTERS = "abcdefghijklmnopqrstuvwxyz"


def download_if_updated():
    req = urllib.request.Request(WORD_LIST_URL, method="GET")

    if os.path.exists(ETAG_FILE):
        with open(ETAG_FILE, "r") as f:
            etag = f.read().strip()
            if etag:
                req.add_header("If-None-Match", etag)

    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                new_etag = response.getheader("ETag", "")
                content = response.read()
                with open(WORD_LIST_FILE, "wb") as f:
                    f.write(content)
                if new_etag:
                    with open(ETAG_FILE, "w") as f:
                        f.write(new_etag)
                logger.debug("✅ Word list updated.")
    except HTTPError as e:
        if e.code == 304:
            logger.debug("Word list not modified. Using cached version.")
        else:
            logger.debug(f"Error downloading word list: {e}")
    except Exception as e:
        logger.debug(f"Unknown error occurred: {e}")


def load_words(file_path):
    with open(file_path, "r") as f:
        return [word.strip().lower() for word in f if len(word.strip()) == 5 and word.strip().isalpha()]


def generate_words(greens, yellows, grays, english_words):
    green_chars = list(greens.values())
    yellow_chars = list(yellows.values())
    gray_chars = grays
    available_chars = green_chars + yellow_chars + gray_chars
    logger.debug(f"{available_chars=}")

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
        for index, char in yellows.items():
            chars_by_index[str(index)].remove(char)
    logger.debug(f"{chars_by_index=}")

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
                        logger.debug(f"{generated_word=}")
                        generated_words.append(generated_word)
    return generated_words


def main() -> None:

    download_if_updated()
    if not os.path.exists(WORD_LIST_FILE):
        logger.debug("❌ 'words.txt' not found. Aborting.")
        return

    english_words = load_words(WORD_LIST_FILE)

    green = input("\n🟩 Which letters are correct? Use '_' for unknowns. E.g. '__a__'\n>>> ").strip().lower()
    yellow = input("\n🟨 Which letters are used but in the wrong positions? Format being 'a1 b3' meaning 'a not in pos 1, b not in pos 3'\n>>> ").strip().lower()
    gray = input("⬜ Which letters are still availble? Just list them. E.g. 'xqz'\n>>> ").strip().lower()

    logger.debug(f"Green: {green}")
    logger.debug(f"Yellow: {yellow}")
    logger.debug(f"Gray: {gray}")

    # Process grays
    greens = {}
    for i, char in enumerate(green, start=1):
        if char != '_':
            greens[str(i)] = char
    logger.debug(f"Greens: {greens}")

    # Process yellows
    yellows = {}
    for part in yellow.split():
        letter = part[0]
        number = part[1:]
        yellows[number] = letter
    logger.debug(f"Yellows: {yellows}")

    # Process grays
    grays = list(gray)
    logger.debug(f"Grays: {grays}")

    generated_words = generate_words(greens, yellows, grays, english_words)


def setup_logging(
        logger: logging.Logger,
        log_file_path: typing.Union[str, pathlib.Path],
        console_logging_level: int = logging.DEBUG,
        file_logging_level: int = logging.DEBUG,
        log_message_format: str = "%(asctime)s.%(msecs)03d %(levelname)s [%(funcName)s] [%(name)s]: %(message)s",
        date_format: str = "%Y-%m-%d %H:%M:%S") -> None:
    logger.setLevel(file_logging_level)  # Set the overall logging level

    # File Handler for script-named log file (overwrite each run)
    file_handler = logging.FileHandler(log_file_path, encoding="utf-8", mode="w")
    file_handler.setLevel(file_logging_level)
    file_handler.setFormatter(logging.Formatter(log_message_format, datefmt=date_format))
    logger.addHandler(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_logging_level)
    console_handler.setFormatter(logging.Formatter(log_message_format, datefmt=date_format))
    logger.addHandler(console_handler)


if __name__ == "__main__":
    script_name = pathlib.Path(__file__).stem
    log_file_name = f"{script_name}.log"
    log_file_path = pathlib.Path(log_file_name)
    setup_logging(logger, log_file_path, log_message_format="%(asctime)s.%(msecs)03d %(levelname)s [%(funcName)s]: %(message)s")

    error = 0
    try:
        start_time = time.perf_counter()
        logger.info("Starting operation...")
        main()
        end_time = time.perf_counter()
        duration = end_time - start_time
        logger.info(f"Completed operation in {duration:.4f}s.")
    except Exception as e:
        logger.warning(f"A fatal error has occurred: {repr(e)}\n{traceback.format_exc()}")
        error = 1
    finally:
        sys.exit(error)
