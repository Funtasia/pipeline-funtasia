import csv
import json

FILENAME = "Booth Data - Booth Data.csv"

def funtasia_csv_to_json(filename_in, filename_out="funtasia_data.json"):

    json_data = {}

    with open(filename_in, "r",encoding="UTF-8") as file:

        for row in csv.DictReader(file):
            del row["sort_helper"]
            booth_id = row.pop("booth_id")
            level = row.pop("level").lower()

            # Empty list if empty string
            row["tags"]       = row["tags"]       and [tag.strip() for tag in row["tags"].split(",")      ] or []
            row["invis_tags"] = row["invis_tags"] and [tag.strip() for tag in row["invis_tags"].split(",")] or []

            if level not in json_data:
                json_data[level] = {}

            json_data[level][booth_id] = row

    with open(filename_out, "w") as file:
        json.dump(json_data, file, indent=2)

if __name__ == "__main__":
    funtasia_csv_to_json(FILENAME)
