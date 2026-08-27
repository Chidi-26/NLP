import re
from dataclasses import dataclass, field
from typing import Optional


# This dataclass represents the state of the dialogue with the user
@dataclass
class DialogueState:
    # Booking details collected from the user

    origin: str = ""
    destination: str = ""
    cabin: str = ""
    tripType: str = ""
    passengers: int = 0
    leaveDate: str = ""
    returnDate: str = ""

    # Store the last confirmed booking details for potential edits
    lastComfirmedBooking: Optional[dict] = None
    # Flag to indicate if the user is editing a previous booking
    editPrev: bool = False
    



    def readyToSearch(self) -> bool:
        """Check if all necessary information is present to perform a flight search."""

        # Minimum requirement for one way search
        if not (self.origin and self.destination and self.leaveDate):
            return False
        # if return trip, ensure return date is also set
        if self.tripType == "return" and not self.returnDate:
            return False
        
        return True
    
    

    def parseDate(self,dateS: str) -> str:
        """Parse date string into standard format YYYY-MM-DD."""

        # Remove any trailing spaces
        dateS = dateS.strip()
        if not dateS:
            return ""

        # This is already in the desired format
        if re.match(r"^\d{4}-\d{2}-\d{2}$", dateS):
            return dateS
        


        return ""