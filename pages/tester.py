import streamlit as st
from datetime import datetime
from bs4 import BeautifulSoup
from amadeus import Client, ResponseError
import requests

am_auth = st.secrets["am_auth"]
am_key = st.secrets["am_key"]
google_api_key = st.secrets["google_api_key"]
amadeus = Client(
    client_id=am_key,
    client_secret=am_auth
)


def get_hotel_data(city, checkin, checkout):
    url = f"https://www.booking.com/searchresults.html?ss={city}&ssne={city}&ssne_untouched={city}&checkin={checkin}&checkout={checkout}&group_adults=2&no_rooms=1&group_children=0&sb_travel_purpose=leisure&selected_currency=USD"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US, en;q=0.5'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Check if request was successful
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return []
    soup = BeautifulSoup(response.text, 'html.parser')
    hotels = soup.find_all('div', {'data-testid': 'property-card'})
    hotels_data = []
    for hotel in hotels:
        name = hotel.find('div', {'data-testid': 'title'}).text.strip() if hotel.find('div', {'data-testid': 'title'}) else "N/A"
        location = hotel.find('span', {'data-testid': 'address'}).text.strip() if hotel.find('span', {'data-testid': 'address'}) else "N/A"
        price = hotel.find('span', {'data-testid': 'price-and-discounted-price'}).text.strip() if hotel.find('span', {'data-testid': 'price-and-discounted-price'}) else "N/A"
        hotels_data.append({'name': name, 'location': location, 'price': price})
    return hotels_data

def get_coords(city_name):
    geocode_url = f'https://maps.googleapis.com/maps/api/geocode/json?address={city_name}&key={google_api_key}'
    geocode_response = requests.get(geocode_url)


    if geocode_response.status_code == 200:
        geocode_data = geocode_response.json()
        if geocode_data['status'] == 'OK' and geocode_data['results']:
            # Get latitude and longitude
            lat = geocode_data['results'][0]['geometry']['location']['lat']
            lng = geocode_data['results'][0]['geometry']['location']['lng']

    return lat, lng



depart_date = st.date_input("Departure Date:")
return_date = st.date_input("Return Date:")

# Calculate duration and validate dates
d1 = datetime.strptime(str(depart_date), "%Y-%m-%d")
d2 = datetime.strptime(str(return_date), "%Y-%m-%d")
#lat, lng = get_coords("athens")
hotels = get_hotel_data("athens", str(depart_date), str(return_date))
st.write("Hotels: ", hotels)
st.write("numnber: ", len(hotels))
for hotel in hotels:
    st.write(hotel)