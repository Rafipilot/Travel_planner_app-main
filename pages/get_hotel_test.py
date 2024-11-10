from amadeus import Client, ResponseError
import streamlit as st
from datetime import datetime

am_auth = st.secrets["am_auth"]
am_key = st.secrets["am_key"]

# Initialize Amadeus client
amadeus = Client(
    client_id=am_key,
    client_secret=am_auth
)




def hotel_search(origin, checkin_date, checkout_date):
    try:
        # Step 1: Get list of hotels in the specified city
        hotel_list = amadeus.reference_data.locations.hotels.by_city.get(cityCode=origin)
        
        hotel_offers = []
        hotel_ids = []
        
        # Collect hotel IDs (Limit to 40 for simplicity)
        for i in hotel_list.data[:40]:  # Adjust the number as needed
            hotel_ids.append(i['hotelId'])
        
        # Step 2: Search for hotel offers based on the city and dates
        search_hotels = amadeus.shopping.hotel_offers_search.get(
            hotelIds=hotel_ids,
            checkInDate=checkin_date,
            checkOutDate=checkout_date
        )
        
        # Prepare hotel offers to print the result
        for hotel in search_hotels.data:
            hotel_offers.append({
                'name': hotel['hotel']['name'],
                'price': hotel['offers'][0]['price']['total']  # First offer's price
            })
        
        # Print the hotel names and prices
        if hotel_offers:
            for offer in hotel_offers:
                print(f"Hotel: {offer['name']}, Price: {offer['price']}")
        else:
            print("No hotels found for your search criteria.")

    except ResponseError as error:
        print(f"Error: {error.response.body}")

# Example usage
origin = "LON"  # City code for London
checkin_date = "2024-12-01"
checkout_date = "2024-12-10"

hotel_search(origin, checkin_date, checkout_date)


