from bot.state import DialogueState

# Convert the current DialogueState into a natural language summary.
def realise_itinerary(state: DialogueState, price_text: str = "") -> str:

    # Collect individual textual fragments of the summary.
    parts = []

    # Add origin → destination only if both are known.
    if state.origin and state.destination:
        parts.append(f"From {state.origin} to {state.destination}")
    
    # Add departure date when sspecified
    if state.leaveDate:
        parts.append(f"leaving on {state.leaveDate}")

    # For return trips also include inbound dates before adding
    if state.tripType == "return" and state.returnDate:
        parts.append(f"returning on {state.returnDate}")
    
    # Add cabin and passenger count (always included once we reach confirmation stage).
    parts.append(f"in {state.cabin} class for {state.passengers} passenger(s)")

    # Append pricing information if provided (useful in search results or confirmation).
    if price_text:
        parts.append(price_text)

   
    # Join all components into a single readable sentence.
    return ", ".join(parts)


def confirm_prompt(sumarry: str) -> str:
    """Generate a confirmation prompt for the user based on the itinerary summary."""

    return(f"Please confirm your booking with the following details: {sumarry}. Is this correct?")