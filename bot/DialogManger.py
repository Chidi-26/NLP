"""Rule based dialog manager that coordinates intent handling and flight search."""

import re
from bot.mem import set_username, get_username
from bot.small_talk import small_talk
from bot.ir import FlightIndex
from bot.state import DialogueState
from bot.nlg import realise_itinerary, confirm_prompt

# Regular expressions for extracting structured info from user input. Used light-weight pattern matching instead of a full parser so we keep coverage broad and easy to tweak without retraining models.

# User name: captures "call me Chidi" / "my name is Chidi" variations.
NAME_REGEX = re.compile(
    r"(?:call\s+me|my\s+name\s+is)\s+(?P<name>[A-Za-z\-']{2,})",
    re.IGNORECASE,
)

# City patterns: supports "from X to Y", "from X", "to Y" with lookahead so we
# stop before other slot values (dates, verbs, punctuation).
CITY_REGEX = re.compile(
    r"""
    # from X to Y 
    (?:
        from\s+(?P<o>[A-Za-z ]+?)\s+to\s+(?P<d>[A-Za-z ]+?)
        (?=\s+(?:on|leaving|leave|departing|for|in)\b|[,.!?]|$)
    )
    |
    # only origin: from X 
    (?:
        from\s+(?P<o2>[A-Za-z ]+?)
        (?=\s+(?:to|on|leaving|leave|departing|for|in)\b|[,.!?]|$)
    )
    |
    # only destination: to Y 
    (?:
        to\s+(?P<d2>[A-Za-z ]+?)
        (?=\s+(?:from|on|leaving|leave|departing|for|in)\b|[,.!?]|$)
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Dates: covers basic natural language keywords and numeric forms that
# DialogueState.parseDate can interpret.
DATE_REGEX = re.compile(
    r"(?P<date>\b(?:today|tomorrow|the day after tomorrow|next week|next month|"
    r"\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?[A-Za-z]+|"
    r"\d{4}-\d{2}-\d{2}|"
    r"\d{1,2}/\d{1,2}/\d{2,4})\b)",
    re.IGNORECASE,
)

# Passengers: looks for a cardinal number followed by a pax token.
PASSENGER_REGEX = re.compile(
    r"(?P<pax>\b\d{1,2}\b)\s*(passengers?|people|pax|person|adults?)\b",
    re.IGNORECASE,
)

# Cabin: accepts a canonical cabin keyword.
CABIN_REGEX = re.compile(r"(economy|business|first|premium)", re.IGNORECASE)

# Options: maps "option 1" / "option 2" etc. back to the previous search list.
OPTION_REGEX = re.compile(r"option\s+(?P<idx>\d+)", re.IGNORECASE)



# Dialog manager class
class DialogManager:
    """Main controller for dialogue flow and state updates."""

    def __init__(self, clf):
        # Injected intent classifier
        self.clf = clf

        # Dialogue state stores origin, destination, dates, cabin, etc.
        self.state = DialogueState()

        # Flight index (loads flight data from flights.csv)
        self.flight_index = FlightIndex()
        self.flight_index.load()

        # Have we already shown options and now waiting for yes/no?
        self.awaiting_confirmation = False

        # Last search results (either a list of FlightOption or return combo dicts)
        self.lastSearchRes = []

        # This flag is used to comfirm whether the user intends to cancel the flight
        self.cancelComfirm = False



    # Utility: reset dialogue state after a finished / cancelled booking
 
    def reset(self) -> None:
        """Reset the dialogue state to initial values."""
        oldBooking = self.state.lastComfirmedBooking
        self.state = DialogueState()
        self.awaiting_confirmation = False
        self.state.lastComfirmedBooking = oldBooking
        self.cancelComfirm = False
  

    def handle(self, text: str) -> str:
        """Handle one user turn and return the bot's reply."""

        # Small talk  Early return avoids entering booking state when the user is just chatting.
        reply = small_talk(text)
        if reply:
            return reply

        # Name capture so we can greet the user later from memory.
        n = NAME_REGEX.search(text)
        if n:
            set_username(n.group("name"))
            return f"Nice to meet you, {get_username().title()}, how can I help you today?"

        # If we are waiting for a yes/no after showing an option
        if self.awaiting_confirmation:
            t = text.lower().strip()
            # Words that the user may use to comfirm their choice
            comfirmWords = {
                "yes",
                "confirm",
                "sure",
                "yeah",
                "yep",
                "correct",
                "absolutely",
                "please do",
                "go ahead",
                "book it"
            }
            # Words that user may use to reject their choice
            cancelWords = {
                "no",
                "cancel",
                "nevermind",
                "nope",
                "don't",
                "do not",
                "stop",
            }
            # If user wants to cancel their booking(cancel booking flag true)
            if self.cancelComfirm:
                # If user accepts cancellation
                if t in comfirmWords:
                    # Drops stored booking
                    self.state.lastComfirmedBooking = None
                    
                    self.reset()
                    return "Ok, your booking has succesfully been cancelled."
                
                # If user wants to change their mind and not cancel their booking
                if t in cancelWords:
                    # Set cancel flag and awaiting_comifmation flag back to false to remove us out of this state
                    self.cancelComfirm = False
                    self.awaiting_confirmation = False
                    return 'Ok, I will keep your booking as it is.'


            if t in comfirmWords:
                # Call method to store booking
                self.last_comfirmed_booking()
                # Booking confirmed – reset state
                self.reset()
                return "Great! Your flight has been booked. Safe travels!"

            elif t in cancelWords:
                # Booking cancelled – reset state
                self.reset()
                return "Ok, I will not proceed with the booking."
            

            # Still in confirmation mode, but user said something else
            return "Please answer with 'yes' to confirm or 'no' to cancel the booking."

        # Predict intent using trained classifier
        intent = self.clf.predict(text)

        # Simple intents (greet / function / name / FAQ / unknown)
        if intent == "greet":
            return "Hello! Nice to meet you, what is your name?"

        # Function to handle small talk and explain bot's capabilities
        elif intent == "function":
            return "I am able to greet you, have small talk with you, remember your name while also searching and booking flights for you!"

        # User wants to know thier name
        elif intent == "get_name":
            return f"Your name is {get_username().title()}"

        # User asks a simple FAQ question
        elif intent == "faq":
            lower = text.lower()
            # If user asks about cabin baggage
            if "baggage" in lower or "luggage" in lower:
                return (
                    "Most economy tickets include one cabin bag and one checked bag, "
                    "but exact allowances vary by airline."
                )
            # If user asks about ticket changes or refunds
            if any(word in lower for word in ["change", "refund", "cancel"]):
                return (
                    "Change and refund rules depend on the fare type. "
                    "Flexible tickets are usually easier to change or cancel."
                )
            # If user asks about other topics, return a generic response
            return (
                "Sorry, I can't help with that — I only answer simple travel questions like "
                "baggage or ticket changes."
            )
        
        # intent lies outside of domain of the bot
        elif intent == "unknown":
            return "Sorry I don't understand. Can you please try rephrasing?"
            

        # Flight related intents: update slots, then either search or ask next question
        elif intent in {
            "set_origin",
            "set_destination",
            "search_flights",
            "set_cabin",
            "set_passengers",
            "set_trip_type",
            "set_departure_date",
            "set_return_date",
        }:
            # Update dialogue state based on this user turn
            self.extractAndUpdates(text)


            # If we now have everything, go search immediately with no further
            # questioning.
            if self.state.readyToSearch():
                return self.runFlightSearch()

            # Otherwise ask for the next missing piece in a sensible order

            # 1) origin + destination
            if not self.state.origin and not self.state.destination:
                return "What is your city are you flying from and what city are you flying too?"

            #  trip type (one-way or return)
            if not self.state.tripType:
                return "Would that be a return trip or a single (one-way) flight?"

            #  number of passengers
            if not self.state.passengers:
                return "How many passengers are you booking for?"

            #cabin class
            if not self.state.cabin:
                return "What cabin would you like to travel in? (economy, premium, business, first)"

            # departure date
            if not self.state.leaveDate:
                return "When would you like to leave? Please give me a specific date."

            #return date (only if tripType is return)
            if self.state.tripType == "return" and not self.state.returnDate:
                return "And when would you like to come back?"

            # Fallback if something odd happens
            return "Please repeat your booking request so I can make sure I have all the details."
       

        # User chooses an option: “option 1”, “option 2”, etc.
        elif intent == "choose_option":
            return self.handle_choose_option(text)
        
        # User wants to edit a previous booking
        elif intent == "edit_booking":
            return self.handle_edit_booking()
        
        # User wants to cancel a previous booking
        elif intent == "cancel_booking":
            # Check if user is actually trying to cancel
            if not any(word in text.lower() for word in ['cancel', 'remove', 'delete']):
                return "So sorry, I didn't quite catch that, could you please rephrase what you need help with?"
            
            # If no previous booking exsists
            if not self.state.lastComfirmedBooking:
                return "There is no booking to cancel"
            
            # Set cancel confirmatiion flag to true
            self.cancelComfirm = True
            # Getting booking details to show user
            booking = self.state.lastComfirmedBooking

            # Build booking summary to show user
            summary = [
                f"Your booking is:\n"
                f"- {booking.get('tripType','one-way')} trip",
                f"- From {booking.get('origin','Unknown')} to {booking.get('destination','Unknown')}",
                f"- Leaving on {booking.get('leaveDate','an unknown date')}",
            ]

            # Add return date if applicable
            if booking.get("tripType") == "return" and booking.get("returnDate"):
                summary.append(f"- Returning on {booking['returnDate']}")
            
            summary.append(f"- {booking.get('passengers',1)} passenger(s)")
            summary.append(f"- Cabin: {booking.get('cabin','economy')}")
            summary.append("\nDo you want to cancel this booking? (yes/no)")

            # Set awaiting confirmation to true
            self.awaiting_confirmation = True
            # Prompt user to confirm cancelation
            return "\n".join(summary)
                      

        # Fallback for any unhandled intents
        return "I'm not sure how to help with that."
    

    
    # Function to decided whether string looks like a city and not a cabin
    def cleanCity(self, raw: str):
        if not raw:
            return None
        
        # Strip leading whitespaces
        c = raw.strip()
        if not c:
            return None
        
        # Rejects cabin related strings
        if CABIN_REGEX.search(c.lower()) or 'class' in c.lower():
            return None
        
        # Normalise formatting
        return c.title()
        
        

    # Slot extraction / updating from raw user text
    def extractAndUpdates(self, inptext: str) -> None:
        """Update the dialogue state with info found in the given text."""

        #  City extraction
        # Gets first match per turn; subsequent turns can overwrite
        # previous slots so the user can correct themselves.
        lower_text = inptext.lower()
        city_match = CITY_REGEX.search(inptext)
        if city_match:
            gd = city_match.groupdict()

            o = self.cleanCity(gd.get("o"))
            d = self.cleanCity(gd.get("d"))
            o2 = self.cleanCity(gd.get("o2"))
            d2 = self.cleanCity(gd.get("d2"))

            # Overwrites if extracted value looks like a city
            if o:
                self.state.origin = o
            if d:
                self.state.destination = d
            if o2:
                self.state.origin = o2
            if d2:
                self.state.destination = d2

        # Date extraction (uses DialogueState.parseDate) 
        # When editing a previous booking, allow new dates to overwrite the old ones.
        for date_match in DATE_REGEX.finditer(inptext):
            raw = date_match.group("date")
            date_str = self.state.parseDate(raw)
            if not date_str:
                continue

            # Special handling when editing an existing booking
            if getattr(self.state, "editPrev", False):
                span = date_match.span()
                before = lower_text[max(0, span[0] - 20): span[0]]

                # If text just before the date looks like a "back"/return phrase,
                # treat it as a new return date.
                if any(word in before for word in ["back", "return", "come back", "returning"]):
                    self.state.returnDate = date_str
                # If it looks like a "leave"/outbound phrase, treat as new departure date.
                elif any(word in before for word in ["leave", "leaving", "depart", "departure", "outbound"]):
                    self.state.leaveDate = date_str
                else:
                    # Fallback: if only one date is being changed, overwrite return first,
                    # otherwise overwrite leave date.
                    if self.state.tripType == "return":
                        self.state.returnDate = date_str
                    else:
                        self.state.leaveDate = date_str

            else:
                # Normal behaviour for fresh bookings
                if not self.state.leaveDate:
                    self.state.leaveDate = date_str
                elif self.state.tripType == "return" and not self.state.returnDate:
                    self.state.returnDate = date_str

        # Passengers extraction
        pass_match = PASSENGER_REGEX.search(inptext)
        if pass_match:
            try:
                self.state.passengers = max(1, int(pass_match.group("pax")))
            except ValueError:
                pass

        # Cabin type 
        cabin_match = CABIN_REGEX.search(inptext)
        if cabin_match:
            self.state.cabin = cabin_match.group(0).lower()

        # Trip type (one-way or return) 
        # Make the assignment explicit so that phrases like "one way" clear any
        # previous return date that might linger from an earlier search.  
        if any(
            phrase in lower_text
            for phrase in [
                "one way",
                "one-way",
                "single flight",
                "single ticket",
                "just one way",
            ]
        ):
            self.state.tripType = "one-way"
            # Ensure no accidentally use of a return date from a previous search
            self.state.returnDate = ""

        # Return trip phrases
        elif any(
            phrase in lower_text
            for phrase in [
                "return trip",
                "round trip",
                "round-trip",
                "return flight",
                "return ticket",
                "coming back",
                "back on",
            ]
        ):
            self.state.tripType = "return"


    # Internal helpers for searching flights

    def _search_leg(self, origin, destination, date, cabin):
        """Search one leg: try exact match first, then similar flights."""
        options = self.flight_index.search(origin, destination, date, cabin)
        used_similar = False

        if not options:
            # Fall back to similar flights if no exact match
            options = self.flight_index.search_similar(
                origin,
                destination,
                date,
                cabin,
                top_k=3,
            )
            # if we found any similar options
            if options:
                used_similar = True

        #  NORMALISE: unwrap  tuples if needed 
        if options and isinstance(options[0], tuple):
            
            # list to hold normalised flight options
            normalised = []

            for a,b in options:
                # whichever side looks like a FlightOption
                if hasattr(a, "origin"):
                    normalised.append(a)
    
                elif hasattr(b, "origin"):
                    normalised.append(b)
                else:
                    # neirther looks right so skip the pair
                    continue
            # assume shape 
            options = normalised
        #  Return found options and whether similar search was used
        return options, used_similar
    


    def runFlightSearch(self) -> str:
        """
        Perform either a one-way search or a return search,
        using the current dialogue state.
        """

        #  ONE–WAY SEARCH 
        if self.state.tripType != "return":
            # search for matching flights
            options, used_similar = self._search_leg(
                self.state.origin,
                self.state.destination,
                self.state.leaveDate,
                self.state.cabin,
            )
            # No options found
            if not options:
                return (
                    "I couldn't find any flights close to that request. "
                    "Try another date, origin/destination, or cabin?"
                )

            # Store options for later selections
            self.lastSearchRes = options

            # Build option lines (show at most 5)
            lines = []
            for i, opt in enumerate(options, start=1):
                lines.append(
                    f"{i}. {opt.origin} -> {opt.destination} "
                    f"{opt.date} {opt.time} with {opt.carrier}, "
                    f"{opt.cabin.title()} £{opt.price:.2f}"
                )
           
            # build summary of current search
            summary = realise_itinerary(self.state)

            # build intro text
            intro = "Here is your search summary:\n" f"{summary}\n"
            # if similar flights used
            if used_similar:
                intro += "I couldn't find an exact match, but here are some similar options:\n"
            else:
                intro += "I found these options:\n"

            # build final reply
            reply = (
                intro
                + "\n".join(lines)
                + "\n\nPlease choose an option (for example: 'option 1' or 'option 2')."
            )

            # Not yet awaiting confirmation – that happens after choose_option
            self.awaiting_confirmation = False
            return reply          
              
        # RETURN SEARCH (both legs)
        if self.state.tripType == "return":
            # Use FlightIndex to build sensible return-trip combinations
            combos, used_similar = self.flight_index.search_return_trips(
                self.state.origin,
                self.state.destination,
                self.state.leaveDate,
                self.state.returnDate,
                self.state.cabin,
                allow_similar=True,
            )
            # No commbos found
            if not combos:
                return (
                    "I couldn't find any flights for your return trip. "
                    "Try changing the dates, origin/destination, or cabin."
                )

            # Store all combos so the user can pick later
            self.lastSearchRes = combos

            # Not yet awaiting confirmation – that happens after choose_option
            self.awaiting_confirmation = False

            # Build the list text (show at most 5 options)
            summary = realise_itinerary(self.state)
            print(f"Passengers: {self.state.passengers}")

            # Build option lines with total price for all passengers
            lines = []
            # Iterate through top 5 combos
            for i, (out, back, base_price) in enumerate(combos[:5], start=1):
                total_price = base_price * self.state.passengers
                lines.append(
                    f"{i}. OUT: {out.origin} -> {out.destination} {out.date} {out.time} "
                    f"with {out.carrier}, {out.cabin.title()} £{out.price:.2f}; "
                    f"RETURN: {back.origin} -> {back.destination} {back.date} {back.time} "
                    f"with {back.carrier}, {back.cabin.title()} £{back.price:.2f}; "
                    f"Total for {self.state.passengers} passenger(s): £{total_price:.2f}"
                )
            # Build intro text 
            intro = (
                "Here is your search summary:\n"
                f"From {self.state.origin} to {self.state.destination}, "
                f"leaving on {self.state.leaveDate}, returning on {self.state.returnDate}, "
                f"in {self.state.cabin} class for {self.state.passengers} passenger(s)\n"
            )
            # if similar flights were used
            if used_similar:
                intro += (
                    "I couldn't find exact matches for one or both legs, "
                    "but here are some similar options:\n"
                )
            else:
                # exact matches found
                intro += "I found these options:\n"

            #build final reply
            reply = (
                intro
                + "\n".join(lines)
                + "\n\nPlease choose an option (for example: 'option 1' or 'option 2')."
            )
            return reply
        
    
    def handle_choose_option(self, text: str) -> str:
        """Handle user selecting 'option 1', 'option 2', etc."""
        if not self.lastSearchRes:
            return "There is no list of options to choose from yet. Try searching for flights first."

        # Extract option index from user input
        m_opt = OPTION_REGEX.search(text)
        if not m_opt:
            return "Please say which option you want, for example: 'option 1' or 'option 2'."

        # Convert user-facing numbering into list indices, guarding bounds.
        idx = int(m_opt.group("idx")) - 1  # 1-based -> 0-based

        # Check index validity
        if idx < 0 or idx >= len(self.lastSearchRes):
            return (
            f"I only have {len(self.lastSearchRes)} option(s). "
            f"Please choose between 1 and {len(self.lastSearchRes)}."
            )

        chosen = self.lastSearchRes[idx]

        # One-way: chosen is a single FlightOption
        # Return trip: chosen is (out: FlightOption, back: FlightOption, base_price: float)
        if isinstance(chosen, tuple) and len(chosen) == 3:
            # Return trip chosen
            out, back, base_price = chosen
            base_price = float(base_price)
            total_price = base_price * self.state.passengers

            # Build description of selected option
            desc = (
            "Selected return option:\n"
            f"OUT: {out.origin} -> {out.destination} {out.date} {out.time} "
            f"with {out.carrier}, {out.cabin.title()} £{out.price:.2f}\n"
            f"RETURN: {back.origin} -> {back.destination} {back.date} {back.time} "
            f"with {back.carrier}, {back.cabin.title()} £{back.price:.2f}"
            )
        else:
            # One-way chosen
            out = chosen
            base_price = float(out.price)
            total_price = base_price * self.state.passengers

            # Build description of selected option
            desc = (
            f"Top option: {out.origin} -> {out.destination} {out.date} {out.time} "
            f"with {out.carrier}, {out.cabin.title()} £{out.price:.2f}"
        )
        # Build booking summary and prompt for confirmation
        summary = realise_itinerary(self.state, price_text=f"Total = £{total_price:.2f}")

        # Awaiting a yes/no confirmation
        self.awaiting_confirmation = True
        # Prompt user to comfirm their choice
        return confirm_prompt(f"{desc}. {summary}")
    

    # Method handles editing a ready exsisting booking
    def handle_edit_booking(self) -> str:
        """Handle user editing a previously booked flight."""

        # If no booking is stored/ no previous booking tell the user and return
        if not self.state.lastComfirmedBooking:
            return (
                "There is no previous booking to edit. "
                "Let's start a new search. Where would you like to fly from, and where to?"
            )
        
       # Load previous booking into the live state
        booking = self.state.lastComfirmedBooking
        # Set current state to previous booking details
        self.state.origin = booking.get("origin", "")
        self.state.destination = booking.get("destination", "")
        self.state.leaveDate = booking.get("leaveDate", "")
        self.state.returnDate = booking.get("returnDate", "")
        self.state.tripType = booking.get("tripType", "")
        self.state.cabin = booking.get("cabin", "")
        self.state.passengers = booking.get("passengers", 1)

        # Set edit previous booking flag to true
        self.state.editPrev = True
    

        # Tell the user what we’re editing and ask for new details
        summary_parts = [
            f"from {self.state.origin} to {self.state.destination}",
            f"leaving on {self.state.leaveDate}" if self.state.leaveDate else "",
        ]
        # Add return date part if applicable
        if self.state.tripType == "return" and self.state.returnDate:
            summary_parts.append(f"returning on {self.state.returnDate}")
        summary = ", ".join(p for p in summary_parts if p)

        # Prompt user to provide new details
        return (
        "No problem, we'll modify your previous booking.\n"
        f"Your last booking was {summary} "
        f"in {self.state.cabin} class for {self.state.passengers} passenger(s).\n"
        "Tell me what you’d like to change – for example:\n"
        "e.g 'make it 3 people'\n"
        "e.g 'change to business class'\n"
        "e.g 'leave on 2025-12-20 instead'\n"
        "e.g 'book flight from Manchester to Doha'."
        )
    

    # Method stores comfirmed bookings
    def last_comfirmed_booking(self) -> None:
        self.state.lastComfirmedBooking = {
            "origin": self.state.origin,
            "destination": self.state.destination,
            "leaveDate": self.state.leaveDate,
            "returnDate": self.state.returnDate,
            "tripType": self.state.tripType,
            "cabin": self.state.cabin,
            "passengers": self.state.passengers,
            "options": self.lastSearchRes,       # last shown flights
        }