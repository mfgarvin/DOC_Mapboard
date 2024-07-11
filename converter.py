import json

#First, make a backup of whatever we have
with open('parish_data.json', 'r') as file:
    with open('parish_data.json.bkp', 'w') as backup:
        backup.write(file.read())
        backup.close()
    file.close()

#Now, prep files for an update
new_data_in = open('export.json', 'r')
original_data_in = open('live.json', 'r')
new_data_out = open('parish_data.json', 'w', encoding='utf-8')

#Start the conversion process
from_json = json.load(new_data_in)
old_data = json.load(original_data_in)
new_data_staged = {}


days = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

for parishName in from_json:
    parish_data_staged = {}
    parish = old_data.get(parishName)
    if parish is not None:
        parish_data_staged["ID"] = parish.get("ID")
        parish_data_staged["Last Updated"] = from_json[parishName][3]["last_run_timestamp"]
        massDB = from_json[parishName][4]["mass_times"]
        massList = {}
        for day in days:
            timeList = []
            for liturgy in massDB:
                if liturgy["day"] == day:
                    timeList.append(liturgy["time"])
                    massList[liturgy["day"]] = timeList
        parish_data_staged["Mass Times"] = massList
        confDB = from_json[parishName][5]["conf_times"]
        confList = {}
        for day in days:
            timeList = []
            for liturgy in confDB:
                if liturgy["day"] == day:
                    timeList.append({liturgy["time"]: liturgy["duration"]})
                    confList[liturgy["day"]] = timeList
        parish_data_staged["Confessions"] = confList
        adoreDB = from_json[parishName][6]["adore_times"]
        adoreList = {}
        if adoreDB != "":
            adoreList["is24hour"] = adoreDB[0]["is24hour"]
        for day in days:
            timeList = []
            for liturgy in adoreDB:
                if liturgy["day"] == day:
                    timeList.append({liturgy["time"]: liturgy["duration"]})
                    adoreList[liturgy["day"]] = timeList
        parish_data_staged["Adoration"] = adoreList
    new_data_staged[parishName] = parish_data_staged

#And, write it.
json.dump(new_data_staged, new_data_out, ensure_ascii=False, indent=2)
new_data_in.close(), original_data_in.close(), new_data_out.close()
print("Conversion complete! Find it in parish_data.json")


