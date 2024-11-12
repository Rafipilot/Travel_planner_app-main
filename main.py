import streamlit as st
from datetime import datetime
from bs4 import BeautifulSoup
from amadeus import Client, ResponseError
from openai import OpenAI
import requests
import pandas as pd
import pdfplumber



# Importing secret keys
openai_key = st.secrets["openai_key"]
am_auth = st.secrets["am_auth"]
am_key = st.secrets["am_key"]
google_api_key = st.secrets["google_api_key"]
st.set_page_config(layout="wide")


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

# Display Title of the App
st.title("CityTravel.AI")


url_airports = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
df_airports = pd.read_csv(url_airports, header=None)
df_airports.columns = ["AirportID", "Name", "City", "Country", "IATA", "ICAO", "Latitude", "Longitude", "Altitude",
                       "Timezone", "DST", "TzDatabase", "Type", "Source"]

# Filter for major airports
major_airports = df_airports[df_airports['IATA'].notna()]
airport_options = {row["IATA"]: f"{row['Name']} ({row['IATA']}) - {row['City']}, {row['Country']}" for _, row in major_airports.iterrows()}

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
    depart_date = st.date_input("Departure Date:")
    return_date = st.date_input("Return Date:")
Cost = int(0)
non_stop = "true"# For call to amadeus
non_stop2 = "Yes"# For call to GPT
# Calculate duration and validate dates
d1 = datetime.strptime(str(depart_date), "%Y-%m-%d")
d2 = datetime.strptime(str(return_date), "%Y-%m-%d")
duration = (d2 - d1).days
weather_info = get_average_temp(city_destination, depart_date)
if duration <= 0:
    st.error("Return date must be after departure date.")

# Button to generate travel plan
if st.button("Generate"):

    lat, lng = get_coords(city_destination) # get coords of destination

    hotels = get_hotel_data(lat, lng, str(depart_date), str(return_date))#get hotels based on coords
    actvities = get_activities(city_destination, lat, lng)# get activities based on coords

    # Retrieve and display fight information
    flight, flight_price = get_flight_price(departure, destination, str(depart_date), int(number_of_people))
    return_flight, return_flight_price = get_flight_price(destination, departure, str(return_date), int(number_of_people))
    if flight is None or return_flight is None:
        non_stop2 = "No"
        flight, flight_price = get_flight_price(departure, destination, str(depart_date), int(number_of_people), non_stop="false")
        return_flight, return_flight_price = get_flight_price(destination, departure, str(return_date), int(number_of_people), non_stop="false")



    airline_name = get_airline_name(flight)
    # Calculate total flight price
    if flight_price is not None and return_flight_price is not None:
        total_price_flight = flight_price + return_flight_price
    else:
        st.error("Failed to retrieve complete flight information.")
    Cost = Cost+ total_price_flight
    # Retrieve and display hotel information




    

    if price_point and total_price_flight:
        hotel_info = ""
        per_night_budget = (int(price_point - total_price_flight)) - 100*duration 
        best_hotel = None
        min_price_diff = float('inf')
        for hotel in hotels:
            hotel_info += f"- **{hotel['name']}**\n"
            hotel_info += f"  - Price: {hotel['price']}\n"
            hotel_info += f"  - [Click here to book]({hotel['url']})\n"  
            print("URL: ", hotel['url'])
            

            
            # Extract price from the price string (removes non-numeric characters)
            price = int(float(hotel['price']))

            
            # Calculate the price difference from the per-night budget
            price_diff = abs(per_night_budget - price)
            
            # Select the hotel with the smallest difference to the per-night budget
            if price_diff < min_price_diff:
                min_price_diff = price_diff
                best_hotel = hotel

        # Return the best hotel found
        if best_hotel:
            print(f"Best Hotel: {best_hotel['name']}")
            print(f"Best Price: {best_hotel['price']}")
        else:
            print("No suitable hotel found.")
            
        # After the loop, best_hotel will be the best-matching hotel based on budget
        price = int(float(hotel['price']))
        Cost = Cost+  price  
        Cost = Cost + 20*int(duration)*2*int(number_of_people) #Adding estimate for meals
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

            f"**Hotel Recommendation**\n"
            f"{best_hotel}"
            f"- Price ({duration-1} nights): {best_hotel['price']}"
            f"- CLick here to book your stay at {best_hotel}"
 


            f"**Activities and Attractions:**\n"
            f"- Based on the duration of the trip, suggest activities that are relevant to the destination. Maybe like 1-2 activites per day "
            f"actvities list: {actvities}\n"
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

        # Make the OpenAI API call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=1200,
            temperature=0.7,
        )

        travel_plan = response.choices[0].message.content
        st.subheader("Your AI-Generated Travel Plan:")
        st.write(travel_plan)

    else:
        st.warning("Please fill in all fields to generate a travel plan.")
