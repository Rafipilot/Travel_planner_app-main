import requests
import pdfplumber

def get_city_code(city_name, url="https://www.serveto.com/img/bloques/1432804003.pdf"):
    # Step 1: Download the PDF
    pdf_path = "city_codes.pdf"
    response = requests.get(url)
    with open(pdf_path, "wb") as file:
        file.write(response.content)
    print("PDF downloaded successfully!")

    # Step 2 & 3: Extract city codes and look up the given city
    city_data = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split('\n')
            for line in lines:
                parts = line.split()
                if len(parts) >= 3 and all(len(part) <= 3 for part in parts[-2:]):
                    city = " ".join(parts[:-2]).strip()
                    city_code = parts[-2].strip()
                    if any(keyword in city for keyword in ["Código", "Location", "Aeropuerto", "Airport"]):
                        continue
                    if city.lower() not in city_data:
                        city_data[city.lower()] = []
                    city_data[city.lower()].append(city_code)

    # Normalize input and fetch city code
    city_name = city_name.lower().strip()
    codes = city_data.get(city_name)
    if codes:
        return codes[0] if len(codes) == 1 else f"Multiple codes found for {city_name.capitalize()}: {', '.join(codes)}"
    else:
        return f"No code found for {city_name}"

# Usage
city_name = input("Enter a city name: ")
city_code = get_city_code(city_name)
print(f"The city code for {city_name} is: {city_code}")
