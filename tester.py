import streamlit as st
from amadeus import Client, ResponseError
from datetime import datetime
am_auth = st.secrets["am_auth"]
am_key = st.secrets["am_key"]

amadeus = Client(
    client_id=am_key,
    client_secret=am_auth
)

def get_flight_price(departure, destination, depart_date, number_of_people=3, non_stop="true"):
    try:

        # Make the API call with the provided data
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=departure,
            destinationLocationCode=destination,
            departureDate=depart_date,
            adults=number_of_people,
            travelClass="ECONOMY",
            nonStop=non_stop  # Direct flights only if True
        )

        if response.status_code == 200:   
            # Check if we received any flight offers
            if len(response.data) == 0:
                print("No direct flights from the location selected!")
                return None, None
            
            # Loop through the flight offers and extract relevant details
            for offer in response.data:
                carrier_code = offer["itineraries"][0]["segments"][0]["carrierCode"]
                price = float(offer["price"]["total"])  # Convert price to float
                print(f"Carrier Code: {carrier_code}, Price: {price}")
                return carrier_code, price

        else:
            # If status code is not 200, print error and response details
            print("Error: Unable to retrieve flight data.")
            print("Response Data:", response.result)
            return None, None

    except ResponseError as error:
        # Catch and print any API errors
        print(f"API error in getting flight prices: {error}")
        print(f"Error Description: {error.description}")
        return None, None
    

depart_date = st.date_input("Departure Date:", min_value=datetime.today())
code, price = get_flight_price(departure="LHR", destination="FCO", depart_date=depart_date)
print(code, price)
return_date = st.date_input("Return Date:", min_value=depart_date)