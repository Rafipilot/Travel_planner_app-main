from serpapi import GoogleSearch

# Function to get hotels data from SerpAPI Google Hotels API
def get_hotels(city_name, check_in_date, check_out_date, google_api_key, min_price=None, max_price=None, currency='USD', rating=None):
    # Define parameters for the request
    params = {
        'engine': 'google_hotels',
        'q': f"Hotels in {city_name}",
        'check_in_date': check_in_date,
        'check_out_date': check_out_date,
        'api_key': google_api_key,
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
            hotel_data = {
                'name': property.get('name'),
                'price': property.get('rate_per_night', {}).get('lowest', 'Price not available'),
                'url': property.get('serpapi_property_details_link', 'No URL available')
            }
            hotels.append(hotel_data)
    
    return hotels

# Example usage
city_name = 'London'  
check_in_date = '2024-11-15'  
check_out_date = '2024-11-20'  

# Call the function to get hotels
hotels_info = get_hotels(city_name, check_in_date, check_out_date, ser_api_key)

# Print the extracted hotel data
print(hotels_info)
for hotel in hotels_info:
    print(hotel["name"])
    print(hotel["price"])

