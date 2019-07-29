from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from rasa_core.actions.action import Action
from rasa_core.events import SlotSet
import zomatopy
import json
import pandas as pd
from threading import Thread
from flask import Flask
from flask_mail import Mail, Message

global config
config={"user_key":"f4924dc9ad672ee8c4f8c84743301af5"}
zomato = zomatopy.initialize_app(config)


city_dict = ['Bangalore', 'Chennai', 'Delhi', 'Hyderabad', 'Kolkata', 'Mumbai', 'Lucknow', 'Agra', 'Ajmer', 'Aligarh', 'Amravati', 'Amritsar', 'Asansol', 'Aurangabad', 'Ahmedabad', 'Bareilly', 'Belgaum', 'Bhavnagar', 'Bhiwandi', 'Bhopal', 'Bhubaneswar', 'Bikaner', 'Bokaro Steel City', 'Chandigarh', 'Coimbatore', 'Nagpur', 'Cuttack', 'Dehradun', 'Dhanbad', 'Durg-Bhilai Nagar', 'Durgapur', 'Erode', 'Faridabad', 'Firozabad', 'Ghaziabad', 'Gorakhpur', 'Gulbarga', 'Guntur', 'Gwalior', 'Gurgaon', 'Guwahati', 'Hubli-Dharwad', 'Indore', 'Jabalpur', 'Jaipur', 'Jalandhar', 'Jammu', 'Jamnagar', 'Jamshedpur', 'Jhansi', 'Jodhpur', 'Kakinada', 'Kannur',' Kanpur','Kochi','Kottayam','Kolhapur','Kollam','Kota','Kozhikode','Kurnool', 'Ludhiana','Madurai','Malappuram','Mathura','Goa','Mangalore','Meerut','Moradabad','Mysore', 'Nanded', 'Nashik','Nellore','Noida','Palakkad','Patna','Pondicherry','Raipur','Rajkot','Rajahmundry','Ranchi','Rourkela','Salem','Sangli','Siliguri', 'Solapur','Srinagar','Sultanpur','Surat','Thiruvananthapuram', 'Thrissur', 'Tiruchirappalli', 'Tirunelveli', 'Tiruppur', 'Tiruvannamalai', 'Ujjain', 'Bijapur', 'Vadodara', 'Varanasi', 'Vasai-Virar City', 'Vijayawada', 'Visakhapatnam', 'Vellore', 'Warangal']

city_dict = [x.lower() for x in city_dict]
def check_location(loc,city_dict = city_dict):
	get_location_detail = zomato.get_location(loc, 1)
	location_detail_json = json.loads(get_location_detail)
	location_results = len(location_detail_json['location_suggestions'])
	if location_results == 0:
		return {'location_f' : 'notfound', 'location_new' : None}
	elif loc.lower() not in city_dict:
		return {'location_f' : 'tier3', 'location_new' : None}
	else:
		return {'location_f' : 'found', 'location_new' : loc}


def results(loc,cuisine,price):
	location_detail=zomato.get_location(loc, 1)
	location_json = json.loads(location_detail)
	location_results = len(location_json['location_suggestions'])
	lat=location_json["location_suggestions"][0]["latitude"]
	lon=location_json["location_suggestions"][0]["longitude"]
	city_id=location_json["location_suggestions"][0]["city_id"]
	cuisines_dict={'american': 1,'chinese': 25, 'north indian': 50, 'italian': 55, 'mexican': 73, 'south indian': 85}
			
	list1 = [0,20,40,60,80]
	d = []
	df = pd.DataFrame()
	for i in list1:
		results = zomato.restaurant_search("", lat, lon, str(cuisines_dict.get(cuisine)), limit=i)
		d1 = json.loads(results)
		d = d1['restaurants']
		df1 = pd.DataFrame([{'restaurant_name': x['restaurant']['name'], 'restaurant_rating': x['restaurant']['user_rating']['aggregate_rating'],
			'restaurant_address': x['restaurant']['location']['address'],'budget_for2people': x['restaurant']['average_cost_for_two'],
			'restaurant_photo': x['restaurant']['featured_image'], 'restaurant_url': x['restaurant']['url'] } for x in d])
		df = df.append(df1)

	def budget_group(row):
		if row['budget_for2people'] <300 :
			return 'lesser than 300'
		elif 300 <= row['budget_for2people'] <700 :
			return 'between 300 to 700'
		else:
			return 'more than 700'

	df['budget'] = df.apply(lambda row: budget_group(row),axis=1)
		#sorting by review & filter by budget
	restaurant_df = df[(df.budget == price)]
	restaurant_df = restaurant_df.sort_values(['restaurant_rating'], ascending=0)
	restaurant_df = restaurant_df.drop_duplicates()	
	return restaurant_df

def Config():
	gmail_user = 'botservice.iiitb2018dec@gmail.com'
	gmail_pwd = 'Qwerty123$' #Gmail Password
	gmail_config = (gmail_user, gmail_pwd)
	return gmail_config

gmail_credentials = Config()
app = Flask(__name__)


mail_settings = {
         "MAIL_SERVER": 'smtp.gmail.com',
         "MAIL_PORT": 465,
         "MAIL_USE_TLS": False,
         "MAIL_USE_SSL": True,
         "MAIL_USERNAME": gmail_credentials[0],
         "MAIL_PASSWORD": gmail_credentials[1]
     }

app.config.update(mail_settings)
mail = Mail(app)


def send_async_email(app, recipient, response):
     with app.app_context():
          if '<mailto' in recipient:
            recipient = recipient.split("|",1)[1]
            recipient = recipient.split(">",1)[0]
          print(recipient)
          msg = Message(subject="Restaurant Details", sender=gmail_credentials[0], recipients=[recipient])
          msg.html =u'<h2>Foodie has found few restaurants for you:</h2>'
          restaurant_names = response['restaurant_name'].values
          restaurant_photo = response['restaurant_photo'].values
          restaurant_location = response['restaurant_address'].values
          restaurant_url = response['restaurant_url'].values
          restaurant_budget = response['budget_for2people'].values
          restaurant_rating = response['restaurant_rating'].values
          for i in range(len(restaurant_names)):
               name = restaurant_names[i]
               location = restaurant_location[i]
               image = restaurant_photo[i]
               url = restaurant_url[i]
               budget = restaurant_budget[i]
               rating = restaurant_rating[i]
                    #msg.body +="This is final test"
               msg.html += u'<h3>{name} (Rating: {rating})</h3>'.format(name = name, rating = rating)
               msg.html += u'<h4>Address: {locality}</h4>'.format(locality = location)
               msg.html += u'<h4>Average Budget for 2 people: Rs{budget}</h4>'.format(budget = budget)
               msg.html += u'<div dir="ltr">''<a href={url}><img height = "325", width = "450", src={image}></a><br></div>'.format(url = url, image = image)

          mail.send(msg)

def send_email(recipient, response):
     thr = Thread(target=send_async_email, args=[app, recipient,response])
     thr.start()


class ActionSearchRestaurants(Action):
	def name(self):
		return 'action_restaurant'
		
	def run(self, dispatcher, tracker, domain):
		loc = tracker.get_slot('location')
		cuisine = tracker.get_slot('cuisine')
		price = tracker.get_slot('price')
		global restaurants
		restaurants = results(loc, cuisine, price)

		top5 = restaurants.head(5)
		#print(restaurants)
		# top 5 results to display
		if len(top5)>0:
			response = 'Showing you top results:' + "\n"
			for index, row in top5.iterrows():
				response = response + str(row['restaurant_name']) + ' in ' + row['restaurant_address'] + ' has been rated ' + row['restaurant_rating'] +"\n"
		else:
			response = 'No restaurants found' 

		dispatcher.utter_message(str(response))


class Check_location(Action):
	def name(self):
		return 'action_check_location'
		
	def run(self, dispatcher, tracker, domain):
		loc = tracker.get_slot('location')
		check = check_location(loc)
		
		return [SlotSet('location',check['location_new']), SlotSet('location_found',check['location_f'])]


class SendMail(Action):
	def name(self):
		return 'action_email_restaurant_details'
		
	def run(self, dispatcher, tracker, domain):
		recipient = tracker.get_slot('email')

		top10 = restaurants.head(10)
		send_email(recipient, top10)

		dispatcher.utter_message("Have a great day! Mail is sent")


