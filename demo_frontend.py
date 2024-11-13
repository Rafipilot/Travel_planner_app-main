import streamlit as st
from datetime import datetime
import pandas as pd

# Set up Streamlit page configuration
st.set_page_config(page_title="CityTravel.AI", layout="wide")

# Define custom CSS for styling
st.markdown("""
    <style>
        .main { background-color: #f8f9fa; font-family: Arial, sans-serif; }
        .stButton>button { background-color: #4CAF50; color: white; font-size: 18px; padding: 10px 20px; border-radius: 6px; }
        .stButton>button:hover { background-color: #45a049; }
        .title { font-size: 42px; font-weight: bold; color: #333; text-align: center; margin-top: 40px; }
        .subheader { font-size: 20px; font-weight: 500; color: #444; }
        .center-text { text-align: center; }
    </style>
""", unsafe_allow_html=True)

# Initialize session state to manage the landing screen
if 'form_started' not in st.session_state:
    st.session_state['form_started'] = False

# Landing screen
if not st.session_state['form_started']:
    st.markdown("<div class='title'>Welcome to CityTravel.AI</div>", unsafe_allow_html=True)
    st.markdown("""
        <div class="center-text" style="font-size: 20px; color: #555; margin-top: 20px;">
            Plan your next adventure with ease. Get personalized flight options, hotel recommendations, and activities in one place.
        </div>
    """, unsafe_allow_html=True)
    if st.button("Start Planning"):
        st.session_state['form_started'] = True
        st.rerun()
else:
    # Display the app title and travel details form
    st.markdown("<div class='title'>CityTravel.AI</div>", unsafe_allow_html=True)

    # Sidebar input fields for travel details
    with st.sidebar:
        st.markdown("<div class='subheader'>Travel Details</div>", unsafe_allow_html=True)
        st.text_input("Number of people:", key="number_of_people", placeholder="Enter number of travelers")
        departure_airport = st.selectbox("Departure Airport", options=["JFK", "LAX", "ORD"])  # Example airports
        destination_airport = st.selectbox("Destination Airport", options=["CDG", "FCO", "LHR"])
        budget = st.slider("Total Budget", min_value=500, max_value=20000, step=500)
        destination_city = st.text_input("Destination City").lower()
        depart_date = st.date_input("Departure Date:")
        return_date = st.date_input("Return Date:")

    # Travel plan generation button
    if st.sidebar.button("Generate Travel Plan"):
        # Check if return date is after departure date
        if return_date <= depart_date:
            st.sidebar.error("Return date must be after departure date.")
        else:
            # Fetch and display results in tabs
            st.markdown("<div class='subheader'>Your Personalized Travel Plan</div>", unsafe_allow_html=True)
            tabs = st.tabs(["Flights", "Hotels", "Activities", "Itinerary"])

            # Flight details
            with tabs[0]:
                st.subheader("Flight Options")
                # Sample flight data (replace with actual function calls)
                st.write("Airline: Example Airline")
                st.write("Price: $500 (Round-trip)")
                st.write("Non-stop: Yes")

            # Hotel recommendations
            with tabs[1]:
                st.subheader("Recommended Hotels")
                # Sample hotel data (replace with actual function calls)
                hotel_list = [
                    {"name": "Hotel Sunshine", "price": 1200, "url": "https://example.com/book-hotel1"},
                    {"name": "Hotel Relax", "price": 1100, "url": "https://example.com/book-hotel2"}
                ]
                for hotel in hotel_list:
                    st.write(f"**{hotel['name']}** - Price: ${hotel['price']} for 5 nights")
                    st.write(f"[Book Now]({hotel['url']})")

            # Activity suggestions
            with tabs[2]:
                st.subheader("Activities")
                # Sample activity data (replace with actual function calls)
                activities = [
                    {"name": "Museum Visit", "description": "Explore art and history.", "location": "City Museum"},
                    {"name": "City Park", "description": "Relax in the green heart of the city.", "location": "Central Park"}
                ]
                for activity in activities:
                    st.write(f"- **{activity['name']}**")
                    st.write(f"  - Location: {activity['location']}")
                    st.write(f"  - Description: {activity['description']}")

            # Full itinerary
            with tabs[3]:
                st.subheader("Your Day-by-Day Itinerary")
                # Sample itinerary details
                st.write("**Day 1**: Arrival, City Tour")
                st.write("**Day 2**: Museum Visit and Dinner at a local restaurant")
                st.write("**Day 3**: Shopping and Cultural Show")
                st.write("**Day 4**: Relaxing Day at the Beach")
                st.write("**Day 5**: Departure")

    else:
        st.warning("Fill in all fields in the sidebar to generate a travel plan.")
