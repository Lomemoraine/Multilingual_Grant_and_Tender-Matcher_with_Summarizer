import os, random, json, csv
from datetime import datetime, timedelta

sectors = ["agritech","healthtech","cleantech","edtech","fintech","wastetech"]
budgets = ["5000 USD","50000 USD","200000 USD","1000000 USD"]
countries = ["Rwanda","Kenya","Senegal","DRC","Ethiopia"]

def random_deadline():
    return (datetime.now() + timedelta(days=random.randint(30,365))).strftime("%Y-%m-%d")

def generate_tender(i):
    sector = random.choice(sectors)
    budget = random.choice(budgets)
    deadline = random_deadline()
    region = random.choice(countries)
    lang = "EN" if random.random() < 0.6 else "FR"
    title = f"{sector.capitalize()} Innovation Grant {i}"
    eligibility = "SMEs and startups in Africa"
    return {
        "id": i,
        "title": title,
        "sector": sector,
        "budget": budget,
        "deadline": deadline,
        "eligibility": eligibility,
        "region": region,
        "language": lang
    }

def generate_profile(i):
    sector = random.choice(sectors)
    country = random.choice(countries)
    employees = random.randint(5,200)
    languages = ["EN"] if random.random()<0.5 else ["FR"]
    needs_text = f"Looking for funding in {sector} sector"
    past_funding = "None"
    return {
        "id": i,
        "sector": sector,
        "country": country,
        "employees": employees,
        "languages": languages,
        "needs_text": needs_text,
        "past_funding": past_funding
    }

# Generate tenders
tenders = [generate_tender(i) for i in range(1,41)]
os.makedirs("data/tenders", exist_ok=True)
for t in tenders:
    fname = f"data/tenders/tender_{t['id']}.txt"
    with open(fname,"w",encoding="utf-8") as f:
        f.write(f"Title: {t['title']}\nSector: {t['sector']}\nBudget: {t['budget']}\nDeadline: {t['deadline']}\nEligibility: {t['eligibility']}\nRegion: {t['region']}\n")

# Generate profiles
profiles = [generate_profile(i) for i in range(1,11)]
with open("data/profiles.json","w",encoding="utf-8") as f:
    json.dump(profiles,f,indent=2)

# Generate gold matches (simple heuristic)
with open("data/gold_matches.csv","w",newline="",encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["profile_id","tender_id"])
    for p in profiles:
        matches = random.sample(tenders,3)
        for m in matches:
            writer.writerow([p["id"],m["id"]])
