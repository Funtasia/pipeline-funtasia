from pathlib import Path
import csv
import json
import re

__all__ = ["csv_data_to_json"]

def convert_ascii(s: str):
    if s.isascii():
        return s

    def replace(m: re.Match):
        m = ord(m.group(0))

        # em-dash and the like, U+2013-2015
        if m in (0x2013, 0x2014, 0x2015):
            return '-'

        # single quotation mark
        elif m in (0x2018, 0x2019):
            return "'"

        # double quotation mark
        elif m in (0x201C, 0x201D):
            return '"'

    res = re.sub(r"[\u2013\u2014\u2015\u2018\u2019\u201C\u201D]", replace, s)

def csv_data_to_json(
    filename_in: Path,
    filename_out: Path = Path("funtasia_data.json"),
    prefer_ascii: bool = True
):

    json_data = {}

    with open(filename_in, "r", encoding="UTF-8") as file:

        for entry in csv.DictReader(file):
            del entry["sort_helper"]
            booth_id = entry.pop("booth_id")
            level = entry.pop("level").lower()

            if prefer_ascii:
                entry = dict((k, convert_ascii(v)) for k, v in entry.items())

            # Empty list if empty string
            entry["tags"]       = entry["tags"]       and [tag.strip() for tag in entry["tags"].split(",")      ] or []
            entry["invis_tags"] = entry["invis_tags"] and [tag.strip() for tag in entry["invis_tags"].split(",")] or []

            if level not in json_data:
                json_data[level] = {}

            json_data[level][booth_id] = entry

    with open(filename_out, "w") as file:
        json.dump(json_data, file, indent=2)

if __name__ == "__main__":
    csv_data_to_json(Path("Booth Data - Booth Data.csv"))
