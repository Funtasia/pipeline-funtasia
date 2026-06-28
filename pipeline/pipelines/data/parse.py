import json
import csv

from pprint import pprint 

with open("Booth Data - Booth Data.csv", "r",encoding="UTF-8") as file:
    data = list(csv.DictReader(file))
    pprint(data)

json_data = {}

for i in data:
    del i["sort_helper"]
    booth_id = i.pop("booth_id")
    level = i.pop("level").lower()

    # Empty list if empty string
    i["tags"]       = i["tags"]       and [tag.strip() for tag in i["tags"].split(",")      ] or []
    i["invis_tags"] = i["invis_tags"] and [tag.strip() for tag in i["invis_tags"].split(",")] or []

    if level not in json_data:
        json_data[level] = {}
    json_data[level][booth_id] = i

with open("funtasia_data.json", "w") as file:
    json.dump(json_data, file, indent=2)
