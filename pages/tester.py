import streamlit as st
from datetime import datetime
from bs4 import BeautifulSoup
from amadeus import Client, ResponseError
from openai import OpenAI
import requests
import re
import pandas as pd

# Importing secret keys
openai_key = st.secrets["openai_key"]
am_auth = st.secrets["am_auth"]
am_key = st.secrets["am_key"]
st.set_page_config(layout="wide")



# Load the CSV file directly from the URL for getting airline name from code
url = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat"
df = pd.read_csv(url, header=None, names=["AirlineID", "Name", "Alias", "IATA", "ICAO", "Callsign", "Country", "Active"])

# Replace \N with NaN for missing values
df.replace(r'\\N', pd.NA, inplace=True, regex=True)

# Filter out rows without IATA codes
df = df[df['IATA'].notna()]

# Create a dictionary of IATA codes to airline names
airline_codes = dict(zip(df['IATA'], df['Name']))

# Initialize Amadeus client
amadeus = Client(
    client_id=am_key,
    client_secret=am_auth
)

def get_airline_name(code):
    return airline_codes.get(code.upper(), "Unknown Airline Code")

def get_average_temp(location, depart_date):
    location = location.lower()
    month = depart_date.strftime("%B").lower()
    url = f"https://www.holiday-weather.com/{location}/averages/{month}/"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching weather info: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    temp_div = soup.find("div", class_="p-2 pl-md-3 text fw-600")
    if temp_div:
        temp = temp_div.text.strip()
        return f"The average temperature in {location} during {month} is {temp}."
    else:
        return f"Could not find temperature information for {location} in {month}."

def get_flight_price(departure, destination, depart_date, number_of_people, non_stop="true"):
    try:
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=departure,
            destinationLocationCode=destination,
            departureDate=depart_date,
            adults=number_of_people,
            travelClass="ECONOMY",
            nonStop=non_stop
        )

        if response.status_code == 200:
            if len(response.data) == 0:
                st.error("No direct flights from the location selected!")
                return None, None

            for offer in response.data:
                carrier_code = offer["itineraries"][0]["segments"][0]["carrierCode"]
                price = float(offer["price"]["total"])  # Convert price to float
                return carrier_code, price
        else:
            st.error("Unable to retrieve flight data.")
            return None, None
    except ResponseError as error:
        st.error(f"API error: {error}")
        return None, None

def get_hotel_data(city, checkin, checkout):
    url = f"https://www.booking.com/searchresults.html?ss={city}&ssne={city}&checkin={checkin}&checkout={checkout}&group_adults=2&no_rooms=1&group_children=0&selected_currency=USD"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US, en;q=0.5'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        st.error(f"Request failed: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    hotels = soup.find_all('div', {'data-testid': 'property-card'})
    hotels_data = []

    for hotel in hotels:
        name = hotel.find('div', {'data-testid': 'title'}).text.strip() if hotel.find('div', {'data-testid': 'title'}) else "N/A"
        location = hotel.find('span', {'data-testid': 'address'}).text.strip() if hotel.find('span', {'data-testid': 'address'}) else "N/A"
        price = hotel.find('span', {'data-testid': 'price-and-discounted-price'}).text.strip() if hotel.find('span', {'data-testid': 'price-and-discounted-price'}) else "N/A"
        link = hotel.find('a', href=True)['href'] if hotel.find('a', href=True) else None

        if link and not link.startswith("http"):
            link = "https://www.booking.com" + link

        hotels_data.append({'name': name, 'location': location, 'price': price, 'url': link})

    return hotels_data

# OpenAI client initialization
client = OpenAI(api_key=openai_key)

# Display Title of the App
st.title("CityTravel.AI")

# Input fields
number_of_people = st.text_input("Number of people traveling:")
departure = st.text_input("Departure Airport Code (e.g., LHR for London Heathrow):")
destination = st.text_input("Destination Airport Code (e.g., JFK for New York JFK):")
price_point = st.slider("Budget", 1, 20000)
city_destination = st.text_input("Destination City: ")
depart_date = st.date_input("Departure Date:")
return_date = st.date_input("Return Date:")
Cost = int(0)
non_stop = "Yes"

# Validate dates
d1 = datetime.strptime(str(depart_date), "%Y-%m-%d")
d2 = datetime.strptime(str(return_date), "%Y-%m-%d")
duration = (d2 - d1).days
weather_info = get_average_temp(city_destination, depart_date)

if duration <= 0:
    st.error("Return date must be after departure date.")

# Button to generate travel plan
if st.button("Generate"):
    # Retrieve flight information
    flight, flight_price = get_flight_price(departure, destination, str(depart_date), int(number_of_people))
    return_flight, return_flight_price = get_flight_price(destination, departure, str(return_date), int(number_of_people))
    
    if flight is None or return_flight is None:
        non_stop = "No"
        flight, flight_price = get_flight_price(departure, destination, str(depart_date), int(number_of_people), non_stop="false")
        return_flight, return_flight_price = get_flight_price(destination, departure, str(return_date), int(number_of_people), non_stop="false")

    airline_name = get_airline_name(flight)
    
    # Calculate total flight price
    if flight_price is not None and return_flight_price is not None:
        total_price_flight = flight_price + return_flight_price
    else:
        st.error("Failed to retrieve complete flight information.")
    
    Cost = Cost + total_price_flight

    # Retrieve hotel information
    hotels = get_hotel_data(city_destination, str(depart_date), str(return_date))
    
    if not hotels:
        st.warning("No hotels found for the selected dates and location.")
        hotel_info = "No hotels available."
    else:
        hotel_info = "\n".join([f"{hotel['name']} - {hotel['price']} - {hotel['location']}" for hotel in hotels[:5]])

    # Calculate best hotel based on budget
    if price_point and duration and number_of_people and departure and destination:
        per_night_budget = (int(price_point - total_price_flight)) - 1000
        best_hotel = None
        min_price_diff = float('inf')

        for hotel in hotels[:20]:  # Loop through the top 20 hotels
            price_str = hotel['price']
            price_numeric = int(re.sub(r'[^\d]', '', price_str)) if price_str.isdigit() else 0
            price_diff = abs(per_night_budget - price_numeric)
            
            # Select the hotel with the smallest difference to the per-night budget
            if price_diff < min_price_diff:
                min_price_diff = price_diff
                best_hotel = hotel

        # After the loop, best_hotel will be the best-matching hotel based on budget
        if best_hotel is None:
            st.warning("No suitable hotels found within your budget.")
        else:
            price_str = best_hotel['price']
            price_numeric = int(re.sub(r'[^\d]', '', price_str))
            Cost = Cost + price_numeric
            Cost = Cost + 20 * int(duration) * 2

    st.write(f"**Total Travel Cost**: ${Cost}")
    st.write(weather_info)
    st.write(f"**Best Airline**: {airline_name} - Flight Price: ${flight_price}")
    st.write(f"**Best Hotel**: {best_hotel['name']} - Price per night: ${best_hotel['price']}")
