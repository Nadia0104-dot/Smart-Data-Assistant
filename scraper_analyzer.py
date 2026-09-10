def clean_text(text):
    if not text:
        return ""
    return (
        text
        .replace("", "")
        .replace("", "")
        .strip()
    )

def analyze(data):
    formatted = []

    for d in data:
        formatted.append({
            "Name": clean_text(d.get("name")),
            "maps_url": d.get("maps_url") or d.get("url"),
            "Rating": d.get("rating"),
            "address": clean_text(d.get("address")),
            "phone": clean_text(d.get("phone")),
            "website_url": d.get("website"),
        })

    return formatted