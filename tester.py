import streamlit as st
from amadeus import Client, ResponseError
import requests
# Retrieve secrets from Streamlit configuration
am_auth = st.secrets["am_auth"]
am_key = st.secrets["am_key"]
google_api_key = st.secrets["google_api_key"]
# Initialize Amadeus client
amadeus = Client(
    client_id=am_key,
    client_secret=am_auth
)

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
# Define the function to get hotel data
def get_hotel_data(city_name, checkin, checkout):
    try:
        # Retrieve hotels by city
        lat, lng = get_coords(city_name)
        hotel_list = amadeus.reference_data.locations.hotels.by_geocode.get(latitude = lat, longitude=lng, radius = 200)
        if not hotel_list.data:
            st.write("No hotels found for city code:", city_code)
            return []
        
        hotel_offers = []
        hotel_ids = [hotel['hotelId'] for hotel in hotel_list.data[:40]]  # Retrieve more hotel IDs if needed

        # Fetch hotel offers based on IDs and dates
        search_hotels = amadeus.shopping.hotel_offers_search.get(
            hotelIds=hotel_ids,
            checkInDate=checkin,
            checkOutDate=checkout
        )
        
        if not search_hotels.data:
            st.write("No hotel offers available for the given dates.")
            return []

        # Process hotel offers and retrieve booking information
        for hotel in search_hotels.data:
            hotel_name = hotel['hotel']['name']
            price = hotel['offers'][0]['price']['total']
            hotel_offers.append({'name': hotel_name, 'price': price})
        
        return hotel_offers
    
    except Exception as e:
        st.write("Error occurred in getting hotel data:", e)
        return []

# Streamlit interface
st.title("Hotel Finder")

# Input fields for city code and dates
city_code = st.text_input("Enter City Code", "ATH")
checkin = st.date_input("Check-in Date")
checkout = st.date_input("Check-out Date")

# Search button
if st.button("Search Hotels"):
    if city_code and checkin and checkout:
        # Get hotel data
        hotels = get_hotel_data(city_code, str(checkin), str(checkout))
        
        if hotels:
            st.write("Available Hotels:")
            for hotel in hotels:
                st.write(f"Hotel Name: {hotel['name']}, Price: ${hotel['price']}")
        else:
            st.write("No hotels found for the selected dates and city code.")
    else:
        st.write("Please enter all required fields.")
