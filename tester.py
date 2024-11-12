import streamlit as st
from datetime import datetime
from bs4 import BeautifulSoup
from amadeus import Client, ResponseError
from openai import OpenAI
import requests
import pandas as pd
import pdfplumber

st.set_page_config(page_title="CityTravel.AI", layout="wide", initial_sidebar_state="expanded")

# Importing secret keys
openai_key = st.secrets["openai_key"]
am_auth = st.secrets["am_auth"]
am_key = st.secrets["am_key"]
google_api_key = st.secrets["google_api_key"]


print("PDF downloaded successfully!")

st.markdown("""
    <style>
        .main {
            background-color: #f7f7f7;
            font-family: 'Arial', sans-serif;
        }
        .stButton>button {
            background-color: #4CAF50;
            color: white;
            font-size: 18px;
            padding: 15px;
            border-radius: 8px;
            border: none;
        }
        .stButton>button:hover {
            background-color: #45a049;
            color: white;
        }
        .stSlider>div>label {
            font-size: 16px;
            color: #333;
        }
        .stTextInput>div>label {
            font-size: 16px;
            color: #333;
        }
        .stTitle {
            font-size: 32px;
            color: #1e2a47;
            font-weight: bold;
        }
        .stSubheader {
            font-size: 20px;
            font-weight: 500;
            color: #444;
        }
        .stWarning>div>label {
            color: #f8d7da;
            background-color: #f1b0b7;
        }
    </style>
""", unsafe_allow_html=True)



# Load the CSV file directly from the URL For getting airline name from code
url_airline_codes = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat" #Data set for code to name
df_ac = pd.read_csv(url_airline_codes, header=None, names=["AirlineID", "Name", "Alias", "IATA", "ICAO", "Callsign", "Country", "Active"])


# Replace \N with NaN for missing values
df_ac.replace(r'\\N', pd.NA, inplace=True, regex=True)

# Filter out rows without IATA codes
df = df_ac[df_ac['IATA'].notna()]

# Create a dictionary of IATA codes to airline names
airline_codes = dict(zip(df['IATA'], df['Name']))

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

def get_hotel_website(name):  
    url = 'https://www.google.com/search'
    headers = {
        'Accept' : '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82',
    }

    parameters = {'q': name}
    content = requests.get(url, headers = headers, params = parameters).text
    soup = BeautifulSoup(content, 'html.parser')
    search = soup.find(id = 'search')
    first_link = search.find('a')
    return first_link['href']


def get_airline_name(code):
    try:
        code = airline_codes.get(code.upper(), "Unknown Airline Code")
        print("airline code :", code)
    except Exception as e:
        print("Error in getting airline code : ", e)
    return 


def get_activities(city_name, lat ,lng):


    #Use the Places API to get nearby activities (tourist attractions)
    places_url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
    places_params = {
        'location': f'{lat},{lng}',  # Lat, Lng coordinates
        'radius': 5000,  # Search within a 5 km radius 
        'type': 'tourist_attraction',  # Type of places to search for
        'key': google_api_key  
    }

    # Make the request to the Places API
    places_response = requests.get(places_url, params=places_params)

    if places_response.status_code == 200:
        places_data = places_response.json()

        # Check if there are any results
        if places_data['results']:
            activities = []
            for place in places_data['results']:
                name = place.get('name')
                address = place.get('vicinity')
                place_id = place.get('place_id')


                details_url = 'https://maps.googleapis.com/maps/api/place/details/json'
                details_params = {
                    'place_id': place_id,
                    'key': google_api_key
                }

                # Make the request to the Place Details API
                details_response = requests.get(details_url, params=details_params)
                if details_response.status_code == 200:
                    details_data = details_response.json()
                    if details_data['status'] == 'OK':
                        # Get the description from the Place Details API response
                        description = details_data['result'].get('editorial_summary', {}).get('overview', 'No description available')
                    else:
                        description = 'No description available'
                else:
                    description = 'Error retrieving details'

                # Append the activity details to the list
                activities.append([name, address, description])

            return activities
        else:
            print("No activities found near the city.")
    else:
        print("Error retrieving places:", places_response.status_code, places_response.text)








def get_average_temp(location, depart_date):
    # Extract the month from the depart_date
    location = location.lower()
    month = depart_date.strftime("%B").lower()
    # Format the URL to match the location and month
    url = f"https://www.holiday-weather.com/{location}/averages/{month}/"
    
    # Send a request to the URL
    response = requests.get(url)
    if response.status_code != 200:
        print("error in weather")
        return f"Error: Unable to access page for {location} in {month}."

    # Parse the page content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the div containing the average temperature
    temp_div = soup.find("div", class_="p-2 pl-md-3 text fw-600")
    if temp_div:
        # Extract the temperature text
        temp = temp_div.text.strip()
        return f"The average temperature in {location} during {month} is {temp}."
    else:
        return f"Could not find temperature information for {location} in {month}."



def get_flight_price(departure, destination, depart_date, number_of_people, non_stop="true"):
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



def get_hotel_data(lat, lng, checkin, checkout):
    try:
        hotel_list = amadeus.reference_data.locations.hotels.by_geocode.get(latitude = lat, longitude=lng, radius = 200)
        if not hotel_list.data:
            st.write("No hotels found")
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
            url = get_hotel_website(hotel_name)
            hotel_offers.append({'name': hotel_name, 'price': price, "url": url})
        
        return hotel_offers
    
    except Exception as e:
        st.write("Error occurred in getting hotel data:", e)
        return []






# OpenAI client initialization
client = OpenAI(api_key=openai_key)






####frontend
# Set Streamlit page configuration


# Add custom CSS styling for enhanced UI/UX
st.markdown("""
    <style>
        .main { background-color: #f9f9f9; font-family: 'Arial', sans-serif; }
        .header-text { font-size: 40px; font-weight: bold; color: #1e2a47; }
        .sub-header { font-size: 18px; color: #333; }
        .stButton>button { background-color: #1e90ff; color: white; border-radius: 8px; }
        .stButton>button:hover { background-color: #1c86ee; }
        .info-card { padding: 10px; margin: 10px 0; background-color: #e6f2ff; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# Load the airport codes and names for dropdown selection
url_airports = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
df_airports = pd.read_csv(url_airports, header=None)
df_airports.columns = ["AirportID", "Name", "City", "Country", "IATA", "ICAO", "Latitude", "Longitude", "Altitude",
                       "Timezone", "DST", "TzDatabase", "Type", "Source"]

# Filter for major airports and prepare options for dropdowns
major_airports = df_airports[df_airports['IATA'].notna()]
airport_options = {row["IATA"]: f"{row['Name']} ({row['IATA']}) - {row['City']}, {row['Country']}" for _, row in major_airports.iterrows()}

# Sidebar input fields for trip details
with st.sidebar:
    st.markdown("<h2 class='header-text'>CityTravel.AI</h2>", unsafe_allow_html=True)
    st.write("Your personalized travel assistant")

    st.subheader("Travel Details")
    number_of_people = st.number_input("Number of people traveling:", min_value=1, max_value=10, value=1)
    departure_airport = st.selectbox("Departure Airport", options=airport_options.keys(),
                                     format_func=lambda x: airport_options[x])
    destination_airport = st.selectbox("Destination Airport", options=airport_options.keys(),
                                       format_func=lambda x: airport_options[x])

    destination_city = st.text_input("Destination City:").capitalize()
    budget = st.slider("Total Budget ($)", 100, 10000, 1500)

    # Date selection with date validation
    depart_date = st.date_input("Departure Date", min_value=datetime.today())
    return_date = st.date_input("Return Date", min_value=depart_date)
    if return_date <= depart_date:
        st.error("Return date must be after departure date.")

# Layout for main sections
st.header("Plan Your Perfect Trip!")
st.markdown("Enter your travel details in the sidebar, and we’ll help you find flights, hotels, activities, and more within your budget.")

# Tabbed layout for each step of the travel plan
tabs = st.tabs(["Flights", "Hotels", "Activities", "Itinerary"])

# Flights tab with spinner and placeholder for results
with tabs[0]:  # Flights tab
    st.subheader("Flight Options")
    if st.button("Search Flights"):
        with st.spinner("Searching for flights..."):
                flight, flight_price = get_flight_price(departure_airport, destination_airport, str(depart_date), int(number_of_people))
                return_flight, return_flight_price = get_flight_price(destination_airport, departure_airport, str(return_date), int(number_of_people))
                if flight is None or return_flight is None:
                    non_stop2 = "No"
                    flight, flight_price = get_flight_price(departure_airport, destination_airport, str(depart_date), int(number_of_people), non_stop="false")
                    return_flight, return_flight_price = get_flight_price(destination_airport, departure_airport, str(return_date), int(number_of_people), non_stop="false")
        
        airline_name = get_airline_name(flight)
        st.success("Flights found!")
        st.write("Flight details:")
        st.write("Airline name: ", str(airline_name))
        st.write("Price(return tickets): ", str(round(flight_price+return_flight_price, 2)))

# Hotels tab with spinner and placeholder for results
with tabs[1]:  # Hotels tab
    st.subheader("Hotel Options")
    if st.button("Search Hotels"):
        with st.spinner("Searching for hotels..."):
            # Placeholder for backend integration
            lat, lng = get_coords(destination_city) # get coords of destination

            hotels = get_hotel_data(lat, lng, str(depart_date), str(return_date))#get hotels based on coords
            st.success("Hotels found!")
            for hotel in hotels:
                st.write(hotel["name"])
                st.write("Price: ", hotel["price"])
                st.write("Link to book: ", hotel["url"])

# Activities tab with spinner and placeholder for results
with tabs[2]:  # Activities tab
    st.subheader("Activities & Attractions")
    if st.button("Find Activities"):
        with st.spinner("Finding activities..."):
            # Placeholder for backend integration
            # activities = get_activity_data(...)
            st.success("Activities found!")
            st.write("Activities details would appear here.")

# Itinerary tab for displaying sample itinerary
with tabs[3]:  # Itinerary tab
    st.subheader("Your Itinerary")
    # Example itinerary layout (replace with dynamic content if needed)
    itinerary = """
    **Day 1: Arrival**
    - Check into hotel
    - Explore local neighborhood
    - Dinner at recommended restaurant
    
    **Day 2: Main Attractions**
    - Visit major sights and landmarks
    - Suggested lunch spot nearby
    """
    st.write(itinerary)

# Additional section to summarize the travel plan
st.markdown("<h3 class='sub-header'>Travel Summary</h3>", unsafe_allow_html=True)
st.write("Once you've reviewed the options in each tab, a summary will appear here.")
st.write("Summary details would show the selected flights, hotels, and activities.")
