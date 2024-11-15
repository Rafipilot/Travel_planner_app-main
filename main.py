import streamlit as st
from datetime import datetime
from bs4 import BeautifulSoup
from amadeus import Client, ResponseError
from openai import OpenAI
import requests
import pandas as pd
from serpapi import GoogleSearch
import re 

# Importing secret keys
openai_key = st.secrets["openai_key"]
am_auth = st.secrets["am_auth"]
am_key = st.secrets["am_key"]
google_api_key = st.secrets["google_api_key"]
ser_api_key = st.secrets["ser_api_key"]

st.set_page_config(layout="wide", page_title="CityTravel.AI", page_icon=":airplane:")

if 'form_started' not in st.session_state:
    st.session_state['form_started'] = False

print("PDF downloaded successfully!")

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
    except Exception as e:
        print("Error in getting airline code : ", e)
    return code


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



def get_hotel_data(city_name, lat, lng, checkin, checkout, min_price=None, max_price=None, currency='USD', rating=None):
    try:
        # Define parameters for the request
        params = {
            'engine': 'google_hotels',
            'q': f"Hotels in {city_name}",
            'check_in_date': checkin,
            'check_out_date': checkout,
            'api_key': ser_api_key,
            'currency': currency,
            'min_price': min_price,
            'max_price': max_price,
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Check if there are results in the response
        hotels = []
        if 'properties' in results:
            for property in results['properties']:
                price_string = property.get('rate_per_night', {}).get('lowest', 'Price not available')
                # Remove non-numeric characters (like '$', commas, etc.)
                price_clean = re.sub(r'[^\d.]', '', price_string)
                
                # Convert to float, if it's valid
                try:
                    price = float(price_clean)
                except ValueError:
                    price = None  # In case conversion fails
                
                hotel_data = {
                    'name': property.get('name'),
                    'price': price if price is not None else 'Price not available',
                    'url': property.get('link', 'No URL available')
                }
                hotels.append(hotel_data)
            
            if len(hotels) != 0:
                return hotels
            else:
                print(hotels)
                print("No hotels found with serapi")
    except Exception as e:
        print("Error with serapi", e)

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

url_airports = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
df_airports = pd.read_csv(url_airports, header=None)
df_airports.columns = ["AirportID", "Name", "City", "Country", "IATA", "ICAO", "Latitude", "Longitude", "Altitude",
                       "Timezone", "DST", "TzDatabase", "Type", "Source"]

# Filter for major airports
major_airports = df_airports[df_airports['IATA'].notna()]
airport_options = {row["IATA"]: f"{row['Name']} ({row['IATA']}) - {row['City']}, {row['Country']}" for _, row in major_airports.iterrows()}


st.markdown("""
    <style>
        .main {
            background: linear-gradient(135deg, #6e8efb, #a777e3);
            color: #f9f9f9;
            font-family: 'Arial', sans-serif;
        }
        .title {
            font-size: 3.5rem;
            color: #ffffff;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }
        .subtitle {
            font-size: 1.7rem;
            color: #e0e0e0;
            margin-bottom: 20px;
        }
        .start-button {
            font-size: 1.5rem;
            padding: 10px 20px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }
        .start-button:hover {
            background-color: #45a049;
        }
    </style>
    

""", unsafe_allow_html=True)


if not st.session_state["form_started"]:
    # Define the landing page content
    st.markdown("<div class='landing-container'>", unsafe_allow_html=True)
    st.markdown("<div class='title animate'>🌍 CityTravel.AI</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle animate'>Plan your next adventure with ease!</div>", unsafe_allow_html=True)
    st.markdown("""
        <div class='info-text animate'>
            Discover amazing destinations, find the best flights and hotels, and explore personalized activity recommendations.
            CityTravel.AI is your all-in-one travel planner, designed to make your trip planning seamless and enjoyable.
        </div>
    """, unsafe_allow_html=True)

    st.write("")
    # Add the start button
    if st.button("Start Planning", key="start", help="Click here to begin your travel planning journey!", args=('form_started', True)):
        st.session_state['form_started'] = True
        st.rerun()




if st.session_state["form_started"]:
    # Input fields
    with st.sidebar:
        st.subheader("Travel Details")
        number_of_people = st.text_input("Number of people traveling:")
        departure = st.selectbox("Departure Airport", options=airport_options.keys(),
                                        format_func=lambda x: airport_options[x])
        destination = st.selectbox("Destination Airport", options=airport_options.keys(),
                                        format_func=lambda x: airport_options[x])
        price_point = st.slider("Budget", 1, 20000)
        city_destination = st.text_input("Destination City: ").lower()
        depart_date = st.date_input("Departure Date:", min_value=datetime.today())
        return_date = st.date_input("Return Date:", min_value=depart_date)
    Cost = int(0)
    non_stop = "true"# For call to amadeus
    non_stop2 = "Yes"# For call to GPT
    # Calculate duration and validate dates
    d1 = datetime.strptime(str(depart_date), "%Y-%m-%d")
    d2 = datetime.strptime(str(return_date), "%Y-%m-%d")
    duration = (d2 - d1).days
    weather_info = get_average_temp(city_destination, depart_date)
    if duration <= 0:
        st.warning("Return date must be after departure date.")

    # Button to generate travel plan
    if st.button("Generate"):

        tabs = st.tabs(["Flights", "Hotels", "Activities", "Full Plan"])

        lat, lng = get_coords(city_destination)
        hotels = get_hotel_data(city_destination, lat, lng, str(depart_date), str(return_date))

        activities = get_activities(city_destination, lat, lng)
        print(departure, destination, depart_date, number_of_people)
        flight, flight_price = get_flight_price(departure, destination, str(depart_date), int(number_of_people))
        return_flight, return_flight_price = get_flight_price(destination, departure, str(return_date), int(number_of_people))
        if flight is None or return_flight is None:
            non_stop2 = "No"
            flight, flight_price = get_flight_price(departure, destination, str(depart_date), int(number_of_people), non_stop="false")
            return_flight, return_flight_price = get_flight_price(destination, departure, str(return_date), int(number_of_people), non_stop="false")

        airline_name = get_airline_name(flight)
        if flight_price is not None and return_flight_price is not None:
            total_price_flight = flight_price + return_flight_price
        else:
            st.error("Failed to retrieve complete flight information.")
        Cost = Cost + total_price_flight

        with tabs[0]:
            st.subheader("Flight Options")
            st.write("Airline name: ", airline_name)
            st.write("Price: ", total_price_flight)

        if price_point and total_price_flight:
            hotel_info = ""
            per_night_budget = (int(price_point - total_price_flight)) - 100 * duration
            # Initialize variables
        best_hotels = []
        min_price_diffs = []

        # Find the four hotels with prices closest to the budget
        for hotel in hotels:
            hotel_info += f"- **{hotel['name']}**\n"
            hotel_info += f"  - Price: {hotel['price'] * (duration - 1)}\n"
            hotel_info += f"  - [Click here to book]({hotel['url']})\n"

            price = int(float(hotel['price']))
            price_diff = abs(per_night_budget - price)
            
            # Add each hotel to the list with its price difference
            min_price_diffs.append((hotel, price_diff))

            # Sort by price difference and select the top 4
            min_price_diffs = sorted(min_price_diffs, key=lambda x: x[1])[:4]
            best_hotels = [[hotel['name'], hotel['price'], hotel['url']] for hotel, diff in min_price_diffs]

        # Display the recommended hotels
        with tabs[1]:
            st.subheader("Recommended Hotels")
            for i, hotel in enumerate(best_hotels, start=1):
                st.write(f"**Hotel {i}:** {hotel[0]}")
                st.write(f"Price for {duration - 1} nights: {hotel[1]}")
                st.write(f"[Click here to book]({hotel[2]})\n")


            with tabs[2]:
                st.subheader("Activities")
                for activity in activities[:duration]:
                    st.write(f"- **{activity[0]}**")
                    st.write(f"  - Location: {activity[1]}")
                    st.write(f"  - Description: {activity[2]}")
                    website = get_hotel_website(activity[0])
                    st.write(f"Website: {website}")

            Cost = Cost + price + 20 * int(duration) * 2 * int(number_of_people)
            # Constructing the GPT prompt 
            prompt = (
                f"You are an expert travel planner. Based on the details provided below, create a structured, "
                f"personalized, and informative travel plan. The plan should be balanced, staying within the given "
                f"budget and trip duration. Please follow the guidelines for each section:\n\n"

                f"**Trip Overview:**\n"
                f"- Budget: {price_point}$\n"
                f"- Trip Duration: {duration} days\n"
                f"- Number of Travelers: {number_of_people}\n"
                f"- Departure Location: {departure}\n"
                f"- Destination Location: {destination}\n\n"

                f"**Flight Information:**\n"
                f"- Airline: {airline_name}\n"
                f"- Price: ${total_price_flight} (Return tickets)\n"
                f"- Non-stop: {non_stop2}"
                f"- Flight Details: Departure from {departure} and return from {destination}. Include flight duration and any relevant details.\n\n"
                f"- URL to bookling page of airline, try to find it if possible, if not then just leave it out"

                f"**Weather info**"
                f"{weather_info}"
                f"Based on weather info give some tips to the traveller(s)"
    
                f"**Hotel Recommendation**\n"
                f"{best_hotels}"
                f"- Price ({duration-1} nights):"
                f"- CLick here to book your stay at"

                f"**Activities and Attractions:**\n"
                f"- Based on the duration of the trip, suggest activities that are relevant to the destination. Maybe like 1-2 activites per day "
                f"actvities list: {activities}\n"
                f"- Include brief descriptions of each activity and links to booking or more details if available.\n\n"

                f"**Day-by-Day Itinerary:**\n"
                f"- Create a detailed day-by-day itinerary based on the trip duration. Include suggested times for activities, "
                f"transportation tips, and meal recommendations.\n"
                f"Include the days that the Traveller(s) arrive"
                f"- Balance the itinerary to avoid overwhelming the traveler, but also ensure that the trip is fulfilling and diverse.\n\n"

                f"**Budget Breakdown:**\n"
                f"- Cost: {Cost} This is including Hotel, Flights and estimate for meals\n\n"

                f"**Additional Tips:**\n"
                f"- Provide useful travel tips, such as advice on local customs, transportation options (e.g., metro, taxis), and "
                f"any cultural insights specific to {city_destination}.\n\n"

                f"Ensure that the plan is practical, engaging, and inspiring. The tone should be exciting and easy to follow, "
                f"with clear steps for the traveler to enjoy their journey."
            )

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": prompt}],
                max_tokens=1200,
                temperature=0.7,
            )
            travel_plan = response.choices[0].message.content

            with tabs[3]:
                st.subheader("Your AI-Generated Travel Plan:")
                st.write(travel_plan)
