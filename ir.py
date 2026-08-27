from dataclasses import dataclass
from typing import List, Tuple, Optional
import os, csv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from bot.preprocessing import normalise_text

# This dataclass is a simple container for one row of the flights.csv file.
# Storing each flight as a Python object (instead of a raw dict)
@dataclass
class FlightOption:
    origin: str
    destination: str
    date: str
    carrier: str
    cabin: str
    price: float
    time: str

# loads all rows from flights.csv into a list of FlightOption objects;
#   - supports exact search for one-way flights;
#   - supports a "similar" search when exact matches fail;
#   - supports building return-trip combinations (outbound + inbound).
class FlightIndex:

    def __init__(self, path: Optional[str] = None):
        """Initialises flight index"""
        self.path = path or os.path.join(os.path.dirname(__file__), "..", "data", "flights.csv")

        # Holds list of flight options objects  
        self.rows: List[FlightOption] = []

        # Load flight options from CSV file into memory
    def load(self) -> None:
        """Load flight options from CSV file into memory."""
        with open(self.path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Create FlightOption object and add to list
                    self.rows.append(
                        FlightOption(
                            origin=row["origin"].strip().title(),
                            destination=row["destination"].strip().title(),
                            date=row["date"].strip(),
                            carrier=row["carrier"].strip(),
                            cabin=row["cabin"].strip().lower(),
                            price=float(row["price"]),
                            time = row["time"].strip()
                        )
                    )
                except Exception as e:
                    continue
                
        
    # one way search method
    def search(self, origin: str, destination: str, date: str, cabin: str) -> List[FlightOption]:
        """Search for flight options matching the given criteria."""
        origin = (origin or "")
        destination = (destination or "").strip().title()
        date = (date or "").strip()
        cabin = (cabin or "economy").strip().lower()

        # Find all matching flight options
        matches: List[FlightOption] = []
        # Iterate through all flight options and apply filters
        for opt in self.rows:
            # Apply each filter; skip non-matching options
            if origin and opt.origin != origin:
                continue
            if destination and opt.destination != destination:
                continue
            if date and opt.date != date:
                continue
            if cabin and opt.cabin != cabin:
                continue
            # If all filters passed, add to matches
            matches.append(opt)

        # sort cheapest first
        matches.sort(key=lambda o: o.price)
        return matches
    
    #one way simular search (fallback)
    def search_similar(
        self,
        origin: str,
        destination: str,
        date: str,
        cabin: str,
        top_k: int = 3,
    ) -> list[FlightOption]:
        """Return up to top_k flights similar to the requested details.

        This is a softer search used when the strict search finds nothing.
        It prefers matching origin/destination, then date, then cabin.
        """
        o = (origin or "").strip().title()
        d = (destination or "").strip().title()
        date = (date or "").strip()
        cabin = (cabin or "economy").strip().lower()

        results: list[tuple[float, FlightOption]] = []

        for opt in self.rows:
            score = 0.0

            # Lock origin and destination
            if o and opt.origin != o:
                continue
            if d and opt.destination != d:
                continue

            # Date match helps, but is softer
            if date and opt.date == date:
                score += 1.0

            # Cabin match is even softer
            if cabin and opt.cabin.lower() == cabin:
                score += 0.5

            # Only keep flights that share at least something
            if score > 0:
                results.append((score, opt))

        # Highest score first, then cheapest
        results.sort(key=lambda x: (-x[0], x[1].price))

        # Return only the FlightOption objects
        return [opt for  opt in results[:top_k]]
    
    # Method Seatches return trips
    def search_return_trips(
        self,
        origin: str,
        destination: str,
        depart_date: str,
        return_date: str,
        cabin: str,
        allow_similar: bool = True,
    ) -> Tuple[List[Tuple[FlightOption, FlightOption, float]], bool]:
        """
        Search for return trip combinations:
            OUT:  origin -> destination   on depart_date
            BACK: destination -> origin   on return_date

        If no exact matches are found:
            - relax date & cabin,
            - BUT keep city-pair the same (NO Kenya, Paris, etc.)
        """
        origin = (origin or "").strip().title()
        destination = (destination or "").strip().title()
        depart_date = (depart_date or "").strip()
        return_date = (return_date or "").strip()
        cabin = (cabin or "economy").strip().lower()

        # empty list to hold (outbound, return, total_price) tuples
        combos = []

        # Exact outbound trip
        outbound_exact = [
            f for f in self.rows
            if f.origin == origin
            and f.destination == destination
            and f.date == depart_date
            and f.cabin == cabin
        ]

        # Exact return trip
        return_exact = [
            f for f in self.rows
            if f.origin == destination
            and f.destination == origin
            and f.date == return_date
            and f.cabin == cabin
        ]

        # Build all possible (outbound, return) combinations from the exact sets.
        for out in outbound_exact:
            for back in return_exact:
                combos.append((out, back, out.price + back.price))

        # If we found any exact match combos, return them sorted by total price.
        if combos:
            combos.sort(key=lambda x: x[2])
            return combos, False   # False = did NOT use similar

        # No exact results and we are not allowed to relax constraints.
        if not allow_similar:
            return [], False

        
        #  SIMILAR SEARCH (city pair fixed)

        out_similar = [
            # Find outbound flights with matching origin/destination
            f for f in self.rows
            if f.origin == origin and f.destination == destination
        ]
        # Find return flights with matching destination/origin
        back_similar = [
            f for f in self.rows
            if f.origin == destination and f.destination == origin
        ]
        # Build all possible (outbound, return) combinations from the similar sets.
        for out in out_similar:
            for back in back_similar:
                combos.append((out, back, out.price + back.price))

        
        # Sort by total combined price so the cheapest pair is first.
        combos.sort(key=lambda x: x[2])

        return combos, True  # True = used similar