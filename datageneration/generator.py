import os, random, json, csv
from datetime import datetime, timedelta
from fpdf import FPDF

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
def save_tender(t, fmt):
    # Templated description built from slots
    if t.get("language") == "FR":
        template = (
            f"Appel à propositions pour des solutions innovantes dans le secteur {t['sector']} en {t['region']}. "
            f"Budget disponible: {t['budget']}. Date limite: {t['deadline']}."
        )
    else:
        template = (
            f"Call for proposals seeking innovative solutions in the {t['sector']} sector in {t['region']}. "
            f"Available budget: {t['budget']}. Deadline: {t['deadline']}."
        )

    # Random bureaucratic boilerplate (EN/FR)
    en_boilerplates = [
        "Applicants are invited to submit comprehensive proposals that demonstrate technical excellence, sustainability, and capacity for scale.",
        "Proposals should align with national priorities and demonstrate measurable impact on target populations.",
        "All submissions will be evaluated according to predefined criteria and may be subject to additional due diligence."
    ]
    fr_boilerplates = [
        "Les candidats sont invités à soumettre des propositions complètes démontrant l'excellence technique, la durabilité et la capacité de montée en charge.",
        "Les propositions doivent s'aligner sur les priorités nationales et démontrer un impact mesurable sur les populations cibles.",
        "Toutes les soumissions seront évaluées selon des critères prédéfinis et pourront faire l'objet d'une diligence supplémentaire."
    ]

    boilerplate = random.choice(fr_boilerplates) if t.get("language") == "FR" else random.choice(en_boilerplates)

    content = (
        f"Title: {t['title']}\n"
        f"Sector: {t['sector']}\n"
        f"Budget: {t['budget']}\n"
        f"Deadline: {t['deadline']}\n"
        f"Region: {t['region']}\n"
        f"Language: {t['language']}\n\n"
        f"Description: {template} {boilerplate}\n\n"
        f"Eligibility: {t['eligibility']}\n"
    )

    if fmt == "txt":
        fname = f"datageneration/data/tenders/tender_{t['id']}.txt"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(content)

    elif fmt == "html":
        fname = f"datageneration/data/tenders/tender_{t['id']}.html"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(f"<html><body><pre>{content}</pre></body></html>")

    elif fmt == "pdf":
        fname = f"datageneration/data/tenders/tender_{t['id']}.pdf"
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for line in content.splitlines():
            pdf.cell(200, 10, txt=line, ln=True)
        pdf.output(fname)

# Generate tenders with random formats
tenders = [generate_tender(i) for i in range(1,41)]
formats = ["txt","html","pdf"]

# Ensure output directories exist before saving any files
os.makedirs("datageneration/data/tenders", exist_ok=True)

for t in tenders:
    fmt = random.choice(formats)
    save_tender(t, fmt)

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

# Generate profiles
profiles = [generate_profile(i) for i in range(1,11)]
with open("datageneration/data/profiles.json","w",encoding="utf-8") as f:
    json.dump(profiles,f,indent=2)

# Generate gold matches (simple heuristic)
with open("datageneration/data/gold_matches.csv","w",newline="",encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["profile_id","tender_id"])
    for p in profiles:
        matches = random.sample(tenders,3)
        for m in matches:
            writer.writerow([p["id"],m["id"]])
