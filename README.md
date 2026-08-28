# NLP


Flight Booking Chatbot – System Overview
Introduction
The aim of this project was to develop an interactive Natural Language Processing (NLP) chatbot capable of assisting users with booking flights through natural language conversations. Rather than relying on large language models or external APIs, the chatbot was designed using classical NLP techniques including TF-IDF vectorisation, cosine similarity, regular expressions, and a rule-based dialogue management system.
The chatbot allows users to search for flights, book one-way and return journeys, modify or cancel bookings, and engage in simple conversational interactions such as greetings and small talk. The system follows a modular architecture to ensure each component has a clearly defined responsibility, making the chatbot transparent, explainable, and easy to maintain.
 
Overall System Architecture
The chatbot follows a sequential processing pipeline consisting of seven main components:
1.	User Input
2.	Text Preprocessing
3.	Intent Recognition
4.	Slot Filling
5.	Dialogue Manager
6.	Flight Search Engine
7.	Natural Language Generation
Each component performs one specific task before passing information to the next module.
 
1. Text Preprocessing Module
The preprocessing module is responsible for cleaning and normalising every user message before any further processing occurs.
Functions implemented
•	Convert text to lowercase
•	Remove punctuation
•	Remove unnecessary whitespace
•	Standardise contractions
•	Normalise dates
•	Produce consistent text for classification
Why this was implemented
Without preprocessing, the classifier would treat:
Book Flight
book flight
BOOK FLIGHT
as different inputs.
Normalisation significantly improves classification accuracy by ensuring similar sentences produce similar TF-IDF vectors.
 
2. Intent Recognition Module
Intent recognition determines what the user wants to achieve.
Examples include:
•	greeting
•	goodbye
•	book flight
•	modify booking
•	cancel booking
•	help
•	small talk
•	unknown
Instead of using deep learning, the chatbot uses:
•	TF-IDF Vectoriser
•	Cosine Similarity
The classifier is trained using the intents.json dataset.
How it works
1.	Training utterances are loaded.
2.	Every sentence is converted into a TF-IDF vector.
3.	A centroid vector is created for every intent.
4.	New user input is vectorised.
5.	Cosine similarity compares the input against every centroid.
6.	The intent with the highest similarity score is returned.
7.	If confidence is below a threshold, the chatbot predicts the “unknown” intent.
Why this method was chosen
•	Fast
•	Explainable
•	Lightweight
•	No internet required
•	Easy to debug
 
3. Slot Filling Module
Intent classification only determines what the user wants.
Slot filling determines the details.
The chatbot extracts information including:
•	Origin city
•	Destination city
•	Departure date
•	Return date
•	Number of passengers
•	Cabin class
•	Trip type
Techniques used
Regular expressions
Keyword matching
Context-aware updating
For example:
Book me a flight from London to Rome tomorrow
extracts
Origin = London
Destination = Rome
Date = tomorrow
The extracted information is stored inside the DialogueState object.
 
4. Dialogue State
The chatbot maintains a conversation state throughout the interaction.
The DialogueState stores:
•	user name
•	booking status
•	origin
•	destination
•	leave date
•	return date
•	passengers
•	cabin
•	trip type
•	confirmation state
•	selected flight
This enables multi-turn conversations without asking the user to repeat information.
Example
User:
Change my cabin to Business.
The chatbot already remembers
•	London
•	Rome
•	departure date
•	passengers
Only the cabin changes.
 
5. Dialogue Manager
The DialogueManager is the central controller of the chatbot.
It coordinates every module.
Its responsibilities include:
Intent routing
Depending on the predicted intent, it decides which action to perform.
Examples
Greeting
Booking
Modification
Cancellation
Help
Small talk
 
Slot prompting
If important booking information is missing, the chatbot asks targeted follow-up questions.
For example
Would that be a return trip or a single flight?
instead of restarting the booking.
 
Conversation flow
The DialogueManager ensures conversations follow a logical order.
Example
Greeting

↓

Booking

↓

Collect details

↓

Search flights

↓

Show results

↓

Confirmation

↓

Booking complete
 
Booking confirmation
Before saving a booking the chatbot produces a summary including
Origin
Destination
Dates
Passengers
Cabin
Price
The user must explicitly confirm.
 
Modify booking
The chatbot supports changing:
departure date
return date
cabin
passengers
trip type
without restarting the booking.
 
Cancel booking
Users can cancel bookings.
The chatbot first asks for confirmation before deleting the stored booking.
 
Unknown intent handling
If the classifier confidence is too low
the chatbot responds with
I'm sorry, I didn't quite understand that.
rather than guessing.
 
6. Flight Search Engine
Flight data is stored inside
flights.csv
Every row becomes a FlightOption object.
Each flight stores
origin
destination
date
carrier
cabin
price
departure time
 
Exact Search
The chatbot first searches for
same origin
same destination
same date
same cabin
Results are sorted by price.
 
Similar Search
If no exact match exists
the chatbot performs a relaxed search.
It keeps
origin
destination
fixed
while relaxing
date
cabin
The best three alternatives are returned.
This prevents dead ends.
 
Return Trip Search
Return journeys search for
Outbound
Origin → Destination
AND
Inbound
Destination → Origin
The cheapest valid combinations are returned.
 
7. Natural Language Generation
Instead of printing raw database values
the chatbot generates conversational responses.
Example
Here is your itinerary:

From London to Rome

Leaving on 12 December

Economy Class

2 passengers

Price £200
Template-based NLG ensures
consistent wording
easy maintenance
predictable responses
 
Additional Features
Greeting system
Recognises greetings
Introduces itself
Asks for the user’s name
 
Memory
Remembers the user’s name
Uses it later
Example
Nice to see you again Chidi.
 
Help intent
Explains supported functionality.
 
Small talk
Answers conversational questions such as
How are you?
 
Booking summary
Generates readable itineraries before confirmation.
 
Performance Evaluation
The chatbot was evaluated using three approaches.
Intent classification accuracy using a labelled test set.
Scenario-based dialogue testing covering one-way bookings, return bookings, modification, cancellation, and error handling.
Response-time measurements using Python’s time.perf_counter(), which showed an average response time of approximately 0.6 ms per interaction.
 
User Evaluation
Usability was assessed using the Chatbot Usability Questionnaire (CUQ).
Participants evaluated aspects including:
•	Ease of use
•	Personality
•	Navigation
•	Error handling
•	Response quality
•	Overall usability
The results were analysed to produce an overall CUQ score, providing quantitative evidence of the chatbot’s usability.
 
Conversational Design Principles Implemented
Your chatbot incorporates several key conversational design principles:
•	Turn-taking: The bot asks one focused question at a time, creating a natural conversation flow.
•	Slot-filling: Required booking information is collected progressively rather than all at once.
•	Grounding: The chatbot confirms important details through itinerary summaries before booking.
•	Repair strategies: Unknown or incomplete inputs trigger clarification rather than incorrect assumptions.
•	User agency: Users remain in control by explicitly confirming bookings and cancellations.
•	Context retention: Previously supplied information is remembered, enabling booking modification without restarting.
•	Consistency: Responses follow predictable templates, making interactions easy to understand.
•	Restricted domain: The chatbot politely declines requests outside the flight-booking domain instead of attempting unsupported tasks.
 
Overall Summary
The completed chatbot is a modular, rule-based conversational agent that combines classical NLP techniques with structured dialogue management to provide an efficient flight-booking experience. It supports one-way and return flight searches, booking modification, cancellation, conversational memory, small talk, fallback handling, and template-based response generation. The use of TF-IDF intent recognition, regex-based slot extraction, a dialogue state manager, and a flight search engine demonstrates how traditional NLP methods can be integrated into a robust conversational system without relying on large language models. The system is transparent, explainable, computationally efficient, and well suited to a restricted-domain application, making it an effective solution for the objectives of the COMP3074 coursework.

