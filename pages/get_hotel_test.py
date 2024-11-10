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

def get_city_code(city_name):
    try:
        # Fetch city code dynamically using the correct method
        response = amadeus.reference_data.locations.get(keyword=city_name)
        
        if response.status_code == 200 and 'data' in response.result:
            if len(response.result['data']) > 0:
                # Get the first result (if there are multiple)
                city_code = response.result['data'][0]['cityCode']
                print(f"City code for {city_name}: {city_code}")
                return city_code
            else:
                print(f"No city found for {city_name}.")
                return None
        else:
            print(f"Error in response: {response.result}")
            return None
    
    except ResponseError as error:
        print(f"Error retrieving city code: {error}")
        return None

def get_hotel_offers(city_code, check_in_date, check_out_date, adults=1):
    hotel_offers = []
    
    # Convert dates to the correct format (YYYY-MM-DD)
    check_in_date_str = check_in_date.strftime('%Y-%m-%d')
    check_out_date_str = check_out_date.strftime('%Y-%m-%d')
    
    print(f"Requesting hotel offers for {city_code} from {check_in_date_str} to {check_out_date_str}")

    try:
        # Correct endpoint for getting hotel offers
        response = amadeus.shopping.hotel_offers_search.get(
            cityCode=city_code,
            checkInDate=check_in_date_str,
            checkOutDate=check_out_date_str,
            adults=adults
        )
        
        print(f"Response Status: {response.status_code}")
        
        # Check if the response is successful
        if response.status_code == 200 and 'data' in response.result:
            offers = response.result['data']
            for offer in offers:
                hotel_offer = {
                    'hotel_name': offer['hotel']['name'],
                    'address': offer['hotel']['address']['lines'],
                    'room_details': [
                        {
                            'room_type': room['room']['type'],
                            'price': room['offers'][0]['price']['total'],
                            'currency': room['offers'][0]['price']['currency'],
                            'cancellation_policy': room['offers'][0]['policies']['cancellation']['description']
                        }
                        for room in offer['rooms']
                    ]
                }
                hotel_offers.append(hotel_offer)

        else:
            print(f"Error in response: {response.result}")
    
    except ResponseError as error:
        print(f"API error: {error}")
    
    return hotel_offers

# Streamlit input fields
depart_date = st.date_input("Departure Date:")
return_date = st.date_input("Return Date:")

# Get the city code dynamically if needed
city_code = get_city_code("Paris")  # Replace with the desired city name

# Example of calling the function with city code 'PAR' (Paris)
if depart_date and return_date and city_code:
    hotel_offers = get_hotel_offers(city_code, depart_date, return_date)
    st.write(hotel_offers)

